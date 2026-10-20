"""Source-grounded MedQuAD question retrieval, not diagnosis or prognosis.

The official archive contains question-only copyright-restricted subsets. We
account for every XML QAPair, but fit the retrieval model only on pairs with
both a question and an answer. No patient data or future outcomes are used.
"""

from __future__ import annotations

import hashlib
import json
import re
from functools import lru_cache
from pathlib import Path
from xml.etree import ElementTree
from zipfile import ZipFile

import joblib
import numpy as np
from scipy.sparse import hstack
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import linear_kernel


ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "medquad_official_master.zip"
ARTIFACT = ROOT / "artifacts" / "medquad_qa"
MODEL = ARTIFACT / "medquad_retrieval.joblib"
RECORDS = ARTIFACT / "answer_records.jsonl"
REPORT = ARTIFACT / "training_report.json"
SEMANTIC = ARTIFACT / "semantic"
SEMANTIC_REPORT = SEMANTIC / "semantic_report.json"
SEMANTIC_MATRIX = SEMANTIC / "semantic_embeddings.npy"
ENCODER = SEMANTIC / "encoder"
BENCHMARK = ARTIFACT / "generalization_benchmark.json"
ROBUSTNESS = ARTIFACT / "robustness_audit.json"
MEDIQA_AUDIT = ARTIFACT / "mediqa2019_audit.json"
LATEST_GENERALIZATION = ARTIFACT / "generalization_20261014.json"
BLIND_EVALUATION = ARTIFACT / "blind_eval_manifest_20261014.json"
DEVELOPMENT_EVALUATION = ARTIFACT / "medication_development_manifest_20261014.json"
SOURCE_URL = "https://github.com/abachaa/MedQuAD"
HYBRID_METHOD = "0.5 lexical TF-IDF + 0.5 pretrained MiniLM semantic retrieval with abstention gates"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _plain(value: str | None) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def read_official_archive(path: Path = SOURCE, *, question_corpus: list[str] | None = None) -> tuple[list[dict], dict]:
    """Parse every XML member and count answerless pairs explicitly."""
    records: list[dict] = []
    counts = {"xml_documents": 0, "qa_pairs_total": 0, "answer_bearing_pairs": 0,
              "answerless_pairs": 0, "questionless_pairs": 0, "parse_errors": 0}
    by_source: dict[str, dict[str, int]] = {}
    with ZipFile(path) as archive:
        for name in sorted(archive.namelist()):
            if not name.lower().endswith(".xml"):
                continue
            counts["xml_documents"] += 1
            try:
                root = ElementTree.fromstring(archive.read(name))
            except ElementTree.ParseError:
                counts["parse_errors"] += 1
                continue
            source = root.get("source", "unknown")
            source_counts = by_source.setdefault(source, {"total": 0, "trainable": 0, "answerless": 0})
            focus = _plain(root.findtext("Focus"))
            url = root.get("url", "")
            for pair in root.findall(".//QAPair"):
                counts["qa_pairs_total"] += 1
                source_counts["total"] += 1
                question_node = pair.find("Question")
                answer_node = pair.find("Answer")
                question = _plain("".join(question_node.itertext()) if question_node is not None else "")
                answer = _plain("".join(answer_node.itertext()) if answer_node is not None else "")
                if question and question_corpus is not None:
                    question_corpus.append(question)
                if not question:
                    counts["questionless_pairs"] += 1
                if not answer:
                    counts["answerless_pairs"] += 1
                    source_counts["answerless"] += 1
                if not question or not answer:
                    continue
                counts["answer_bearing_pairs"] += 1
                source_counts["trainable"] += 1
                records.append({
                    "id": f"{name}:{pair.get('pid', '')}",
                    "question": question, "answer": answer, "focus": focus,
                    "question_type": question_node.get("qtype", "") if question_node is not None else "",
                    "source": source, "source_url": url,
                })
    counts["sources"] = by_source
    return records, counts


def train(source: Path = SOURCE, artifact_dir: Path = ARTIFACT) -> dict:
    """Fit a full-corpus word/character TF-IDF answer retriever.

    This is a fitted retrieval model, not a fine-tuned neural MAPFM model.
    It returns source answers verbatim and never estimates disease incidence.
    """
    all_questions: list[str] = []
    records, counts = read_official_archive(source, question_corpus=all_questions)
    if counts["parse_errors"] or not records:
        raise ValueError("The official MedQuAD archive is incomplete or unreadable")
    questions = [record["question"] for record in records]
    word = TfidfVectorizer(ngram_range=(1, 2), min_df=2, max_features=180_000,
                           sublinear_tf=True, dtype=np.float32, strip_accents="unicode")
    char = TfidfVectorizer(analyzer="char", ngram_range=(3, 5), min_df=2,
                           max_features=140_000, sublinear_tf=True, dtype=np.float32,
                           strip_accents="unicode")
    # All official questions, including answerless copyright-restricted rows,
    # shape the vocabulary and IDF statistics. Only answer-bearing rows are
    # eligible to become retrieved answers.
    word.fit(all_questions)
    char.fit(all_questions)
    word_matrix = word.transform(questions)
    char_matrix = char.transform(questions)
    artifact_dir.mkdir(parents=True, exist_ok=True)
    model_file = artifact_dir / MODEL.name
    records_file = artifact_dir / RECORDS.name
    report_file = artifact_dir / REPORT.name
    if any(path.exists() for path in (model_file, records_file, report_file)):
        raise FileExistsError("Refusing to overwrite an existing MedQuAD model; choose a new artifact directory")
    joblib.dump({"word": word, "char": char, "word_matrix": word_matrix,
                 "char_matrix": char_matrix}, model_file, compress=3)
    with records_file.open("w", encoding="utf-8") as handle:
        for row in records:
            handle.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")
    report = {
        "schema": "careguard.medquad.qa-retrieval.v1",
        "method": "full-corpus fitted word-and-character TF-IDF nearest-question retrieval",
        "neural_weights_trained": False,
        "prospective_diabetes_training": False,
        "clinical_use_allowed": False,
        "source_url": SOURCE_URL,
        "source_sha256": sha256(source),
        "source_license": "CC BY 4.0; three MedlinePlus subsets have answers removed by upstream",
        **counts,
        "indexed_pairs": len(records),
        "vocabulary_fitted_questions": len(all_questions),
        "word_vocabulary": len(word.vocabulary_),
        "character_vocabulary": len(char.vocabulary_),
        "model_sha256": sha256(model_file),
        "records_sha256": sha256(records_file),
        "evaluation": "No independent clinical or answer-quality validation. Exact-corpus retrieval is not generalization.",
    }
    report_file.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


def _verify_semantic(records_count: int) -> tuple[dict, np.ndarray]:
    semantic_report = json.loads(SEMANTIC_REPORT.read_text(encoding="utf-8"))
    if (semantic_report.get("schema") != "careguard.medquad.semantic-index.v1"
            or semantic_report.get("source_sha256") != sha256(SOURCE)
            or semantic_report.get("records_sha256") != sha256(RECORDS)
            or semantic_report.get("embeddings_sha256") != sha256(SEMANTIC_MATRIX)
            or semantic_report.get("index_rows") != records_count):
        raise ValueError("MedQuAD semantic index audit failed")
    encoder_files = semantic_report.get("encoder_file_sha256", {})
    if not encoder_files or "encoder/model.safetensors" not in encoder_files:
        raise ValueError("MedQuAD encoder manifest is incomplete")
    for relative, digest in encoder_files.items():
        path = (SEMANTIC / relative).resolve()
        if not path.is_relative_to(ENCODER.resolve()):
            raise ValueError("MedQuAD encoder manifest contains an unsafe path")
        if not path.is_file() or sha256(path) != digest:
            raise ValueError(f"MedQuAD encoder file audit failed: {relative}")
    matrix = np.load(SEMANTIC_MATRIX, mmap_mode="r")
    if matrix.shape != (records_count, 384) or matrix.dtype != np.float32:
        raise ValueError("MedQuAD semantic matrix has unexpected shape or dtype")
    return semantic_report, matrix


@lru_cache(maxsize=1)
def _load() -> tuple[dict, list[dict], dict, np.ndarray, object]:
    report = json.loads(REPORT.read_text(encoding="utf-8"))
    if report.get("source_sha256") != sha256(SOURCE) or report.get("model_sha256") != sha256(MODEL) or report.get("records_sha256") != sha256(RECORDS):
        raise ValueError("MedQuAD source, model, or records failed SHA-256 verification")
    model = joblib.load(MODEL)
    with RECORDS.open(encoding="utf-8") as handle:
        records = [json.loads(line) for line in handle]
    if len(records) != report["indexed_pairs"] or model["word_matrix"].shape[0] != len(records):
        raise ValueError("MedQuAD model and record count disagree")
    _, matrix = _verify_semantic(len(records))
    from sentence_transformers import SentenceTransformer
    encoder = SentenceTransformer(str(ENCODER), device="cpu", local_files_only=True)
    return model, records, report, matrix, encoder


def status() -> dict:
    if not all(path.exists() for path in (SOURCE, MODEL, RECORDS, REPORT,
                                         SEMANTIC_REPORT, SEMANTIC_MATRIX, ENCODER,
                                         BENCHMARK, ROBUSTNESS, MEDIQA_AUDIT,
                                         LATEST_GENERALIZATION, BLIND_EVALUATION,
                                         DEVELOPMENT_EVALUATION)):
        return {"ready": False, "reason": "Complete MedQuAD source or trained retrieval artifact missing"}
    try:
        report = json.loads(REPORT.read_text(encoding="utf-8"))
        if report.get("source_sha256") != sha256(SOURCE) or report.get("model_sha256") != sha256(MODEL) or report.get("records_sha256") != sha256(RECORDS):
            raise ValueError("SHA-256 mismatch")
        semantic_report, _ = _verify_semantic(report["indexed_pairs"])
        benchmark = json.loads(BENCHMARK.read_text(encoding="utf-8"))
        if (benchmark.get("schema") != "careguard.medquad.partial-liveqa-benchmark.v1"
                or benchmark.get("medquad_source_sha256") != report["source_sha256"]):
            raise ValueError("MedQuAD generalization benchmark audit failed")
        robustness = json.loads(ROBUSTNESS.read_text(encoding="utf-8"))
        if (robustness.get("schema") != "careguard.medquad.robustness-audit.v1"
                or robustness.get("deployed_source_sha256") != sha256(Path(__file__))
                or robustness.get("model_sha256") != report["model_sha256"]
                or robustness.get("candidate_decision") != "rejected; baseline retained"):
            raise ValueError("MedQuAD robustness deployment audit failed")
        mediqa = json.loads(MEDIQA_AUDIT.read_text(encoding="utf-8"))
        if (mediqa.get("schema") != "careguard.medquad.mediqa2019-audit.v1"
                or mediqa.get("model_sha256") != report["model_sha256"]
                or mediqa.get("strict_evaluable_questions") != 52
                or mediqa.get("answer_field_candidate", {}).get("promotion_decision") != "rejected; baseline retained"
                or mediqa.get("deployed_baseline", {}).get("known_answer_at_3_hits") != 32):
            raise ValueError("MedQuAD MEDIQA 2019 audit failed")
        latest = json.loads(LATEST_GENERALIZATION.read_text(encoding="utf-8"))
        if (latest.get("schema") != "careguard.medquad.generalization-audit.v1"
                or latest.get("deployed_model_sha256") != report["model_sha256"]
                or latest.get("baseline_retained") is not True
                or latest.get("candidate_count") != 3
                or latest.get("candidates_rejected") != 3
                or set(latest.get("trials", {})) != {
                    "rqe_feature_classifier", "rqe_finetuned_encoder", "meqsum_finetuned_encoder"
                }
                or any(trial.get("decision") != "rejected" for trial in latest["trials"].values())):
            raise ValueError("MedQuAD latest generalization audit failed")
        blind = json.loads(BLIND_EVALUATION.read_text(encoding="utf-8"))
        development = json.loads(DEVELOPMENT_EVALUATION.read_text(encoding="utf-8"))
        if (blind.get("schema") != "careguard.medquad.blind-evaluation-manifest.v1"
                or blind.get("deployed_model_sha256") != report["model_sha256"]
                or blind.get("locked_question_count") != 250
                or blind.get("labels_complete") is not False
                or blind.get("performance_estimate_available") is not False
                or development.get("schema") != "careguard.medquad.medication-development-manifest.v1"
                or development.get("deployed_model_sha256") != report["model_sha256"]
                or development.get("development_question_count") != 100
                or development.get("linked_locked_packet_id") != blind.get("packet_id")
                or development.get("labels_complete") is not False):
            raise ValueError("MedQuAD blind evaluation audit failed")
    except (OSError, ValueError, KeyError) as exc:
        return {"ready": False, "reason": str(exc)}
    return {"ready": True, "method": HYBRID_METHOD, "qa_pairs_total": report["qa_pairs_total"],
            "answer_bearing_pairs": report["answer_bearing_pairs"],
            "answerless_pairs": report["answerless_pairs"], "indexed_pairs": report["indexed_pairs"],
            "vocabulary_fitted_questions": report["vocabulary_fitted_questions"],
            "source_sha256": report["source_sha256"], "model_sha256": report["model_sha256"],
            "semantic_encoder": semantic_report["encoder"],
            "semantic_encoder_pretrained_not_finetuned": True,
            "external_test_questions": benchmark["official_test_questions"],
            "external_evaluable_questions": benchmark["queries_with_aligned_relevant_answer"],
            "known_relevant_at_3_lexical": benchmark["results"]["lexical_gated"]["known_relevant_at_3"],
            "known_relevant_at_3_hybrid": benchmark["results"]["hybrid_50_50_gated"]["known_relevant_at_3"],
            "natural_query_holdout_count": robustness["sealed"]["count"],
            "natural_query_known_answer_at_3": robustness["sealed"]["baseline_known_answer_at_3"],
            "nonmedical_abstention": robustness["sealed"]["baseline_nonmedical_abstention"],
            "rejected_candidate_known_answer_at_3": robustness["sealed"]["rejected_candidate_known_answer_at_3"],
            "mediqa2019_evaluable_questions": mediqa["strict_evaluable_questions"],
            "mediqa2019_baseline_known_answer_at_1": round(mediqa["deployed_baseline"]["known_answer_at_1_hits"] / mediqa["strict_evaluable_questions"], 4),
            "mediqa2019_baseline_known_answer_at_3": round(mediqa["deployed_baseline"]["known_answer_at_3_hits"] / mediqa["strict_evaluable_questions"], 4),
            "mediqa2019_rejected_candidate_known_answer_at_3": round(mediqa["answer_field_candidate"]["known_answer_at_3_hits"] / mediqa["strict_evaluable_questions"], 4),
            "mediqa2019_answer_field_candidate_deployed": False,
            "latest_generalization_audit_date": latest["audit_date"],
            "latest_generalization_candidates_rejected": latest["candidates_rejected"],
            "latest_generalization_baseline_retained": latest["baseline_retained"],
            "blind_evaluation_locked_questions": blind["locked_question_count"],
            "blind_evaluation_development_questions": development["development_question_count"],
            "blind_evaluation_human_labels_complete": False,
            "neural_weights_trained": False, "prospective_diabetes_training": False,
            "clinical_use_allowed": False}


def ask(question: str, *, top_k: int = 3) -> dict:
    query = _plain(question)
    if not 5 <= len(query) <= 500:
        raise ValueError("Question length must be 5–500 characters")
    if not 1 <= top_k <= 5:
        raise ValueError("top_k must be 1–5")
    model, records, report, semantic_matrix, encoder = _load()
    word_score = linear_kernel(model["word"].transform([query]), model["word_matrix"]).ravel()
    char_score = linear_kernel(model["char"].transform([query]), model["char_matrix"]).ravel()
    lexical_scores = 0.65 * word_score + 0.35 * char_score
    query_embedding = encoder.encode_query([query], normalize_embeddings=True,
                                           convert_to_numpy=True, show_progress_bar=False)[0]
    semantic_scores = semantic_matrix @ query_embedding
    scores = 0.5 * lexical_scores + 0.5 * semantic_scores
    candidate_count = min(100, len(scores))
    candidates = np.argpartition(scores, -candidate_count)[-candidate_count:]
    def answer_aware_rank(index: int) -> float:
        """Break near-ties from upstream repeated template questions.

        A document can repeat the same question for unrelated answer snippets.
        Prefer a direct definition and the health-topic source only within a
        narrow lexical-similarity margin; never treat this as clinical quality.
        """
        record = records[int(index)]
        focus = record["focus"].casefold()
        intro = record["answer"][:120].casefold()
        direct = bool(focus and (intro.startswith(focus + " ") or intro.startswith(focus + " is ")))
        return (float(scores[index]) + (0.012 if direct else 0.0)
                + (0.004 if record["source"] == "MPlusHealthTopics" else 0.0))

    ordered = sorted(candidates, key=answer_aware_rank, reverse=True)
    matches = []
    seen_urls: set[str] = set()
    for index in ordered:
        score = float(scores[index])
        if (score < 0.32 or float(semantic_scores[index]) < 0.40
                or float(lexical_scores[index]) < 0.08):
            continue
        record = records[int(index)]
        # Several upstream documents repeat a question with different answer
        # fragments. Do not present those fragments as independent sources.
        key = record["source_url"] or record["id"].rsplit(":", 1)[0]
        if key in seen_urls:
            continue
        seen_urls.add(key)
        matches.append({**record, "match_score": round(score, 4),
                        "lexical_score": round(float(lexical_scores[index]), 4),
                        "semantic_score": round(float(semantic_scores[index]), 4)})
        if len(matches) >= top_k:
            break
    return {"question": query, "matches": matches,
            "abstained": not matches, "model": HYBRID_METHOD,
            "source_sha256": report["source_sha256"],
            "disclaimer": "Historical English source-answer retrieval only; not a diagnosis, current guideline, or future disease prediction.",
            "clinical_use_allowed": False}
