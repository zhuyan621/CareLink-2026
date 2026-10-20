"""Offline MedQuAD QA retrieval gate for the MeQSum-tuned encoder."""

from __future__ import annotations

import json

import numpy as np
from scipy.sparse import csr_matrix
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import linear_kernel

from medquad_holdout import OUT_OF_SCOPE, cases as liveqa_cases
from medquad_mediqa_audit import cases as mediqa_cases
from medquad_qa import _load, ask, sha256
from train_medquad_meqsum_encoder import OUTPUT, REPORT


MATRIX = REPORT.parent / "meqsum_encoder_questions.npy"
RESULT = REPORT.parent / "meqsum_qa_trial.json"
GATE = "Each exposed set: no known-answer top-1/top-3 regression; combined top-3 gain >=3; nonmedical abstention unchanged"


def retrieve(query: str, model: dict, records: list[dict], matrix: np.ndarray,
             encoder: SentenceTransformer) -> list[dict]:
    word = linear_kernel(model["word"].transform([query]), model["word_matrix"]).ravel()
    char = linear_kernel(model["char"].transform([query]), model["char_matrix"]).ravel()
    lexical = 0.65 * word + 0.35 * char
    vector = encoder.encode_query([query], normalize_embeddings=True,
                                  convert_to_numpy=True, show_progress_bar=False)[0]
    semantic = matrix @ vector
    scores = 0.5 * lexical + 0.5 * semantic
    count = min(100, len(scores))
    candidates = np.argpartition(scores, -count)[-count:]

    def rank(index: int) -> float:
        record = records[int(index)]
        focus = record["focus"].casefold()
        intro = record["answer"][:120].casefold()
        direct = bool(focus and (intro.startswith(focus + " ") or intro.startswith(focus + " is ")))
        return (float(scores[index]) + (0.012 if direct else 0.0)
                + (0.004 if record["source"] == "MPlusHealthTopics" else 0.0))

    selected = []
    urls = set()
    for index in sorted(candidates, key=rank, reverse=True):
        if scores[index] < 0.32 or semantic[index] < 0.40 or lexical[index] < 0.08:
            continue
        record = records[int(index)]
        key = record["source_url"] or record["id"].rsplit(":", 1)[0]
        if key in urls:
            continue
        urls.add(key)
        selected.append(record)
        if len(selected) >= 3:
            break
    return selected


def evaluate(rows: list[dict], model: dict, records: list[dict], matrix: np.ndarray,
             encoder: SentenceTransformer) -> dict:
    totals = {name: {metric: 0 for metric in ("top1", "top3", "source3", "answered")}
              for name in ("baseline", "candidate")}
    for row in rows:
        baseline = ask(row["question"], top_k=3)["matches"]
        candidate = retrieve(row["question"], model, records, matrix, encoder)
        for name, selected in (("baseline", baseline), ("candidate", candidate)):
            ids = [item["id"] for item in selected]
            urls = [item["source_url"] for item in selected]
            totals[name]["top1"] += bool(ids and ids[0] in row["gold_ids"])
            totals[name]["top3"] += bool(set(ids) & row["gold_ids"])
            totals[name]["source3"] += bool(set(urls) & row["gold_urls"])
            totals[name]["answered"] += bool(ids)
    return {name: {metric: {"hits": count, "rate": round(count / len(rows), 4)}
                   for metric, count in values.items()}
            for name, values in totals.items()}


def main() -> None:
    if RESULT.exists():
        raise FileExistsError(RESULT)
    report = json.loads(REPORT.read_text(encoding="utf-8"))
    for relative, expected in report["output_files_sha256"].items():
        if sha256(OUTPUT / relative) != expected:
            raise ValueError(f"Candidate encoder audit failed: {relative}")
    model, records, deployed, _, _ = _load()
    encoder = SentenceTransformer(str(OUTPUT), device="cpu", local_files_only=True)
    if MATRIX.exists():
        matrix = np.load(MATRIX, mmap_mode="r")
    else:
        matrix = encoder.encode_document([row["question"] for row in records],
                                         batch_size=64, normalize_embeddings=True,
                                         convert_to_numpy=True, show_progress_bar=False).astype(np.float32)
        np.save(MATRIX, matrix)
    if matrix.shape != (len(records), 384):
        raise ValueError("Experimental question index shape mismatch")
    liveqa, _ = liveqa_cases()
    mediqa, _ = mediqa_cases()
    outcomes = {}
    for name, rows in (("exposed_liveqa_natural", liveqa), ("exposed_mediqa_qa", mediqa)):
        outcomes[name] = {"count": len(rows), "metrics": evaluate(rows, model, records, matrix, encoder)}
        print(json.dumps({"set": name, **outcomes[name]}, ensure_ascii=False), flush=True)
    ood = {"baseline": sum(ask(q)["abstained"] for q in OUT_OF_SCOPE),
           "candidate": sum(not retrieve(q, model, records, matrix, encoder) for q in OUT_OF_SCOPE)}
    prior = [item["metrics"]["baseline"] for item in outcomes.values()]
    after = [item["metrics"]["candidate"] for item in outcomes.values()]
    accept = (all(c["top1"]["hits"] >= b["top1"]["hits"]
                  and c["top3"]["hits"] >= b["top3"]["hits"]
                  for b, c in zip(prior, after))
              and sum(c["top3"]["hits"] - b["top3"]["hits"]
                      for b, c in zip(prior, after)) >= 3
              and ood["candidate"] >= ood["baseline"])
    result = {"schema": "careguard.medquad.meqsum-qa-development-trial.v1",
              "scope": "Known-positive retrieval on previously exposed question sets; not independent confirmation",
              "candidate_encoder_report_sha256": sha256(REPORT),
              "candidate_matrix_sha256": sha256(MATRIX),
              "deployed_model_sha256": deployed["model_sha256"],
              "predefined_gate": GATE, "outcomes": outcomes,
              "nonmedical_abstention": {"count": len(OUT_OF_SCOPE), **ood},
              "decision": "eligible for a fresh final test" if accept else "reject; deployed baseline retained"}
    RESULT.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"decision": result["decision"], "nonmedical_abstention": result["nonmedical_abstention"]},
                     ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
