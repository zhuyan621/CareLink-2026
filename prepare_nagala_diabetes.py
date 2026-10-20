"""Convert the verified public NAGALA workbook into a 3-year incident-DM cohort.

Only baseline measurements are exported. Follow-up duration is the observed
time to first incident diabetes or censoring, not a made-up calendar date.
The input is the Okamura et al. Dryad dataset DOI 10.5061/dryad.8q0p192,
downloaded from its Zenodo mirror (record 4996032).
"""

from __future__ import annotations

import argparse
import csv
import hashlib
from pathlib import Path

import numpy as np
import pandas as pd


SOURCE_MD5 = "47edfb147078657a0eecfff7f9364532"
COLUMNS = {
    "participant_id": "Patient Number",
    "age_years": "Baseline Age, yrs",
    "bmi": "Baseline BMI, kg/m2",
    "fasting_glucose_mmol_l": "Baseline Fasting plasma glucose, mmol/L",
    "systolic_bp_mmhg": "Baseline Systolic blood pressure, mmHg",
    "triglyceride_mmol_l": "Baseline Triglycerides, mmol/L",
    "time_to_event_or_censor_days": "Follow up duration, days",
    "diabetes_event": "Incident DM 0/1",
}


def convert(source: Path, output: Path) -> dict[str, int]:
    digest = hashlib.md5(source.read_bytes()).hexdigest()
    if digest != SOURCE_MD5:
        raise ValueError("源文件 MD5 不匹配官方公开版本；拒绝转换。")
    frame = pd.read_excel(source, sheet_name=0)
    missing = set(COLUMNS.values()) - set(frame.columns)
    if missing:
        raise ValueError(f"源数据缺少字段: {sorted(missing)}")
    if len(frame) != 15464 or int(frame[COLUMNS["diabetes_event"]].sum()) != 373:
        raise ValueError("源数据人数或结局数与原始发表队列不一致。")
    if frame[COLUMNS["participant_id"]].isna().any() or not frame[COLUMNS["participant_id"]].is_unique:
        raise ValueError("源数据患者 ID 缺失或重复。")
    numeric_columns = [name for key, name in COLUMNS.items() if key != "participant_id"]
    numeric = frame[numeric_columns].apply(pd.to_numeric, errors="raise")
    if numeric.isna().any().any() or not np.isfinite(numeric.to_numpy(dtype=float)).all():
        raise ValueError("源数据包含缺失或非有限的训练字段。")
    if not numeric[COLUMNS["diabetes_event"]].isin((0, 1)).all():
        raise ValueError("源数据结局不是二元新发糖尿病状态。")
    if (numeric[COLUMNS["time_to_event_or_censor_days"]] <= 0).any():
        raise ValueError("源数据事件/删失时间无效。")
    glucose = numeric[COLUMNS["fasting_glucose_mmol_l"]]
    if not glucose.between(0.01, 6.999).all():
        raise ValueError("源队列包含基线已达糖尿病阈值或无效血糖。")
    if (numeric[COLUMNS["age_years"]] < 18).any():
        raise ValueError("源数据包含未成年人。")

    fields = ["participant_id", "known_diabetes_at_baseline", "diabetes_event",
              "time_to_event_or_censor_days", "age_years", "bmi",
              "fasting_glucose_mmol_l", "systolic_bp_mmhg", "triglyceride_mmol_l"]
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for _, record in frame.iterrows():
            row = {key: record[name] for key, name in COLUMNS.items()}
            row["participant_id"] = f"nagala-{int(row['participant_id'])}"
            row["known_diabetes_at_baseline"] = 0
            row["diabetes_event"] = int(row["diabetes_event"])
            row["time_to_event_or_censor_days"] = int(row["time_to_event_or_censor_days"])
            writer.writerow({field: row[field] for field in fields})
    horizon = 1095
    times = numeric[COLUMNS["time_to_event_or_censor_days"]]
    events = numeric[COLUMNS["diabetes_event"]]
    return {
        "source_rows": len(frame),
        "source_events_all_followup": int(events.sum()),
        "events_within_3y": int(((events == 1) & (times <= horizon)).sum()),
        "excluded_early_censor_3y": int(((events == 0) & (times < horizon)).sum()),
        "decidable_3y_rows": int(((events == 1) | (times >= horizon)).sum()),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("--output", type=Path, default=Path("data/prospective/diabetes_onset.csv"))
    args = parser.parse_args()
    print(convert(args.source, args.output))


if __name__ == "__main__":
    main()
