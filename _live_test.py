#!/usr/bin/env python3
"""Live end-to-end proof: run one synthetic competition case against real Ollama.

Mirrors dashboard.py's ecosystem bootstrap, then calls run_collaborative_task()
with a realistic chief complaint, and prints the fields the diagnosis page reads.
"""
import argparse
import sys, time, json, traceback
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--refresh-pubmed", action="store_true",
        help="Fetch real PubMed title/abstract records before the synthetic demo",
    )
    args = parser.parse_args()
    t0 = time.time()
    print("[1/4] Loading ecosystem + dataset ...", flush=True)
    from mapfm_ecosystem_repaired import (
        EcosystemConfig, HeterogeneousMultiAgentEcosystem, load_medical_dataset,
    )
    from config_loader import load_yaml_config
    config = load_yaml_config(EcosystemConfig, ROOT / "config.yaml")
    csv_path = ROOT / "medNo.22.csv"
    dataset = load_medical_dataset(
        csv_path if csv_path.exists() else None,
        target_classes=config.target_classes,
        seed=config.random_seed,
    )
    eco = HeterogeneousMultiAgentEcosystem(
        config=config, dataset=dataset,
        base_model=config.ollama_model_name, verbose=False,
    )
    print(f"      ok in {time.time()-t0:.1f}s | model={config.ollama_model_name} | labels={len(eco.label_set)}", flush=True)

    evidence_refresh = {"attempted": bool(args.refresh_pubmed), "added": 0, "error": None}
    if args.refresh_pubmed:
        print("      refreshing traceable PubMed evidence for myocardial infarction ...", flush=True)
        try:
            added_ids = eco.online_kb.refresh_from_pubmed(["myocardial infarction"], n_per_topic=3)
            evidence_refresh["added"] = len(added_ids)
            evidence_refresh["error"] = eco.online_kb.last_crawl_error
            print(f"      PubMed added={len(added_ids)} error={eco.online_kb.last_crawl_error}", flush=True)
        except Exception as exc:
            evidence_refresh["error"] = f"{type(exc).__name__}: {exc}"
            print(f"      PubMed refresh failed explicitly: {evidence_refresh['error']}", flush=True)

    query = (
        "竞赛合成演示案例（synthetic demo）：sudden severe central chest pressure radiating "
        "to the left arm, diaphoresis, nausea and shortness of breath; no real patient identity."
    )

    print(f"[2/4] Running collaborative task: {query!r}", flush=True)
    t1 = time.time()
    try:
        result = eco.run_collaborative_task(patient_query=query)
    except Exception as exc:
        print("FAILED:", exc, flush=True)
        traceback.print_exc()
        sys.exit(1)
    print(f"      done in {time.time()-t1:.1f}s", flush=True)

    print("[3/4] Field summary:", flush=True)
    top = result or {}
    for k in ("request_id", "latency_seconds", "degradation", "high_risk"):
        print(f"      {k} = {top.get(k)}", flush=True)

    dma = top.get("dma") or {}
    print(f"      dma.prediction = {dma.get('prediction')}")
    print(f"      dma.confidence = {dma.get('confidence')}")
    print(f"      dma.backend = {dma.get('dma_backend')} | fallback = {dma.get('fallback_used')}")
    print(f"      dma.backend_verified = {dma.get('backend_verified')}")
    probs = dma.get("probabilities") or {}
    print(f"      dma.probabilities = {len(probs)} entries")
    if probs:
        print("      top3 probs =", sorted(probs.items(), key=lambda kv: -kv[1])[:3])

    tfa = top.get("tfa") or {}
    print(f"      tfa.risk_level = {tfa.get('risk_level')} | risk_label = {tfa.get('risk_label')} | score = {tfa.get('risk_score')}")

    consensus = top.get("consensus") or {}
    print(f"      consensus.approved = {consensus.get('approved')} | tier = {consensus.get('tier')} | weighted = {consensus.get('weighted_approvals')}/{consensus.get('total_weight')}")

    ca = top.get("comprehensive_answer") or {}
    dx = ca.get("diagnosis") or {}
    risk = ca.get("risk_assessment") or {}
    print(f"      comprehensive.diagnosis = {dx.get('prediction')} (conf={dx.get('confidence')})")
    print(f"      comprehensive.risk = {risk.get('risk_level')} / {risk.get('risk_label')}")
    recs = ca.get("recommendations") or []
    print(f"      recommendations = {len(recs)}")

    readiness = top.get("clinical_readiness") or {}
    integrity = top.get("execution_integrity") or {}
    print(f"      competition research status = {readiness.get('status')}")
    print(f"      clinical_use_allowed = {readiness.get('clinical_use_allowed')}")
    print(f"      verified_evidence_count = {integrity.get('verified_evidence_count')}")

    output_dir = ROOT / "artifacts" / "competition"
    output_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    envelope = {
        "evidence_type": "synthetic_case_live_pipeline_proof",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "no_real_patient_data": True,
        "pubmed_refresh": evidence_refresh,
        "result": result,
    }
    paths = [
        output_dir / f"live_pipeline_{stamp}.json",
        output_dir / "live_pipeline_latest.json",
    ]
    print(f"[4/4] Writing evidence to {paths[0]}", flush=True)
    for path in paths:
        with path.open("w", encoding="utf-8") as f:
            json.dump(envelope, f, ensure_ascii=False, indent=2, default=str)

    real_ollama = (
        dma.get("dma_backend") == "ollama_local_http"
        and dma.get("fallback_used") is False
        and dma.get("backend_verified") is True
    )
    research_only = readiness.get("clinical_use_allowed") is False
    if not (real_ollama and research_only):
        print("      VERIFICATION FAILED: backend or safety boundary mismatch", flush=True)
        sys.exit(2)
    print(f"      TOTAL {time.time()-t0:.1f}s  ->  VERIFIED RESEARCH-ONLY DEMO", flush=True)

if __name__ == "__main__":
    main()
