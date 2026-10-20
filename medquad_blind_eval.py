"""Prepare a locked, local-only medication QA review and score human labels.

This is an evaluation workflow, not a training corpus or medical prediction.
Raw consumer questions and the annotation packet must not enter the public ZIP.
"""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import re
from xml.etree import ElementTree

import joblib
import numpy as np
from openpyxl import load_workbook

from medquad_qa import MODEL, SOURCE, ask, read_official_archive, sha256, status


ROOT = Path(__file__).resolve().parent
CANDIDATE = ROOT / "artifacts" / "medquad_qa_candidate"
SOURCE_WORKBOOK = CANDIDATE / "medication_qa_official.xlsx"
SOURCE_URL = "https://github.com/abachaa/Medication_QA_MedInfo2019"
SOURCE_SHA256 = "4f13d0e3b195bd6a5d72a1872f9118cb5f69fd02c370001695330cfc9e3b5832"
OUTPUT = CANDIDATE / "medication_blind_20261014"
PUBLIC_MANIFEST = ROOT / "artifacts" / "medquad_qa" / "blind_eval_manifest_20261014.json"
DEVELOPMENT_MANIFEST = ROOT / "artifacts" / "medquad_qa" / "medication_development_manifest_20261014.json"
PACKET_SCHEMA = "careguard.medquad.blind-review-packet.v1"
LABEL_SCHEMA = "careguard.medquad.blind-review-labels.v1"
MANIFEST_SCHEMA = "careguard.medquad.blind-evaluation-manifest.v1"
SAMPLE_SIZE = 250
DEVELOPMENT_SIZE = 100
SEED = "careguard-medication-blind-v1-20261014"
NEAR_DUPLICATE_LIMIT = 0.85
SOURCE_HEADERS = ("Question", "Focus (Drug)", "Question Type", "Answer", "Section Title", "URL")
PRIVATE_PATTERN = re.compile(
    r"(?:[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}|https?://|\b\d{3}[-. ]?\d{3}[-. ]?\d{4}\b|"
    r"\b\d{1,5}\s+[A-Za-z ]{2,40}\s+(?:street|st|road|rd|avenue|ave)\b|"
    r"\b(?:my name is|i live at|date of birth|dob)\b)", re.I
)
RELEVANCE = {"correct", "partial", "irrelevant", "uncertain"}
GROUNDEDNESS = {"supported", "unsupported", "uncertain"}
SAFETY = {"safe", "unsafe", "uncertain"}
SCOPE = {"in_scope", "out_of_scope", "uncertain"}
ABSTENTION = {"appropriate", "inappropriate", "uncertain"}


def normalize(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.casefold()).strip()


def question_id(question: str) -> str:
    return hashlib.sha256(normalize(question).encode("utf-8")).hexdigest()[:20]


def source_rows(path: Path = SOURCE_WORKBOOK) -> tuple[list[dict], dict]:
    if sha256(path) != SOURCE_SHA256:
        raise ValueError("Official medication QA workbook SHA-256 does not match the pinned source")
    book = load_workbook(path, read_only=True, data_only=True)
    if len(book.worksheets) != 1 or book.active.title != "DrugQA":
        raise ValueError("Unexpected medication QA workbook sheet")
    values = book.active.values
    if tuple(next(values)) != SOURCE_HEADERS:
        raise ValueError("Unexpected medication QA workbook columns")
    raw = list(values)
    rows = []
    seen: set[str] = set()
    duplicate_count = 0
    invalid_count = 0
    private_count = 0
    for excel_row, fields in enumerate(raw, start=2):
        question, focus, kind, answer, _, _ = fields
        question = str(question or "").strip()
        key = normalize(question)
        if not 5 <= len(question) <= 500 or not key or not str(answer or "").strip():
            invalid_count += 1
            continue
        if key in seen:
            duplicate_count += 1
            continue
        seen.add(key)
        if PRIVATE_PATTERN.search(question):
            private_count += 1
            continue
        rows.append({"id": question_id(question), "question": question,
                     "question_type": str(kind or "unknown").strip() or "unknown",
                     "focus": str(focus or "").strip(), "source_row": excel_row})
    book.close()
    return rows, {"workbook_data_rows": len(raw), "invalid_rows": invalid_count,
                  "exact_duplicate_rows": duplicate_count,
                  "possible_identifiers_excluded": private_count,
                  "unique_screened_questions": len(rows)}


def prior_questions() -> tuple[set[str], dict[str, str]]:
    """Use only previously exposed train/development sources for leakage screening."""
    questions: list[str] = []
    read_official_archive(SOURCE, question_corpus=questions)
    provenance = {"medquad_source_sha256": sha256(SOURCE)}
    mirrors = (CANDIDATE / "liveqa_train1_mirror.jsonl", CANDIDATE / "liveqa_train2_mirror.jsonl")
    for path in mirrors:
        provenance[path.name + "_sha256"] = sha256(path)
        for line in path.read_text(encoding="utf-8").splitlines():
            questions.append(str(json.loads(line).get("MESSAGE", "")))
    qa_xml = (CANDIDATE / "mediqa2019_official_test.xml",
              CANDIDATE / "mediqa2019_official_validation.xml",
              CANDIDATE / "mediqa2019_official_alexa.xml")
    for path in qa_xml:
        provenance[path.name + "_sha256"] = sha256(path)
        tree = ElementTree.parse(path)
        questions.extend(node.findtext("QuestionText") or "" for node in tree.getroot().findall("Question"))
    for name in ("rqe_train.xml", "rqe_validation.xml"):
        path = CANDIDATE / name
        provenance[name + "_sha256"] = sha256(path)
        tree = ElementTree.parse(path)
        for node in tree.getroot().findall("pair"):
            questions.extend((node.findtext("chq") or "", node.findtext("faq") or ""))
    meqsum = CANDIDATE / "meqsum_official.xlsx"
    provenance["meqsum_official.xlsx_sha256"] = sha256(meqsum)
    book = load_workbook(meqsum, read_only=True, data_only=True)
    for row in list(book.active.values)[1:]:
        questions.extend((str(row[1] or ""), str(row[2] or "")))
    book.close()
    return {normalize(q) for q in questions if normalize(q)}, provenance


def screen_candidates(rows: list[dict], known: set[str], *, near_limit: float = NEAR_DUPLICATE_LIMIT) -> tuple[list[dict], dict]:
    """Exclude exact and high character-TF-IDF similarity to prior questions.

    This is a leakage screen, not a guarantee that no semantic paraphrase exists.
    """
    if not 0 < near_limit <= 1:
        raise ValueError("near_limit must be in (0, 1]")
    exact = [row for row in rows if normalize(row["question"]) in known]
    remaining = [row for row in rows if normalize(row["question"]) not in known]
    vectorizer = joblib.load(MODEL)["char"]
    known_matrix = vectorizer.transform(sorted(known)).tocsr()
    candidate_matrix = vectorizer.transform([row["question"] for row in remaining]).tocsr()
    eligible = []
    near_count = 0
    for offset in range(0, len(remaining), 32):
        similarities = candidate_matrix[offset:offset + 32] @ known_matrix.T
        maximums = np.asarray(similarities.max(axis=1).toarray()).ravel()
        for row, maximum in zip(remaining[offset:offset + 32], maximums):
            if float(maximum) >= near_limit:
                near_count += 1
            else:
                eligible.append(row)
    return eligible, {"exact_prior_overlap_excluded": len(exact),
                      "near_prior_overlap_excluded": near_count,
                      "near_duplicate_char_tfidf_threshold": near_limit,
                      "eligible_questions": len(eligible)}


def select_locked(rows: list[dict], *, count: int = SAMPLE_SIZE) -> list[dict]:
    if len(rows) < count:
        raise ValueError(f"Need {count} independent screened questions; only {len(rows)} remain")
    return sorted(rows, key=lambda row: hashlib.sha256(
        (SEED + "|" + normalize(row["question"])).encode("utf-8")).hexdigest())[:count]


def _prediction_items(selected: list[dict]) -> list[dict]:
    packet_items = []
    for row in selected:
        response = ask(row["question"], top_k=3)
        packet_items.append({"id": row["id"], "question": row["question"],
                             "matches": [{"id": item["id"], "question": item["question"],
                                          "answer": item["answer"], "source": item["source"],
                                          "source_url": item["source_url"]}
                                         for item in response["matches"]],
                             "abstained": response["abstained"]})
    return packet_items


def prepare(*, source: Path = SOURCE_WORKBOOK, output: Path = OUTPUT,
            public_manifest: Path = PUBLIC_MANIFEST) -> dict:
    if not status()["ready"]:
        raise RuntimeError("Deployed MedQuAD baseline is not verified")
    if output.exists() or public_manifest.exists():
        raise FileExistsError("Refusing to replace an existing locked evaluation packet or manifest")
    rows, source_audit = source_rows(source)
    prior, provenance = prior_questions()
    eligible, screening = screen_candidates(rows, prior)
    selected = select_locked(eligible)
    packet_items = _prediction_items(selected)
    model_sha = sha256(MODEL)
    selection_sha = hashlib.sha256("\n".join(row["id"] for row in selected).encode("utf-8")).hexdigest()
    packet_id = hashlib.sha256((SOURCE_SHA256 + model_sha + selection_sha).encode("ascii")).hexdigest()[:24]
    packet = {"schema": PACKET_SCHEMA, "packet_id": packet_id,
              "scope": "Independent medication-question review; no labels or clinical-validity claims yet",
              "source_url": SOURCE_URL, "items": packet_items}
    output.mkdir(parents=True, exist_ok=False)
    packet_path = output / "review_packet.json"
    packet_path.write_text(json.dumps(packet, ensure_ascii=False, indent=2), encoding="utf-8")
    manifest = {"schema": MANIFEST_SCHEMA, "created_on": "2026-10-14",
                "state": "awaiting_two_independent_medical_reviewers",
                "clinical_use_allowed": False,
                "dataset_scope": "Medication questions only; not a comprehensive medical QA generalization test",
                "source_url": SOURCE_URL, "source_sha256": SOURCE_SHA256,
                "source_audit": source_audit, "screening": screening,
                "leakage_screen_sources_sha256": provenance,
                "sampling_rule": "SHA-256(seed + '|' + normalized question), ascending; first 250",
                "sampling_seed": SEED, "locked_question_count": len(selected),
                "locked_selection_sha256": selection_sha, "packet_id": packet_id,
                "packet_sha256": sha256(packet_path), "deployed_model_sha256": model_sha,
                "question_type_counts": dict(sorted(Counter(row["question_type"] for row in selected).items())),
                "automatic_identifier_screen_is_not_deidentification": True,
                "manual_deidentification_review_required_before_sharing": True,
                "labels_complete": False, "performance_estimate_available": False}
    public_manifest.parent.mkdir(parents=True, exist_ok=True)
    public_manifest.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return manifest


def prepare_development(*, source: Path = SOURCE_WORKBOOK, output: Path = OUTPUT,
                        public_manifest: Path = DEVELOPMENT_MANIFEST) -> dict:
    """Create a separate development slice; never inspect locked review labels."""
    locked_path = output / "review_packet.json"
    dev_path = output / "development_packet.json"
    if not locked_path.is_file() or dev_path.exists() or public_manifest.exists():
        raise FileExistsError("Locked packet missing, or development packet already exists")
    locked_manifest = json.loads(PUBLIC_MANIFEST.read_text(encoding="utf-8"))
    if locked_manifest.get("packet_sha256") != sha256(locked_path):
        raise ValueError("Locked packet changed after freezing")
    rows, _ = source_rows(source)
    prior, _ = prior_questions()
    eligible, _ = screen_candidates(rows, prior)
    ranked = select_locked(eligible, count=SAMPLE_SIZE + DEVELOPMENT_SIZE)
    locked = ranked[:SAMPLE_SIZE]
    locked_sha = hashlib.sha256("\n".join(row["id"] for row in locked).encode("utf-8")).hexdigest()
    if locked_sha != locked_manifest["locked_selection_sha256"]:
        raise ValueError("Locked selection changed")
    selected = ranked[SAMPLE_SIZE:]
    model_sha = sha256(MODEL)
    selection_sha = hashlib.sha256("\n".join(row["id"] for row in selected).encode("utf-8")).hexdigest()
    packet_id = hashlib.sha256((SOURCE_SHA256 + model_sha + selection_sha).encode("ascii")).hexdigest()[:24]
    packet = {"schema": PACKET_SCHEMA, "packet_id": packet_id,
              "scope": "Development-only medication question review; not an independent final test",
              "source_url": SOURCE_URL, "items": _prediction_items(selected)}
    dev_path.write_text(json.dumps(packet, ensure_ascii=False, indent=2), encoding="utf-8")
    manifest = {"schema": "careguard.medquad.medication-development-manifest.v1",
                "created_on": "2026-10-14", "state": "awaiting_two_medical_reviewers",
                "clinical_use_allowed": False, "source_sha256": SOURCE_SHA256,
                "deployed_model_sha256": model_sha,
                "linked_locked_packet_id": locked_manifest["packet_id"],
                "sampling_rule": "same hash order, rows 251-350 after leakage screening",
                "development_question_count": len(selected),
                "development_selection_sha256": selection_sha,
                "packet_id": packet_id, "packet_sha256": sha256(dev_path),
                "labels_complete": False, "performance_estimate_available": False}
    public_manifest.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return manifest


def validate_labels(packet: dict, labels: dict) -> tuple[bool, list[str]]:
    errors = []
    if labels.get("schema") != LABEL_SCHEMA or labels.get("packet_id") != packet.get("packet_id"):
        errors.append("Label schema or packet ID mismatch")
    if not str(labels.get("reviewer_id", "")).strip():
        errors.append("Reviewer ID is required")
    entries = labels.get("entries")
    if not isinstance(entries, list):
        return False, errors + ["Entries must be a list"]
    by_id = {row.get("id"): row for row in entries if isinstance(row, dict)}
    expected = {row["id"] for row in packet["items"]}
    if set(by_id) != expected or len(entries) != len(expected):
        errors.append("Every packet question must be labeled exactly once")
    for item in packet["items"]:
        label = by_id.get(item["id"], {})
        if label.get("scope") not in SCOPE:
            errors.append(f"Invalid scope for {item['id']}")
        if item["abstained"] and label.get("abstention") not in ABSTENTION:
            errors.append(f"Missing abstention judgment for {item['id']}")
        matched = label.get("matches")
        if (not isinstance(matched, list) or not all(isinstance(m, dict) for m in matched)
                or [m.get("id") for m in matched] != [m["id"] for m in item["matches"]]):
            errors.append(f"Matched answer IDs differ for {item['id']}")
            continue
        for match in matched:
            if match.get("relevance") not in RELEVANCE or match.get("groundedness") not in GROUNDEDNESS or match.get("safety") not in SAFETY:
                errors.append(f"Incomplete answer rating for {item['id']}")
    return not errors, errors


def review_readiness(packet_path: Path, label_paths: list[Path]) -> dict:
    packet = json.loads(packet_path.read_text(encoding="utf-8"))
    if packet.get("schema") != PACKET_SCHEMA:
        raise ValueError("Unexpected review packet schema")
    reports = []
    reviewer_ids = set()
    for path in label_paths:
        labels = json.loads(path.read_text(encoding="utf-8"))
        valid, errors = validate_labels(packet, labels)
        reviewer = labels.get("reviewer_id")
        if reviewer in reviewer_ids:
            errors.append("Reviewer IDs must be distinct")
            valid = False
        reviewer_ids.add(reviewer)
        reports.append({"reviewer_id": reviewer, "complete": valid, "errors": errors[:20]})
    return {"packet_id": packet["packet_id"], "question_count": len(packet["items"]),
            "independent_reviewers_received": len(reports),
            "ready_for_adjudication": len(reports) >= 2 and all(row["complete"] for row in reports),
            "performance_estimate_available": False,
            "reviewers": reports}


def _wilson(successes: int, total: int) -> list[float] | None:
    if total == 0:
        return None
    z = 1.96
    rate = successes / total
    denominator = 1 + z * z / total
    center = (rate + z * z / (2 * total)) / denominator
    radius = z * math.sqrt(rate * (1 - rate) / total + z * z / (4 * total * total)) / denominator
    return [round(max(0, center - radius), 4), round(min(1, center + radius), 4)]


def _metric(hits: int, total: int) -> dict:
    return {"hits": hits, "count": total, "rate": round(hits / total, 4) if total else None,
            "wilson_95ci": _wilson(hits, total)}


def score_reviewed_packet(packet: dict, reviewer_a: dict, reviewer_b: dict,
                          adjudication: dict | None = None,
                          question_types: dict[str, str] | None = None) -> dict:
    """Compute reviewer-judged retrieval only after complete dual review.

    Disagreement cannot be silently converted into a negative or a success.
    A third complete file provides adjudicated values only for disputed fields.
    """
    if packet.get("schema") != PACKET_SCHEMA:
        raise ValueError("Unexpected review packet")
    for labels in (reviewer_a, reviewer_b, adjudication):
        if labels is None:
            continue
        valid, errors = validate_labels(packet, labels)
        if not valid:
            raise ValueError("Incomplete or mismatched labels: " + "; ".join(errors[:3]))
    reviewers = [reviewer_a["reviewer_id"], reviewer_b["reviewer_id"]]
    if reviewers[0] == reviewers[1]:
        raise ValueError("Two independent reviewer IDs are required")
    if adjudication and adjudication["reviewer_id"] in reviewers:
        raise ValueError("Adjudicator must be a third reviewer")
    a = {item["id"]: item for item in reviewer_a["entries"]}
    b = {item["id"]: item for item in reviewer_b["entries"]}
    c = {item["id"]: item for item in adjudication["entries"]} if adjudication else {}
    disputed = 0
    resolved = []
    for item in packet["items"]:
        key = item["id"]
        out = {"id": key, "matches": []}
        for field in ("scope", "abstention"):
            if field == "abstention" and not item["abstained"]:
                continue
            left, right = a[key].get(field), b[key].get(field)
            if left != right:
                disputed += 1
            out[field] = left if left == right else c.get(key, {}).get(field)
        for index, match in enumerate(item["matches"]):
            rating = {"id": match["id"]}
            for field in ("relevance", "groundedness", "safety"):
                left, right = a[key]["matches"][index][field], b[key]["matches"][index][field]
                if left != right:
                    disputed += 1
                rating[field] = left if left == right else (
                    c[key]["matches"][index][field] if key in c else None)
            out["matches"].append(rating)
        resolved.append(out)
    if disputed and adjudication is None:
        return {"schema": "careguard.medquad.blind-review-score.v1",
                "packet_id": packet["packet_id"], "state": "adjudication_required",
                "reviewed_questions": len(packet["items"]), "disputed_fields": disputed,
                "performance_estimate_available": False}
    rows = []
    for item, labels in zip(packet["items"], resolved):
        accepted = [m["relevance"] == "correct" and m["groundedness"] == "supported"
                    and m["safety"] == "safe" for m in labels["matches"]]
        rows.append({"id": item["id"], "scope": labels["scope"],
                     "abstained": item["abstained"],
                     "abstention": labels.get("abstention"),
                     "top1": bool(accepted and accepted[0]), "top3": any(accepted),
                     "unsafe_return": any(m["safety"] == "unsafe" for m in labels["matches"]),
                     "question_type": (question_types or {}).get(item["id"], "unknown")})
    in_scope = [r for r in rows if r["scope"] == "in_scope"]
    out_scope = [r for r in rows if r["scope"] == "out_of_scope"]
    returned = [r for r in rows if not r["abstained"]]
    by_type = {}
    for kind in sorted({row["question_type"] for row in in_scope}):
        group = [row for row in in_scope if row["question_type"] == kind]
        by_type[kind] = {"top1_supported_safe": _metric(sum(r["top1"] for r in group), len(group)),
                         "top3_supported_safe": _metric(sum(r["top3"] for r in group), len(group))}
    return {"schema": "careguard.medquad.blind-review-score.v1",
            "packet_id": packet["packet_id"], "state": "human_review_completed",
            "reviewed_questions": len(rows), "disputed_fields_adjudicated": disputed,
            "performance_estimate_available": True,
            "scope_counts": dict(Counter(row["scope"] for row in rows)),
            "metrics": {
                "in_scope_top1_supported_safe": _metric(sum(r["top1"] for r in in_scope), len(in_scope)),
                "in_scope_top3_supported_safe": _metric(sum(r["top3"] for r in in_scope), len(in_scope)),
                "returned_query_with_unsafe_answer": _metric(sum(r["unsafe_return"] for r in returned), len(returned)),
                "out_of_scope_appropriate_abstention": _metric(sum(r["abstained"] and r["abstention"] == "appropriate" for r in out_scope), len(out_scope)),
                "in_scope_inappropriate_abstention": _metric(sum(r["abstained"] and r["abstention"] == "inappropriate" for r in in_scope), len(in_scope)),
            }, "by_question_type": by_type,
            "limitations": "Reviewer judgments on a medication-only public corpus; not clinical validation or a complete medical QA test."}


def score_files(packet_path: Path, label_paths: list[Path], adjudication_path: Path | None = None) -> dict:
    packet = json.loads(packet_path.read_text(encoding="utf-8"))
    reviewers = [json.loads(path.read_text(encoding="utf-8")) for path in label_paths]
    adjudication = json.loads(adjudication_path.read_text(encoding="utf-8")) if adjudication_path else None
    source, _ = source_rows()
    type_by_id = {row["id"]: row["question_type"] for row in source}
    return score_reviewed_packet(packet, reviewers[0], reviewers[1], adjudication, type_by_id)


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare or check a locked medication QA blind review")
    command = parser.add_subparsers(dest="command", required=True)
    command.add_parser("prepare")
    command.add_parser("prepare-development")
    check = command.add_parser("check-labels")
    check.add_argument("packet", type=Path)
    check.add_argument("labels", type=Path, nargs="+")
    score = command.add_parser("score")
    score.add_argument("packet", type=Path)
    score.add_argument("reviewer_a", type=Path)
    score.add_argument("reviewer_b", type=Path)
    score.add_argument("--adjudication", type=Path)
    args = parser.parse_args()
    if args.command == "prepare":
        report = prepare()
    elif args.command == "prepare-development":
        report = prepare_development()
    elif args.command == "check-labels":
        report = review_readiness(args.packet, args.labels)
    else:
        report = score_files(args.packet, [args.reviewer_a, args.reviewer_b], args.adjudication)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
