"""Full official-source accounting and live attributed QA contract."""

import io
from zipfile import ZipFile

from fastapi.testclient import TestClient

from api import app
from medquad_qa import SOURCE, ask, read_official_archive, sha256, status
from medquad_generalization import external_judgments


def test_complete_official_archive_and_fitted_model_have_matching_coverage():
    records, counts = read_official_archive(SOURCE)
    state = status()
    assert state["ready"] is True
    assert counts["parse_errors"] == 0
    assert counts["qa_pairs_total"] == 47441
    assert counts["answer_bearing_pairs"] == len(records) == state["indexed_pairs"] == 16407
    assert counts["answerless_pairs"] == 31034
    assert counts["qa_pairs_total"] == counts["answer_bearing_pairs"] + counts["answerless_pairs"]
    assert state["source_sha256"] == sha256(SOURCE)
    assert state["vocabulary_fitted_questions"] == counts["qa_pairs_total"]
    assert state["neural_weights_trained"] is False
    assert state["prospective_diabetes_training"] is False
    assert state["semantic_encoder_pretrained_not_finetuned"] is True
    assert state["external_test_questions"] == 104
    assert state["external_evaluable_questions"] == 38
    assert state["known_relevant_at_3_hybrid"] > state["known_relevant_at_3_lexical"]
    assert state["natural_query_holdout_count"] == 38
    assert state["natural_query_known_answer_at_3"] == 0.4211
    assert state["rejected_candidate_known_answer_at_3"] < state["natural_query_known_answer_at_3"]
    assert state["nonmedical_abstention"] == 1.0
    assert state["mediqa2019_evaluable_questions"] == 52
    assert state["mediqa2019_baseline_known_answer_at_1"] == 0.4231
    assert state["mediqa2019_baseline_known_answer_at_3"] == 0.6154
    assert state["mediqa2019_answer_field_candidate_deployed"] is False
    assert state["latest_generalization_candidates_rejected"] == 3
    assert state["latest_generalization_baseline_retained"] is True
    assert state["blind_evaluation_locked_questions"] == 250
    assert state["blind_evaluation_development_questions"] == 100
    assert state["blind_evaluation_human_labels_complete"] is False


def test_source_parser_never_trains_on_empty_answers(tmp_path):
    example = b'<Document source="NIDDK" url="https://example.org/a"><Focus>Diabetes</Focus><QAPairs><QAPair pid="1"><Question qtype="information">What is diabetes?</Question><Answer>Source text.</Answer></QAPair><QAPair pid="2"><Question>What is missing?</Question><Answer></Answer></QAPair></QAPairs></Document>'
    source = tmp_path / "tiny.zip"
    with ZipFile(source, "w") as archive:
        archive.writestr("MedQuAD-master/demo.xml", example)
    rows, counts = read_official_archive(source)
    assert counts["qa_pairs_total"] == 2
    assert counts["answer_bearing_pairs"] == 1
    assert counts["answerless_pairs"] == 1
    assert rows[0]["answer"] == "Source text."


def test_live_qa_returns_attributed_source_and_no_foot_routes():
    client = TestClient(app)
    assert client.get("/mapfm/medquad-qa/status").json()["ready"] is True
    response = client.post("/mapfm/medquad-qa/ask", json={"question": "What is diabetes?", "top_k": 3})
    assert response.status_code == 200
    data = response.json()
    assert data["clinical_use_allowed"] is False
    assert data["matches"]
    assert data["matches"][0]["answer"].lower().startswith("diabetes is")
    assert all(item["source_url"] and item["answer"] for item in data["matches"])
    assert len({item["source_url"] for item in data["matches"]}) == len(data["matches"])
    assert client.post("/mapfm/medquad-qa/ask", json={"question": "a"}).status_code == 422
    paths = client.get("/openapi.json").json()["paths"]
    assert "/risk/foot-ulcer-2y" not in paths
    assert "/foot-ulcer/segment" not in paths


def test_unrelated_question_abstains_instead_of_inventing_an_answer():
    for question in ("How do I repair my bicycle chain?", "How do I bake sourdough bread?",
                     "What was the score of the football game last night?"):
        result = ask(question)
        assert result["abstained"] is True
        assert result["matches"] == []


def test_external_question_alignment_and_semantic_paraphrase():
    queries, stats = external_judgments()
    assert len(queries) == stats["official_test_questions"] == 104
    assert stats["official_judged_answers"] == 2479
    assert stats["exactly_aligned_answer_rows"] == 565
    result = ask("What are the signs that someone might have diabetes?")
    assert not result["abstained"]
    assert "diabetes" in result["matches"][0]["question"].lower()
    assert result["matches"][0]["semantic_score"] > result["matches"][0]["lexical_score"]


def test_site_only_loads_active_research_modules():
    from careguard_site import app as site_app

    client = TestClient(site_app)
    html = client.get("/").text
    assert '/medquad.js' in html and '/medquad.css' in html
    assert '/foot-risk.js' not in html and '/foot-ulcer.js' not in html
    assert client.get("/medquad.js").status_code == 200
    assert client.get("/medquad.css").status_code == 200
