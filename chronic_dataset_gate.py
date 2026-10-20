"""Read-only intake gate for prospective chronic-disease cohorts.

Checks structure and temporal order only. A passing schema does not establish
consent, representativeness, calibration, external validation, or clinical use.
Patient identifiers and record values are never returned by the API.
"""

from __future__ import annotations

import csv
import json
from datetime import date
from pathlib import Path


ROOT = Path(__file__).resolve().parent
TASKS = {
    "diabetes_onset": {
        "file": "diabetes_onset.csv",
        "event": "diabetes_event",
        "baseline_disease": "known_diabetes_at_baseline",
        "baseline_allowed": "0",
        "predictors": {"age_years", "bmi", "fasting_glucose_mmol_l",
                       "systolic_bp_mmhg", "triglyceride_mmol_l"},
    },
}
COMMON_COLUMNS = {"participant_id"}
MAX_AUDIT_ROWS = 1_000_000


def audit_candidate_csv(path: Path, task: str) -> dict:
    """Audit a local CSV without returning identifiable row data."""
    if task not in TASKS:
        raise ValueError(f"Unknown prospective task: {task}")
    schema = TASKS[task]
    required = COMMON_COLUMNS | {schema["event"], schema["baseline_disease"]} | schema["predictors"]
    issues: list[str] = []
    rows = 0
    events = 0
    seen: set[str] = set()
    if not path.is_file():
        return {"task": task, "present": False, "schema_compatible": False,
                "rows_checked": 0, "event_count": 0, "issues": ["未提供纵向随访 CSV。"],
                "approved_for_training": False}
    try:
        with path.open(encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            columns = set(reader.fieldnames or [])
            date_mode = {"baseline_date", "followup_date", "event_date"} <= columns
            duration_mode = "time_to_event_or_censor_days" in columns
            missing = sorted(required - columns)
            if missing:
                issues.append("缺少必要字段：" + ", ".join(missing))
            if not date_mode and not duration_mode:
                issues.append("缺少时间字段：baseline_date、followup_date、event_date，或 time_to_event_or_censor_days。")
            if not missing and (date_mode or duration_mode):
                for row in reader:
                    rows += 1
                    if rows > MAX_AUDIT_ROWS:
                        issues.append("超过审计行数上限；请分批处理并保存患者级划分方案。")
                        break
                    participant = (row["participant_id"] or "").strip()
                    if not participant or participant in seen:
                        issues.append("患者 ID 缺失或重复；当前入口要求每人一条基线记录。")
                    seen.add(participant)
                    if date_mode:
                        try:
                            baseline = date.fromisoformat(row["baseline_date"])
                            followup = date.fromisoformat(row["followup_date"])
                            if followup <= baseline:
                                issues.append("随访日期必须晚于基线日期。")
                            event_date = date.fromisoformat(row["event_date"]) if row["event_date"] else None
                            if event_date and not baseline < event_date <= followup:
                                issues.append("事件日期必须晚于基线、不晚于最后随访。")
                        except (TypeError, ValueError):
                            issues.append("日期必须是 YYYY-MM-DD，且不能缺失。")
                    else:
                        try:
                            duration = float(row["time_to_event_or_censor_days"])
                            if not 0 < duration < 40000:
                                issues.append("事件/删失时长必须为合理的正数天。")
                        except (TypeError, ValueError):
                            issues.append("事件/删失时长必须为合理的正数天。")
                    if row[schema["event"]] not in {"0", "1"}:
                        issues.append("随访事件必须明确为 0 或 1；失访/删失需另行建模。")
                    else:
                        events += row[schema["event"]] == "1"
                        if date_mode and (row[schema["event"]] == "1") != bool(row["event_date"]):
                            issues.append("事件标志必须与实际事件日期一致。")
                    if row[schema["baseline_disease"]] != schema["baseline_allowed"]:
                        issues.append("基线疾病状态与该任务的适用人群不符。")
                    for predictor in schema["predictors"]:
                        if not (row[predictor] or "").strip():
                            issues.append("必要基线预测字段存在空值。")
            if rows == 0 and not missing and (date_mode or duration_mode):
                issues.append("CSV 没有数据行。")
            if events == 0 and rows:
                issues.append("没有记录到随访事件，无法拟合事件风险模型。")
    except (OSError, UnicodeError, csv.Error):
        issues.append("无法以 UTF-8 CSV 安全读取文件。")
    # Errors are categories only; no patient IDs, dates, or feature values escape.
    issues = list(dict.fromkeys(issues))
    return {"task": task, "present": True, "schema_compatible": not issues,
            "rows_checked": min(rows, MAX_AUDIT_ROWS), "event_count": events,
            "issues": issues,
            "approved_for_training": False,
            "approval_note": "结构检查通过也不代表获得数据授权、伦理审批、外部验证或临床使用许可。"}


def audit_local_sources(root: Path = ROOT) -> dict:
    """Summarize actual bundled sources and fixed, non-public candidate slots."""
    qa = root / "medNo.22.csv"
    with qa.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        qa_columns = set(reader.fieldnames or [])
        qa_rows = sum(1 for _ in reader)
    report_path = root / "artifacts" / "medquad_qa" / "training_report.json"
    report = json.loads(report_path.read_text(encoding="utf-8")) if report_path.exists() else {}
    candidates = {
        task: audit_candidate_csv(root / "data" / "prospective" / spec["file"], task)
        for task, spec in TASKS.items()
    }
    return {
        "sources": [
            {"name": "medNo.22.csv", "kind": "medical_qa", "rows": qa_rows,
             "has_patient_followup": {"participant_id", "baseline_date", "followup_date"} <= qa_columns,
             "suitable_for_future_onset_training": False},
            {"name": "MedQuAD", "kind": "medical_qa", "rows": report.get("qa_pairs_total"),
             "answer_bearing_pairs": report.get("answer_bearing_pairs"),
             "has_patient_followup": False, "suitable_for_future_onset_training": False},
        ],
        "candidate_cohorts": candidates,
        "own_prospective_model_trained": False,
        "clinical_use_allowed": False,
        "note": "结构审计仅用于决定是否进入下一步数据治理；医学问答不能当成未来事件随访。",
    }
