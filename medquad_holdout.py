"""Natural-query MedQuAD retrieval audit with a deterministic sealed split.

LiveQA'17 *training* questions are used only as out-of-source user wording.
Their reference answers must exactly share a long normalized prefix with an
answer-bearing MedQuAD row to create a positive retrieval target. The public
mirror is kept out of the delivery ZIP because questions may contain personal
health narratives. This is not clinical answer-quality validation.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import defaultdict
from pathlib import Path

import numpy as np

from medquad_qa import RECORDS, SOURCE, ask, read_official_archive, sha256


ROOT = Path(__file__).resolve().parent
MIRROR = ROOT / "artifacts" / "medquad_qa_candidate"
MIRROR_FILES = (MIRROR / "liveqa_train1_mirror.jsonl", MIRROR / "liveqa_train2_mirror.jsonl")
MIRROR_URLS = (
    "https://huggingface.co/datasets/hyesunyun/liveqa_medical_trec2017/resolve/main/TREC2017-LiveQA-Medical-Train1.jsonl",
    "https://huggingface.co/datasets/hyesunyun/liveqa_medical_trec2017/resolve/main/TREC2017-LiveQA-Medical-Train2.jsonl",
)
OUT_OF_SCOPE = (
    "How do I repair my bicycle chain?",
    "How do I bake sourdough bread?",
    "What was the football score last night?",
    "Which camera should I buy for wildlife photography?",
    "How do I file my taxes this year?",
    "How do I fix a leaking kitchen faucet?",
    "How does a rocket engine work?",
    "What is the weather forecast for tomorrow?",
    "How should I prune my apple tree?",
    "What are the rules of chess castling?",
)


def _normal(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.casefold()).strip()


def cases() -> tuple[list[dict], dict]:
    missing = [path for path in MIRROR_FILES if not path.is_file()]
    if missing:
        raise FileNotFoundError("External LiveQA mirror files are not bundled with the delivery archive; "
                                "download from MIRROR_URLS into the paths in MIRROR_FILES before rerunning this audit")
    with RECORDS.open(encoding="utf-8") as handle:
        records = [json.loads(line) for line in handle]
    answer_index: dict[str, list[int]] = defaultdict(list)
    for index, record in enumerate(records):
        answer_index[_normal(record["answer"])[:120]].append(index)
    all_questions: list[str] = []
    read_official_archive(SOURCE, question_corpus=all_questions)
    seen_questions = {_normal(question) for question in all_questions}

    grouped: dict[tuple[int, str], set[int]] = defaultdict(set)
    parse_count = [0, 0]
    for part, path in enumerate(MIRROR_FILES, start=1):
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                row = json.loads(line)
                parse_count[part - 1] += 1
                question = row["MESSAGE"].strip()
                if not 5 <= len(question) <= 500 or _normal(question) in seen_questions:
                    continue
                answers = ([answer["__text"] for answer in row["ANSWERS"]]
                           if part == 1 else [row["ANSWER"]])
                for answer in answers:
                    normalized = _normal(answer)
                    if len(normalized) >= 120:
                        grouped[(part, question)].update(answer_index.get(normalized[:120], []))

    result = []
    for (part, question), gold in sorted(grouped.items()):
        if not gold:
            continue
        qhash = hashlib.sha256(question.encode("utf-8")).hexdigest()
        result.append({"key": qhash[:16], "part": part, "split":
                       "development" if int(qhash[:2], 16) < 128 else "sealed",
                       "question": question, "gold_ids": {records[index]["id"] for index in gold},
                       "gold_urls": {records[index]["source_url"] for index in gold}})
    meta = {"source": "TREC 2017 LiveQA medical training questions, public Hugging Face mirror",
            "source_urls": MIRROR_URLS,
            "mirror_sha256": [sha256(path) for path in MIRROR_FILES],
            "raw_rows_by_part": parse_count,
            "alignment": "same first 120 normalized answer characters; at least 120 characters",
            "exact_medquad_question_overlaps_excluded": True,
            "split_rule": "first byte of SHA-256(question UTF-8) < 128 -> development; otherwise sealed",
            "positive_case_count": len(result),
            "development_count": sum(row["split"] == "development" for row in result),
            "sealed_count": sum(row["split"] == "sealed" for row in result)}
    return result, meta


def evaluate(split: str, *, output: Path | None = None) -> dict:
    if split not in {"development", "sealed"}:
        raise ValueError("split must be development or sealed")
    selected, metadata = cases()
    selected = [row for row in selected if row["split"] == split]
    rows = []
    for row in selected:
        result = ask(row["question"], top_k=3)
        predicted_ids = [item["id"] for item in result["matches"]]
        predicted_urls = [item["source_url"] for item in result["matches"]]
        rows.append({"key": row["key"], "part": row["part"],
                     "answered": not result["abstained"],
                     "known_answer_at_1": bool(predicted_ids and predicted_ids[0] in row["gold_ids"]),
                     "known_answer_at_3": bool(set(predicted_ids) & row["gold_ids"]),
                     "known_source_at_3": bool(set(predicted_urls) & row["gold_urls"]),
                     "returned": predicted_ids, "gold": sorted(row["gold_ids"])})
    ood = [ask(question, top_k=3)["abstained"] for question in OUT_OF_SCOPE]
    metrics = {"count": len(rows), "answer_rate": round(float(np.mean([r["answered"] for r in rows])), 4),
               "known_answer_at_1": round(float(np.mean([r["known_answer_at_1"] for r in rows])), 4),
               "known_answer_at_3": round(float(np.mean([r["known_answer_at_3"] for r in rows])), 4),
               "known_source_at_3": round(float(np.mean([r["known_source_at_3"] for r in rows])), 4),
               "out_of_scope_abstention": round(float(np.mean(ood)), 4)}
    report = {"schema": "careguard.medquad.natural-query-holdout.v1", "split": split,
              "scope": "Known-positive retrieval of exact-matched historical source answers; unjudged returns are not counted as incorrect. Not clinical accuracy.",
              **metadata, "metrics": metrics, "out_of_scope_questions": len(ood),
              "missed_case_keys": [row["key"] for row in rows if not row["known_answer_at_3"]],
              "cases": rows}
    if output is not None:
        output.parent.mkdir(parents=True, exist_ok=True)
        if output.exists():
            raise FileExistsError(f"Refusing to overwrite a saved evaluation: {output}")
        output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--split", required=True, choices=("development", "sealed"))
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = evaluate(args.split, output=args.output)
    print(json.dumps({"split": args.split, "metadata": {k: v for k, v in report.items()
                                                          if k.endswith("_count")},
                      "metrics": report["metrics"]}, ensure_ascii=False, indent=2))
