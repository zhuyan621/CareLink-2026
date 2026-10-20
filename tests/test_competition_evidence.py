from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest
from pydantic import ValidationError

import competition_readiness as readiness_module
from api import QueryRequest
from mapfm_ecosystem_repaired import DecisionMakingAgent, EcosystemConfig, load_medical_dataset
import utils as embedding_utils


def test_public_api_rejects_ground_truth_label() -> None:
    with pytest.raises(ValidationError):
        QueryRequest(patient_query="demo", true_label="Asthma")


def test_model_self_score_does_not_create_fake_probability_distribution() -> None:
    dma = DecisionMakingAgent(EcosystemConfig())
    dma.fit(load_medical_dataset(None, target_classes=3, seed=42))
    label = dma.labels[0]
    normalized = dma._normalize_structured_output({"prediction": label, "confidence": 0.73})
    assert normalized["prediction"] == label
    assert normalized["confidence"] == 0.73
    assert normalized["probabilities"] == {}
    assert normalized["probabilities_source"] == "not_provided"


def test_embedding_fallback_is_disclosed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(embedding_utils, "_ollama_embed_batch", lambda *args, **kwargs: None)
    vector = embedding_utils.semantic_embedding.__wrapped__(
        "demo", dim=16, model_name="nomic-embed-text:latest"
    )
    status = embedding_utils.get_embedding_runtime_status()
    assert vector.shape == (16,)
    assert status["backend"] == "legacy_hash"
    assert status["fallback_used"] is True


def test_readiness_report_separates_demo_from_clinical_use(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "config.yaml").write_text(
        "ollama_model_name: llama3:8b\n"
        "target_classes: 2\n"
        "temporal_checkpoint_path: ''\n"
        "clinical_validation_artifact: ''\n",
        encoding="utf-8",
    )
    pd.DataFrame([
        {"question": "q1", "answer": "a1", "area": "A"},
        {"question": "q2", "answer": "a2", "area": "B"},
    ]).to_csv(tmp_path / "medNo.22.csv", index=False)
    monkeypatch.setattr(
        readiness_module,
        "_ollama_probe",
        lambda config, run_live_inference: {
            "reachable": True,
            "configured_model": config.ollama_model_name,
            "configured_model_installed": True,
            "configured_embedding_model": config.embedding_model_name,
            "configured_embedding_model_installed": True,
            "models": [{"name": config.ollama_model_name}],
            "live_inference": {"attempted": True, "passed": True},
        },
    )
    report = readiness_module.build_competition_readiness_report(
        project_root=tmp_path, run_live_inference=True, persist=False,
    )
    assert report["readiness"]["competition_demo_ready"] is True
    assert report["readiness"]["clinical_use_ready"] is False
    assert report["readiness"]["status"] == "demo_ready_research_only"
    assert report["dataset"]["source_rows"] == 2
    assert report["dataset"]["runtime_rows"] == 2
