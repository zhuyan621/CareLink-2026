"""Create a reproducible, checked local delivery archive without runtime secrets."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile


ROOT = Path(__file__).resolve().parent
PACKAGE_ROOT = "CareLink_2026"
ALLOWED_ARTIFACTS = {
    "artifacts/competition/careguard_pytest_latest.xml",
    "artifacts/competition/careguard_live_smoke_latest.json",
    "artifacts/competition/careguard_engineering_smoke_latest.json",
    "artifacts/medquad_qa/medquad_retrieval.joblib",
    "artifacts/medquad_qa/answer_records.jsonl",
    "artifacts/medquad_qa/training_report.json",
    "artifacts/medquad_qa/liveqa_test_questions.xml",
    "artifacts/medquad_qa/generalization_benchmark.json",
    "artifacts/medquad_qa/semantic/semantic_report.json",
    "artifacts/medquad_qa/semantic/semantic_embeddings.npy",
    "artifacts/medquad_qa/robustness_audit.json",
    "artifacts/medquad_qa/mediqa2019_audit.json",
    "artifacts/medquad_qa/generalization_20261014.json",
    "artifacts/medquad_qa/blind_eval_manifest_20261014.json",
    "artifacts/medquad_qa/medication_development_manifest_20261014.json",
    "artifacts/site-qa/competition-delta-2026-10-11.png",
    "artifacts/site-qa/home-2026-10-11.png",
    "artifacts/site-qa/workspace-2026-10-11.png",
    "artifacts/site-qa/lab-2026-10-11.png",
    "artifacts/site-qa/join-2026-10-11.png",
    "artifacts/site-qa/engineering-bridge-2026-10-11.png",
    "artifacts/site-qa/prospective-neural-live-2026-10-12.png",
    "artifacts/site-qa/prospective-neural-v2-live-2026-10-12.png",
    "artifacts/site-qa/medquad-studio-20261012.png",
    "artifacts/site-qa/mapfm-ten-agents-20261014.jpg",
    "artifacts/site-qa/mapfm-agent-handbook-20261014.jpg",
    "artifacts/site-qa/carelink-brand-20261014.jpg",
}
PROSPECTIVE_MODEL_FILES = {
    "artifacts/prospective_neural/mapfm_prospective_weights.pt",
    "artifacts/prospective_neural/training_report.json",
}
SKIP_DIRS = {".git", ".pytest_cache", "__pycache__", ".venv", "venv", "logs", "releases", "node_modules", "foot_ulcer_fuseg2021"}
SKIP_NAMES = {".env", ".env.local", ".env.production", "Thumbs.db", ".DS_Store", "PACKAGE_MANIFEST.json"}
SKIP_SUFFIXES = {".pyc", ".pyo", ".tmp", ".log", ".key", ".pem"}
REQUIRED = {
    "README.md", "SUBMISSION_PACKAGE_OVERVIEW.md", "DEMO_3_MIN.md", "ORIGINAL_PACKAGE_SNAPSHOT.md", "pytest.ini",
    "打开网页_新同事先看这个.txt", "START_HERE_新同事打开网页.md",
    "careguard_web/index.html", "careguard_web/site.js", "careguard_web/handoff.js", "careguard_web/engineering.css",
    "careguard_site.py", "api.py", "start_demo.py", "requirements.txt", "medNo.22.csv",
    "mapfm_ecosystem_repaired.py", "mapfm_utils/multimodal_utils.py", "config.yaml",
    "ENGINE_SOURCE_MERGE.md", "careguard_engineering_smoke.py", "tests/test_engineering_bridge.py",
    "original_engine_package/README.md", "original_engine_package/api.py",
    "original_engine_package/mapfm_ecosystem_repaired.py", "original_engine_package/mapfm_utils/multimodal_utils.py",
    "original_engine_package/medNo.22.csv", "original_engine_package/config.yaml",
    "original_engine_package/mapfm_ecosystem_repaired_backup.py", "original_engine_package/api_backup.py",
    "artifacts/competition/careguard_pytest_latest.xml",
    "artifacts/competition/careguard_live_smoke_latest.json",
    "artifacts/competition/careguard_engineering_smoke_latest.json",
    "diabetes_risk.py", "mapfm_chronic_extension.py",
    "careguard_web/diabetes.js", "careguard_web/diabetes.css",
    "docs/DIABETES_PREDICTION.md",
    "tests/test_diabetes_risk.py",
    "chronic_dataset_gate.py", "tests/test_chronic_dataset_gate.py",
    "mapfm_prospective_neural.py", "train_mapfm_prospective.py",
    "tests/test_diabetes_prospective.py",
    "prepare_nagala_diabetes.py", "docs/nagala_diabetes_governance.json",
    "careguard_web/prospective-neural.js", "careguard_web/prospective-neural.css",
    "artifacts/site-qa/prospective-neural-live-2026-10-12.png",
    "artifacts/site-qa/prospective-neural-v2-live-2026-10-12.png",
    "medquad_official_master.zip", "medquad_qa.py", "train_medquad_qa.py",
    "build_medquad_semantic.py", "medquad_generalization.py",
    "artifacts/medquad_qa/medquad_retrieval.joblib",
    "artifacts/medquad_qa/answer_records.jsonl",
    "artifacts/medquad_qa/training_report.json",
    "artifacts/medquad_qa/liveqa_test_questions.xml",
    "artifacts/medquad_qa/generalization_benchmark.json",
    "artifacts/medquad_qa/semantic/semantic_report.json",
    "artifacts/medquad_qa/semantic/semantic_embeddings.npy",
    "artifacts/medquad_qa/semantic/encoder/model.safetensors",
    "artifacts/medquad_qa/robustness_audit.json",
    "artifacts/medquad_qa/mediqa2019_audit.json",
    "artifacts/medquad_qa/generalization_20261014.json",
    "artifacts/medquad_qa/blind_eval_manifest_20261014.json",
    "artifacts/medquad_qa/medication_development_manifest_20261014.json",
    "medquad_holdout.py", "docs/MEDQUAD_ROBUSTNESS.md",
    "medquad_mediqa_audit.py", "docs/MEDQUAD_MEDIQA2019.md",
    "medquad_rqe_trial.py", "train_medquad_rqe_encoder.py",
    "medquad_rqe_encoder_eval.py", "train_medquad_meqsum_encoder.py",
    "medquad_meqsum_eval.py", "medquad_meqsum_qa_trial.py",
    "docs/MEDQUAD_GENERALIZATION_20261014.md",
    "docs/MEDQUAD_BLIND_EVAL_20261014.md", "medquad_blind_eval.py",
    "tools/medquad_blind_review.html",
    "careguard_web/medquad.js", "careguard_web/medquad.css",
    "careguard_web/medquad-review.js", "careguard_web/medquad-review.css",
    "medical_language.py", "careguard_web/medical-language.js", "careguard_web/medical-language.css",
    "careguard_web/workspace-guidance.css",
    "careguard_web/architecture.js", "careguard_web/architecture.css",
    "careguard_web/architecture-details.js",
    "careguard_web/join-story.css", "careguard_web/join-story.js",
    "tests/test_join_story_controls.cjs",
    "careguard_web/assets/diagrams/input-flow.svg",
    "careguard_web/assets/diagrams/agent-map.svg",
    "careguard_web/assets/diagrams/source-check.svg",
    "careguard_web/assets/diagrams/review-loop.svg",
    "careguard_web/assets/diagrams/research-head.svg",
    "careguard_web/assets/diagrams/audit-trail.svg",
    "tests/test_medical_language.py",
    "docs/MEDICAL_LANGUAGE_WORKSPACE.md",
    "docs/MEDQUAD_QA.md", "tests/test_medquad_qa.py",
    "DELIVERY_QA_MEDQUAD_20261012.md",
    "DELIVERY_QA_MEDQUAD_GENERALIZATION_20261012.md",
}


def _verified_semantic_files(root: Path) -> set[str]:
    base = root / "artifacts/medquad_qa"
    semantic = base / "semantic"
    report_path = semantic / "semantic_report.json"
    benchmark_path = base / "generalization_benchmark.json"
    test_path = base / "liveqa_test_questions.xml"
    try:
        report = json.loads(report_path.read_text(encoding="utf-8"))
        benchmark = json.loads(benchmark_path.read_text(encoding="utf-8"))
        files = report["encoder_file_sha256"]
        if (report["schema"] != "careguard.medquad.semantic-index.v1"
                or report["source_sha256"] != sha256(root / "medquad_official_master.zip")
                or report["records_sha256"] != sha256(base / "answer_records.jsonl")
                or report["embeddings_sha256"] != sha256(semantic / "semantic_embeddings.npy")
                or report["index_rows"] != 16407
                or benchmark["schema"] != "careguard.medquad.partial-liveqa-benchmark.v1"
                or benchmark["test_sha256"] != sha256(test_path)
                or benchmark["medquad_source_sha256"] != report["source_sha256"]
                or "encoder/model.safetensors" not in files):
            raise ValueError("semantic index or benchmark audit failed")
        selected = set()
        for relative, digest in files.items():
            path = (semantic / relative).resolve()
            if not path.is_relative_to((semantic / "encoder").resolve()) or sha256(path) != digest:
                raise ValueError("encoder manifest failed")
            selected.add(path.relative_to(root).as_posix())
        return selected
    except (OSError, UnicodeError, ValueError, TypeError, KeyError, AttributeError):
        return set()


def _verified_prospective_model(root: Path) -> bool:
    """Ship aggregate research weights only with a complete v2 audit record."""
    report_path = root / "artifacts/prospective_neural/training_report.json"
    weights_path = root / "artifacts/prospective_neural/mapfm_prospective_weights.pt"
    if not report_path.is_file() or not weights_path.is_file():
        return False
    try:
        report = json.loads(report_path.read_text(encoding="utf-8"))
        trained = {name: task for name, task in report.get("tasks", {}).items()
                   if task.get("trained") is True}
        def auditable(task: dict) -> bool:
            features = task.get("features", [])
            bounds = (task.get("train_feature_min", []), task.get("train_feature_max", []))
            interval = task.get("test_bootstrap_95ci", {}).get("auroc", [])
            return (isinstance(features, list) and len(features) > 0
                    and all(isinstance(values, list) and len(values) == len(features) for values in bounds)
                    and isinstance(interval, list) and len(interval) == 2
                    and task.get("split", {}).get("test", {}).get("events", 0) > 0
                    and bool(task.get("source_uri"))
                    and isinstance(task.get("source_sha256"), str)
                    and len(task["source_sha256"]) == 64)
        return (report.get("schema") == "careguard.mapfm.prospective-neural.v2"
                and report.get("clinical_use_allowed") is False
                and bool(trained) and all(auditable(task) for task in trained.values())
                and report.get("checkpoint_sha256") == sha256(weights_path))
    except (OSError, UnicodeError, ValueError, TypeError, KeyError, AttributeError):
        return False


def deliverable_files(root: Path = ROOT) -> list[tuple[str, Path]]:
    selected: list[tuple[str, Path]] = []
    prospective_verified = _verified_prospective_model(root)
    semantic_files = _verified_semantic_files(root)
    for path in root.rglob("*"):
        if not path.is_file() or path.is_symlink():
            continue
        relative = path.relative_to(root).as_posix()
        parts = Path(relative).parts
        # Retired diabetic-foot UI, endpoints, experiments, and old delivery
        # reports remain recoverable in the local workspace but not the new ZIP.
        if not relative.startswith("original_engine_package/") and (
            "foot" in relative.lower() or "fuseg" in relative.lower()
            or relative.startswith("DELIVERY_QA_CHRONIC_RISK_")
            or relative.startswith("DELIVERY_QA_MAPFM_NEURAL_")
            or relative == "docs/MAPFM_CHRONIC_RISK_EXTENSION.md"
            or relative == "docs/MAPFM_PROSPECTIVE_NEURAL.md"
            or relative == "tests/test_mapfm_prospective_neural.py"
        ):
            continue
        if relative in {"medquad_rerank_trial.py", "medquad_intent_trial.py",
                        "medquad_sealed_compare.py", "medquad_multifield_trial.py",
                        "medquad_mediqa_compare.py", "medquad_locked_trial.py"}:
            continue
        if any(part in SKIP_DIRS for part in parts[:-1]):
            continue
        # Preserve the three historical documentation build logs inside the
        # separate original snapshot so its 225-file source audit stays exact.
        snapshot_document_log = relative.startswith("original_engine_package/docs/") and path.suffix.lower() == ".log"
        if path.name in SKIP_NAMES or (path.suffix.lower() in SKIP_SUFFIXES and not snapshot_document_log):
            continue
        if relative.startswith("artifacts/") and relative not in ALLOWED_ARTIFACTS and relative not in semantic_files and not (
            prospective_verified and relative in PROSPECTIVE_MODEL_FILES
        ):
            continue
        # Prospective cohorts can contain identifiable clinical records and
        # must never be silently copied into a competition ZIP.
        if relative.startswith("data/prospective/"):
            continue
        if any(part.startswith(".") for part in parts[:-1]):
            continue
        if path.name.startswith(".") and path.name not in {".env.example", ".gitignore"}:
            continue
        selected.append((relative, path))
    selected.sort(key=lambda item: item[0])
    return selected


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_archive(destination: Path, root: Path = ROOT) -> dict:
    from medquad_qa import read_official_archive

    report_path = root / "artifacts/medquad_qa/training_report.json"
    report = json.loads(report_path.read_text(encoding="utf-8"))
    source = root / "medquad_official_master.zip"
    model = root / "artifacts/medquad_qa/medquad_retrieval.joblib"
    records = root / "artifacts/medquad_qa/answer_records.jsonl"
    _, counts = read_official_archive(source)
    if (report.get("source_sha256") != sha256(source)
            or report.get("model_sha256") != sha256(model)
            or report.get("records_sha256") != sha256(records)
            or report.get("qa_pairs_total") != counts["qa_pairs_total"]
            or report.get("indexed_pairs") != counts["answer_bearing_pairs"]):
        raise ValueError("MedQuAD complete-source or fitted-model audit failed")
    if not _verified_semantic_files(root):
        raise ValueError("MedQuAD semantic index or external benchmark audit failed")
    robustness = json.loads((root / "artifacts/medquad_qa/robustness_audit.json").read_text(encoding="utf-8"))
    if (robustness.get("schema") != "careguard.medquad.robustness-audit.v1"
            or robustness.get("deployed_source_sha256") != sha256(root / "medquad_qa.py")
            or robustness.get("model_sha256") != sha256(model)
            or robustness.get("candidate_decision") != "rejected; baseline retained"):
        raise ValueError("MedQuAD deployment robustness gate failed")
    mediqa = json.loads((root / "artifacts/medquad_qa/mediqa2019_audit.json").read_text(encoding="utf-8"))
    if (mediqa.get("schema") != "careguard.medquad.mediqa2019-audit.v1"
            or mediqa.get("model_sha256") != sha256(model)
            or mediqa.get("strict_evaluable_questions") != 52
            or mediqa.get("answer_field_candidate", {}).get("promotion_decision") != "rejected; baseline retained"):
        raise ValueError("MedQuAD MEDIQA 2019 audit gate failed")
    latest = json.loads((root / "artifacts/medquad_qa/generalization_20261014.json").read_text(encoding="utf-8"))
    if (latest.get("schema") != "careguard.medquad.generalization-audit.v1"
            or latest.get("deployed_model_sha256") != sha256(model)
            or latest.get("baseline_retained") is not True
            or latest.get("candidate_count") != 3
            or latest.get("candidates_rejected") != 3
            or any(trial.get("decision") != "rejected" for trial in latest.get("trials", {}).values())):
        raise ValueError("MedQuAD latest generalization deployment gate failed")
    blind = json.loads((root / "artifacts/medquad_qa/blind_eval_manifest_20261014.json").read_text(encoding="utf-8"))
    development = json.loads((root / "artifacts/medquad_qa/medication_development_manifest_20261014.json").read_text(encoding="utf-8"))
    if (blind.get("schema") != "careguard.medquad.blind-evaluation-manifest.v1"
            or blind.get("deployed_model_sha256") != sha256(model)
            or blind.get("locked_question_count") != 250
            or blind.get("labels_complete") is not False
            or blind.get("performance_estimate_available") is not False
            or development.get("schema") != "careguard.medquad.medication-development-manifest.v1"
            or development.get("deployed_model_sha256") != sha256(model)
            or development.get("development_question_count") != 100
            or development.get("linked_locked_packet_id") != blind.get("packet_id")
            or development.get("labels_complete") is not False):
        raise ValueError("MedQuAD blind evaluation packaging gate failed")
    files = deliverable_files(root)
    paths = {relative for relative, _ in files}
    missing = sorted(REQUIRED - paths)
    if missing:
        raise ValueError(f"Missing required delivery files: {missing}")
    if destination.exists():
        raise FileExistsError(f"Will not overwrite an existing archive: {destination}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    manifest = {
        "schema_version": "careguard.delivery.v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "package_root": PACKAGE_ROOT,
        "files": {relative: {"bytes": path.stat().st_size, "sha256": sha256(path)} for relative, path in files},
    }
    with ZipFile(destination, "w", compression=ZIP_DEFLATED, compresslevel=7) as archive:
        for relative, path in files:
            archive.write(path, f"{PACKAGE_ROOT}/{relative}")
        archive.writestr(
            f"{PACKAGE_ROOT}/PACKAGE_MANIFEST.json",
            json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True).encode("utf-8"),
        )
    with ZipFile(destination) as archive:
        bad = archive.testzip()
        if bad:
            raise ValueError(f"Archive CRC verification failed: {bad}")
        if len(archive.namelist()) != len(files) + 1:
            raise ValueError("Archive file count mismatch")
    return {"archive": str(destination), "bytes": destination.stat().st_size, "files": len(files), "sha256": sha256(destination)}


def main() -> None:
    parser = argparse.ArgumentParser(description="Package the complete local CareLink contest deliverable")
    parser.add_argument("--output", type=Path, help="Explicit path for a new ZIP file")
    args = parser.parse_args()
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output = args.output or ROOT / "releases" / f"CareLink_2026_完整交付包_{stamp}.zip"
    print(json.dumps(build_archive(output), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
