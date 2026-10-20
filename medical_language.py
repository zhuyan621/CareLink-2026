"""Conservative natural-language routing for source QA and 3-year diabetes research.

The parser never invents missing baseline features. It is an input adapter,
not a trained language model or evidence of clinical generalization.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any


FEATURE_LABELS = {
    "age_years": "年龄（岁）",
    "bmi": "BMI（kg/m²），或身高与体重",
    "fasting_glucose_mmol_l": "基线空腹血糖（mmol/L 或 mg/dL）",
    "systolic_bp_mmhg": "收缩压（mmHg）",
    "triglyceride_mmol_l": "甘油三酯（mmol/L 或 mg/dL）",
    "known_diabetes_at_baseline": "明确说明基线没有糖尿病",
}
NUM = r"(?P<value>\d{1,3}(?:\.\d+)?)"


def _match_values(text: str, patterns: tuple[str, ...]) -> list[re.Match[str]]:
    return [match for pattern in patterns for match in re.finditer(pattern, text, flags=re.I)]


def _one(values: list[float], label: str, issues: list[str]) -> float | None:
    if not values:
        return None
    if any(abs(value - values[0]) > 0.02 for value in values[1:]):
        issues.append(f"{label}出现多个不同数值，请核对后只保留一项。")
        return None
    return round(values[0], 4)


def _lab_values(text: str, names: str, *, divisor: float, label: str,
                issues: list[str]) -> float | None:
    pattern = rf"(?:{names})\s*(?:为|是|约|大约|:|=)?\s*{NUM}\s*(?P<unit>mmol\s*/\s*l|mg\s*/\s*dl)?"
    found = _match_values(text, (pattern,))
    values: list[float] = []
    for match in found:
        unit = re.sub(r"\s+", "", match.group("unit") or "").lower()
        if not unit:
            issues.append(f"{label}缺少单位，请写明 mmol/L 或 mg/dL。")
            continue
        number = float(match.group("value"))
        values.append(number / divisor if unit == "mg/dl" else number)
    return _one(values, label, issues)


def parse_medical_prompt(question: str) -> dict[str, Any]:
    """Route an arbitrary prompt without assuming every question supports risk."""
    text = unicodedata.normalize("NFKC", question).strip().lower()
    future = bool(re.search(r"未来|今后|接下来|发病|新发|风险|概率|预测|会得|患上|\brisk\b|\bchance\b|\bprobability\b|\bdevelop\b|\bonset\b", text))
    diabetes = bool(re.search(r"糖尿病|\bdiabetes\b|\bdiabetic\b", text))
    foot = bool(re.search(r"糖尿病足|足溃疡|\bfoot ulcer\b|\bdiabetic foot\b", text))
    if foot and future:
        return {"kind": "unsupported_outcome", "message": "当前没有经过验证的未来足溃疡发生模型，不能输出概率。"}
    if future and not diabetes:
        return {"kind": "unsupported_outcome", "message": "当前只支持未来 3 年新发糖尿病研究估计；其他疾病不能从问答文本推算概率。"}
    if not diabetes or not future:
        if re.search(r"[\u4e00-\u9fff]", text):
            return {"kind": "qa_language_unsupported", "message": "当前 MedQuAD 来源检索仅验证英文医学知识问法。请用英文提问；知识问答不产生疾病概率。"}
        return {"kind": "source_qa", "message": "使用 MedQuAD 原始来源检索，不进行疾病概率推断。"}

    horizon = re.search(r"(?:未来|今后|接下来|within|over the next|in the next)\s*(\d+|三|五|十)\s*(?:年|years?)", text)
    if not horizon:
        horizon = re.search(r"\b(\d+)\s*[- ]\s*year\s+(?:risk|probability|incidence)", text)
    if horizon and horizon.group(1) not in ("3", "三"):
        return {"kind": "unsupported_horizon", "message": "本研究权重只预测固定的未来 3 年结局，不能换算为其他年限。"}

    negative_pattern = r"无糖尿病史|未患糖尿病|没有糖尿病|基线无糖尿病|既往无糖尿病|尚未确诊糖尿病|no known diabetes|without diabetes|not diagnosed with diabetes|non[- ]diabetic"
    negative = bool(re.search(negative_pattern, text))
    positive = bool(re.search(r"已患糖尿病|已经有糖尿病|确诊糖尿病|患有糖尿病|known diabetes|diagnosed with diabetes|i have diabetes",
                              re.sub(negative_pattern, " ", text)))
    if positive and not negative:
        return {"kind": "ineligible", "message": "新发糖尿病模型只适用于基线未患糖尿病人群；已患病不能计算新发风险。"}
    if positive and negative:
        return {"kind": "conflict", "message": "基线糖尿病状态出现矛盾，请核对后重新输入。"}

    issues: list[str] = []
    age = _one([float(m.group("value")) for m in _match_values(text, (
        rf"(?:年龄|\bage\b|\baged\b)\s*(?:为|是|:|=)?\s*{NUM}\s*(?:岁|years?|y/o)?",
        rf"{NUM}\s*岁",
        rf"{NUM}\s*years?\s*old",
    ))], "年龄", issues)
    bmi = _one([float(m.group("value")) for m in _match_values(text, (
        rf"(?:\bbmi\b|体质指数)\s*(?:为|是|:|=)?\s*{NUM}",
    ))], "BMI", issues)
    if bmi is None:
        heights = _match_values(text, (rf"(?:身高|height)\s*(?:为|是|:|=)?\s*{NUM}\s*(?P<unit>cm|厘米|m|米)\b",))
        weights = _match_values(text, (rf"(?:体重|weight)\s*(?:为|是|:|=)?\s*{NUM}\s*(?:kg|公斤|千克)\b",))
        if len(heights) == 1 and len(weights) == 1:
            height = float(heights[0].group("value"))
            if heights[0].group("unit") in ("cm", "厘米"):
                height /= 100
            if 1.0 <= height <= 2.4:
                bmi = round(float(weights[0].group("value")) / height ** 2, 4)
    glucose = _lab_values(text, r"空腹(?:血糖|葡萄糖)|\bfpg\b|fasting\s+(?:plasma\s+)?glucose", divisor=18.0182, label="空腹血糖", issues=issues)
    systolic = _one([float(m.group("value")) for m in _match_values(text, (
        rf"(?:收缩压|高压|\bsbp\b|systolic\s+(?:blood\s+)?pressure)\s*(?:为|是|:|=)?\s*{NUM}(?:\s*mmhg)?",
        rf"(?:血压|blood\s+pressure|\bbp\b)\s*(?:为|是|:|=)?\s*{NUM}\s*/\s*\d{{2,3}}(?:\s*mmhg)?",
    ))], "收缩压", issues)
    triglyceride = _lab_values(text, r"甘油三酯|\btg\b|\btriglycerides?\b", divisor=88.57, label="甘油三酯", issues=issues)
    extracted = {"age_years": age, "bmi": bmi, "fasting_glucose_mmol_l": glucose,
                 "systolic_bp_mmhg": systolic, "triglyceride_mmol_l": triglyceride,
                 "known_diabetes_at_baseline": 0 if negative else None}
    missing = [FEATURE_LABELS[key] for key, value in extracted.items() if value is None]
    if issues:
        return {"kind": "needs_clarification", "message": "数值或单位有歧义，不能运行模型。", "extracted": extracted,
                "missing": missing, "issues": sorted(set(issues))}
    if missing:
        return {"kind": "needs_clarification", "message": "还缺少模型必需的基线信息；不能根据问题主题编造数值。",
                "extracted": extracted, "missing": missing, "issues": []}
    return {"kind": "diabetes_3y_ready", "message": "已提取完整基线输入；仅能进行未来 3 年新发糖尿病研究推断。",
            "extracted": extracted, "missing": [], "issues": []}
