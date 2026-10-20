"""Gate an experimental RQE-tuned encoder on unseen RQE development pairs."""

from __future__ import annotations

import json

import numpy as np
from sentence_transformers import SentenceTransformer

from medquad_qa import _load, sha256
from medquad_rqe_benchmark import FILES
from medquad_rqe_trial import OUT, feature_matrix, metrics, parse
from train_medquad_rqe_encoder import OUTPUT, REPORT


def main() -> None:
    saved = json.loads(REPORT.read_text(encoding="utf-8"))
    if saved.get("source_sha256") != sha256(FILES["train"]):
        raise ValueError("RQE training source hash mismatch")
    for relative, expected in saved["output_files_sha256"].items():
        if sha256(OUTPUT / relative) != expected:
            raise ValueError(f"RQE encoder file hash mismatch: {relative}")
    rows, labels = parse("development")
    model, _, _, _, _ = _load()
    candidate = SentenceTransformer(str(OUTPUT), device="cpu", local_files_only=True)
    features = feature_matrix(rows, model, candidate)
    baseline = np.load(OUT / "development_features.npz")
    if not np.array_equal(labels, baseline["labels"]):
        raise ValueError("RQE development labels changed")
    old = metrics(labels, baseline["features"][:, 0], threshold=0.5)
    new = metrics(labels, features[:, 0], threshold=0.5)
    accept = new["auroc"] >= old["auroc"] + 0.01 and new["average_precision"] >= old["average_precision"]
    result = {"schema": "careguard.medquad.rqe-encoder-development.v1",
              "scope": "Question entailment pair discrimination, not deployed answer retrieval",
              "development_source_sha256": sha256(FILES["development"]),
              "trained_encoder_report_sha256": sha256(REPORT),
              "predefined_gate": "AUROC gain >=0.01 and no average-precision regression",
              "baseline": old, "candidate": new,
              "decision": "continue to sealed RQE and QA retrieval" if accept else "reject; do not expose sealed RQE test"}
    destination = OUT / "encoder_development_report.json"
    if destination.exists():
        raise FileExistsError(destination)
    destination.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2), flush=True)


if __name__ == "__main__":
    main()
