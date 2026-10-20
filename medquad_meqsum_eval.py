"""One-shot held-out MeQSum question-to-summary retrieval gate."""

from __future__ import annotations

import json

import numpy as np
from sentence_transformers import SentenceTransformer

from medquad_qa import ENCODER, sha256
from train_medquad_meqsum_encoder import OUTPUT, REPORT, split_pairs


def metrics(model: SentenceTransformer, pairs: list[tuple[str, str]]) -> dict:
    inputs = [a for a, _ in pairs]
    summaries = [b for _, b in pairs]
    q = model.encode(inputs, batch_size=64, normalize_embeddings=True,
                     convert_to_numpy=True, show_progress_bar=False)
    s = model.encode(summaries, batch_size=64, normalize_embeddings=True,
                     convert_to_numpy=True, show_progress_bar=False)
    scores = q @ s.T
    gold = np.arange(len(pairs))
    rank = 1 + np.count_nonzero(scores > scores[gold, gold][:, None], axis=1)
    return {"count": len(pairs), "gold_at_1": round(float(np.mean(rank <= 1)), 4),
            "gold_at_5": round(float(np.mean(rank <= 5)), 4),
            "mrr": round(float(np.mean(1.0 / rank)), 4),
            "median_gold_rank": float(np.median(rank))}


def main() -> None:
    report = json.loads(REPORT.read_text(encoding="utf-8"))
    for relative, expected in report["output_files_sha256"].items():
        if sha256(OUTPUT / relative) != expected:
            raise ValueError(f"MeQSum candidate encoder file hash mismatch: {relative}")
    _, development, source_meta = split_pairs()
    if len(development) != report["development_pairs"] or source_meta["source_sha256"] != report["source_sha256"]:
        raise ValueError("MeQSum source or split changed")
    baseline_model = SentenceTransformer(str(ENCODER), device="cpu", local_files_only=True)
    candidate_model = SentenceTransformer(str(OUTPUT), device="cpu", local_files_only=True)
    baseline = metrics(baseline_model, development)
    candidate = metrics(candidate_model, development)
    accept = (candidate["gold_at_1"] >= baseline["gold_at_1"] + 0.05
              and candidate["gold_at_5"] >= baseline["gold_at_5"])
    result = {"schema": "careguard.medquad.meqsum-development-gate.v1",
              "scope": "Long-question to its human-written summary retrieval; not answer correctness",
              "candidate_report_sha256": sha256(REPORT),
              "predefined_gate": "gold summary recall@1 gain >=0.05 and recall@5 nondecrease",
              "baseline": baseline, "candidate": candidate,
              "decision": "continue to MedQuAD QA retrieval trial" if accept else "reject; do not deploy"}
    destination = REPORT.parent / "meqsum_development_report.json"
    if destination.exists():
        raise FileExistsError(destination)
    destination.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2), flush=True)


if __name__ == "__main__":
    main()
