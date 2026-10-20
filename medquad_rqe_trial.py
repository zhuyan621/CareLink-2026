"""Offline RQE supervision trial; never silently changes deployed QA ranking."""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path
from xml.etree import ElementTree

import joblib
import numpy as np
from scipy.sparse import csr_matrix
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, average_precision_score, f1_score, roc_auc_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from medquad_qa import _load, sha256
from medquad_rqe_benchmark import FILES, SOURCE_BASE, SOURCE_NAMES


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "artifacts/medquad_qa_candidate/rqe_trial"
INTENTS = {
    "definition": re.compile(r"\b(what is|what are|information about|tell me about|define)\b", re.I),
    "treatment": re.compile(r"\b(treat|treatment|therap|cure|manage|medication|drug|medicine)\w*\b", re.I),
    "symptoms": re.compile(r"\b(symptom|sign|manifestation)\w*\b", re.I),
    "causes": re.compile(r"\b(cause|why|risk factor|develop)\w*\b", re.I),
    "diagnosis": re.compile(r"\b(diagnos|test|screen|detect)\w*\b", re.I),
    "prevention": re.compile(r"\b(prevent|avoid|reduce risk)\w*\b", re.I),
    "prognosis": re.compile(r"\b(prognos|outlook|surviv|life expectancy)\w*\b", re.I),
}
STOP = {"a", "an", "and", "are", "can", "do", "does", "for", "how", "i", "in", "is", "it", "my",
        "of", "on", "or", "the", "to", "what", "when", "where", "which", "who", "why", "with"}
FEATURE_NAMES = ["semantic_cosine", "word_tfidf_cosine", "char_tfidf_cosine", "content_jaccard",
                 "faq_content_recall", "consumer_content_recall", "length_ratio", "intent_shared",
                 "intent_conflict", "negation_mismatch"]


def parse(split: str) -> tuple[list[tuple[str, str]], np.ndarray]:
    root = ElementTree.parse(FILES[split]).getroot()
    pairs, labels = [], []
    for pair in root.findall("pair"):
        chq, faq = (pair.findtext("chq") or "").strip(), (pair.findtext("faq") or "").strip()
        if not chq or not faq:
            continue
        pairs.append((chq, faq))
        labels.append((pair.get("value") or "").casefold() == "true")
    return pairs, np.asarray(labels, dtype=np.int8)


def _tokens(value: str) -> set[str]:
    return {token for token in re.findall(r"[a-z0-9]+", value.casefold())
            if token not in STOP and len(token) > 2}


def feature_matrix(pairs: list[tuple[str, str]], model: dict, encoder: object) -> np.ndarray:
    texts = sorted({text for pair in pairs for text in pair})
    embeddings = encoder.encode(texts, batch_size=64, normalize_embeddings=True,
                                convert_to_numpy=True, show_progress_bar=False)
    embeddings = {text: vector for text, vector in zip(texts, embeddings)}
    word = model["word"].transform(texts)
    char = model["char"].transform(texts)
    index = {text: i for i, text in enumerate(texts)}
    rows = np.zeros((len(pairs), len(FEATURE_NAMES)), dtype=np.float32)
    for i, (consumer, faq) in enumerate(pairs):
        left, right = index[consumer], index[faq]
        rows[i, 0] = float(embeddings[consumer] @ embeddings[faq])
        rows[i, 1] = float(word[left].multiply(word[right]).sum())
        rows[i, 2] = float(char[left].multiply(char[right]).sum())
        a, b = _tokens(consumer), _tokens(faq)
        shared = len(a & b)
        rows[i, 3] = shared / max(1, len(a | b))
        rows[i, 4] = shared / max(1, len(b))
        rows[i, 5] = shared / max(1, len(a))
        rows[i, 6] = min(len(a), len(b)) / max(1, max(len(a), len(b)))
        ia = {name for name, pattern in INTENTS.items() if pattern.search(consumer)}
        ib = {name for name, pattern in INTENTS.items() if pattern.search(faq)}
        rows[i, 7] = bool(ia & ib)
        rows[i, 8] = bool(ia and ib and not ia & ib)
        rows[i, 9] = (bool(re.search(r"\b(no|not|never|without)\b", consumer, re.I))
                      != bool(re.search(r"\b(no|not|never|without)\b", faq, re.I)))
    return rows


def metrics(y: np.ndarray, probability: np.ndarray, threshold: float = 0.5) -> dict:
    predicted = probability >= threshold
    return {"count": len(y), "positive": int(y.sum()),
            "accuracy": round(float(accuracy_score(y, predicted)), 4),
            "f1": round(float(f1_score(y, predicted, zero_division=0)), 4),
            "auroc": round(float(roc_auc_score(y, probability)), 4),
            "average_precision": round(float(average_precision_score(y, probability)), 4)}


def main(split: str) -> None:
    if split not in {"train", "development"}:
        raise ValueError("Sealed RQE test must be evaluated only after a candidate is frozen")
    OUT.mkdir(parents=True, exist_ok=True)
    model, _, report, _, encoder = _load()
    pairs, labels = parse(split)
    features = feature_matrix(pairs, model, encoder)
    np.savez_compressed(OUT / f"{split}_features.npz", features=features, labels=labels)
    print(json.dumps({"split": split, "count": len(pairs), "positive": int(labels.sum()),
                      "source_url": SOURCE_BASE + SOURCE_NAMES[split],
                      "source_sha256": sha256(FILES[split]), "feature_shape": features.shape},
                     ensure_ascii=False), flush=True)
    if split == "development":
        train = np.load(OUT / "train_features.npz")
        classifier = make_pipeline(StandardScaler(), LogisticRegression(max_iter=1000,
                                                                       class_weight="balanced",
                                                                       random_state=42))
        classifier.fit(train["features"], train["labels"])
        probability = classifier.predict_proba(features)[:, 1]
        semantic = features[:, 0]
        result = {"schema": "careguard.medquad.rqe-development-trial.v1",
                  "scope": "RQE pair classification only; not MedQuAD answer retrieval or clinical accuracy",
                  "train_source_sha256": sha256(FILES["train"]),
                  "development_source_sha256": sha256(FILES["development"]),
                  "medquad_model_sha256": report["model_sha256"],
                  "feature_names": FEATURE_NAMES,
                  "classifier": metrics(labels, probability),
                  "semantic_only": metrics(labels, semantic, threshold=0.5)}
        (OUT / "development_report.json").write_text(json.dumps(result, ensure_ascii=False, indent=2),
                                                        encoding="utf-8")
        joblib.dump(classifier, OUT / "classifier.joblib")
        print(json.dumps(result, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--split", required=True, choices=("train", "development"))
    main(parser.parse_args().split)
