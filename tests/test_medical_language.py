"""Natural language may fill model fields, but may not invent prognosis data."""

import pytest
from fastapi.testclient import TestClient

from careguard_site import app
from medical_language import parse_medical_prompt


@pytest.mark.parametrize("question", [
    "未患糖尿病，50岁，BMI 25，空腹血糖5.3 mmol/L，收缩压125 mmHg，甘油三酯1.2 mmol/L。未来3年新发糖尿病风险？",
    "未来三年发生糖尿病的概率？基线无糖尿病，年龄50岁，体质指数25，空腹葡萄糖5.3 mmol/L，高压125，TG 1.2 mmol/L。",
    "No known diabetes; age 50; BMI 25; FPG 5.3 mmol/L; SBP 125 mmHg; TG 1.2 mmol/L. What is my diabetes risk in the next 3 years?",
    "Without diabetes, 50 years old, BMI 25, fasting glucose 95 mg/dL, systolic blood pressure 125 mmHg, triglycerides 106 mg/dL. What is my diabetes risk?",
    "未来3年糖尿病风险：无糖尿病史，身高170cm，体重72kg，50岁，空腹血糖5.3 mmol/L，血压125/80 mmHg，甘油三酯1.2 mmol/L。",
])
def test_complete_bilingual_paraphrases_extract_model_baseline(question):
    result = parse_medical_prompt(question)
    assert result["kind"] == "diabetes_3y_ready"
    assert result["extracted"]["age_years"] == 50
    assert result["extracted"]["known_diabetes_at_baseline"] == 0
    assert result["extracted"]["fasting_glucose_mmol_l"] == pytest.approx(5.3, abs=.05)


@pytest.mark.parametrize("question, expected", [
    ("未来3年糖尿病风险是多少？", "needs_clarification"),
    ("未来3年糖尿病风险：未患糖尿病，50岁，BMI25，空腹血糖5.3，收缩压125，甘油三酯1.2 mmol/L。", "needs_clarification"),
    ("已确诊糖尿病，未来3年新发糖尿病风险？", "ineligible"),
    ("未来5年糖尿病风险：未患糖尿病，50岁，BMI25，空腹血糖5.3 mmol/L，收缩压125，甘油三酯1.2 mmol/L。", "unsupported_horizon"),
    ("未来3年足溃疡的概率是多少？", "unsupported_outcome"),
    ("未来3年冠心病概率是多少？", "unsupported_outcome"),
    ("什么是糖尿病？", "qa_language_unsupported"),
    ("What is diabetes?", "source_qa"),
])
def test_unanswerable_or_out_of_scope_questions_never_become_risk(question, expected):
    assert parse_medical_prompt(question)["kind"] == expected


def test_conflicting_values_stop_risk_extraction():
    question = "未患糖尿病，50岁，BMI25，空腹血糖5.3 mmol/L，收缩压125、收缩压140 mmHg，甘油三酯1.2 mmol/L。未来3年风险？"
    result = parse_medical_prompt(question)
    assert result["kind"] == "needs_clarification"
    assert any("收缩压" in issue for issue in result["issues"])


def test_incomplete_and_identifying_inputs_are_not_sent_to_model():
    client = TestClient(app)
    incomplete = client.post("/mapfm/medical-language/evaluate", json={"question": "未来3年糖尿病风险是多少？"})
    assert incomplete.status_code == 200
    assert incomplete.json()["probability_available"] is False
    assert "estimate" not in incomplete.json()
    identifying = client.post("/mapfm/medical-language/evaluate", json={"question": "未来3年糖尿病风险，请联系 13812345678。"})
    assert identifying.status_code == 422


def test_complete_question_runs_existing_mapfm_tfa_weights():
    client = TestClient(app)
    question = "未患糖尿病，50岁，BMI 25，空腹血糖5.3 mmol/L，收缩压125 mmHg，甘油三酯1.2 mmol/L。未来3年新发糖尿病风险？"
    response = client.post("/mapfm/medical-language/evaluate", json={"question": question})
    assert response.status_code == 200
    result = response.json()
    assert result["kind"] == "diabetes_3y_result"
    assert result["probability_available"] is True
    assert 0 < result["estimate"]["research_probability"] < 1
    assert result["estimate"]["model"] == "mapfm_tfa_prospective_neural_v2"
    assert result["estimate"]["execution_path"] == "original_mapfm_tfa.forecast_prospective"
    assert result["estimate"]["external_validation_completed"] is False
    assert result["estimate"]["clinical_use_allowed"] is False


def test_source_qa_branch_has_no_probability(monkeypatch):
    import api

    monkeypatch.setattr(api, "medquad_status", lambda: {"ready": True})
    monkeypatch.setattr(api, "ask_medquad", lambda question, top_k: {"matches": [{"id": "source-1", "answer": "Source text."}]})
    response = TestClient(app).post("/mapfm/medical-language/evaluate", json={"question": "What is diabetes?"})
    assert response.status_code == 200
    assert response.json()["kind"] == "source_qa"
    assert response.json()["probability_available"] is False
    assert "estimate" not in response.json()
