"""Research-only neural training for MAPFM's prospective TFA extension.

The script refuses Q&A, cross-sectional diagnosis labels, wound masks, early
censoring as negatives, and missing governance records. It writes no patient
rows to the report or checkpoint and never activates a clinical endpoint.
"""

from __future__ import annotations

import argparse
import json
import random
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, brier_score_loss, roc_auc_score
from sklearn.model_selection import train_test_split

from mapfm_prospective_neural import (CHECKPOINT_DIR, REPORT_SCHEMA, TASKS, Cohort, CohortRejected,
                                      _sha256, load_cohort, validate_governance)


def build_model():
    """Construct a baseline-feature encoder with task-specific adapters/heads.

    Follow-up time defines the target label; this network does not consume a
    longitudinal sequence. The distinction matters for research reporting.
    """
    import torch
    from torch import nn

    class MAPFMProspectiveNet(nn.Module):
        def __init__(self) -> None:
            super().__init__()
            self.input_adapters = nn.ModuleDict({name: nn.Linear(len(spec["features"]), 32)
                                                 for name, spec in TASKS.items()})
            self.shared_baseline_encoder = nn.Sequential(
                nn.LayerNorm(32), nn.GELU(), nn.Linear(32, 32), nn.GELU(),
                nn.Dropout(0.1),
            )
            self.outcome_heads = nn.ModuleDict({name: nn.Linear(32, 1) for name in TASKS})

        def forward(self, values, task: str):
            latent = self.input_adapters[task](values)
            latent = self.shared_baseline_encoder(latent)
            return self.outcome_heads[task](latent).squeeze(-1)

    return MAPFMProspectiveNet()


def _bootstrap_test_intervals(labels: np.ndarray, probabilities: np.ndarray,
                              *, seed: int, draws: int = 1000) -> dict[str, list[float]]:
    """Descriptive percentile intervals for the *internal test set* only."""
    rng = np.random.default_rng(seed)
    values: dict[str, list[float]] = {"auroc": [], "average_precision": [], "brier": []}
    for _ in range(draws):
        sampled = rng.integers(0, len(labels), size=len(labels))
        y, p = labels[sampled], probabilities[sampled]
        if len(np.unique(y)) < 2:
            continue
        values["auroc"].append(float(roc_auc_score(y, p)))
        values["average_precision"].append(float(average_precision_score(y, p)))
        values["brier"].append(float(brier_score_loss(y, p)))
    if len(values["auroc"]) < draws // 2:
        raise CohortRejected("内部测试事件过少，无法给出稳定的重抽样区间。")
    return {name: [float(np.quantile(scores, 0.025)), float(np.quantile(scores, 0.975))]
            for name, scores in values.items()}


def _split_and_scale(cohort: Cohort, seed: int) -> dict:
    indices = np.arange(len(cohort.labels))
    train_idx, reserve_idx = train_test_split(indices, test_size=0.3, stratify=cohort.labels,
                                              random_state=seed)
    val_idx, test_idx = train_test_split(reserve_idx, test_size=0.5,
                                        stratify=cohort.labels[reserve_idx], random_state=seed)
    sets = {"train": train_idx, "validation": val_idx, "test": test_idx}
    if len({cohort.patient_ids[int(i)] for group in sets.values() for i in group}) != len(cohort.patient_ids):
        raise CohortRejected("患者级划分发生重叠。")
    means = cohort.features[train_idx].mean(axis=0)
    scales = cohort.features[train_idx].std(axis=0)
    scales[scales < 1e-6] = 1.0
    transformed = (cohort.features - means) / scales
    return {"sets": sets, "features": transformed.astype(np.float32),
            "mean": means.tolist(), "scale": scales.tolist()}


def train(cohorts: dict[str, Cohort], governance: dict[str, dict[str, str]],
          output_dir: Path = CHECKPOINT_DIR, *, epochs: int = 24,
          seed: int = 2026) -> dict:
    """Jointly optimize available tasks; evaluate once on held-out patients."""
    import torch
    from torch.nn import functional as F

    if not cohorts or set(cohorts) - set(TASKS) or set(cohorts) != set(governance):
        raise CohortRejected("任务、队列和授权记录不一致。")
    if not 1 <= epochs <= 200:
        raise CohortRejected("训练轮数必须在 1–200 之间。")
    checkpoint = output_dir / "mapfm_prospective_weights.pt"
    if checkpoint.exists() or (output_dir / "training_report.json").exists():
        raise CohortRejected("目标目录已有模型；为防覆盖，请指定一个新的输出目录。")
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.set_num_threads(min(4, torch.get_num_threads()))
    prepared = {task: _split_and_scale(cohort, seed) for task, cohort in cohorts.items()}
    model = build_model()
    optimizer = torch.optim.AdamW(model.parameters(), lr=6e-4, weight_decay=1e-3)
    best_loss = float("inf")
    best_weights = None
    stale = 0
    steps_per_task = 24
    for epoch in range(epochs):
        model.train()
        for task in sorted(cohorts):
            cohort, prep = cohorts[task], prepared[task]
            train_idx = prep["sets"]["train"]
            positives = max(1, int(cohort.labels[train_idx].sum()))
            pos_weight = min(20.0, (len(train_idx) - positives) / positives)
            for _ in range(steps_per_task):
                batch = np.random.choice(train_idx, size=min(256, len(train_idx)), replace=True)
                x = torch.from_numpy(prep["features"][batch])
                y = torch.from_numpy(cohort.labels[batch])
                optimizer.zero_grad()
                logits = model(x, task)
                loss = F.binary_cross_entropy_with_logits(
                    logits, y, pos_weight=torch.tensor(pos_weight, dtype=torch.float32))
                loss.backward()
                optimizer.step()
        model.eval()
        with torch.no_grad():
            losses = []
            for task in sorted(cohorts):
                cohort, prep = cohorts[task], prepared[task]
                idx = prep["sets"]["validation"]
                logits = model(torch.from_numpy(prep["features"][idx]), task)
                labels = torch.from_numpy(cohort.labels[idx])
                losses.append(float(F.binary_cross_entropy_with_logits(logits, labels)))
            validation_loss = float(np.mean(losses))
        if validation_loss < best_loss - 1e-4:
            best_loss = validation_loss
            best_weights = {key: value.detach().clone() for key, value in model.state_dict().items()}
            stale = 0
        else:
            stale += 1
            if stale >= 6:
                break
    assert best_weights is not None
    model.load_state_dict(best_weights)
    model.eval()
    task_reports = {}
    for task in sorted(cohorts):
        cohort, prep = cohorts[task], prepared[task]
        with torch.no_grad():
            val_logits = model(torch.from_numpy(prep["features"][prep["sets"]["validation"]]), task).numpy()
            test_logits = model(torch.from_numpy(prep["features"][prep["sets"]["test"]]), task).numpy()
        val_y = cohort.labels[prep["sets"]["validation"]].astype(int)
        test_y = cohort.labels[prep["sets"]["test"]].astype(int)
        if len(np.unique(val_y)) < 2 or len(np.unique(test_y)) < 2:
            raise CohortRejected("验证集或测试集缺少事件/非事件，不能评估。")
        calibrator = LogisticRegression(max_iter=2000, random_state=seed)
        calibrator.fit(val_logits.reshape(-1, 1), val_y)
        test_prob = calibrator.predict_proba(test_logits.reshape(-1, 1))[:, 1]
        task_reports[task] = {
            "trained": True,
            "horizon_days": TASKS[task]["horizon_days"],
            "features": list(TASKS[task]["features"]),
            "source_sha256": cohort.source_sha256,
            "source_uri": governance[task]["source_uri"],
            "license_or_dua": governance[task]["license_or_dua"],
            "approval_reference": governance[task]["approval_reference"],
            "eligible_rows": len(cohort.labels),
            "excluded_early_censor": cohort.excluded_early_censor,
            "split": {part: {"rows": len(idx), "events": int(cohort.labels[idx].sum())}
                      for part, idx in prep["sets"].items()},
            "test_auroc": float(roc_auc_score(test_y, test_prob)),
            "test_average_precision": float(average_precision_score(test_y, test_prob)),
            "test_brier": float(brier_score_loss(test_y, test_prob)),
            "test_event_rate": float(np.mean(test_y)),
            "train_feature_mean": prep["mean"],
            "train_feature_scale": prep["scale"],
            "train_feature_min": np.min(cohort.features[prep["sets"]["train"]], axis=0).tolist(),
            "train_feature_max": np.max(cohort.features[prep["sets"]["train"]], axis=0).tolist(),
            "test_bootstrap_95ci": _bootstrap_test_intervals(test_y, test_prob, seed=seed),
            "test_bootstrap_draws": 1000,
            "platt_coef": float(calibrator.coef_[0, 0]),
            "platt_intercept": float(calibrator.intercept_[0]),
        }
    output_dir.mkdir(parents=True, exist_ok=True)
    torch.save(model.state_dict(), checkpoint)
    report = {
        "schema": REPORT_SCHEMA,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "checkpoint_sha256": _sha256(checkpoint),
        "architecture": "MAPFM TFA extension: baseline-feature MLP with task-specific adapters and heads",
        "epochs_completed": epoch + 1,
        "patient_disjoint_internal_split": True,
        "external_validation_completed": False,
        "clinical_use_allowed": False,
        "tasks": task_reports,
        "limitations": "Retrospective internal holdout only; not external or prospective clinical validation.",
    }
    (output_dir / "training_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Train research-only MAPFM TFA outcome heads")
    for task in TASKS:
        parser.add_argument(f"--{task.replace('_', '-')}-csv", type=Path)
        parser.add_argument(f"--{task.replace('_', '-')}-governance", type=Path)
    parser.add_argument("--output-dir", type=Path, default=CHECKPOINT_DIR)
    parser.add_argument("--epochs", type=int, default=24)
    args = parser.parse_args()
    cohorts, governance = {}, {}
    for task in TASKS:
        prefix = task
        path = getattr(args, f"{prefix}_csv")
        manifest = getattr(args, f"{prefix}_governance")
        if bool(path) != bool(manifest):
            parser.error(f"{task}: CSV 和来源授权记录必须同时提供。")
        if path:
            governance[task] = validate_governance(manifest, task)
            cohorts[task] = load_cohort(path, task)
    if not cohorts:
        parser.error("没有提供可训练的真实随访队列；不会生成模型权重。")
    try:
        report = train(cohorts, governance, args.output_dir, epochs=args.epochs)
    except CohortRejected as exc:
        parser.error(str(exc))
    print(json.dumps({"trained_tasks": list(report["tasks"]),
                      "clinical_use_allowed": False,
                      "report": str(args.output_dir / "training_report.json")}, ensure_ascii=False))


if __name__ == "__main__":
    main()
