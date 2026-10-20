"""Train an experimental question paraphrase encoder on official RQE positives.

This is separate from the deployed MedQuAD QA encoder and from MAPFM. No
model is deployed by this command; all outputs remain in candidate artifacts.
"""

from __future__ import annotations

import json
import random
from pathlib import Path

import numpy as np
import torch
from sentence_transformers import SentenceTransformer
from sentence_transformers.sentence_transformer import losses

from medquad_qa import ENCODER, sha256
from medquad_rqe_benchmark import FILES, normal
from medquad_rqe_trial import parse


ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / "artifacts/medquad_qa_candidate/rqe_encoder"
REPORT = ROOT / "artifacts/medquad_qa_candidate/rqe_encoder_training.json"


def main() -> None:
    if OUTPUT.exists() or REPORT.exists():
        raise FileExistsError("Experimental encoder or report already exists; refusing overwrite")
    random.seed(42)
    np.random.seed(42)
    torch.manual_seed(42)
    pairs, labels = parse("train")
    positives = [(a, b) for (a, b), y in zip(pairs, labels)
                 if y and normal(a) != normal(b)]
    if len(positives) < 3000:
        raise ValueError("Expected RQE non-identical positive training pairs are absent")
    random.shuffle(positives)
    model = SentenceTransformer(str(ENCODER), device="cpu", local_files_only=True)
    loss = losses.MultipleNegativesRankingLoss(model)
    optimizer = torch.optim.AdamW(model.parameters(), lr=1e-5, weight_decay=0.01)
    model.train()
    batch_size = 32
    steps = len(positives) // batch_size
    losses_seen = []
    for step in range(steps):
        batch = positives[step * batch_size:(step + 1) * batch_size]
        left = model.tokenize([pair[0] for pair in batch])
        right = model.tokenize([pair[1] for pair in batch])
        optimizer.zero_grad(set_to_none=True)
        value = loss([left, right], torch.empty(0))
        value.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
        optimizer.step()
        losses_seen.append(float(value.detach()))
        if (step + 1) % 20 == 0 or step + 1 == steps:
            print(json.dumps({"step": step + 1, "steps": steps,
                              "recent_loss": round(float(np.mean(losses_seen[-20:])), 4)}), flush=True)
    model.save(str(OUTPUT))
    files = {path.relative_to(OUTPUT).as_posix(): sha256(path)
             for path in OUTPUT.rglob("*") if path.is_file()}
    report = {"schema": "careguard.medquad.experimental-rqe-encoder.v1",
              "scope": "Medical question paraphrase encoder candidate, not deployed or clinical prediction",
              "source_url": "https://github.com/abachaa/MEDIQA2019/tree/master/MEDIQA_Task2_RQE",
              "source_sha256": sha256(FILES["train"]),
              "base_encoder": "sentence-transformers/all-MiniLM-L6-v2",
              "train_pairs_total": len(pairs), "nonidentical_positive_pairs": len(positives),
              "loss": "MultipleNegativesRankingLoss", "epochs": 1,
              "batch_size": 32, "learning_rate": 1e-5, "seed": 42,
              "optimizer_steps": steps, "mean_training_loss": round(float(np.mean(losses_seen)), 6),
              "output_files_sha256": files,
              "clinical_use_allowed": False}
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k: report[k] for k in ("nonidentical_positive_pairs", "epochs", "batch_size")},
                     ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
