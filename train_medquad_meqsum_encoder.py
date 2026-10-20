"""Experimental long-consumer-question encoder, isolated from deployed QA."""

from __future__ import annotations

import hashlib
import json
import random
from pathlib import Path

import numpy as np
import torch
from sentence_transformers import SentenceTransformer
from sentence_transformers.sentence_transformer import losses

from medquad_meqsum_audit import SOURCE, SOURCE_URL, known_external_questions, load_rows, normal
from medquad_qa import ENCODER, SOURCE as MEDQUAD_SOURCE, read_official_archive, sha256


ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / "artifacts/medquad_qa_candidate/meqsum_encoder"
REPORT = ROOT / "artifacts/medquad_qa_candidate/meqsum_encoder_training.json"


def split_pairs() -> tuple[list[tuple[str, str]], list[tuple[str, str]], dict]:
    rows = load_rows()
    excluded = set().union(*known_external_questions().values())
    original_questions: list[str] = []
    read_official_archive(MEDQUAD_SOURCE, question_corpus=original_questions)
    in_corpus = {normal(value) for value in original_questions}
    train, development = [], []
    exclusions = {"external_question_overlap": 0, "medquad_question_summary": 0}
    for row in rows:
        question, summary = row["CHQ"].strip(), row["Summary"].strip()
        qnorm, snorm = normal(question), normal(summary)
        if qnorm in excluded or snorm in excluded:
            exclusions["external_question_overlap"] += 1
            continue
        if snorm in in_corpus:
            exclusions["medquad_question_summary"] += 1
            continue
        first_byte = int(hashlib.sha256(qnorm.encode("utf-8")).hexdigest()[:2], 16)
        (train if first_byte < 204 else development).append((question, summary))
    if not 650 <= len(train) <= 800 or not 140 <= len(development) <= 240:
        raise ValueError("MeQSum source or deterministic split count changed")
    meta = {"source_url": SOURCE_URL, "source_sha256": sha256(SOURCE),
            "source_rows": len(rows), "exclusions": exclusions,
            "split_rule": "first SHA-256 byte of normalized CHQ < 204 is train; rest development",
            "train_pairs": len(train), "development_pairs": len(development)}
    return train, development, meta


def main() -> None:
    if OUTPUT.exists() or REPORT.exists():
        raise FileExistsError("Experimental MeQSum encoder or report exists; refusing overwrite")
    train, development, metadata = split_pairs()
    random.seed(42)
    np.random.seed(42)
    torch.manual_seed(42)
    random.shuffle(train)
    model = SentenceTransformer(str(ENCODER), device="cpu", local_files_only=True)
    loss = losses.MultipleNegativesRankingLoss(model)
    optimizer = torch.optim.AdamW(model.parameters(), lr=1e-5, weight_decay=0.01)
    model.train()
    batch_size = 32
    epoch_losses = []
    for epoch in range(3):
        random.shuffle(train)
        losses_seen = []
        for start in range(0, len(train) - batch_size + 1, batch_size):
            batch = train[start:start + batch_size]
            left = model.tokenize([pair[0] for pair in batch])
            right = model.tokenize([pair[1] for pair in batch])
            optimizer.zero_grad(set_to_none=True)
            value = loss([left, right], torch.empty(0))
            value.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
            optimizer.step()
            losses_seen.append(float(value.detach()))
        mean_loss = round(float(np.mean(losses_seen)), 6)
        epoch_losses.append(mean_loss)
        print(json.dumps({"epoch": epoch + 1, "of": 3, "steps": len(losses_seen),
                          "mean_loss": mean_loss}), flush=True)
    model.save(str(OUTPUT))
    files = {path.relative_to(OUTPUT).as_posix(): sha256(path)
             for path in OUTPUT.rglob("*") if path.is_file()}
    report = {"schema": "careguard.medquad.experimental-meqsum-encoder.v1",
              "scope": "Consumer question summarization encoder candidate, not deployed QA or clinical prediction",
              **metadata, "base_encoder": "sentence-transformers/all-MiniLM-L6-v2",
              "loss": "MultipleNegativesRankingLoss", "epochs": 3, "batch_size": batch_size,
              "learning_rate": 1e-5, "seed": 42, "epoch_mean_losses": epoch_losses,
              "output_files_sha256": files, "clinical_use_allowed": False}
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"train_pairs": len(train), "development_pairs": len(development),
                      "exclusions": metadata["exclusions"]}, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
