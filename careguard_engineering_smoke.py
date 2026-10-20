"""Exercise the browser's original-MAPFM route with one synthetic observation."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

from fastapi.testclient import TestClient

from careguard_site import app


ROOT = Path(__file__).resolve().parent


def main() -> int:
    parser = argparse.ArgumentParser(description="CareGuard original-engine smoke test")
    parser.add_argument("--require-ollama", action="store_true")
    parser.add_argument("--no-persist", action="store_true")
    parser.add_argument("--base-url", help="Check an already-running loopback HTTP server, e.g. http://127.0.0.1:8511")
    args = parser.parse_args()
    request = {
        "patient_query": "合成演示：夜间突发持续胸痛，伴大汗与呼吸困难；已呼叫值班负责人。",
        "observation": {"heart_rate": 112, "spo2": 91, "temperature": 36.8, "respiratory_rate": 25},
        "force_high_risk": True,
    }
    if args.base_url:
        parsed_url = urlsplit(args.base_url)
        if parsed_url.scheme != "http" or parsed_url.hostname not in {"127.0.0.1", "localhost"} or parsed_url.path not in {"", "/"} or parsed_url.query or parsed_url.fragment:
            parser.error("--base-url must be a plain local http://127.0.0.1:PORT or http://localhost:PORT origin")
        endpoint = args.base_url.rstrip("/") + "/screening/engineering"
        outgoing = Request(endpoint, data=json.dumps(request, ensure_ascii=False).encode("utf-8"), headers={"Content-Type": "application/json; charset=utf-8"}, method="POST")
        with urlopen(outgoing, timeout=180) as response:
            result = json.load(response)
        transport = "live_loopback_http"
    else:
        response = TestClient(app).post("/screening/engineering", json=request, timeout=180)
        response.raise_for_status()
        result = response.json()
        transport = "in_process_testclient"
    view = result["screening"]
    engineering = result["engineering"]
    summary = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "transport": transport,
        "request_id": view.get("request_id"),
        "original_core_source_match": engineering.get("core_source_match"),
        "core_sha256": engineering.get("core_sha256"),
        "preprocessor_sha256": engineering.get("preprocessor_sha256"),
        "parsed_observation_count": engineering.get("parsed_observation_count"),
        "active_model_input": engineering.get("active_model_input"),
        "model_input_modalities": engineering.get("model_input_modalities"),
        "dma_backend": engineering.get("dma_backend"),
        "ollama_generation_verified": engineering.get("ollama_generation_verified"),
        "priority": (view.get("priority") or {}).get("code"),
        "dynamic_evidence_count": view.get("evidence_count"),
        "human_review_required": view.get("requires_human_review"),
        "temporal_prediction_used": engineering.get("temporal_prediction_used"),
        "clinical_use_allowed": engineering.get("clinical_use_allowed"),
        "runtime_seconds": view.get("runtime_seconds"),
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    if not args.no_persist:
        path = ROOT / "artifacts" / "competition" / "careguard_engineering_smoke_latest.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(".tmp")
        temporary.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
        temporary.replace(path)
    if not summary["original_core_source_match"] or summary["parsed_observation_count"] != 1:
        return 3
    if not summary["human_review_required"] or summary["clinical_use_allowed"]:
        return 3
    if args.require_ollama and not summary["ollama_generation_verified"]:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
