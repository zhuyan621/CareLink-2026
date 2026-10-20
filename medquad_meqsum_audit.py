"""Read-only provenance and overlap audit for the official MeQSum workbook."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from xml.etree import ElementTree

import pandas as pd


ROOT = Path(__file__).resolve().parent
BASE = ROOT / "artifacts/medquad_qa_candidate"
SOURCE = BASE / "meqsum_official.xlsx"
SOURCE_URL = "https://github.com/abachaa/MeQSum/blob/master/MeQSum_ACL2019_BenAbacha_Demner-Fushman.xlsx"


def normal(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", str(value).casefold()).strip()


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_rows() -> list[dict]:
    frame = pd.read_excel(SOURCE, sheet_name="QS", dtype=str)
    if list(frame.columns) != ["File", "CHQ", "Summary"]:
        raise ValueError("Official MeQSum workbook schema changed")
    rows = frame.fillna("").to_dict("records")
    if len(rows) != 1000:
        raise ValueError("Official MeQSum workbook row count changed")
    return rows


def known_external_questions() -> dict[str, set[str]]:
    known: dict[str, set[str]] = {}
    mirror = set()
    for name in ("liveqa_train1_mirror.jsonl", "liveqa_train2_mirror.jsonl"):
        with (BASE / name).open(encoding="utf-8") as handle:
            mirror.update(normal(json.loads(line)["MESSAGE"]) for line in handle)
    known["liveqa_train"] = mirror
    for name in ("mediqa2019_official_test.xml", "mediqa2019_official_validation.xml",
                 "mediqa2019_official_alexa.xml"):
        tree = ElementTree.parse(BASE / name)
        known[name.replace("mediqa2019_official_", "mediqa_qa_").replace(".xml", "")] = {
            normal(q.findtext("QuestionText") or "") for q in tree.getroot().findall("Question")}
    return known


def main() -> None:
    rows = load_rows()
    inputs = [normal(row["CHQ"]) for row in rows]
    summaries = [normal(row["Summary"]) for row in rows]
    external = known_external_questions()
    report = {"schema": "careguard.medquad.meqsum-source-audit.v1",
              "source_url": SOURCE_URL, "source_sha256": _sha(SOURCE),
              "rows": len(rows), "nonempty_pairs": sum(bool(a and b) for a, b in zip(inputs, summaries)),
              "unique_input_questions": len(set(inputs)),
              "unique_summaries": len(set(summaries)),
              "identical_question_summary_pairs": sum(a == b for a, b in zip(inputs, summaries)),
              "median_input_chars": int(pd.Series([len(row["CHQ"]) for row in rows]).median()),
              "median_summary_chars": int(pd.Series([len(row["Summary"]) for row in rows]).median()),
              "exact_input_overlap": {name: len(set(inputs) & questions)
                                      for name, questions in external.items()},
              "scope": "Question summarization pairs only; no answer relevance or disease outcome labels."}
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
