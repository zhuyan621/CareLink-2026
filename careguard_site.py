"""Serve the competition website and the existing screening API on one local origin."""

from __future__ import annotations

import json
import csv
import hashlib
from datetime import datetime
from functools import lru_cache
from pathlib import Path
from xml.etree import ElementTree

from fastapi.staticfiles import StaticFiles
from fastapi import HTTPException
from fastapi.responses import FileResponse, RedirectResponse

from api import app
from careguard_join import router as join_router


ROOT = Path(__file__).resolve().parent
WEB_ROOT = ROOT / "careguard_web"

app.include_router(join_router)


FEATURED_QUESTION_IDS = (641, 506, 753, 250, 19, 433)


@lru_cache(maxsize=1)
def _dataset_questions() -> tuple[dict[str, str], ...]:
    """Load source Q&A rows as reference material, not patient cases."""
    with (ROOT / "medNo.22.csv").open(encoding="utf-8-sig", newline="") as handle:
        return tuple(csv.DictReader(handle))


@app.get("/site/dataset/questions")
def dataset_questions(q: str = "", area: str = "", offset: int = 0, limit: int = 24, featured: bool = False) -> dict:
    """Browse source questions, including exact original-ID lookup with #123."""
    rows = _dataset_questions()
    query = q.strip().casefold()[:100]
    topic = area.strip().casefold()[:80]
    exact_id = query[1:] if query.startswith("#") and query[1:].isdigit() else None

    def matches_query(row: dict[str, str]) -> bool:
        if not query:
            return True
        if exact_id is not None:
            return row["id"] == exact_id
        return query in row["question"].casefold() or query in row["area"].casefold()

    matched = [row for row in rows if
               matches_query(row)
               and (not topic or topic == row["area"].casefold())]
    if featured and not query and not topic:
        by_id = {int(row["id"]): row for row in matched}
        matched = [by_id[item_id] for item_id in FEATURED_QUESTION_IDS if item_id in by_id]
    start = max(0, offset)
    page = matched[start:start + min(max(limit, 1), 24)]
    return {
        "dataset": "medNo.22.csv",
        "kind": "medical_qa_not_patient_records",
        "total_rows": len(rows),
        "matched": len(matched),
        "items": [
            {
                "id": int(row["id"]),
                "question": row["question"].strip(),
                "area": row["area"].strip(),
                "source": row["source"].strip(),
                "answer_excerpt": row["answer"].strip()[:380].rstrip() + ("…" if len(row["answer"].strip()) > 380 else ""),
            }
            for row in page
        ],
    }


@app.get("/site/dataset/manifest")
def dataset_manifest() -> dict:
    """Expose independently checkable import coverage and the complete topic list."""
    rows = _dataset_questions()
    topics: dict[str, dict[str, str | int]] = {}
    for row in rows:
        area = row["area"].strip()
        key = area.casefold()
        if key not in topics:
            topics[key] = {"area": area, "count": 0}
        topics[key]["count"] += 1
    source = ROOT / "medNo.22.csv"
    return {
        "dataset": source.name,
        "kind": "medical_qa_not_patient_records",
        "total_rows": len(rows),
        "unique_ids": len({row["id"] for row in rows}),
        "topic_count": len(topics),
        "topics": [topics[key] for key in sorted(topics)],
        "sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
    }


@app.get("/site/dataset/source")
def dataset_source() -> FileResponse:
    """Allow reviewers to reconcile the displayed index with the original CSV."""
    return FileResponse(ROOT / "medNo.22.csv", media_type="text/csv", filename="medNo.22.csv")


@app.get("/site/dataset/questions/{question_id}")
def dataset_question_detail(question_id: int) -> dict:
    for row in _dataset_questions():
        if int(row["id"]) == question_id:
            return {key: value.strip() for key, value in row.items()}
    raise HTTPException(status_code=404, detail="Question row not found")


@app.get("/site/status")
def site_status() -> dict:
    """Read snapshots without implying that a historical check is live."""
    artifact_root = ROOT / "artifacts" / "competition"
    smoke_path = artifact_root / "careguard_live_smoke_latest.json"
    tests_path = artifact_root / "careguard_pytest_latest.xml"
    smoke: dict = {}
    tests: dict = {}
    if smoke_path.exists():
        try:
            smoke = json.loads(smoke_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            pass
    if tests_path.exists():
        try:
            root = ElementTree.parse(tests_path).getroot()
            suite = root.find("testsuite") if root.tag == "testsuites" else root
            if suite is not None:
                tests = {
                    "total": int(suite.attrib.get("tests", 0)),
                    "failures": int(suite.attrib.get("failures", 0)),
                    "errors": int(suite.attrib.get("errors", 0)),
                    "skipped": int(suite.attrib.get("skipped", 0)),
                }
        except (OSError, ElementTree.ParseError, ValueError):
            pass
    checked_at = smoke.get("generated_at_utc")
    try:
        checked_at = datetime.fromisoformat(checked_at).astimezone().strftime("%Y-%m-%d %H:%M")
    except (TypeError, ValueError):
        checked_at = None
    return {
        "tests": tests,
        "smoke": {
            "checked_at_local": checked_at,
            "ollama_generation_verified": bool(smoke.get("ollama_generation_verified")),
            "fallback_used": bool(smoke.get("fallback_used")),
            "latency_seconds": smoke.get("latency_seconds"),
            "dynamic_evidence_count": smoke.get("dynamic_evidence_count"),
        },
        "clinical_use_ready": False,
    }


@app.get("/site/medquad-review")
def medquad_review_tool() -> RedirectResponse:
    """Send old review bookmarks to the integrated site; never expose packets."""
    return RedirectResponse(url="/?view=workspace#review-desk", status_code=302)


@app.api_route("/assets/{asset_path:path}", methods=["GET", "HEAD"])
def public_assets(asset_path: str) -> FileResponse:
    """Keep retired photos/scans recoverable on disk but outside the public site."""
    asset_root = (WEB_ROOT / "assets").resolve()
    path = (asset_root / asset_path).resolve()
    if not path.is_relative_to(asset_root) or not path.is_file():
        raise HTTPException(status_code=404, detail="Asset not found")
    if path.relative_to(asset_root).parts[0].lower() in {"archive", "join", "research"}:
        raise HTTPException(status_code=404, detail="Asset not published")
    return FileResponse(path)


app.mount("/", StaticFiles(directory=WEB_ROOT, html=True), name="careguard-web")
