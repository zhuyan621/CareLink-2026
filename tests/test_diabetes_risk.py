"""Published future-diabetes score: boundaries and live API contract."""

from fastapi.testclient import TestClient

from api import app
from diabetes_risk import DiabetesRiskInput, calculate_diabetes_risk


BASE = dict(
    known_diabetes=False, sex="male", bmi=22.0, systolic_bp=118, diastolic_bp=76,
    fasting_glucose_mmol_l=5.0, hdl_mmol_l=1.4,
    triglycerides_mmol_l=1.0, parental_diabetes=False, bp_medication=False,
)


def test_low_score_is_range_not_fabricated_exact_percent():
    result = calculate_diabetes_risk(DiabetesRiskInput(**BASE))
    assert result["score"] == 0
    assert result["risk_text"] == "≤3%"
    assert result["risk_percent"] is None
    assert result["horizon_years"] == 8
    assert result["clinical_use_allowed"] is False


def test_changed_real_inputs_change_score_and_risk():
    payload = BASE | dict(bmi=31, systolic_bp=132, fasting_glucose_mmol_l=6.0,
                          hdl_mmol_l=0.8, triglycerides_mmol_l=2.0,
                          parental_diabetes=True)
    result = calculate_diabetes_risk(DiabetesRiskInput(**payload))
    assert result["score"] == 28
    assert result["risk_text"] == ">35%"
    assert result["risk_percent"] is None
    assert sum(item["points"] for item in result["factors"]) == result["score"]


def test_published_11_point_lookup():
    payload = BASE | dict(fasting_glucose_mmol_l=5.6, bmi=25.5,
                          hdl_mmol_l=1.4, triglycerides_mmol_l=1.0)
    result = calculate_diabetes_risk(DiabetesRiskInput(**payload))
    assert result["score"] == 12
    assert result["risk_text"] == "4%"


def test_api_refuses_baseline_diagnostic_range_and_extra_data():
    client = TestClient(app)
    invalid = client.post("/risk/diabetes-8y", json=BASE | {"fasting_glucose_mmol_l": 7.0})
    assert invalid.status_code == 422
    assert "不能" in invalid.json()["detail"]
    known = client.post("/risk/diabetes-8y", json=BASE | {"known_diabetes": True})
    assert known.status_code == 422
    assert "已确诊" in known.json()["detail"]
    extra = client.post("/risk/diabetes-8y", json=BASE | {"heart_rate": 80})
    assert extra.status_code == 422


def test_live_route_returns_source_and_not_canned_case():
    client = TestClient(app)
    first = client.post("/risk/diabetes-8y", json=BASE)
    second = client.post("/risk/diabetes-8y", json=BASE | {"bp_medication": True})
    assert first.status_code == second.status_code == 200
    assert second.json()["score"] == first.json()["score"] + 2
    assert second.json()["method"] == "published_cohort_point_score_not_newly_trained_ml"
    assert "jamanetwork.com" in second.json()["source"]["url"]
