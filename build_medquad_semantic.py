"""Build an offline semantic retrieval index from the existing MedQuAD records.

The encoder is pretrained elsewhere; this command does not fine-tune neural
weights on MedQuAD and does not train a disease prediction model.
"""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

import numpy as np
from sentence_transformers import SentenceTransformer

from medquad_qa import ARTIFACT, RECORDS, SOURCE, sha256


def build(encoder_source: Path, destination: Path) -> dict:
    if destination.exists():
        raise FileExistsError(f"Refusing to overwrite semantic index: {destination}")
    with RECORDS.open(encoding="utf-8") as handle:
        records = [json.loads(line) for line in handle]
    if not records:
        raise ValueError("No answer-bearing MedQuAD records")
    encoder = SentenceTransformer(str(encoder_source), device="cpu", local_files_only=True)
    embeddings = encoder.encode_document(
        [record["question"] for record in records], batch_size=128,
        normalize_embeddings=True, convert_to_numpy=True, show_progress_bar=True,
    ).astype(np.float32)
    if embeddings.shape != (len(records), 384) or not np.isfinite(embeddings).all():
        raise ValueError("Invalid MiniLM embedding matrix")
    destination.mkdir(parents=True)
    np.save(destination / "semantic_embeddings.npy", embeddings)
    shutil.copytree(encoder_source, destination / "encoder")
    files = {p.relative_to(destination).as_posix(): sha256(p)
             for p in (destination / "encoder").rglob("*") if p.is_file()}
    report = {
        "schema": "careguard.medquad.semantic-index.v1",
        "encoder": "sentence-transformers/all-MiniLM-L6-v2",
        "encoder_license": "Apache-2.0",
        "encoder_url": "https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2",
        "pretrained_encoder_not_finetuned": True,
        "source_sha256": sha256(SOURCE), "records_sha256": sha256(RECORDS),
        "index_rows": int(embeddings.shape[0]), "embedding_dimensions": int(embeddings.shape[1]),
        "embeddings_sha256": sha256(destination / "semantic_embeddings.npy"),
        "encoder_file_sha256": files,
        "clinical_use_allowed": False,
    }
    (destination / "semantic_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--encoder-source", type=Path, required=True)
    parser.add_argument("--destination", type=Path, default=ARTIFACT / "semantic")
    args = parser.parse_args()
    result = build(args.encoder_source, args.destination)
    print(json.dumps({key: value for key, value in result.items()
                      if key != "encoder_file_sha256"}, indent=2))
