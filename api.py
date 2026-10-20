"""FastAPI entrypoint for the MAPFM medical AI ecosystem.

Supports multimodal input: CSV (vital signs, lab results), TXT (clinical text),
JPG/PNG (medical images).
"""

from __future__ import annotations

import asyncio
import csv
import hashlib
import json
import re
import shutil
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, ConfigDict, Field

PROJECT_ROOT = Path(__file__).resolve().parent
try:
    from dotenv import load_dotenv
    load_dotenv(PROJECT_ROOT / ".env", override=False)
except ImportError:
    pass

from mapfm_ecosystem_repaired import EcosystemConfig, HeterogeneousMultiAgentEcosystem, load_medical_dataset
from config_loader import load_yaml_config
from mapfm_utils.multimodal_utils import MultimodalPreprocessor
from competition_readiness import build_competition_readiness_report
from careguard_presenter import build_audit_report, build_screening_view
from diabetes_risk import DiabetesRiskInput, ExistingDiabetesEvaluation
from mapfm_chronic_extension import (
    agent_status as chronic_agent_status, attach_to_ecosystem, capabilities as chronic_capabilities,
    predict_diabetes_onset,
)
from chronic_dataset_gate import audit_local_sources
from mapfm_prospective_neural import CohortRejected, attach_to_tfa, neural_status
from medquad_qa import ask as ask_medquad, status as medquad_status
from medical_language import parse_medical_prompt

app = FastAPI(
    title="CareLink Multi-Agent Screening API",
    description=(
        "Competition and research prototype for care-risk screening, evidence tracing, "
        "and human review. It does not provide an autonomous clinical diagnosis."
    ),
    version="3.0.0",
)
MAX_UPLOAD_BYTES = 20 * 1024 * 1024

_ecosystem: Optional[HeterogeneousMultiAgentEcosystem] = None

# SHA-256 of the team's original desktop code package, checked on 2026-10-11.
# Equality proves source provenance only; it is not a clinical validation claim.
ORIGINAL_ENGINE_HASHES = {
    "mapfm_ecosystem_repaired.py": "99a51b18bdb7e1b806e73af0ef7b3252734106e6accfd83b89cdb0043effa529",
    "mapfm_utils/multimodal_utils.py": "36e6ab0bef79593d8cfa4f281731a313b17c5a78d3af3a3d06251712afdbea02",
    "config.yaml": "3263a85f2417ebe3c69112fde7637eacf96a7806564c4b66182ff5114e883874",
    "medNo.22.csv": "00474d427edd5e93ed96424923ad4e8b66d91bc451ee25e653c1a050bd36384e",
}


def _source_fingerprints() -> Dict[str, Dict[str, Any]]:
    fingerprints: Dict[str, Dict[str, Any]] = {}
    for name, expected in ORIGINAL_ENGINE_HASHES.items():
        digest = hashlib.sha256((PROJECT_ROOT / name).read_bytes()).hexdigest()
        fingerprints[name] = {"sha256": digest, "matches_original_package": digest == expected}
    return fingerprints


def _get_ecosystem() -> HeterogeneousMultiAgentEcosystem:
    """Lazy-initialize the ecosystem on first request so import never crashes."""
    global _ecosystem
    if _ecosystem is not None:
        return _ecosystem
    config = load_yaml_config(EcosystemConfig, PROJECT_ROOT / "config.yaml")
    csv_path = PROJECT_ROOT / "medNo.22.csv"
    dataset = load_medical_dataset(
        csv_path if csv_path.exists() else None,
        target_classes=config.target_classes,
        seed=config.random_seed,
    )
    _ecosystem = HeterogeneousMultiAgentEcosystem(
        config=config, dataset=dataset, base_model=config.ollama_model_name, verbose=False,
    )
    attach_to_ecosystem(_ecosystem)
    attach_to_tfa(_ecosystem)
    return _ecosystem


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------

class QueryRequest(BaseModel):
    """Single diagnosis request (text-only or with pre-processed multimodal input)."""

    model_config = ConfigDict(extra="forbid")
    patient_query: str = Field(..., min_length=1)
    multimodal_input: Optional[Dict[str, Any]] = None
    force_high_risk: bool = False


class ProspectiveNeuralRequest(BaseModel):
    """Research-only baseline values; no patient identifier is accepted."""

    model_config = ConfigDict(extra="forbid")
    task: str
    baseline_values: Dict[str, float]


class BatchRequest(BaseModel):
    """Batch diagnosis request for thread-pooled concurrent execution."""

    model_config = ConfigDict(extra="forbid")
    requests: List[QueryRequest] = Field(..., min_length=1, max_length=32)


class ManualObservation(BaseModel):
    """One measurement set, not an inferred time series or patient diagnosis."""

    model_config = ConfigDict(extra="forbid")
    heart_rate: float = Field(..., ge=20, le=250)
    spo2: float = Field(..., ge=50, le=100)
    temperature: float = Field(..., ge=33, le=44)
    respiratory_rate: float = Field(..., ge=2, le=80)


class EngineeringScreeningRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    patient_query: str = Field(..., min_length=1, max_length=4000)
    observation: ManualObservation
    force_high_risk: bool = False


class DiabetesRiskRequest(BaseModel):
    """Baseline measurements for the published 8-year incident-diabetes score."""

    model_config = ConfigDict(extra="forbid")
    known_diabetes: bool
    sex: str = Field(..., pattern="^(male|female)$")
    bmi: float = Field(..., ge=15, le=55)
    systolic_bp: float = Field(..., ge=70, le=250)
    diastolic_bp: float = Field(..., ge=40, le=150)
    fasting_glucose_mmol_l: float = Field(..., ge=2.5, le=30)
    hdl_mmol_l: float = Field(..., ge=0.2, le=4)
    triglycerides_mmol_l: float = Field(..., ge=0.2, le=20)
    parental_diabetes: bool
    bp_medication: bool


class MedquadQuestionRequest(BaseModel):
    """Non-patient English health-information question."""

    model_config = ConfigDict(extra="forbid")
    question: str = Field(..., min_length=5, max_length=500)
    top_k: int = Field(3, ge=1, le=5)


class MedicalLanguageRequest(BaseModel):
    """One de-identified natural-language research question."""

    model_config = ConfigDict(extra="forbid")
    question: str = Field(..., min_length=5, max_length=1500)


# ---------------------------------------------------------------------------
# Standard endpoints
# ---------------------------------------------------------------------------

@app.get("/health")
def health() -> Dict[str, Any]:
    """Return API health status (does not force ecosystem init)."""
    if _ecosystem is not None:
        return {"status": "ok", "document_count": _ecosystem.online_kb.get_stats()["document_count"]}
    return {"status": "ready", "detail": "Ecosystem not initialized — first request will trigger warm-up."}


@app.get("/engineering/status")
def engineering_status() -> Dict[str, Any]:
    """Expose verifiable code-package provenance without implying live inference."""
    fingerprints = _source_fingerprints()
    return {
        "source_package": "MAPFM_medical_AI_repaired_complete",
        "runtime": "CareLink_2026",
        "core_source_match": all(item["matches_original_package"] for item in fingerprints.values()),
        "files": fingerprints,
        "ecosystem_initialized": _ecosystem is not None,
        "note": "Source equality and process initialization are not a model-generation or clinical-validity test.",
    }


@app.get("/competition/readiness")
def competition_readiness() -> Dict[str, Any]:
    """Return a read-only readiness snapshot without running a generation."""
    return build_competition_readiness_report(
        project_root=PROJECT_ROOT, run_live_inference=False, persist=False,
    )


@app.post("/competition/readiness/live")
def competition_readiness_live() -> Dict[str, Any]:
    """Run a non-clinical nonce challenge against the configured local model."""
    return build_competition_readiness_report(
        project_root=PROJECT_ROOT, run_live_inference=True, persist=False,
    )


@app.post("/diagnose")
def diagnose(request: QueryRequest) -> Dict[str, Any]:
    """Run a single multi-agent diagnosis request (text + optional multimodal dict)."""
    return _get_ecosystem().run_collaborative_task(**request.model_dump())


@app.post("/screening")
def screening(request: QueryRequest) -> Dict[str, Any]:
    """Return the competition-safe screening view and a pending review record.

    The legacy ``/diagnose`` route remains for compatibility. New product clients
    should use this route because it preserves uncertainty and never promotes an
    unvalidated temporal placeholder to a low-risk result.
    """
    raw = _get_ecosystem().run_collaborative_task(**request.model_dump())
    view = build_screening_view(raw)
    return {
        "screening": view,
        "audit": build_audit_report(raw, view),
    }


@app.post("/screening/engineering")
def screening_engineering(request: EngineeringScreeningRequest) -> Dict[str, Any]:
    """Parse the submitted numbers with original MAPFM code, then run its engine.

    A single observation is represented as text for the active model input. It is
    deliberately not promoted to a longitudinal time series or temporal prediction.
    The generated CSV is temporary and never returned or persisted as a case file.
    """
    with tempfile.TemporaryDirectory(prefix="careguard_observation_") as temp_dir:
        csv_path = Path(temp_dir) / "single_observation.csv"
        with csv_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow(("timestamp", "heart_rate", "spo2", "temperature", "respiratory_rate"))
            writer.writerow((
                datetime.now(timezone.utc).isoformat(),
                request.observation.heart_rate,
                request.observation.spo2,
                request.observation.temperature,
                request.observation.respiratory_rate,
            ))
        data = MultimodalPreprocessor(temp_dir=temp_dir).process(vital_signs_csv=str(csv_path))
        if data.metadata.get("vital_signs_error") or len(data.vital_signs) != 1:
            raise HTTPException(status_code=422, detail="The original MAPFM preprocessor could not parse this observation")
        parsed = data.vital_signs[0]
        observation_text = (
            f"单次生命体征（由原工程 CSV 预处理解析）：心率 {parsed.heart_rate:g} 次/分，"
            f"血氧 {parsed.spo2:g}%，体温 {parsed.temperature:g}℃，"
            f"呼吸 {parsed.respiratory_rate:g} 次/分。"
        )
        raw = _get_ecosystem().run_collaborative_task(
            patient_query=request.patient_query,
            multimodal_input={"clinical_text": observation_text},
            force_high_risk=request.force_high_risk,
        )
    view = build_screening_view(raw)
    integrity = raw.get("execution_integrity") or {}
    fingerprints = _source_fingerprints()
    return {
        "screening": view,
        "audit": build_audit_report(raw, view),
        "engineering": {
            "path": "manual input → original MAPFM CSV preprocessor → MAPFM collaborative engine → CareLink safe presenter",
            "parsed_observation_count": 1,
            "parsed_observation": {
                "heart_rate": parsed.heart_rate,
                "spo2": parsed.spo2,
                "temperature": parsed.temperature,
                "respiratory_rate": parsed.respiratory_rate,
            },
            "active_model_input": "clinical_text_from_parsed_single_observation",
            "model_input_modalities": raw.get("model_input_modalities") or {},
            "core_source_match": all(item["matches_original_package"] for item in fingerprints.values()),
            "core_sha256": fingerprints["mapfm_ecosystem_repaired.py"]["sha256"],
            "preprocessor_sha256": fingerprints["mapfm_utils/multimodal_utils.py"]["sha256"],
            "dma_backend": integrity.get("dma_backend") or "unknown",
            "ollama_generation_verified": bool(integrity.get("ollama_generation_verified")),
            "temporal_prediction_used": False,
            "clinical_use_allowed": False,
        },
    }


@app.post("/risk/diabetes-8y")
def diabetes_8y_risk(request: DiabetesRiskRequest) -> Dict[str, Any]:
    """Calculate a source-auditable future diabetes score from live form values."""
    try:
        return predict_diabetes_onset(DiabetesRiskInput(**request.model_dump()))
    except ExistingDiabetesEvaluation as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.get("/mapfm/medquad-qa/status")
def mapfm_medquad_qa_status() -> Dict[str, Any]:
    """Disclose full-source accounting and fitted retrieval readiness."""
    return medquad_status()


@app.post("/mapfm/medquad-qa/ask")
def mapfm_medquad_qa_ask(request: MedquadQuestionRequest) -> Dict[str, Any]:
    """Retrieve attributed source answers; never generate a diagnosis."""
    if not medquad_status()["ready"]:
        raise HTTPException(status_code=503, detail="MedQuAD model is not verified on this installation")
    try:
        return ask_medquad(request.question, top_k=request.top_k)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post("/mapfm/medical-language/evaluate")
def mapfm_medical_language_evaluate(request: MedicalLanguageRequest) -> Dict[str, Any]:
    """Route free text without pretending general QA is a calibrated prognosis.

    Only a complete, explicit baseline can reach the existing MAPFM TFA
    three-year diabetes research head. Other questions never receive a risk.
    """
    if re.search(r"(?<!\d)1[3-9]\d{9}(?!\d)|[\w.+-]+@[\w.-]+\.[a-zA-Z]{2,}", request.question):
        raise HTTPException(status_code=422, detail="请先删除电话、邮箱等个人标识；本入口仅使用合成或充分脱敏输入。")
    parsed = parse_medical_prompt(request.question)
    if parsed["kind"] == "source_qa":
        if not medquad_status()["ready"]:
            return {"kind": "source_qa_unavailable", "message": "本机 MedQuAD 检索模型尚未通过完整性核验；不生成答案或概率。"}
        try:
            answer = ask_medquad(request.question, top_k=3)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        return parsed | {"qa": answer, "probability_available": False}
    if parsed["kind"] != "diabetes_3y_ready":
        return parsed | {"probability_available": False}
    if "diabetes_onset" not in neural_status(PROJECT_ROOT)["trained_tasks"]:
        return {"kind": "model_unavailable", "message": "本机没有通过校验的未来糖尿病研究权重，不输出概率。",
                "extracted": parsed["extracted"], "probability_available": False}
    try:
        estimate = _get_ecosystem().tfa.forecast_prospective(
            "diabetes_onset", parsed["extracted"], root=PROJECT_ROOT)
    except CohortRejected as exc:
        return {"kind": "model_rejected", "message": str(exc), "extracted": parsed["extracted"],
                "probability_available": False}
    return {"kind": "diabetes_3y_result", "message": "未来 3 年新发糖尿病内部研究估计；未经外部临床验证。",
            "extracted": parsed["extracted"], "estimate": estimate | {
                "execution_path": "original_mapfm_tfa.forecast_prospective"},
            "probability_available": True}


@app.get("/mapfm/chronic-risk/capabilities")
def mapfm_chronic_capabilities() -> Dict[str, Any]:
    """Describe the active future-diabetes pathway only."""
    return chronic_capabilities()


@app.get("/mapfm/chronic-risk/agent-status")
def mapfm_chronic_agent_status() -> Dict[str, Any]:
    """Non-identifying execution state of the registered rule adapter."""
    return {"agent": chronic_agent_status(), "core_initialized": _ecosystem is not None,
            "registered_in_core": bool(_ecosystem and "ChronicRiskRules" in _ecosystem.maintenance_agent.registered_agents),
            "original_mapfm_model_used_for_chronic_probability": False}


@app.get("/mapfm/chronic-risk/data-readiness")
def mapfm_chronic_data_readiness() -> Dict[str, Any]:
    """Read-only aggregate audit; never returns patient or image content."""
    return audit_local_sources(PROJECT_ROOT)


@app.get("/mapfm/prospective-neural/status")
def mapfm_prospective_neural_status() -> Dict[str, Any]:
    """Disclose actual learned-weight state, independent of published rules."""
    return neural_status(PROJECT_ROOT) | {
        "tfa_attached_to_running_core": bool(
            _ecosystem and callable(getattr(_ecosystem.tfa, "prospective_neural_status", None))
        ),
    }


@app.post("/mapfm/prospective-neural/research-predict")
def mapfm_prospective_neural_research_predict(request: ProspectiveNeuralRequest) -> Dict[str, Any]:
    """Run actual TFA neural weights only after governed longitudinal training."""
    if request.task not in neural_status(PROJECT_ROOT)["trained_tasks"]:
        raise HTTPException(status_code=503, detail="该结局尚无真实随访数据训练的 MAPFM 神经权重。")
    try:
        # Run through the live original MAPFM TFA object, whose research
        # extension is attached during ecosystem initialization.
        estimate = _get_ecosystem().tfa.forecast_prospective(
            request.task, request.baseline_values, root=PROJECT_ROOT)
        return estimate | {"execution_path": "original_mapfm_tfa.forecast_prospective"}
    except CohortRejected as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post("/diagnose/batch")
def diagnose_batch(request: BatchRequest) -> List[Dict[str, Any]]:
    """Run concurrent diagnosis requests without changing single-task logic."""
    return _get_ecosystem().run_concurrent_tasks([item.model_dump() for item in request.requests])


# ---------------------------------------------------------------------------
# Multimodal data upload endpoints
# ---------------------------------------------------------------------------

@app.post("/diagnose/multimodal")
async def diagnose_multimodal(
    patient_query: str = Form(..., min_length=1),
    force_high_risk: bool = Form(False),
    vital_signs_csv: Optional[UploadFile] = File(None),
    lab_results_csv: Optional[UploadFile] = File(None),
    clinical_text_txt: Optional[UploadFile] = File(None),
    medical_images: Optional[List[UploadFile]] = File(None),
) -> Dict[str, Any]:
    """Full multimodal diagnosis with file uploads.

    Accepts up to 4 modalities simultaneously:
      - vital_signs_csv:   CSV with timestamp, HR, BP, Temp, RR, SpO2
      - lab_results_csv:   CSV with timestamp, test_name, value, unit, ref_range
      - clinical_text_txt: TXT with clinical notes
      - medical_images:    JPG/PNG medical images (up to 5)
    """
    temp_dir = tempfile.mkdtemp(prefix="mapfm_api_")
    patient_data = None

    try:
        # Save uploaded files to temp directory
        vital_path = await _save_upload(vital_signs_csv, temp_dir)
        lab_path = await _save_upload(lab_results_csv, temp_dir)
        text_path = await _save_upload(clinical_text_txt, temp_dir)
        image_paths = await _save_uploads(medical_images, temp_dir, max_count=5)

        # Preprocess multimodal data
        preprocessor = MultimodalPreprocessor(temp_dir=temp_dir)
        patient_data = preprocessor.process(
            vital_signs_csv=vital_path,
            lab_results_csv=lab_path,
            clinical_text_txt=text_path,
            image_paths=image_paths,
        )

        # Build multimodal_input dict for the ecosystem
        multimodal_input: Dict[str, Any] = {}
        if patient_data.has_vital_signs():
            multimodal_input["time_series"] = patient_data.vital_signs_time_series().tolist()
            multimodal_input["vital_signs_count"] = len(patient_data.vital_signs)
        if patient_data.has_lab_results():
            multimodal_input["lab_results"] = [
                {"test": r.test_name, "value": r.value, "unit": r.unit,
                 "abnormal": r.abnormal}
                for r in patient_data.lab_results
            ]
        if patient_data.has_clinical_texts():
            multimodal_input["clinical_text"] = " ".join(
                t.content for t in patient_data.clinical_texts
            )[:2000]
        if patient_data.has_medical_images():
            multimodal_input["images"] = [
                {"path": img.file_path, "modality": img.modality, "body_part": img.body_part}
                for img in patient_data.medical_images
            ]
            multimodal_input["image_count"] = len(patient_data.medical_images)
            multimodal_input["image_modalities"] = [
                img.modality for img in patient_data.medical_images
            ]

        # Set clinical signals from vital signs
        if patient_data.has_vital_signs():
            vs_arr = patient_data.vital_signs_array()
            if vs_arr.size > 0:
                multimodal_input["posture_instability"] = float(
                    vs_arr[-1, 0] / 100.0 if not np.isnan(vs_arr[-1, 0]) else 0.5
                )

        # Run through ecosystem (non-blocking via asyncio.to_thread)
        # === FIX: 同步 Ollama 调用放入线程池，避免阻塞事件循环 ===
        result = await asyncio.to_thread(
            _get_ecosystem().run_collaborative_task,
            patient_query=patient_query,
            multimodal_input=multimodal_input if multimodal_input else None,
            force_high_risk=force_high_risk,
        )

        # Attach patient data metadata
        result["multimodal_meta"] = {
            "vital_signs_count": len(patient_data.vital_signs),
            "lab_results_count": len(patient_data.lab_results),
            "clinical_text_count": len(patient_data.clinical_texts),
            "medical_image_count": len(patient_data.medical_images),
            "preprocessing_errors": patient_data.metadata,
        }

        return result

    finally:
        if patient_data is not None:
            patient_data.cleanup_temp_dir()
        shutil.rmtree(temp_dir, ignore_errors=True)


@app.post("/diagnose/multimodal/simple")
async def diagnose_multimodal_simple(
    patient_query: str = Form(..., min_length=1),
    vital_signs_csv: Optional[UploadFile] = File(None),
    lab_results_csv: Optional[UploadFile] = File(None),
    clinical_text_txt: Optional[UploadFile] = File(None),
) -> Dict[str, Any]:
    """Simplified multimodal diagnosis endpoint (no images).

    For quick CSV/TXT clinical data uploads without complex multipart setup.
    """
    return await diagnose_multimodal(
        patient_query=patient_query,
        vital_signs_csv=vital_signs_csv,
        lab_results_csv=lab_results_csv,
        clinical_text_txt=clinical_text_txt,
    )


@app.get("/system/health")
def system_health() -> Dict[str, Any]:
    """Return detailed system health including degradation status."""
    from mapfm_utils.system_monitor import get_system_monitor

    config = load_yaml_config(EcosystemConfig, PROJECT_ROOT / "config.yaml")
    monitor = get_system_monitor(
        ollama_base_url=config.ollama_base_url,
        medtsllm_model_dir=config.temporal_checkpoint_path,
    )
    health = monitor.check()
    return {
        "ollama_healthy": health.ollama_healthy,
        "medtsllm_loaded": health.medtsllm_loaded,
        "gpu_available": health.gpu_available,
        "gpu_memory_ratio": health.gpu_memory_ratio,
        "memory_ratio": health.memory_ratio,
        "degradation_level": health.degradation_level.name,
        "degradation_reason": health.degradation_reason,
        "user_message": monitor.get_user_message(),
        "history": monitor.get_history(limit=10),
    }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _save_upload(upload: Optional[UploadFile], dest_dir: str) -> Optional[str]:
    """Save a single uploaded file to dest_dir. Returns path or None."""
    if upload is None or upload.filename is None:
        return None
    safe_name = f"{uuid.uuid4().hex[:8]}_{Path(upload.filename).name}"
    dest = str(Path(dest_dir) / safe_name)
    content = await upload.read(MAX_UPLOAD_BYTES + 1)
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="Uploaded file exceeds the 20 MiB limit")
    with open(dest, "wb") as fh:
        fh.write(content)
    return dest


async def _save_uploads(
    uploads: Optional[List[UploadFile]], dest_dir: str, max_count: int = 5
) -> List[str]:
    """Save multiple uploaded files. Returns list of paths."""
    if not uploads:
        return []
    paths: List[str] = []
    for upload in uploads[:max_count]:
        path = await _save_upload(upload, dest_dir)
        if path:
            paths.append(path)
    return paths


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
