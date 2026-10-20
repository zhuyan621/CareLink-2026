"""Synthetic software-behaviour matrix, not a clinical accuracy study."""

from __future__ import annotations

import copy

import pytest

from careguard_presenter import build_screening_view, review_decisions


BASE = {
    "query": "合成夜班记录：状态待核对。",
    "request_id": "matrix-demo",
    "high_risk": False,
    "retrieval": {"top_docs": []},
    "verification": {"serious_conflicts": 0},
    "fusion": {"conflict_count": 0},
    "hitl": {"triggered": False},
    "consensus": {"approved": True},
    "tfa": {"available": False, "validated": False, "risk_score": 0.0},
}


@pytest.mark.parametrize(
    ("change", "expected", "why"),
    [
        ({"query": "突发胸痛伴大汗，已通知值班负责人。"}, "P1", "急性胸痛线索"),
        ({"query": "突发口角歪斜，言语不清。"}, "P1", "突发神经功能线索"),
        ({"query": "呼吸困难，现场情况待核对。"}, "P1", "急性关键词"),
        ({"high_risk": True}, "P1", "强制高风险"),
        ({"verification": {"serious_conflicts": 1}}, "P1", "严重证据冲突"),
        ({"hitl": {"triggered": True}}, "P2", "人工门控"),
        ({"consensus": {"approved": False}}, "P2", "共识未通过"),
        ({}, "P3", "没有强制升级信号；仍需人工复核"),
    ],
)
def test_synthetic_priority_path_is_explicit(change, expected, why):
    raw = copy.deepcopy(BASE)
    raw.update(change)
    view = build_screening_view(raw)
    assert view["priority"]["code"] == expected, why
    assert view["requires_human_review"] is True
    assert view["temporal_assessment"]["available"] is False
    assert "概率" in view["temporal_assessment"]["label"]
    if expected == "P1":
        assert "维持常规观察" not in review_decisions(expected)


def test_source_and_fallback_boundaries_remain_visible_in_demo_matrix():
    raw = copy.deepcopy(BASE)
    raw["retrieval"]["top_docs"] = [{
        "question": "Synthetic source row", "source": "example", "verification_passed": False,
    }]
    raw["execution_integrity"] = {"dma_backend": "legacy_fallback", "dma_fallback_used": True}
    view = build_screening_view(raw)
    assert view["evidence_count"] == 0
    assert view["evidence"] == []
    assert view["engine_label"] == "已降级运行"
    assert view["requires_human_review"] is True
