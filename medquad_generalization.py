"""Reproducible, partial-label evaluation on the author's independent LiveQA set.

The MedQuAD archive bundles judgments for 2,479 retrieved answers. This script
aligns only exact question/URL/answer-prefix matches to the answer-bearing
MedQuAD index. Unmapped and unjudged answers are *not* counted as wrong.
"""

from __future__ import annotations

import csv
import io
import json
import re
from collections import defaultdict
from pathlib import Path
from xml.etree import ElementTree
from zipfile import ZipFile

import joblib
import numpy as np
from sklearn.metrics.pairwise import linear_kernel

from medquad_qa import ARTIFACT, MODEL, RECORDS, SOURCE, read_official_archive, sha256


ROOT = Path(__file__).resolve().parent
LIVEQA = ARTIFACT / "liveqa_test_questions.xml"
ENCODER_ID = "sentence-transformers/all-MiniLM-L6-v2"


def _normal(text: str) -> str:
    text = re.split(r"\(Also called:", text, maxsplit=1, flags=re.I)[0]
    return re.sub(r"[^a-z0-9]+", " ", text.casefold()).strip()


def external_judgments(source: Path = SOURCE, questions_file: Path = LIVEQA,
                       records_file: Path = RECORDS) -> tuple[list[dict], dict]:
    """Return original LiveQA questions with the subset of exact aligned labels."""
    with records_file.open(encoding="utf-8") as handle:
        records = [json.loads(line) for line in handle]
    lookup = defaultdict(list)
    for index, record in enumerate(records):
        lookup[_normal(record["question"])].append(index)

    with ZipFile(source) as archive:
        nested = next(name for name in archive.namelist()
                      if name.endswith("QA-TestSet-LiveQA-Med-Qrels-2479-Answers.zip"))
        with ZipFile(io.BytesIO(archive.read(nested))) as labels_archive:
            csv_name = next(name for name in labels_archive.namelist()
                            if name.endswith("All-2479-Answers-retrieved-from-MedQuAD.csv"))
            qrels_name = next(name for name in labels_archive.namelist()
                              if name.endswith("All-qrels_LiveQAMed2017-TestQuestions_2479_Judged-Answers.txt"))
            answer_rows = list(csv.DictReader(io.StringIO(
                labels_archive.read(csv_name).decode("utf-8-sig"))))
            qrels = {}
            for line in labels_archive.read(qrels_name).decode("utf-8").splitlines():
                qid, grade, answer_id = line.split(maxsplit=2)
                qrels[answer_id] = (int(qid), int(grade.split("-", maxsplit=1)[0]))

    aligned = defaultdict(dict)
    aligned_rows = 0
    for row in answer_rows:
        match = re.search(r"Question:\s*(.*?)\s*URL:\s*(.*?)\s*Answer:\s*(.*)", row["Answer"], re.S)
        if not match:
            continue
        question, url, answer = match.groups()
        answer_prefix = _normal(answer)[:120]
        for index in lookup.get(_normal(question), []):
            record = records[index]
            if (record["source_url"].rstrip("/") == url.strip().rstrip("/")
                    and _normal(record["answer"])[:120] == answer_prefix):
                qid, grade = qrels[row["AnswerID"]]
                aligned[qid][index] = max(grade, aligned[qid].get(index, 0))
                aligned_rows += 1
                break

    root = ElementTree.parse(questions_file).getroot()
    queries = []
    for node in root.findall("NLM-QUESTION"):
        qid = int(node.get("qid", "TQ0")[2:])
        original = node.findtext("Original-Question/MESSAGE") or ""
        summary = node.findtext("NLM-Summary") or ""
        queries.append({"qid": qid, "original": original.strip(), "summary": summary.strip(),
                        "judgments": aligned[qid]})
    stats = {"official_test_questions": len(queries), "official_judged_answers": len(answer_rows),
             "exactly_aligned_answer_rows": aligned_rows,
             "queries_with_aligned_relevant_answer": sum(
                 any(grade >= 3 for grade in query["judgments"].values()) for query in queries),
             "alignment_rule": "same normalized question, exact source URL, and normalized answer prefix"}
    return queries, stats


def benchmark(semantic_matrix: np.ndarray | None = None, encoder=None,
              *, output: Path | None = None) -> dict:
    """Compare candidates by known-positive retrieval; labels are incomplete."""
    model = joblib.load(MODEL)
    queries, stats = external_judgments()
    source_questions: list[str] = []
    read_official_archive(question_corpus=source_questions)
    seen_training_questions = {_normal(question) for question in source_questions}
    records_count = model["word_matrix"].shape[0]
    if semantic_matrix is not None and semantic_matrix.shape[0] != records_count:
        raise ValueError("Semantic embedding count does not match answer index")
    methods = {"lexical": [], "lexical_gated": [], "semantic": [], "hybrid_75_25": [],
               "hybrid_50_50": [], "hybrid_25_75": [], "hybrid_50_50_gated": []}
    for variant in ("original", "summary"):
        active = [item for item in queries if item[variant] and
                  any(grade >= 3 for grade in item["judgments"].values())
                  and _normal(item[variant]) not in seen_training_questions]
        for item in active:
            query = item[variant]
            word_score = linear_kernel(model["word"].transform([query]), model["word_matrix"]).ravel()
            char_score = linear_kernel(model["char"].transform([query]), model["char_matrix"]).ravel()
            lexical = (0.65 * word_score + 0.35 * char_score).astype(np.float32)
            lexical_gated = lexical.copy()
            lexical_gated[lexical_gated < 0.28] = -1
            ranked = {"lexical": lexical, "lexical_gated": lexical_gated}
            if semantic_matrix is not None:
                vector = encoder.encode_query([query], normalize_embeddings=True,
                                              convert_to_numpy=True, show_progress_bar=False)[0]
                semantic = semantic_matrix @ vector
                ranked.update({"semantic": semantic,
                               "hybrid_75_25": 0.75 * lexical + 0.25 * semantic,
                               "hybrid_50_50": 0.50 * lexical + 0.50 * semantic,
                               "hybrid_25_75": 0.25 * lexical + 0.75 * semantic})
                gated = ranked["hybrid_50_50"].copy()
                gated[(gated < 0.32) | (semantic < 0.40) | (lexical < 0.08)] = -1
                ranked["hybrid_50_50_gated"] = gated
            positives = {index for index, grade in item["judgments"].items() if grade >= 3}
            for name, scores in ranked.items():
                order = [int(index) for index in np.argsort(scores)[-10:][::-1]
                         if scores[index] >= 0]
                methods[name].append({"qid": item["qid"], "variant": variant,
                                      "top1": bool(order and order[0] in positives),
                                      "top3": bool(positives.intersection(order[:3])),
                                      "top10": bool(positives.intersection(order)),
                                      "answered": bool(order),
                                      "reciprocal_rank10": next((1 / (rank + 1) for rank, idx in
                                                                  enumerate(order) if idx in positives), 0)})
    results = {}
    for name, rows in methods.items():
        if not rows:
            continue
        results[name] = {"evaluated_query_variants": len(rows),
                         "answer_rate": round(np.mean([r["answered"] for r in rows]), 4),
                         "known_relevant_at_1": round(np.mean([r["top1"] for r in rows]), 4),
                         "known_relevant_at_3": round(np.mean([r["top3"] for r in rows]), 4),
                         "known_relevant_at_10": round(np.mean([r["top10"] for r in rows]), 4),
                         "known_relevant_mrr_at_10": round(np.mean([r["reciprocal_rank10"] for r in rows]), 4),
                         "original": {"count": sum(r["variant"] == "original" for r in rows),
                                      "known_relevant_at_3": round(np.mean([r["top3"] for r in rows
                                                                             if r["variant"] == "original"]), 4)},
                         "summary": {"count": sum(r["variant"] == "summary" for r in rows),
                                     "known_relevant_at_3": round(np.mean([r["top3"] for r in rows
                                                                            if r["variant"] == "summary"]), 4)},
                         "odd_qid": {"count": sum(r["qid"] % 2 == 1 for r in rows),
                                     "known_relevant_at_3": round(np.mean([r["top3"] for r in rows
                                                                            if r["qid"] % 2 == 1]), 4)},
                         "even_qid": {"count": sum(r["qid"] % 2 == 0 for r in rows),
                                      "known_relevant_at_3": round(np.mean([r["top3"] for r in rows
                                                                             if r["qid"] % 2 == 0]), 4)}}
    report = {"schema": "careguard.medquad.partial-liveqa-benchmark.v1",
              "test_source": "https://github.com/abachaa/LiveQA_MedicalTask_TREC2017",
              "test_sha256": sha256(LIVEQA), "medquad_source_sha256": sha256(SOURCE),
              "scope": "Independent questions; exact-aligned subset of partial judgments. Scores are known-positive retrieval rates, not accuracy or clinical safety.",
              "exact_query_duplicates_excluded": sum(
                  _normal(item[variant]) in seen_training_questions
                  for item in queries for variant in ("original", "summary")
                  if any(grade >= 3 for grade in item["judgments"].values())),
              **stats, "results": results}
    if output is not None:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--semantic-matrix", type=Path)
    parser.add_argument("--encoder", type=Path)
    parser.add_argument("--output", type=Path, default=ARTIFACT / "generalization_benchmark.json")
    args = parser.parse_args()
    if args.semantic_matrix:
        from sentence_transformers import SentenceTransformer
        encoder = SentenceTransformer(str(args.encoder), device="cpu", local_files_only=True)
        matrix = np.load(args.semantic_matrix)
    else:
        encoder, matrix = None, None
    result = benchmark(matrix, encoder, output=args.output)
    print(json.dumps(result, ensure_ascii=False, indent=2))
