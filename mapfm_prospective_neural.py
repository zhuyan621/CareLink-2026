"""Trainable MAPFM temporal extension for *observed future* disease events.

This module adds neural capacity to the original TFA agent. It does not claim
that the historical MAPFM package contained trained prognosis weights. No
prediction is enabled unless a real, governed longitudinal cohort has been
trained and an independent research holdout has been evaluated.
"""

from __future__ import annotations

import csv
import hashlib
import json
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

import numpy as np


ROOT = Path(__file__).resolve().parent
REPORT_SCHEMA = "careguard.mapfm.prospective-neural.v2"
MODEL_ID = "mapfm_tfa_prospective_neural_v2"
TASKS = {
    "diabetes_onset": {
        "horizon_days": 1095,
        "event_flag": "diabetes_event",
        "features": ("age_years", "bmi", "fasting_glucose_mmol_l",
                     "systolic_bp_mmhg", "triglyceride_mmol_l"),
        "baseline_diabetes": "0",
    },
    "foot_ulcer_onset": {
        "horizon_days": 730,
        "event_flag": "foot_ulcer_event",
        "features": ("age_years", "diabetes_duration_years",
                     "monofilament_insensitive", "any_pedal_pulse_absent",
                     "prior_foot_ulcer_or_amputation"),
        "baseline_diabetes": "1",
    },
}
CHECKPOINT_DIR = ROOT / "artifacts" / "prospective_neural"
MIN_ROWS = 300
MIN_EVENTS = 60


class CohortRejected(ValueError):
    """A cohort cannot safely provide prospective training labels."""


@dataclass(frozen=True)
class Cohort:
    task: str
    patient_ids: tuple[str, ...]
    features: np.ndarray
    labels: np.ndarray
    source_sha256: str
    excluded_early_censor: int


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_governance(manifest_path: Path, task: str) -> dict[str, str]:
    """Require an explicit, task-matched research-use record before training."""
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise CohortRejected("缺少可读取的数据来源与使用授权记录。") from exc
    required = ("task", "source_uri", "license_or_dua", "approval_reference")
    if manifest.get("task") != task or not all(str(manifest.get(k, "")).strip() for k in required):
        raise CohortRejected("来源记录必须匹配任务，并写明 URI、许可/DUA 和审批依据。")
    if manifest.get("research_use_authorized") is not True:
        raise CohortRejected("研究使用授权未被明确确认。")
    return {key: str(manifest[key]) for key in required}


def load_cohort(path: Path, task: str, *, min_rows: int = MIN_ROWS,
                min_events: int = MIN_EVENTS) -> Cohort:
    """Create fixed-horizon labels only from event dates and adequate follow-up.

    An event is positive only if its observed event_date is at or before the
    horizon. Event-free follow-up ending early is censored, never a negative.
    Events after the horizon are negative *at that horizon* if observation
    reached the horizon. One row per patient prevents within-person leakage.
    """
    if task not in TASKS:
        raise CohortRejected("未知的前瞻性任务。")
    spec = TASKS[task]
    required = {"participant_id", spec["event_flag"], "known_diabetes_at_baseline", *spec["features"]}
    if task == "foot_ulcer_onset":
        required.add("current_foot_ulcer_at_baseline")
    ids: list[str] = []
    vectors: list[list[float]] = []
    labels: list[int] = []
    seen: set[str] = set()
    excluded = 0
    try:
        with path.open(encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            columns = set(reader.fieldnames or [])
            date_mode = {"baseline_date", "followup_date", "event_date"} <= columns
            duration_mode = "time_to_event_or_censor_days" in columns
            if not date_mode and not duration_mode:
                raise CohortRejected("必须提供完整事件日期，或明确的事件/删失时长。")
            missing = required - columns
            if missing:
                raise CohortRejected("缺少训练字段：" + ", ".join(sorted(missing)))
            for row in reader:
                patient_id = (row["participant_id"] or "").strip()
                if not patient_id or patient_id in seen:
                    raise CohortRejected("患者 ID 缺失或重复；需要每人一条基线记录。")
                seen.add(patient_id)
                if row["known_diabetes_at_baseline"] != spec["baseline_diabetes"]:
                    raise CohortRejected("基线糖尿病状态与任务人群不符。")
                if task == "foot_ulcer_onset" and row["current_foot_ulcer_at_baseline"] != "0":
                    raise CohortRejected("足溃疡发生队列必须在基线无当前溃疡。")
                try:
                    values = [float(row[name]) for name in spec["features"]]
                except (TypeError, ValueError, OverflowError) as exc:
                    raise CohortRejected("基线特征无效。") from exc
                if not np.isfinite(values).all():
                    raise CohortRejected("基线特征包含非有限数值。")
                flag = row[spec["event_flag"]]
                if flag not in ("0", "1"):
                    raise CohortRejected("事件标志必须为 0 或 1。")
                if date_mode:
                    try:
                        baseline = date.fromisoformat(row["baseline_date"])
                        followup = date.fromisoformat(row["followup_date"])
                        event = date.fromisoformat(row["event_date"]) if row["event_date"] else None
                    except (TypeError, ValueError, OverflowError) as exc:
                        raise CohortRejected("日期需为 YYYY-MM-DD。") from exc
                    if followup <= baseline or (event and not baseline < event <= followup):
                        raise CohortRejected("事件/随访日期时序错误。")
                    if (flag == "1") != (event is not None):
                        raise CohortRejected("事件标志与事件日期不一致。")
                    observed_days = (event - baseline).days if event else (followup - baseline).days
                else:
                    try:
                        observed_days = float(row["time_to_event_or_censor_days"])
                    except (TypeError, ValueError, OverflowError) as exc:
                        raise CohortRejected("事件/删失时长必须为正数天。") from exc
                    if not np.isfinite(observed_days) or observed_days <= 0:
                        raise CohortRejected("事件/删失时长必须为正数天。")
                if task == "diabetes_onset" and not 0 < values[2] < 7.0:
                    raise CohortRejected("糖尿病新发队列基线空腹血糖需小于 7 mmol/L。")
                if task == "foot_ulcer_onset" and any(value not in (0, 1) for value in values[2:]):
                    raise CohortRejected("足部检查的三个二元字段必须为 0 或 1。")
                horizon = spec["horizon_days"]
                if flag == "0" and observed_days < horizon:
                    excluded += 1
                    continue
                label = int(flag == "1" and observed_days <= horizon)
                ids.append(patient_id)
                vectors.append(values)
                labels.append(label)
    except (OSError, UnicodeError, csv.Error) as exc:
        raise CohortRejected("无法安全读取 UTF-8 随访 CSV。") from exc
    if len(ids) < min_rows or sum(labels) < min_events or len(ids) - sum(labels) < min_events:
        raise CohortRejected("可判定结局的样本/事件不足；不能训练前瞻性神经模型。")
    return Cohort(task, tuple(ids), np.asarray(vectors, dtype=np.float32),
                  np.asarray(labels, dtype=np.float32), _sha256(path), excluded)


def neural_status(root: Path = ROOT) -> dict[str, Any]:
    """Report only aggregate checkpoint status; never expose patient rows."""
    report_path = root / "artifacts" / "prospective_neural" / "training_report.json"
    if not report_path.is_file():
        return {
            "architecture": "MAPFM TFA baseline-feature neural research extension",
            "trained_tasks": [],
            "clinical_use_allowed": False,
            "internal_validation": {},
            "reason": "没有经过核验的未来糖尿病研究权重；神经输出关闭。",
        }
    checkpoint = root / "artifacts" / "prospective_neural" / "mapfm_prospective_weights.pt"
    try:
        report = json.loads(report_path.read_text(encoding="utf-8"))
        integrity_ok = (checkpoint.is_file() and report.get("checkpoint_sha256") == _sha256(checkpoint)
                        and report.get("schema") == REPORT_SCHEMA)
        trained = (["diabetes_onset"] if integrity_ok and
                   report.get("tasks", {}).get("diabetes_onset", {}).get("trained") is True else [])
        validation = ({task: {
            "test_rows": int(report["tasks"][task]["split"]["test"]["rows"]),
            "test_events": int(report["tasks"][task]["split"]["test"]["events"]),
            "auroc": float(report["tasks"][task]["test_auroc"]),
            "auroc_95ci": report["tasks"][task]["test_bootstrap_95ci"]["auroc"],
            "external_validation_completed": False,
        } for task in trained})
    except (OSError, UnicodeError, ValueError, TypeError, KeyError, AttributeError):
        trained = []
        validation = {}
    return {
        "architecture": "MAPFM TFA baseline-feature neural research extension",
        "trained_tasks": trained,
        "clinical_use_allowed": False,
        "internal_validation": validation,
        "reason": "仅为研究训练状态；即使内部留出集通过，仍需外部验证和临床审批。",
    }


def research_predict(task: str, baseline_values: dict[str, float], *, root: Path = ROOT) -> dict[str, Any]:
    """Use a verified real checkpoint for research inference, never a rule score.

    This is intentionally separate from the published-rule API. It remains
    unavailable while training data or weights are absent.
    """
    if task not in TASKS:
        raise CohortRejected("未知的前瞻性任务。")
    status = neural_status(root)
    if task not in status["trained_tasks"]:
        raise CohortRejected("该任务没有经过真实随访数据训练的完整检查点。")
    spec = TASKS[task]
    expected = set(spec["features"]) | {"known_diabetes_at_baseline"}
    if task == "foot_ulcer_onset":
        expected.add("current_foot_ulcer_at_baseline")
    if set(baseline_values) != expected:
        raise CohortRejected("输入字段必须与训练时的基线字段完全一致。")
    if baseline_values["known_diabetes_at_baseline"] not in (0, 1) or int(
        baseline_values["known_diabetes_at_baseline"]) != int(spec["baseline_diabetes"]):
        raise CohortRejected("基线糖尿病状态与任务适用人群不符。")
    if task == "foot_ulcer_onset" and baseline_values["current_foot_ulcer_at_baseline"] != 0:
        raise CohortRejected("当前已有足溃疡者不适用发生风险模型。")
    try:
        values = np.asarray([float(baseline_values[name]) for name in spec["features"]], dtype=np.float32)
    except (ValueError, TypeError, OverflowError) as exc:
        raise CohortRejected("基线特征必须为有效数值。") from exc
    if not np.isfinite(values).all() or values[0] < 18 or values[0] > 110:
        raise CohortRejected("基线特征超出有效范围。")
    if task == "diabetes_onset" and not 0 < values[2] < 7:
        raise CohortRejected("基线空腹血糖须小于 7 mmol/L，且不能缺失。")
    if task == "foot_ulcer_onset" and any(value not in (0, 1) for value in values[2:]):
        raise CohortRejected("足部检查字段必须明确为 0 或 1。")
    report = json.loads((root / "artifacts" / "prospective_neural" / "training_report.json").read_text(encoding="utf-8"))
    meta = report["tasks"][task]
    lower, upper = meta.get("train_feature_min"), meta.get("train_feature_max")
    if not isinstance(lower, list) or not isinstance(upper, list) or len(lower) != len(values) or len(upper) != len(values):
        raise CohortRejected("检查点缺少训练输入范围，拒绝研究推断。")
    if np.any(values < np.asarray(lower, dtype=np.float32) - 1e-5) or np.any(
        values > np.asarray(upper, dtype=np.float32) + 1e-5
    ):
        raise CohortRejected("输入超出训练队列的基线观察范围；研究模型拒绝外推。")
    normalized = (values - np.asarray(meta["train_feature_mean"], dtype=np.float32)) / np.asarray(
        meta["train_feature_scale"], dtype=np.float32)
    import torch
    from train_mapfm_prospective import build_model

    model = build_model()
    checkpoint = root / "artifacts" / "prospective_neural" / "mapfm_prospective_weights.pt"
    model.load_state_dict(torch.load(checkpoint, map_location="cpu", weights_only=True))
    model.eval()
    with torch.no_grad():
        logit = float(model(torch.from_numpy(normalized.reshape(1, -1)), task)[0])
    calibrated_logit = float(meta["platt_coef"]) * logit + float(meta["platt_intercept"])
    probability = float(1 / (1 + np.exp(-np.clip(calibrated_logit, -30, 30))))
    return {
        "model": MODEL_ID,
        "task": task,
        "horizon_days": spec["horizon_days"],
        "research_probability": probability,
        "checkpoint_sha256": report["checkpoint_sha256"],
        "external_validation_completed": False,
        "clinical_use_allowed": False,
        "note": "仅用于研究演示；内部留出集性能不等于外部或临床验证。",
    }


def attach_to_tfa(ecosystem: Any) -> None:
    """Make the trainable pathway a TFA capability, not a substitute rule score."""
    ecosystem.tfa.prospective_neural_status = neural_status
    ecosystem.tfa.forecast_prospective = research_predict
    ecosystem.maintenance_agent.register(ecosystem.tfa)
