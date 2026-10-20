from __future__ import annotations

import base64
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from clinical_validation import (
    ClinicalReadinessGate,
    grouped_train_test_split,
    label_mention_mask,
    probability_calibration_metrics,
)
from evidence_ingestion import PubMedEvidenceClient
from mapfm_ecosystem_repaired import (
    ContinuousLearningLoop,
    EcosystemConfig,
    HumanFeedbackRecord,
    RealPerceptionAgent,
    RealPrivacyAgent,
    HeterogeneousMultiAgentEcosystem,
    DecisionMakingAgent,
)
from exceptions import InferenceError
from utils import legacy_hash_embedding


def test_grouped_split_has_no_duplicate_question_overlap() -> None:
    rows = []
    for label in ("Asthma", "Pneumonia"):
        for index in range(12):
            question = f"case {index // 2} for {label}"
            rows.append({"question": question, "answer": "x", "area": label})
    train, test, audit = grouped_train_test_split(pd.DataFrame(rows), test_size=0.25, random_seed=7)
    assert len(train) + len(test) == len(rows)
    assert audit["passed"] is True
    assert audit["overlapping_question_groups"] == 0


def test_label_mention_mask_is_explicit_stress_test() -> None:
    assert "asthma" not in label_mention_mask("Likely Asthma with wheeze", "Asthma").lower()


def test_readiness_gate_fails_closed_without_external_validation() -> None:
    result = ClinicalReadinessGate(require_validation=True).evaluate(
        split_audit={"passed": True},
        tfa_prediction={"validated": False},
        verification_summary={"verification_scope": "provenance_only"},
    )
    assert result.clinical_use_allowed is False
    assert result.status == "research_only"


def test_calibration_metrics_include_brier_and_ece() -> None:
    metrics = probability_calibration_metrics([0.9, 0.8, 0.2, 0.1], [True, True, False, False])
    assert metrics["available"] is True
    assert 0.0 <= metrics["brier_score"] <= 1.0
    assert 0.0 <= metrics["expected_calibration_error"] <= 1.0


def test_aes_gcm_roundtrip_and_tamper_detection(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MAPFM_AES_KEY_B64", base64.b64encode(b"k" * 32).decode("ascii"))
    agent = RealPrivacyAgent(EcosystemConfig())
    ciphertext = agent.encrypt_message("patient payload")
    assert agent.decrypt_message(ciphertext) == "patient payload"
    packed = bytearray(base64.urlsafe_b64decode(ciphertext))
    packed[-1] ^= 1
    with pytest.raises(Exception):
        agent.decrypt_message(base64.urlsafe_b64encode(bytes(packed)).decode("ascii"))


def test_actual_image_pixels_are_consumed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import mapfm_ecosystem_repaired as ecosystem_module
    monkeypatch.setattr(
        ecosystem_module,
        "semantic_embedding",
        lambda text, dim, model_name: np.ones(dim, dtype=np.float32) / np.sqrt(dim),
    )
    pil = pytest.importorskip("PIL.Image")
    image_path = tmp_path / "scan.png"
    pil.fromarray(np.full((24, 24), 160, dtype=np.uint8)).save(image_path)
    agent = RealPerceptionAgent(EcosystemConfig())
    result = agent.encode("chest image", {"images": [{"path": str(image_path)}]})
    assert result["metadata"]["images_consumed"] == 1
    assert result["metadata"]["image_sources"] == ["actual_pixels"]
    assert result["metadata"]["image_interpretation_validated"] is False


def test_human_review_is_persisted_then_removed(tmp_path: Path) -> None:
    config = EcosystemConfig(feedback_store_path=str(tmp_path / "feedback.jsonl"))
    loop = ContinuousLearningLoop(config)
    record = HumanFeedbackRecord(sample_id=8, query="q", predicted_label="A", corrected_label="B")
    loop.ingest(record)
    loop.record_feedback(record=record, human_label="B", is_correct=False, reviewer="doctor")
    assert (tmp_path / "feedback.jsonl").read_text(encoding="utf-8").strip()
    assert loop.remove_from_buffer({"sample_id": 8, "query": "q", "predicted_label": "A"}) is True
    assert not loop.feedback_buffer
    assert len(loop.training_buffer) == 1


def test_pubmed_client_parses_traceable_record() -> None:
    xml = b"""<PubmedArticleSet><PubmedArticle><MedlineCitation><PMID>123</PMID><Article>
    <ArticleTitle>Validated title</ArticleTitle><Abstract><AbstractText>Real abstract.</AbstractText></Abstract>
    <Journal><Title>Journal</Title><JournalIssue><PubDate><Year>2025</Year></PubDate></JournalIssue></Journal>
    </Article></MedlineCitation><PubmedData><ArticleIdList><ArticleId IdType='doi'>10.1/x</ArticleId></ArticleIdList>
    </PubmedData></PubmedArticle></PubmedArticleSet>"""

    class Response:
        def __init__(self, *, payload=None, content=b"") -> None:
            self._payload = payload
            self.content = content

        def json(self):
            return self._payload

        def raise_for_status(self):
            return None

    class Session:
        calls = 0

        def get(self, *args, **kwargs):
            self.calls += 1
            if self.calls == 1:
                return Response(payload={"esearchresult": {"idlist": ["123"]}})
            return Response(content=xml)

    report = PubMedEvidenceClient(session=Session()).search("asthma", max_results=1)
    assert report.error is None
    assert report.documents[0]["metadata"]["pmid"] == "123"
    assert report.documents[0]["metadata"]["provenance_verified"] is True


def test_end_to_end_is_forced_to_research_only_without_validation(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    import mapfm_ecosystem_repaired as ecosystem_module

    monkeypatch.setattr(
        DecisionMakingAgent,
        "_ollama_json_infer",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            InferenceError("offline test", code="TEST_OFFLINE")
        ),
    )
    monkeypatch.setattr(
        ecosystem_module,
        "semantic_embedding",
        lambda text, dim, model_name: legacy_hash_embedding(text, dim),
    )
    monkeypatch.setattr(
        ecosystem_module,
        "batch_semantic_embeddings",
        lambda texts, dim, model_name: np.vstack([legacy_hash_embedding(text, dim) for text in texts]),
    )
    rows = []
    for label in ("Asthma", "Pneumonia"):
        for index in range(20):
            rows.append({
                "id": len(rows) + 1,
                "question": f"unique clinical presentation {index} for {label}",
                "answer": f"reviewed educational content {index}",
                "area": label,
                "source": "Dataset",
            })
    config = EcosystemConfig(
        enable_faiss_dense_index=False,
        enable_medtsllm=False,
        feedback_store_path=str(tmp_path / "feedback.jsonl"),
    )
    ecosystem = HeterogeneousMultiAgentEcosystem(config, pd.DataFrame(rows), verbose=False)
    result = ecosystem.run_collaborative_task(
        "severe wheeze and cough",
        multimodal_input={
            "clinical_text": "No patient identifiers. Symptoms started yesterday.",
            "lab_results": [{"test": "CRP", "value": 12, "unit": "mg/L", "abnormal": True}],
            "time_series": [0.2, 0.3, 0.4],
        },
    )
    assert result["clinical_readiness"]["status"] == "research_only"
    assert result["clinical_readiness"]["clinical_use_allowed"] is False
    assert result["consensus"]["approved"] is False
    assert result["perception"]["metadata"]["lab_results_consumed"] == 1
    assert result["tfa"]["validated"] is False
    assert result["high_risk"] is True
    assert ecosystem.topology_manager.routed_messages >= 7
