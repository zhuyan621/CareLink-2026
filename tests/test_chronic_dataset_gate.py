"""Prospective training gate never treats Q&A as patient follow-up."""

import csv

from fastapi.testclient import TestClient

from api import app
from chronic_dataset_gate import audit_candidate_csv, audit_local_sources
from package_competition import deliverable_files


def _write_csv(path, fields, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def test_bundled_sources_are_not_prospective_training_cohorts():
    result = audit_local_sources()
    assert [item["kind"] for item in result["sources"]] == ["medical_qa", "medical_qa"]
    assert result["sources"][0]["rows"] == 605
    assert result["sources"][1]["answer_bearing_pairs"] == 16407
    assert all(item["suitable_for_future_onset_training"] is False for item in result["sources"])
    assert result["own_prospective_model_trained"] is False
    api_result = TestClient(app).get("/mapfm/chronic-risk/data-readiness")
    assert api_result.status_code == 200
    assert set(api_result.json()["candidate_cohorts"]) == {"diabetes_onset"}
    assert api_result.json()["candidate_cohorts"]["diabetes_onset"]["rows_checked"] >= 0


def test_schema_compatible_candidate_still_not_approved_for_training(tmp_path):
    path = tmp_path / "diabetes_onset.csv"
    fields = ["participant_id", "baseline_date", "followup_date", "event_date", "diabetes_event",
              "known_diabetes_at_baseline", "age_years", "bmi", "fasting_glucose_mmol_l",
              "systolic_bp_mmhg", "triglyceride_mmol_l"]
    _write_csv(path, fields, [
        dict(zip(fields, ["synthetic-001", "2023-01-01", "2025-01-01", "", "0", "0", "56", "27", "5.2", "128", "1.4"])),
        dict(zip(fields, ["synthetic-002", "2023-01-01", "2024-01-01", "2024-01-01", "1", "0", "52", "26", "5.6", "121", "1.1"])),
    ])
    result = audit_candidate_csv(path, "diabetes_onset")
    assert result["schema_compatible"] is True
    assert result["rows_checked"] == 2
    assert result["event_count"] == 1
    assert result["approved_for_training"] is False
    assert "synthetic-001" not in str(result)


def test_rejects_cross_sectional_label_and_temporal_leakage(tmp_path):
    pima = tmp_path / "diabetes.csv"
    _write_csv(pima, ["Glucose", "BloodPressure", "BMI", "Age", "Outcome"],
               [{"Glucose": 148, "BloodPressure": 72, "BMI": 33.6, "Age": 50, "Outcome": 1}])
    result = audit_candidate_csv(pima, "diabetes_onset")
    assert result["schema_compatible"] is False
    assert any("baseline_date" in issue for issue in result["issues"])

    cohort = tmp_path / "diabetes_onset.csv"
    fields = ["participant_id", "baseline_date", "followup_date", "event_date", "diabetes_event",
              "known_diabetes_at_baseline", "age_years", "bmi", "fasting_glucose_mmol_l",
              "systolic_bp_mmhg", "triglyceride_mmol_l"]
    row = dict(zip(fields, ["s-1", "2025-01-02", "2024-01-01", "2024-01-01", "1", "0", "56", "25", "5.5", "120", "1.2"]))
    _write_csv(cohort, fields, [row, row])
    audit = audit_candidate_csv(cohort, "diabetes_onset")
    assert audit["schema_compatible"] is False
    assert any("随访日期" in issue for issue in audit["issues"])
    assert any("重复" in issue for issue in audit["issues"])
    assert "s-1" not in str(audit)


def test_candidate_cohorts_are_never_silently_packaged(tmp_path):
    file = tmp_path / "data" / "prospective" / "diabetes_onset.csv"
    _write_csv(file, ["participant_id"], [{"participant_id": "synthetic-private"}])
    assert "data/prospective/diabetes_onset.csv" not in {
        name for name, _ in deliverable_files(tmp_path)
    }
