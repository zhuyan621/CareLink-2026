"""Map official MEDIQA 2019 RQE labels to answer-bearing MedQuAD FAQs.

The task is *question entailment*, not answer correctness. Consumer health
questions may contain personal details, so this script reports counts only
and does not package or print raw questions.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import defaultdict
from pathlib import Path
from xml.etree import ElementTree

from medquad_qa import RECORDS, SOURCE, read_official_archive, sha256


ROOT = Path(__file__).resolve().parent
BASE = ROOT / "artifacts/medquad_qa_candidate"
FILES = {"train": BASE / "rqe_train.xml", "development": BASE / "rqe_validation.xml",
         "sealed": BASE / "rqe_test.xml"}
SOURCE_BASE = "https://github.com/abachaa/MEDIQA2019/blob/master/MEDIQA_Task2_RQE/"
SOURCE_NAMES = {"train": "MEDIQA2019-Task2-RQE-TrainingSet-AMIA2016.xml",
                "development": "MEDIQA2019-Task2-RQE-ValidationSet-AMIA2016.xml",
                "sealed": "MEDIQA2019-Task2-RQE-TestSet-wLabels.xml"}


def normal(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.casefold()).strip()


def cases(split: str) -> tuple[list[dict], dict]:
    if split not in FILES:
        raise ValueError(f"Unknown split: {split}")
    path = FILES[split]
    if not path.is_file():
        raise FileNotFoundError(path)
    with RECORDS.open(encoding="utf-8") as handle:
        records = [json.loads(line) for line in handle]
    faq_map: dict[str, set[str]] = defaultdict(set)
    for row in records:
        faq_map[normal(row["question"])].add(row["id"])
    all_questions: list[str] = []
    read_official_archive(SOURCE, question_corpus=all_questions)
    original_questions = {normal(q) for q in all_questions}
    tree = ElementTree.parse(path)
    grouped: dict[str, dict] = {}
    counts = {"pairs_total": 0, "positive_pairs": 0, "negative_pairs": 0,
              "positive_faq_mapped_pairs": 0, "negative_faq_mapped_pairs": 0,
              "positive_faq_in_full_question_corpus": 0,
              "consumer_questions_exactly_in_medquad": 0,
              "positive_pairs_with_identical_questions": 0}
    for pair in tree.getroot().findall("pair"):
        counts["pairs_total"] += 1
        label = (pair.get("value") or "").casefold() == "true"
        counts["positive_pairs" if label else "negative_pairs"] += 1
        question = (pair.findtext("chq") or "").strip()
        faq = (pair.findtext("faq") or "").strip()
        normalized_question = normal(question)
        normalized_faq = normal(faq)
        if label and normalized_faq in original_questions:
            counts["positive_faq_in_full_question_corpus"] += 1
        if label and normalized_question == normalized_faq:
            counts["positive_pairs_with_identical_questions"] += 1
        if normalized_question in original_questions:
            counts["consumer_questions_exactly_in_medquad"] += 1
            continue
        if not 5 <= len(question) <= 500 or not normalized_faq:
            continue
        ids = faq_map.get(normalized_faq, set())
        if not ids:
            continue
        counts["positive_faq_mapped_pairs" if label else "negative_faq_mapped_pairs"] += 1
        row = grouped.setdefault(normalized_question, {"question": question,
                                                       "positive_ids": set(), "negative_ids": set()})
        row["positive_ids" if label else "negative_ids"].update(ids)
    rows = []
    for normalized_question, row in sorted(grouped.items()):
        if row["positive_ids"]:
            row["key"] = hashlib.sha256(normalized_question.encode("utf-8")).hexdigest()[:16]
            rows.append(row)
    metadata = {"split": split, "source_url": SOURCE_BASE + SOURCE_NAMES[split],
                "source_sha256": sha256(path),
                "alignment": "Exact normalized FAQ question text to answer-bearing MedQuAD row; only positive entailment pairs are retrieval targets",
                "exact_medquad_consumer_questions_excluded": True,
                **counts, "evaluable_consumer_questions": len(rows)}
    return rows, metadata


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--split", required=True, choices=FILES)
    args = parser.parse_args()
    _, meta = cases(args.split)
    print(json.dumps(meta, ensure_ascii=False, indent=2))
