"""Contract tests for the actual original-engine computation path."""

from fastapi.testclient import TestClient

import api
from careguard_site import app


SYNTHETIC_INPUT = {
    "patient_query": "合成夜班交接：观察到突发胸痛，已呼叫值班负责人。",
    "observation": {
        "heart_rate": 112,
        "spo2": 91,
        "temperature": 36.8,
        "respiratory_rate": 25,
    },
    "force_high_risk": True,
}


def test_original_source_is_present_and_byte_identical():
    result = TestClient(app).get("/engineering/status")
    assert result.status_code == 200
    body = result.json()
    assert body["core_source_match"] is True
    assert set(body["files"]) == set(api.ORIGINAL_ENGINE_HASHES)
    assert all(item["matches_original_package"] for item in body["files"].values())


def test_single_observation_is_preprocessed_and_feeds_real_engine_call(monkeypatch):
    calls = []

    class Engine:
        def run_collaborative_task(self, **kwargs):
            calls.append(kwargs)
            return {
                "query": kwargs["patient_query"] + "\n" + kwargs["multimodal_input"]["clinical_text"],
                "request_id": "bridge-001",
                "high_risk": kwargs["force_high_risk"],
                "latency_seconds": 0.32,
                "model_input_modalities": {"clinical_text": True, "time_series": 0, "images": 0, "lab_results": 0},
                "execution_integrity": {"dma_backend": "ollama_local_http", "ollama_generation_verified": True},
                "dma": {"prediction": "unvalidated", "confidence": 0.3},
                "tfa": {"available": False, "validated": False},
                "retrieval": {"top_docs": []},
                "fusion": {"conflict_count": 0},
                "verification": {"verification_status": "not_available"},
                "hitl": {"triggered": True},
                "consensus": {"approved": False},
                "clinical_readiness": {"clinical_use_allowed": False},
            }

    monkeypatch.setattr(api, "_get_ecosystem", lambda: Engine())
    response = TestClient(app).post("/screening/engineering", json=SYNTHETIC_INPUT)
    assert response.status_code == 200
    body = response.json()
    assert len(calls) == 1
    assert calls[0]["patient_query"] == SYNTHETIC_INPUT["patient_query"]
    assert "心率 112" in calls[0]["multimodal_input"]["clinical_text"]
    assert "血氧 91%" in calls[0]["multimodal_input"]["clinical_text"]
    assert "time_series" not in calls[0]["multimodal_input"]
    assert body["engineering"]["parsed_observation_count"] == 1
    assert body["engineering"]["parsed_observation"]["temperature"] == 36.8
    assert body["engineering"]["core_source_match"] is True
    assert body["engineering"]["temporal_prediction_used"] is False
    assert body["screening"]["request_id"] == "bridge-001"
    assert body["screening"]["engine_label"] == "Ollama 已验证"
    assert body["audit"]["human_review"]["status"] == "pending"
    assert SYNTHETIC_INPUT["patient_query"] not in str(body["audit"])


def test_engineering_rejects_invalid_observation_before_model_call(monkeypatch):
    monkeypatch.setattr(api, "_get_ecosystem", lambda: (_ for _ in ()).throw(AssertionError("called")))
    invalid = {**SYNTHETIC_INPUT, "observation": {**SYNTHETIC_INPUT["observation"], "spo2": 130}}
    response = TestClient(app).post("/screening/engineering", json=invalid)
    assert response.status_code == 422
