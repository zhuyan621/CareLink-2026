import csv
from pathlib import Path

from careguard_cases import SAMPLE_CASES, clinical_text_for_case


def test_all_synthetic_cases_have_structured_vitals_without_fake_time_series():
    assert len(SAMPLE_CASES) == 6
    for case in SAMPLE_CASES.values():
        text = clinical_text_for_case(case)
        assert case["note"] in text
        assert "生命体征" in text
        assert "time_series" not in case


def test_added_cases_match_single_rows_in_demo_vitals_csv():
    csv_path = Path(__file__).resolve().parent.parent / "demo_assets" / "sample_vitals.csv"
    with csv_path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    for name, row_index in [("夜班单次记录", 0), ("复测语境待核对", 1), ("交接信息缺口", 2)]:
        case = SAMPLE_CASES[name]
        row = rows[row_index]
        assert case["vitals"] == {
            "heart_rate": int(row["heart_rate"]),
            "spo2": int(row["spo2"]),
            "temperature": float(row["temperature"]),
            "respiratory_rate": int(row["respiratory_rate"]),
        }
        assert case["source"] == f"demo_assets/sample_vitals.csv:{row_index + 2}"
