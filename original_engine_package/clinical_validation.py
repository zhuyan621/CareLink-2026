"""Leakage controls and clinical-readiness gating for the research system."""
from __future__ import annotations

import json
import hashlib
import hmac
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

import pandas as pd
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import GroupShuffleSplit


def normalize_question(text: str) -> str:
    """Create a stable group key so duplicate/rephrased-whitespace rows stay together."""
    value = re.sub(r"[^a-z0-9]+", " ", str(text).lower())
    return re.sub(r"\s+", " ", value).strip()


def label_mention_mask(question: str, label: str) -> str:
    """Mask exact disease-label mentions for an explicit leakage stress test."""
    masked = str(question)
    terms = {str(label).strip()}
    terms.update(part.strip() for part in re.split(r"[/,;()]", str(label)) if part.strip())
    for term in sorted(terms, key=len, reverse=True):
        if len(term) >= 3:
            masked = re.sub(re.escape(term), "[DISEASE]", masked, flags=re.IGNORECASE)
    return masked


def probability_calibration_metrics(
    confidences: Sequence[float], correct: Sequence[bool], bins: int = 10
) -> Dict[str, Any]:
    """Return Brier score, ECE, and logistic calibration intercept/slope."""
    if len(confidences) == 0 or len(confidences) != len(correct):
        return {"available": False, "reason": "missing_or_mismatched_inputs"}
    probabilities = np.clip(np.asarray(confidences, dtype=float), 1e-6, 1 - 1e-6)
    outcomes = np.asarray(correct, dtype=int)
    brier = float(np.mean((probabilities - outcomes) ** 2))
    edges = np.linspace(0.0, 1.0, num=max(int(bins), 2) + 1)
    ece = 0.0
    for left, right in zip(edges[:-1], edges[1:]):
        mask = (probabilities >= left) & (probabilities < right if right < 1.0 else probabilities <= right)
        if mask.any():
            ece += float(mask.mean()) * abs(float(probabilities[mask].mean()) - float(outcomes[mask].mean()))
    intercept = None
    slope = None
    if len(outcomes) >= 10 and len(np.unique(outcomes)) == 2:
        logits = np.log(probabilities / (1.0 - probabilities)).reshape(-1, 1)
        model = LogisticRegression(C=1e6, solver="lbfgs").fit(logits, outcomes)
        intercept = float(model.intercept_[0])
        slope = float(model.coef_[0, 0])
    return {
        "available": True,
        "n": len(outcomes),
        "brier_score": brier,
        "expected_calibration_error": float(ece),
        "calibration_intercept": intercept,
        "calibration_slope": slope,
    }


def grouped_train_test_split(
    dataframe: pd.DataFrame,
    *,
    test_size: float = 0.2,
    random_seed: int = 42,
    group_column: Optional[str] = None,
) -> Tuple[pd.DataFrame, pd.DataFrame, Dict[str, Any]]:
    """Split by patient/source group or normalized question, never by individual row."""
    if dataframe.empty:
        empty = dataframe.copy()
        return empty, empty, {"passed": True, "reason": "empty_dataset"}
    data = dataframe.copy().reset_index(drop=True)
    if group_column and group_column in data.columns:
        groups = data[group_column].fillna("").astype(str)
        strategy = f"group_column:{group_column}"
    elif "patient_id" in data.columns and data["patient_id"].fillna("").astype(str).str.strip().ne("").any():
        patient_groups = data["patient_id"].fillna("").astype(str).str.strip()
        fallback_groups = data["question"].map(normalize_question)
        groups = patient_groups.where(patient_groups.ne(""), "question:" + fallback_groups)
        strategy = "patient_id_with_question_fallback"
    else:
        groups = data["question"].map(normalize_question)
        strategy = "normalized_question"

    splitter = GroupShuffleSplit(n_splits=64, test_size=test_size, random_state=random_seed)
    labels = set(data["area"].astype(str))
    best: Optional[Tuple[List[int], List[int], float]] = None
    for train_idx, test_idx in splitter.split(data, groups=groups):
        train_labels = set(data.iloc[train_idx]["area"].astype(str))
        test_labels = set(data.iloc[test_idx]["area"].astype(str))
        missing_train = len(labels - train_labels)
        size_error = abs(len(test_idx) / len(data) - test_size)
        score = missing_train * 100.0 + len(labels - test_labels) + size_error
        if best is None or score < best[2]:
            best = (train_idx.tolist(), test_idx.tolist(), score)
    if best is None:
        raise ValueError("Unable to construct a grouped train/test split")
    train = data.iloc[best[0]].reset_index(drop=True)
    test = data.iloc[best[1]].reset_index(drop=True)
    audit = audit_split(train, test, strategy=strategy)
    return train, test, audit


def audit_split(train: pd.DataFrame, test: pd.DataFrame, *, strategy: str = "unknown") -> Dict[str, Any]:
    train_groups = set(train["question"].map(normalize_question)) if "question" in train else set()
    test_groups = set(test["question"].map(normalize_question)) if "question" in test else set()
    overlap = sorted(train_groups & test_groups)
    patient_overlap: List[str] = []
    if "patient_id" in train.columns and "patient_id" in test.columns:
        train_patients = set(train["patient_id"].fillna("").astype(str).str.strip()) - {""}
        test_patients = set(test["patient_id"].fillna("").astype(str).str.strip()) - {""}
        patient_overlap = sorted(train_patients & test_patients)
    mention_rows = 0
    for _, row in test.iterrows():
        label = str(row.get("area", "")).strip().lower()
        if label and label in str(row.get("question", "")).lower():
            mention_rows += 1
    return {
        "passed": len(overlap) == 0 and len(patient_overlap) == 0,
        "strategy": strategy,
        "train_rows": len(train),
        "test_rows": len(test),
        "train_unique_groups": len(train_groups),
        "test_unique_groups": len(test_groups),
        "overlapping_question_groups": len(overlap),
        "overlap_examples": overlap[:5],
        "overlapping_patient_groups": len(patient_overlap),
        "patient_overlap_examples": patient_overlap[:5],
        "test_exact_label_mention_rows": mention_rows,
        "test_exact_label_mention_rate": mention_rows / max(len(test), 1),
        "warning": "Label mentions must be reported separately; masking them is a stress test, not a substitute for external validation.",
    }


@dataclass
class ClinicalReadinessReport:
    clinical_use_allowed: bool
    status: str
    checks: Dict[str, bool]
    blockers: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def as_dict(self) -> Dict[str, Any]:
        return {
            "clinical_use_allowed": self.clinical_use_allowed,
            "status": self.status,
            "checks": self.checks,
            "blockers": self.blockers,
            "warnings": self.warnings,
        }


class ClinicalReadinessGate:
    """Fail closed unless every declared clinical validation artifact is present."""

    def __init__(self, validation_artifact: str = "", require_validation: bool = True) -> None:
        self.validation_artifact = str(validation_artifact or "")
        self.require_validation = bool(require_validation)

    def _artifact_is_valid(self) -> bool:
        if not self.validation_artifact:
            return False
        path = Path(self.validation_artifact)
        if not path.is_file():
            return False
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return False
        required = {
            "dataset", "intended_use", "external_validation", "calibration", "approved_by",
            "protocol_sha256", "result_report_sha256", "signature",
        }
        if not required.issubset(payload) or payload.get("external_validation") is not True:
            return False
        calibration = payload.get("calibration") or {}
        metrics_present = all(
            calibration.get(name) is not None
            for name in ("brier_score", "calibration_intercept", "calibration_slope")
        )
        reviewers = payload.get("approved_by") or []
        hashes_valid = all(
            re.fullmatch(r"[0-9a-f]{64}", str(payload.get(name, "")))
            for name in ("protocol_sha256", "result_report_sha256")
        )
        secret = os.getenv("MAPFM_VALIDATION_SIGNING_SECRET", "").encode("utf-8")
        if not (metrics_present and isinstance(reviewers, list) and len(reviewers) >= 2 and hashes_valid and secret):
            return False
        unsigned = {key: value for key, value in payload.items() if key != "signature"}
        canonical = json.dumps(unsigned, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
        expected = hmac.new(secret, canonical, hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, str(payload.get("signature", "")))

    def evaluate(
        self,
        *,
        split_audit: Dict[str, Any],
        tfa_prediction: Optional[Dict[str, Any]],
        verification_summary: Dict[str, Any],
    ) -> ClinicalReadinessReport:
        tfa_valid = tfa_prediction is None or bool(tfa_prediction.get("validated", False))
        checks = {
            "zero_group_overlap": bool(split_audit.get("passed", False)),
            "external_validation_artifact": self._artifact_is_valid(),
            "temporal_model_validated": tfa_valid,
            "evidence_scope_declared": bool(verification_summary.get("verification_scope")),
        }
        blockers: List[str] = []
        if not checks["zero_group_overlap"]:
            blockers.append("训练集与测试集存在重复问题/患者组泄漏")
        if not checks["external_validation_artifact"]:
            blockers.append("缺少包含外部验证与校准结果的临床验证工件")
        if not checks["temporal_model_validated"]:
            blockers.append("时序模型没有与当前结局定义匹配的已验证检查点")
        if not checks["evidence_scope_declared"]:
            blockers.append("证据核验范围未声明")
        allowed = all(checks.values()) if self.require_validation else False
        return ClinicalReadinessReport(
            clinical_use_allowed=allowed,
            status="clinical_validation_passed" if allowed else "research_only",
            checks=checks,
            blockers=blockers,
            warnings=["本系统用于科研与竞赛演示，不替代医生判断。"] if not allowed else [],
        )
