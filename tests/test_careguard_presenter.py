from careguard_presenter import build_audit_report, build_screening_view, review_decisions


def _raw_result():
    return {
        "query": "老人突发胸痛并伴大汗，夜班护工请求复核。",
        "request_id": "demo-001",
        "high_risk": True,
        "latency_seconds": 2.345,
        "dma": {
            "prediction": "Myocardial Infarction",
            "confidence": 0.76,
            "confidence_interpretation": "uncalibrated_model_self_report",
        },
        "retrieval": {
            "top_docs": [
                {
                    "question": "Acute chest pain guideline",
                    "source": "PubMed",
                    "last_updated": "2026-01-01",
                    "similarity": 0.82,
                    "verification_passed": True,
                    "metadata": {"source_url": "https://example.test/evidence"},
                }
            ]
        },
        "fusion": {"conflict_count": 1},
        "verification": {
            "verification_status": "passed",
            "verification_ratio": 0.75,
            "serious_conflicts": 0,
        },
        "tfa": {
            "available": False,
            "validated": False,
            "risk_score": 0.0,
            "blocked_reason": "No validated checkpoint",
        },
        "hitl": {"triggered": True, "reason": "urgent signal"},
        "consensus": {"approved": False, "escalate_to_human": True},
        "clinical_readiness": {"clinical_use_allowed": False},
    }


def test_high_risk_case_is_never_auto_released():
    view = build_screening_view(_raw_result())
    assert view["priority"]["code"] == "P1"
    assert view["requires_human_review"] is True
    assert view["candidate_risk_domain"] == "急性胸痛警示线索"
    assert view["legacy_model_suppressed"] is True
    assert view["reference_count"] == 1


def test_unvalidated_temporal_zero_is_not_presented_as_low_risk():
    view = build_screening_view(_raw_result())
    assert view["temporal_assessment"]["available"] is False
    assert "未提供" in view["temporal_assessment"]["label"]


def test_evidence_keeps_provenance_and_scope_boundary():
    row = build_screening_view(_raw_result())["evidence"][0]
    assert row["source"] == "PubMed"
    assert row["url"] == "https://example.test/evidence"
    assert "不等同" in row["scope"]


def test_unverified_retrieval_hit_is_not_displayed_as_evidence():
    raw = _raw_result()
    raw["retrieval"]["top_docs"][0]["verification_passed"] = False
    view = build_screening_view(raw)
    assert view["evidence"] == []
    assert view["reference_count"] == 1


def test_wrong_legacy_diagnosis_is_suppressed():
    raw = _raw_result()
    raw["dma"]["prediction"] = "Skin Cancer"
    raw["dma"]["confidence"] = 0.052
    view = build_screening_view(raw)
    assert "Skin Cancer" not in view["candidate_risk_domain"]
    assert view["priority"]["code"] == "P1"


def test_engine_status_only_claims_ollama_when_generation_is_verified():
    raw = _raw_result()
    assert build_screening_view(raw)["engine_label"] == "状态未确认"
    raw["execution_integrity"] = {
        "dma_backend": "ollama_local_http",
        "ollama_generation_verified": True,
        "dma_fallback_used": False,
    }
    view = build_screening_view(raw)
    assert view["engine_label"] == "Ollama 已验证"
    assert view["diagnostic_label_suppressed"] is True
    raw["execution_integrity"] = {"dma_backend": "legacy_fallback", "dma_fallback_used": True}
    assert build_screening_view(raw)["engine_label"] == "已降级运行"


def test_p1_review_cannot_choose_routine_observation():
    assert "维持常规观察" not in review_decisions("P1")
    assert "维持常规观察" in review_decisions("P2")


def test_synthetic_stroke_and_chronic_change_are_separated():
    raw = _raw_result()
    raw["high_risk"] = False
    raw["verification"]["serious_conflicts"] = 0
    raw["query"] = "突发口角歪斜、言语含糊，单侧上肢无力"
    assert build_screening_view(raw)["candidate_risk_domain"] == "突发神经功能异常线索"
    raw["query"] = "近三日气促加重，双下肢水肿，平卧不适"
    view = build_screening_view(raw)
    assert view["candidate_risk_domain"] == "呼吸与水肿变化线索"
    assert view["priority"]["code"] == "P2"


def test_audit_report_assigns_final_decision_to_human():
    raw = _raw_result()
    view = build_screening_view(raw)
    report = build_audit_report(
        raw,
        view,
        {
            "status": "completed",
            "reviewer": "演示复核员",
            "decision": "立即转人工评估",
            "notes": "已确认演示流程",
            "reviewed_at": "2026-10-10T10:00:00+08:00",
        },
    )
    assert report["human_review"]["status"] == "completed"
    assert report["reproducibility"]["clinical_use_allowed"] is False
    assert "query" not in report["input_summary"]
    assert len(report["input_summary"]["query_sha256"]) == 64
