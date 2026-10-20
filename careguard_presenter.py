"""Competition-safe presentation helpers for the CareLink demo.

The research pipeline returns detailed internal fields.  This module turns those
fields into a small, audience-facing view model without promoting model output to
a clinical diagnosis or inventing a temporal-risk probability.
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Mapping, Optional


URGENT_TERMS = (
    "胸痛", "胸闷", "呼吸困难", "意识不清", "昏厥", "偏瘫", "口角歪斜",
    "言语不清", "大汗", "chest pain", "shortness of breath", "unconscious",
    "facial droop", "slurred speech", "one-sided weakness",
)

# Manually selected public information cards for the three synthetic demo cases.
# These are not live retrieval hits and must never be counted as such.
REFERENCE_CARDS = {
    "chest": {
        "title": "NHS：Chest pain",
        "summary": "持续胸部压迫感，尤其伴出汗、恶心、气短或向手臂放射，是需要立即寻求急救评估的警示表现。",
        "url": "https://www.nhs.uk/symptoms/chest-pain/",
        "source": "NHS 公共健康信息",
        "checked_on": "2026-10-10",
    },
    "stroke": {
        "title": "NHS：Symptoms of a stroke",
        "summary": "突发面部下垂、单侧上肢无力、言语异常属于 FAST 警示表现，应立即寻求急救评估。",
        "url": "https://www.nhs.uk/conditions/stroke/symptoms/",
        "source": "NHS 公共健康信息",
        "checked_on": "2026-10-10",
    },
    "breathing": {
        "title": "NHS：Heart failure",
        "summary": "活动或平卧时气短、腿部肿胀等变化需要由专业人员评估原因；单凭症状不能确诊。",
        "url": "https://www.nhs.uk/conditions/heart-failure/",
        "source": "NHS 公共健康信息",
        "checked_on": "2026-10-10",
    },
}


def _number(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _evidence_rows(raw: Mapping[str, Any], limit: int = 5) -> List[Dict[str, Any]]:
    retrieval = raw.get("retrieval") or {}
    rows: List[Dict[str, Any]] = []
    for item in retrieval.get("top_docs") or []:
        if not item.get("verification_passed", False):
            continue
        metadata = item.get("metadata") or {}
        rows.append(
            {
                "title": item.get("question") or "未命名证据",
                "source": item.get("source") or "来源未标注",
                "updated": item.get("last_updated") or "—",
                "relevance": round(_number(item.get("similarity")), 3),
                "verified": bool(item.get("verification_passed", False)),
                "url": metadata.get("source_url") or "",
                "scope": "来源与时效核验；不等同于医学结论已被证明",
            }
        )
        if len(rows) >= limit:
            break
    return rows


def _observed_clues(query: str) -> Dict[str, Any]:
    """Conservative, explainable demo routing; not a clinical triage rule."""
    q = query.lower()
    chest = any(term in q for term in ("胸痛", "胸部压榨", "chest pain"))
    chest_associated = any(term in q for term in ("大汗", "放射", "呼吸困难", "恶心", "sweat"))
    stroke = any(term in q for term in ("口角歪斜", "言语含糊", "言语不清", "单侧无力", "上肢无力", "facial droop", "slurred speech"))
    breathing = any(term in q for term in ("气促", "呼吸困难", "breathless"))
    deterioration = any(term in q for term in ("加重", "水肿", "垫高枕头", "平卧", "worsening", "swelling"))
    if chest and chest_associated:
        return {"label": "急性胸痛警示线索", "level": "P1", "matched": "胸痛及伴随症状", "reference_keys": ["chest"]}
    if stroke:
        return {"label": "突发神经功能异常线索", "level": "P1", "matched": "面部、言语或单侧肢体变化", "reference_keys": ["stroke"]}
    if breathing and deterioration:
        return {"label": "呼吸与水肿变化线索", "level": "P2", "matched": "气促加重及水肿或平卧不适", "reference_keys": ["breathing"]}
    return {"label": "未能可靠归类", "level": "P2", "matched": "没有命中本版演示规则", "reference_keys": []}


def _priority(raw: Mapping[str, Any], query: str, clue: Mapping[str, Any]) -> Dict[str, str]:
    hitl = raw.get("hitl") or {}
    verification = raw.get("verification") or {}
    urgent_keyword = any(term in query.lower() for term in URGENT_TERMS)
    serious_conflicts = int(verification.get("serious_conflicts", 0) or 0)
    if clue["level"] == "P1" or urgent_keyword or bool(raw.get("high_risk")) or serious_conflicts:
        return {
            "code": "P1",
            "label": "立即人工复核",
            "color": "#d84a4a",
            "reason": "存在急性风险线索或证据冲突，系统不自动放行。",
        }
    if hitl.get("triggered") or not (raw.get("consensus") or {}).get("approved", False):
        return {
            "code": "P2",
            "label": "优先人工复核",
            "color": "#d8912f",
            "reason": "模型不确定性、证据不足或验证门控要求人工确认。",
        }
    return {
        "code": "P3",
        "label": "常规复核",
        "color": "#2f9f78",
        "reason": "未发现强制升级信号，仍需由专业人员确认。",
    }


def review_decisions(priority_code: str) -> List[str]:
    """A P1 demo must not offer a routine-observation disposition."""
    if priority_code == "P1":
        return [
            "立即转专业人员评估",
            "已按机构急救流程升级",
            "退回重新筛查（人工继续接管）",
        ]
    return [
        "转专业人员评估",
        "补充信息后复核",
        "维持常规观察",
        "退回重新筛查",
    ]


def build_screening_view(raw: Mapping[str, Any]) -> Dict[str, Any]:
    """Build the truthful, competition-facing output used by UI and API."""
    dma = raw.get("dma") or {}
    tfa = raw.get("tfa") or {}
    verification = raw.get("verification") or {}
    fusion = raw.get("fusion") or {}
    consensus = raw.get("consensus") or {}
    hitl = raw.get("hitl") or {}
    integrity = raw.get("execution_integrity") or {}
    query = str(raw.get("query") or "")
    clue = _observed_clues(query)
    evidence = _evidence_rows(raw)
    reference_cards = [REFERENCE_CARDS[key] for key in clue["reference_keys"]]
    confidence = _number(dma.get("confidence"))
    temporal_available = bool(tfa.get("available") and tfa.get("validated"))
    priority = _priority(raw, query, clue)
    backend = integrity.get("dma_backend") or dma.get("dma_backend") or "unknown"
    if backend == "ollama_local_http" and integrity.get("ollama_generation_verified"):
        engine_label = "Ollama 已验证"
        engine_status = "本机 Ollama 已完成生成；诊断标签仍不参与养老场景分流。"
    elif backend == "legacy_fallback" or integrity.get("dma_fallback_used"):
        engine_label = "已降级运行"
        engine_status = "本机大模型不可用，已降级运行；诊断标签被隔离。"
    else:
        engine_label = "状态未确认"
        engine_status = "尚无可核验的本机大模型生成记录；诊断标签不参与分流。"

    return {
        "request_id": raw.get("request_id") or "—",
        "priority": priority,
        "candidate_risk_domain": clue["label"],
        "observed_clue": clue["matched"],
        "legacy_model_suppressed": bool(dma.get("prediction")),
        "legacy_model_suppression_reason": "诊断标签未完成养老场景适配和外部验证，不参与分流。",
        "diagnostic_label_suppressed": bool(dma.get("prediction")),
        "engine_label": engine_label,
        "engine_status": engine_status,
        "engine_backend": backend,
        "model_self_score": round(confidence, 3),
        "score_interpretation": dma.get("confidence_interpretation")
        or "模型内部自评分，不是临床概率",
        "requires_human_review": True,
        "review_reason": hitl.get("reason") or consensus.get("reason")
        or "比赛演示版所有输出均需由专业人员确认",
        "evidence": evidence,
        "evidence_count": len(evidence),
        "reference_cards": reference_cards,
        "reference_count": len(reference_cards),
        "evidence_status": verification.get("verification_status") or "not_available",
        "verification_ratio": round(_number(verification.get("verification_ratio")), 3),
        "conflict_count": int(fusion.get("conflict_count", 0) or 0),
        "temporal_assessment": {
            "available": temporal_available,
            "label": tfa.get("risk_label") if temporal_available else "未提供临床风险概率",
            "reason": (
                tfa.get("reasoning")
                if temporal_available
                else "未配置与当前养老照护任务匹配且完成验证的时序检查点。"
            ),
        },
        "pipeline": [
            {"name": "输入边界", "status": "已提醒", "detail": "仅接收合成或已脱敏记录；审计导出不包含原文"},
            {"name": "多策略检索", "status": "完成", "detail": f"动态检索中有 {len(evidence)} 条通过来源核验；离线参考资料单列"},
            {"name": "证据融合", "status": "完成", "detail": f"检测到 {int(fusion.get('conflict_count', 0) or 0)} 处潜在冲突"},
            {"name": "线索筛查", "status": "完成", "detail": "可解释演示规则提取风险线索；未经验证的诊断标签不参与分流"},
            {"name": "人工复核", "status": "待处理" if bool(hitl.get("triggered")) else "按制度复核", "detail": "由具备资质的人员作出最终判断"},
        ],
        "limitations": [
            "本作品为科研与竞赛原型，不替代医生或护理专业人员。",
            "模型自评分不等于经临床校准的患病概率。",
            "证据核验覆盖来源、时效与一致性，不宣称自动证明医学结论。",
            "离线公共信息卡由人工整理，与实时检索证据分开显示；不能替代本地临床规范。",
            "时序模型未通过任务匹配验证时，不展示0.0为低风险。",
        ],
        "runtime_seconds": round(_number(raw.get("latency_seconds")), 2),
        "raw_clinical_use_allowed": bool(
            (raw.get("clinical_readiness") or {}).get("clinical_use_allowed", False)
        ),
    }


def build_audit_report(
    raw: Mapping[str, Any],
    view: Mapping[str, Any],
    review: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Any]:
    """Create a downloadable record that preserves claims and human ownership."""
    review_payload = dict(review or {})
    return {
        "schema_version": "careguard.competition-demo.v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "intended_use": "competition_demo_and_research_only",
        "request_id": view.get("request_id"),
        "input_summary": {
            "query_sha256": hashlib.sha256(str(raw.get("query") or "").encode("utf-8")).hexdigest(),
            "query_length": len(str(raw.get("query") or "")),
            "modalities": raw.get("model_input_modalities") or {},
            "note": "不导出输入原文；哈希仅用于比对同一份演示记录。",
        },
        "screening_summary": {
            "priority": view.get("priority"),
            "candidate_risk_domain": view.get("candidate_risk_domain"),
            "observed_clue": view.get("observed_clue"),
            "legacy_model_suppressed": view.get("legacy_model_suppressed"),
            "legacy_model_suppression_reason": view.get("legacy_model_suppression_reason"),
            "diagnostic_label_suppressed": view.get("diagnostic_label_suppressed"),
            "engine_label": view.get("engine_label"),
            "engine_status": view.get("engine_status"),
            "model_self_score": view.get("model_self_score"),
            "requires_human_review": view.get("requires_human_review"),
            "review_reason": view.get("review_reason"),
            "temporal_assessment": view.get("temporal_assessment"),
        },
        "evidence": view.get("evidence") or [],
        "offline_reference_cards": view.get("reference_cards") or [],
        "human_review": {
            "status": review_payload.get("status", "pending"),
            "reviewer": review_payload.get("reviewer", ""),
            "decision": review_payload.get("decision", ""),
            "notes": review_payload.get("notes", ""),
            "reviewed_at": review_payload.get("reviewed_at", ""),
        },
        "claim_boundary": view.get("limitations") or [],
        "reproducibility": {
            "runtime_seconds": view.get("runtime_seconds"),
            "clinical_use_allowed": view.get("raw_clinical_use_allowed", False),
        },
    }
