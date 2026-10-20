#!/usr/bin/env python3
"""Run one synthetic case through the real local engine and print safe diagnostics.

This is an on-demand pre-demo check, not part of the fast unit-test suite.
No patient text or raw model output is printed or saved.
"""

from __future__ import annotations

import argparse
from contextlib import redirect_stdout
from datetime import datetime, timezone
from io import StringIO
import json
from pathlib import Path

from careguard_cases import SAMPLE_CASES, clinical_text_for_case
from careguard_presenter import build_audit_report, build_screening_view
from config_loader import load_yaml_config
from mapfm_ecosystem_repaired import (
    EcosystemConfig,
    HeterogeneousMultiAgentEcosystem,
    load_medical_dataset,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="CareGuard synthetic live-pipeline check")
    parser.add_argument("--case", choices=list(SAMPLE_CASES), default="夜间突发胸痛")
    parser.add_argument("--require-ollama", action="store_true")
    parser.add_argument("--no-persist", action="store_true", help="Do not update the local evidence-board snapshot")
    args = parser.parse_args()

    root = Path(__file__).resolve().parent
    config = load_yaml_config(EcosystemConfig, root / "config.yaml")
    dataset = load_medical_dataset(root / "medNo.22.csv", target_classes=config.target_classes, seed=config.random_seed)
    ecosystem = HeterogeneousMultiAgentEcosystem(
        config=config, dataset=dataset, base_model=config.ollama_model_name, verbose=False
    )
    case = SAMPLE_CASES[args.case]
    with redirect_stdout(StringIO()):
        raw = ecosystem.run_collaborative_task(
            patient_query=case["note"],
            multimodal_input={"clinical_text": clinical_text_for_case(case)},
            force_high_risk=case["force_high_risk"],
        )
    view = build_screening_view(raw)
    audit = build_audit_report(raw, view)
    integrity = raw.get("execution_integrity") or {}
    summary = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "case": args.case,
        "request_id": view["request_id"],
        "priority": view["priority"]["code"],
        "clue": view["candidate_risk_domain"],
        "ollama_model": integrity.get("configured_ollama_model"),
        "dma_backend": integrity.get("dma_backend"),
        "ollama_generation_verified": bool(integrity.get("ollama_generation_verified")),
        "fallback_used": bool(integrity.get("dma_fallback_used")),
        "dynamic_evidence_count": view["evidence_count"],
        "offline_reference_count": view["reference_count"],
        "human_review_required": view["requires_human_review"],
        "clinical_use_allowed": view["raw_clinical_use_allowed"],
        "latency_seconds": view["runtime_seconds"],
        "audit_contains_input_text": case["note"] in json.dumps(audit, ensure_ascii=False),
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    if not args.no_persist:
        destination = root / "artifacts" / "competition" / "careguard_live_smoke_latest.json"
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary = destination.with_suffix(".tmp")
        temporary.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
        temporary.replace(destination)
    if summary["audit_contains_input_text"] or not summary["human_review_required"]:
        return 3
    if args.require_ollama and (summary["fallback_used"] or not summary["ollama_generation_verified"]):
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
