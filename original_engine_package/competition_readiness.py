"""Generate a factual, machine-verifiable readiness record for live competition demos.

This module deliberately separates a runnable research prototype from clinical-use
readiness.  It never converts a missing model, checkpoint, or validation artifact
into a passing result.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import platform
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

import pandas as pd
import requests

from clinical_validation import ClinicalReadinessGate
from config_loader import load_yaml_config
from mapfm_ecosystem_repaired import EcosystemConfig, load_medical_dataset


PROJECT_ROOT = Path(__file__).resolve().parent
SCHEMA_VERSION = "mapfm.competition-readiness.v1"


def _sha256(path: Path) -> Optional[str]:
    if not path.is_file():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _git_state(project_root: Path) -> Dict[str, Any]:
    def run(*args: str) -> str:
        completed = subprocess.run(
            ["git", *args], cwd=project_root, capture_output=True, text=True,
            timeout=5, check=False,
        )
        return completed.stdout.strip() if completed.returncode == 0 else ""

    commit = run("rev-parse", "HEAD")
    status_lines = [line for line in run("status", "--porcelain").splitlines() if line]
    return {
        "repository_detected": bool(commit),
        "commit": commit or None,
        "dirty": bool(status_lines),
        "changed_path_count": len(status_lines),
        "note": "Uncommitted files must be packaged with the submission." if status_lines else "Tracked state is clean.",
    }


def _temporal_checkpoint_status(path_value: str) -> Dict[str, Any]:
    path = Path(path_value) if path_value else None
    status: Dict[str, Any] = {
        "configured": bool(path_value),
        "present": bool(path and path.is_file()),
        "metadata_valid": False,
        "ready": False,
    }
    if not status["present"]:
        return status
    try:
        import torch
        checkpoint = torch.load(str(path), map_location="cpu", weights_only=True)
        metadata = checkpoint.get("metadata", {}) if isinstance(checkpoint, dict) else {}
        status.update({
            "task": metadata.get("task"),
            "external_validation": bool(metadata.get("external_validation", False)),
            "calibrated": bool(metadata.get("calibrated", False)),
        })
        status["metadata_valid"] = status["task"] == "clinical_deterioration_risk"
        status["ready"] = bool(
            status["metadata_valid"]
            and status["external_validation"]
            and status["calibrated"]
        )
    except Exception as exc:
        status["error"] = f"{type(exc).__name__}: {exc}"
    return status


def _ollama_probe(config: EcosystemConfig, *, run_live_inference: bool) -> Dict[str, Any]:
    base_url = config.ollama_base_url.rstrip("/")
    probe: Dict[str, Any] = {
        "base_url": base_url,
        "reachable": False,
        "configured_model": config.ollama_model_name,
        "configured_model_installed": False,
        "configured_embedding_model": config.embedding_model_name,
        "configured_embedding_model_installed": False,
        "models": [],
        "live_inference": {"attempted": bool(run_live_inference), "passed": False},
    }
    try:
        version_response = requests.get(f"{base_url}/api/version", timeout=3)
        version_response.raise_for_status()
        tags_response = requests.get(f"{base_url}/api/tags", timeout=5)
        tags_response.raise_for_status()
        tags_payload = tags_response.json()
        models = []
        for item in tags_payload.get("models", []):
            models.append({
                "name": str(item.get("name") or item.get("model") or ""),
                "digest": item.get("digest"),
                "size_bytes": int(item.get("size", 0) or 0),
                "modified_at": item.get("modified_at"),
            })
        model_names = {item["name"] for item in models}
        probe.update({
            "reachable": True,
            "version": version_response.json().get("version"),
            "models": models,
            "configured_model_installed": config.ollama_model_name in model_names,
            "configured_embedding_model_installed": config.embedding_model_name in model_names,
        })
    except Exception as exc:
        probe["error"] = f"{type(exc).__name__}: {exc}"
        return probe

    if not run_live_inference or not probe["configured_model_installed"]:
        return probe

    nonce = hashlib.sha256(str(time.time_ns()).encode("ascii")).hexdigest()[:16]
    prompt = (
        "Return JSON only. Use exactly two string fields: status='ok' and "
        f"nonce='{nonce}'. Do not add any other text."
    )
    started = time.perf_counter()
    try:
        response = requests.post(
            f"{base_url}/api/chat",
            json={
                "model": config.ollama_model_name,
                "messages": [{"role": "user", "content": prompt}],
                "format": "json",
                "stream": False,
                "options": {"temperature": 0, "num_ctx": 512},
            },
            timeout=config.ollama_timeout_seconds,
        )
        response.raise_for_status()
        payload = response.json()
        raw_content = str((payload.get("message") or {}).get("content", ""))
        parsed = json.loads(raw_content)
        passed = (
            parsed.get("status") == "ok"
            and parsed.get("nonce") == nonce
            and bool(payload.get("done"))
        )
        probe["live_inference"] = {
            "attempted": True,
            "passed": passed,
            "wall_seconds": round(time.perf_counter() - started, 3),
            "served_model": payload.get("model"),
            "done_reason": payload.get("done_reason"),
            "total_duration_ns": int(payload.get("total_duration", 0) or 0),
            "eval_count": int(payload.get("eval_count", 0) or 0),
            "response_sha256": hashlib.sha256(raw_content.encode("utf-8")).hexdigest(),
            "nonce_verified": parsed.get("nonce") == nonce,
        }
    except Exception as exc:
        probe["live_inference"] = {
            "attempted": True,
            "passed": False,
            "wall_seconds": round(time.perf_counter() - started, 3),
            "error": f"{type(exc).__name__}: {exc}",
        }
    return probe


def build_competition_readiness_report(
    *,
    project_root: Path = PROJECT_ROOT,
    run_live_inference: bool = True,
    persist: bool = False,
    output_dir: Optional[Path] = None,
) -> Dict[str, Any]:
    """Inspect real local state and optionally persist a timestamped JSON artifact."""
    project_root = Path(project_root).resolve()
    config_path = project_root / "config.yaml"
    config = load_yaml_config(EcosystemConfig, config_path)
    dataset_path = project_root / "medNo.22.csv"

    dataset_info: Dict[str, Any] = {
        "present": dataset_path.is_file(),
        "filename": dataset_path.name,
        "sha256": _sha256(dataset_path),
        "source_rows": None,
        "source_classes": None,
        "configured_target_classes": int(config.target_classes),
        "runtime_rows": None,
        "runtime_classes": None,
        "runtime_labels": [],
        "class_scope_matches_config": False,
    }
    if dataset_path.is_file():
        try:
            data = pd.read_csv(dataset_path, usecols=lambda name: name in {"area"})
            dataset_info["source_rows"] = int(len(data))
            dataset_info["source_classes"] = int(data["area"].nunique()) if "area" in data else None
            runtime_data = load_medical_dataset(
                dataset_path,
                target_classes=config.target_classes,
                seed=config.random_seed,
            )
            dataset_info["runtime_rows"] = int(len(runtime_data))
            dataset_info["runtime_classes"] = int(runtime_data["area"].nunique())
            dataset_info["runtime_labels"] = sorted(runtime_data["area"].astype(str).unique().tolist())
            dataset_info["class_scope_matches_config"] = (
                dataset_info["runtime_classes"] == dataset_info["configured_target_classes"]
            )
        except Exception as exc:
            dataset_info["read_error"] = f"{type(exc).__name__}: {exc}"

    ollama_probe = _ollama_probe(config, run_live_inference=run_live_inference)
    validation_gate = ClinicalReadinessGate(
        validation_artifact=config.clinical_validation_artifact,
        require_validation=config.require_validation_for_approval,
    )
    external_validation_valid = validation_gate._artifact_is_valid()
    temporal_status = _temporal_checkpoint_status(config.temporal_checkpoint_path)

    code_hashes = {
        name: _sha256(project_root / name)
        for name in (
            "mapfm_ecosystem_repaired.py",
            "api.py",
            "clinical_validation.py",
            "evidence_ingestion.py",
            "config.yaml",
        )
    }
    code_hashes = {name: value for name, value in code_hashes.items() if value}

    demo_ready = all((
        dataset_info["present"],
        dataset_info["class_scope_matches_config"],
        ollama_probe["reachable"],
        ollama_probe["configured_model_installed"],
        ollama_probe["configured_embedding_model_installed"],
        (not run_live_inference) or ollama_probe["live_inference"]["passed"],
    ))
    clinical_use_ready = bool(
        external_validation_valid
        and ((not config.enable_tfa) or temporal_status["ready"])
    )

    report: Dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "competition_positioning": {
            "track": "科技发明制作B类",
            "group": "信息技术",
            "prototype_scope": "低投入、本地部署的医学科研决策支持原型",
        },
        "readiness": {
            "competition_demo_ready": demo_ready,
            "clinical_use_ready": clinical_use_ready,
            "status": "demo_ready_research_only" if demo_ready and not clinical_use_ready else (
                "clinical_validation_artifacts_present" if clinical_use_ready else "not_demo_ready"
            ),
        },
        "ollama": ollama_probe,
        "dataset": dataset_info,
        "validation": {
            "external_validation_artifact_valid": external_validation_valid,
            "temporal_checkpoint": temporal_status,
            "temporal_risk_estimation_enabled": bool(config.enable_tfa and temporal_status["ready"]),
            "consensus_forced_research_only_without_validation": bool(config.require_validation_for_approval),
        },
        "fallback_policy": {
            "statistical_dma_fallback_allowed": bool(config.allow_dma_legacy_fallback),
            "fallback_must_be_disclosed": True,
            "temporal_heuristic_probability_fallback": False,
        },
        "reproducibility": {
            "python": sys.version.split()[0],
            "platform": platform.platform(),
            "git": _git_state(project_root),
            "code_sha256": code_hashes,
        },
        "claim_boundary": [
            "现场报告仅证明本机模型、数据与软件链路可运行。",
            "内部数据和合成场景不能替代独立外部临床验证。",
            "模型自报confidence不是临床校准概率。",
            "合同或感谢材料仅证明合作/使用场景，不证明临床疗效。",
        ],
    }

    if persist:
        destination = Path(output_dir or project_root / "artifacts" / "competition")
        destination.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        timestamped = destination / f"competition_readiness_{stamp}.json"
        latest = destination / "competition_readiness_latest.json"
        serialized = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True)
        timestamped.write_text(serialized, encoding="utf-8")
        latest.write_text(serialized, encoding="utf-8")
        report["artifact_paths"] = {
            "timestamped": str(timestamped),
            "latest": str(latest),
        }
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate a factual MAPFM competition-readiness report")
    parser.add_argument("--no-live", action="store_true", help="Skip the live Ollama generation proof")
    parser.add_argument("--no-persist", action="store_true", help="Print only; do not write an artifact")
    parser.add_argument("--output-dir", type=Path, default=None)
    args = parser.parse_args()
    report = build_competition_readiness_report(
        run_live_inference=not args.no_live,
        persist=not args.no_persist,
        output_dir=args.output_dir,
    )
    print(json.dumps(report, ensure_ascii=False, indent=2, default=str))
    return 0 if report["readiness"]["competition_demo_ready"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
