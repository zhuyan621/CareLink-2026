from pathlib import Path

from package_competition import ROOT, deliverable_files, REQUIRED


def test_package_has_complete_runnable_core_without_runtime_secrets():
    paths = {name for name, _ in deliverable_files(ROOT)}
    assert REQUIRED <= paths
    assert "docs/assets/business-plan.pdf" in paths
    assert not any(path.startswith("logs/") or path.startswith("releases/") for path in paths)
    assert not any("__pycache__" in Path(path).parts for path in paths)
    assert ".env" not in paths
    assert "artifacts/competition/live_pipeline_latest.json" not in paths
    assert "artifacts/medquad_qa/robustness_audit.json" in paths
    assert "docs/MEDQUAD_ROBUSTNESS.md" in paths
    assert "docs/MEDQUAD_MEDIQA2019.md" in paths
    assert "artifacts/medquad_qa/mediqa2019_audit.json" in paths
    assert "artifacts/medquad_qa/generalization_20261014.json" in paths
    assert "docs/MEDQUAD_GENERALIZATION_20261014.md" in paths
    assert "artifacts/medquad_qa/blind_eval_manifest_20261014.json" in paths
    assert "artifacts/medquad_qa/medication_development_manifest_20261014.json" in paths
    assert "docs/MEDQUAD_BLIND_EVAL_20261014.md" in paths
    assert "tools/medquad_blind_review.html" in paths
    assert "medquad_mediqa_audit.py" in paths
    assert not any("liveqa_train" in path for path in paths)
    assert not any("mediqa2019_official_" in path for path in paths)
    assert "artifacts/medquad_qa/mediqa2019_comparison.json" not in paths
    assert "medquad_rerank_trial.py" not in paths
    assert "medquad_multifield_trial.py" not in paths
    assert "medquad_locked_trial.py" not in paths
    assert not any(path.startswith("artifacts/medquad_qa_candidate/") for path in paths)
    assert not any("foot_ulcer_fuseg2021" in Path(path).parts for path in paths)
    snapshot = {path for path in paths if path.startswith("original_engine_package/")}
    assert len(snapshot) == 225
    assert "original_engine_package/docs/HMAE_Mathematical_Foundations.log" in snapshot
    assert not any(".venv" in Path(path).parts or ".git" in Path(path).parts for path in snapshot)
