"""Human review must not become an unlabelled automatic accuracy claim."""

import json

import pytest
from fastapi.testclient import TestClient

from medquad_blind_eval import (
    LABEL_SCHEMA, PACKET_SCHEMA, score_reviewed_packet, validate_labels,
)
from package_competition import ROOT


def _packet():
    return {"schema": PACKET_SCHEMA, "packet_id": "frozen-123", "items": [
        {"id": "q1", "question": "Example?", "abstained": False,
         "matches": [{"id": "a1"}]},
        {"id": "q2", "question": "Another example?", "abstained": True, "matches": []},
    ]}


def _labels(reviewer, *, q1_relevance="correct", q2_abstention="appropriate"):
    return {"schema": LABEL_SCHEMA, "packet_id": "frozen-123", "reviewer_id": reviewer,
            "entries": [
                {"id": "q1", "scope": "in_scope", "abstention": "",
                 "matches": [{"id": "a1", "relevance": q1_relevance,
                              "groundedness": "supported", "safety": "safe"}]},
                {"id": "q2", "scope": "out_of_scope", "abstention": q2_abstention,
                 "matches": []},
            ]}


def test_complete_dual_review_scores_only_human_judged_outcomes():
    packet = _packet()
    left, right = _labels("A"), _labels("B")
    assert validate_labels(packet, left) == (True, [])
    report = score_reviewed_packet(packet, left, right, question_types={"q1": "Dose"})
    assert report["performance_estimate_available"] is True
    assert report["metrics"]["in_scope_top1_supported_safe"]["hits"] == 1
    assert report["metrics"]["out_of_scope_appropriate_abstention"]["hits"] == 1
    assert report["by_question_type"]["Dose"]["top3_supported_safe"]["count"] == 1


def test_disagreement_blocks_score_until_third_review():
    packet = _packet()
    left, right = _labels("A"), _labels("B", q1_relevance="partial")
    pending = score_reviewed_packet(packet, left, right)
    assert pending["state"] == "adjudication_required"
    assert pending["performance_estimate_available"] is False
    assert "metrics" not in pending
    decided = score_reviewed_packet(packet, left, right, _labels("C", q1_relevance="partial"))
    assert decided["metrics"]["in_scope_top1_supported_safe"]["hits"] == 0


def test_incomplete_or_same_reviewer_cannot_produce_score():
    packet = _packet()
    broken = _labels("A")
    broken["entries"][0]["matches"][0]["safety"] = ""
    assert validate_labels(packet, broken)[0] is False
    with pytest.raises(ValueError):
        score_reviewed_packet(packet, broken, _labels("B"))
    with pytest.raises(ValueError):
        score_reviewed_packet(packet, _labels("A"), _labels("A"))


def test_public_audit_contains_only_aggregate_and_pending_state():
    locked = json.loads((ROOT / "artifacts/medquad_qa/blind_eval_manifest_20261014.json").read_text(encoding="utf-8"))
    development = json.loads((ROOT / "artifacts/medquad_qa/medication_development_manifest_20261014.json").read_text(encoding="utf-8"))
    assert locked["locked_question_count"] == 250
    assert development["development_question_count"] == 100
    assert development["linked_locked_packet_id"] == locked["packet_id"]
    assert locked["performance_estimate_available"] is False
    assert "items" not in locked and "items" not in development
    html = (ROOT / "tools/medquad_blind_review.html").read_text(encoding="utf-8")
    assert "fetch(" not in html


def test_local_review_route_serves_ui_but_not_question_packet():
    from careguard_site import app

    client = TestClient(app)
    response = client.get("/site/medquad-review", follow_redirects=False)
    assert response.status_code == 302
    assert response.headers["location"] == "/?view=workspace#review-desk"
    response = client.get(response.headers["location"])
    assert response.status_code == 200
    assert 'id="review-title"' in response.text
    assert 'id="review-view"' in response.text
    assert 'src="/medical-language.js?' in response.text
    assert 'src="/medquad-review.js?' in response.text
    assert "fetch(" not in (ROOT / "careguard_web/medquad-review.js").read_text(encoding="utf-8")
    assert client.get("/artifacts/medquad_qa_candidate/medication_blind_20261014/review_packet.json").status_code == 404
