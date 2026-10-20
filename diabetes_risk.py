"""Reproducible Framingham Offspring Study incident-diabetes point score.

This is a published, cohort-derived 8-year risk *score*, not a CareGuard-trained
machine-learning model.  It is intentionally isolated from MAPFM's acute-care
screening and from the medNo.22 question-answer dataset.

Source: Wilson et al., Arch Intern Med. 2007;167:1068-1074, Table 6.
https://jamanetwork.com/journals/jamainternalmedicine/fullarticle/486842
"""

from __future__ import annotations

from dataclasses import dataclass


SOURCE_URL = "https://jamanetwork.com/journals/jamainternalmedicine/fullarticle/486842"
MGDL_GLUCOSE_PER_MMOL = 18.0182
MGDL_CHOLESTEROL_PER_MMOL = 38.67
MGDL_TRIGLYCERIDE_PER_MMOL = 88.57


@dataclass(frozen=True)
class DiabetesRiskInput:
    known_diabetes: bool
    sex: str
    bmi: float
    systolic_bp: float
    diastolic_bp: float
    fasting_glucose_mmol_l: float
    hdl_mmol_l: float
    triglycerides_mmol_l: float
    parental_diabetes: bool
    bp_medication: bool


class ExistingDiabetesEvaluation(ValueError):
    """A baseline result is outside the nondiabetic derivation cohort."""


def calculate_diabetes_risk(item: DiabetesRiskInput) -> dict:
    """Calculate the Table 6 score using baseline inputs only.

    Unit conversion is performed once so the published mg/dL cutoffs remain
    authoritative. An already-diagnostic-range fasting glucose is not scored.
    """
    if item.known_diabetes:
        raise ExistingDiabetesEvaluation(
            "已确诊糖尿病者不属于该研究的基线无糖尿病人群，不能计算未来新发糖尿病风险。"
        )
    if item.sex not in {"male", "female"}:
        raise ValueError("sex must be male or female for the published HDL cutoffs")
    if item.fasting_glucose_mmol_l * MGDL_GLUCOSE_PER_MMOL >= 126:
        raise ExistingDiabetesEvaluation(
            "空腹血糖已达到该研究的基线排除阈值（约 7.0 mmol/L）；不能用未患病队列的未来发病评分估计。请由医疗专业人员复核。"
        )

    glucose = item.fasting_glucose_mmol_l * MGDL_GLUCOSE_PER_MMOL
    hdl = item.hdl_mmol_l * MGDL_CHOLESTEROL_PER_MMOL
    triglycerides = item.triglycerides_mmol_l * MGDL_TRIGLYCERIDE_PER_MMOL
    factors = [
        ("空腹血糖 100–<126 mg/dL", 10 if glucose >= 100 else 0),
        ("BMI 25–<30 kg/m²", 2 if 25 <= item.bmi < 30 else 0),
        ("BMI ≥30 kg/m²", 5 if item.bmi >= 30 else 0),
        ("HDL-C 低于性别阈值", 5 if hdl < (40 if item.sex == "male" else 50) else 0),
        ("父母有糖尿病史", 3 if item.parental_diabetes else 0),
        ("甘油三酯 ≥150 mg/dL", 3 if triglycerides >= 150 else 0),
        ("血压 ≥130/85 mmHg 或正在降压治疗", 2 if item.systolic_bp >= 130 or item.diastolic_bp >= 85 or item.bp_medication else 0),
    ]
    score = sum(points for _, points in factors)
    if score <= 10:
        risk_text, risk_percent = "≤3%", None
    elif score >= 25:
        risk_text, risk_percent = ">35%", None
    else:
        risk_percent = {11: 4, 12: 4, 13: 5, 14: 6, 15: 7, 16: 9, 17: 11,
                        18: 13, 19: 15, 20: 18, 21: 21, 22: 25, 23: 29, 24: 33}[score]
        risk_text = f"{risk_percent}%"
    return {
        "model": "framingham_offspring_table_6",
        "horizon_years": 8,
        "score": score,
        "risk_text": risk_text,
        "risk_percent": risk_percent,
        "factors": [{"name": name, "points": points} for name, points in factors],
        "source": {"title": "Prediction of Incident Diabetes Mellitus in Middle-aged Adults, Table 6", "url": SOURCE_URL},
        "method": "published_cohort_point_score_not_newly_trained_ml",
        "input_data_used": "current_form_values_only",
        "limitations": [
            "原研究来自美国 Framingham Offspring 队列，尚未在本项目目标中国照护人群进行外部校准或临床验证。",
            "结果是队列人群的 8 年分层估计，不是个人诊断，也不能据此替代空腹血糖或 HbA1c 检查。",
            "心率、血氧、体温和呼吸频率不在发表的评分中，未被偷偷用于糖尿病预测。",
        ],
        "clinical_use_allowed": False,
    }
