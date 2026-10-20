"""Active MAPFM research pathway is incident diabetes only."""

from fastapi.testclient import TestClient

from api import app
from mapfm_prospective_neural import neural_status, research_predict


def test_verified_diabetes_research_checkpoint_is_independent_of_medquad():
    state = neural_status()
    assert state["trained_tasks"] == ["diabetes_onset"]
    assert state["clinical_use_allowed"] is False
    estimate = research_predict("diabetes_onset", {
        "known_diabetes_at_baseline": 0, "age_years": 50, "bmi": 25,
        "fasting_glucose_mmol_l": 5.3, "systolic_bp_mmhg": 125,
        "triglyceride_mmol_l": 1.2,
    })
    assert 0 < estimate["research_probability"] < 1
    assert estimate["clinical_use_allowed"] is False
    assert estimate["model"] == "mapfm_tfa_prospective_neural_v2"
    assert "foot_ulcer_onset" not in state["trained_tasks"]


def test_only_diabetes_outcome_is_exposed_to_clients():
    client = TestClient(app)
    state = client.get("/mapfm/prospective-neural/status").json()
    assert state["trained_tasks"] == ["diabetes_onset"]
    blocked = client.post("/mapfm/prospective-neural/research-predict", json={
        "task": "foot_ulcer_onset", "baseline_values": {"age_years": 50},
    })
    assert blocked.status_code == 503
