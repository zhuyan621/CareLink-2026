"""Audit independent MEDIQA 2019 QA relevance labels against MedQuAD.

Only answer text with a long verbatim normalized overlap is aligned. The
public test file may contain patient narratives, so no raw questions are
written to the audit result or included in a delivery archive.
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
DEFAULT_TEST = ROOT / "artifacts/medquad_qa_candidate/mediqa2019_official_test.xml"
SOURCE_DIRECTORY = "https://github.com/abachaa/MEDIQA2019/blob/master/MEDIQA_Task3_QA/"


def normal(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.casefold()).strip()


def _answer_keys(value: str) -> set[str]:
    text = normal(value)
    keys = {text[:120]} if len(text) >= 120 else set()
    # CHiQA often prefixes a source title / section name before a colon.
    head, sep, tail = value.partition(":")
    if sep and len(head) < 90:
        body = normal(tail)
        if len(body) >= 120:
            keys.add(body[:120])
    return keys


def cases(path: Path = DEFAULT_TEST) -> tuple[list[dict], dict]:
    if not path.is_file():
        raise FileNotFoundError(f"Official MEDIQA 2019 QA test file absent: {path}")
    with RECORDS.open(encoding="utf-8") as handle:
        records = [json.loads(line) for line in handle]
    by_answer: dict[str, set[int]] = defaultdict(set)
    by_url: dict[str, set[int]] = defaultdict(set)
    for index, row in enumerate(records):
        for key in _answer_keys(row["answer"]):
            by_answer[key].add(index)
        if row["source_url"]:
            by_url[row["source_url"].lower().rstrip("/")].add(index)
    all_questions: list[str] = []
    read_official_archive(SOURCE, question_corpus=all_questions)
    known_questions = {normal(q) for q in all_questions}
    tree = ElementTree.parse(path)
    result: list[dict] = []
    stats = {"questions_total": 0, "positive_label_questions": 0,
             "answer_text_aligned_questions": 0, "url_aligned_questions": 0,
             "exact_medquad_question_overlaps": 0}
    for node in tree.getroot().findall("Question"):
        stats["questions_total"] += 1
        question = (node.findtext("QuestionText") or "").strip()
        if not 5 <= len(question) <= 500:
            continue
        if normal(question) in known_questions:
            stats["exact_medquad_question_overlaps"] += 1
            continue
        gold: set[int] = set()
        url_gold: set[int] = set()
        positive = False
        for answer in node.findall("./AnswerList/Answer"):
            if int(answer.get("ReferenceScore", "0")) < 3:
                continue
            positive = True
            text = answer.findtext("AnswerText") or ""
            for key in _answer_keys(text):
                gold.update(by_answer.get(key, set()))
            url = (answer.findtext("AnswerURL") or "").lower().rstrip("/")
            url_gold.update(by_url.get(url, set()))
        if positive:
            stats["positive_label_questions"] += 1
        if gold:
            stats["answer_text_aligned_questions"] += 1
        if url_gold:
            stats["url_aligned_questions"] += 1
        if gold:
            qhash = hashlib.sha256(question.encode("utf-8")).hexdigest()[:16]
            result.append({"key": qhash, "question": question,
                           "gold_ids": {records[i]["id"] for i in gold},
                           "gold_urls": {records[i]["source_url"] for i in gold}})
    filename = {"mediqa2019_official_test.xml": "MEDIQA2019-Task3-QA-TestSet-wLabels.xml",
                "mediqa2019_official_validation.xml": "MEDIQA2019-Task3-QA-ValidationSet.xml",
                "mediqa2019_official_alexa.xml": "MEDIQA2019-Task3-QA-TrainingSet2-Alexa.xml"}.get(path.name, path.name)
    meta = {"source_url": SOURCE_DIRECTORY + filename, "source_sha256": sha256(path),
            "alignment": "reference score >=3 and first 120 normalized answer characters identical",
            "exact_corpus_questions_excluded": True, **stats,
            "strict_evaluable_questions": len(result)}
    return result, meta


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", type=Path, default=DEFAULT_TEST)
    args = parser.parse_args()
    _, metadata = cases(args.file)
    print(json.dumps(metadata, ensure_ascii=False, indent=2))
