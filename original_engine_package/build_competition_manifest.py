"""Build a hash-linked manifest from already generated competition evidence."""
from __future__ import annotations

import hashlib
import json
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict


ROOT = Path(__file__).resolve().parent
EVIDENCE_DIR = ROOT / "artifacts" / "competition"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def junit_summary(path: Path) -> Dict[str, Any]:
    root = ET.parse(path).getroot()
    suites = [root] if root.tag == "testsuite" else list(root.findall("testsuite"))
    totals = {name: sum(int(float(suite.attrib.get(name, 0))) for suite in suites)
              for name in ("tests", "failures", "errors", "skipped")}
    totals["passed"] = totals["tests"] - totals["failures"] - totals["errors"] - totals["skipped"]
    totals["time_seconds"] = round(sum(float(suite.attrib.get("time", 0.0)) for suite in suites), 3)
    return totals


def main() -> None:
    readiness_path = EVIDENCE_DIR / "competition_readiness_latest.json"
    pipeline_path = EVIDENCE_DIR / "live_pipeline_latest.json"
    junit_path = EVIDENCE_DIR / "pytest_full_report.xml"
    required = [readiness_path, pipeline_path, junit_path]
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        raise SystemExit(f"Missing evidence files: {missing}")

    readiness = json.loads(readiness_path.read_text(encoding="utf-8"))
    pipeline = json.loads(pipeline_path.read_text(encoding="utf-8"))
    result = pipeline["result"]
    integrity = result["execution_integrity"]
    tests = junit_summary(junit_path)

    manifest = {
        "schema_version": "mapfm.competition-release-manifest.v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "release_decision": {
            "competition_demo_ready": bool(readiness["readiness"]["competition_demo_ready"]),
            "clinical_use_ready": bool(readiness["readiness"]["clinical_use_ready"]),
            "tests_passed": tests["passed"],
            "tests_failed_or_errored": tests["failures"] + tests["errors"],
        },
        "live_pipeline_observation": {
            "request_id": result.get("request_id"),
            "latency_seconds": result.get("latency_seconds"),
            "dma_backend": integrity.get("dma_backend"),
            "dma_fallback_used": integrity.get("dma_fallback_used"),
            "embedding_backend": (integrity.get("embedding") or {}).get("backend"),
            "embedding_fallback_used": (integrity.get("embedding") or {}).get("fallback_used"),
            "verified_evidence_count": integrity.get("verified_evidence_count"),
            "high_risk": result.get("high_risk"),
            "temporal_estimate_available": integrity.get("temporal_estimate_available"),
            "clinical_use_allowed": integrity.get("clinical_use_allowed"),
        },
        "test_summary": tests,
        "artifacts": {
            path.name: {"sha256": sha256(path), "bytes": path.stat().st_size}
            for path in required
        },
        "claim_boundary": readiness.get("claim_boundary", []),
    }
    serialized = json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    for path in (
        EVIDENCE_DIR / f"release_manifest_{stamp}.json",
        EVIDENCE_DIR / "release_manifest_latest.json",
    ):
        path.write_text(serialized, encoding="utf-8")
    print(serialized)


if __name__ == "__main__":
    main()
