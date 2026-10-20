"""Page: 诊断演示 (Diagnosis Demo) — 面向 iCAN 现场答辩的核心演示页.

将一次完整的多智能体会诊流水线可视化为三个区块：
  区块A 输入区   —— 主诉 + 症状多选 + [开始诊断]
  区块B 会诊区   —— 各智能体按流水线「发言」，含共识投票与人工介入事件
  区块C 结果区   —— 主诊断 + 置信度 + 风险分级 + 鉴别诊断分布 + 建议

入口: eco.run_collaborative_task(patient_query) 返回的 final_result dict。
布局参考 ai-doctor(多医生会诊) + AI-disease-predictor(症状诊断结果页)，
视觉完全复用 dashboard.theme 的暗色霓虹主题。
"""

from __future__ import annotations

import html
import time
from typing import Any, Dict, List, Optional, Tuple

import plotly.graph_objects as go
import streamlit as st

from dashboard.components import neon_metric_card, section_header, info_bar
from dashboard.theme import COLORS, configure_plotly_dark

# ═══════════════════════════════════════════════════════════════════════════
# 智能体配色盘（流水线顺序，抄 ai-doctor 的 doctorPalette 思想）
# ═══════════════════════════════════════════════════════════════════════════

AGENT_PALETTE: Dict[str, str] = {
    "Perception": "#00f5ff",    # 感知（青）
    "RAA": "#ff00e5",           # 检索增强分析（洋红）
    "Fusion": "#7c3aed",        # 知识融合（紫）
    "Verification": "#ffaa00",  # 验证（黄）
    "DMA": "#00ff88",           # 诊断决策（绿）
    "TFA": "#ff3344",           # 时序预测（红）
    "Consensus": "#ff8c00",     # 共识（橙）
    "HITL": "#3b82f6",          # 人工介入（蓝）
}

AGENT_CN: Dict[str, str] = {
    "Perception": "感知智能体",
    "RAA": "检索增强智能体",
    "Fusion": "知识融合智能体",
    "Verification": "验证智能体",
    "DMA": "诊断决策智能体",
    "TFA": "时序预测智能体",
    "Consensus": "共识模块",
    "HITL": "人工介入(HITL)",
}

PIPELINE: List[str] = [
    "Perception", "RAA", "Fusion", "Verification", "DMA", "TFA", "Consensus",
]

# 风险分级 → (info_box 等级, 中文标签, 警示色)
RISK_META: Dict[str, Tuple[str, str, str]] = {
    "low": ("success", "低风险", COLORS["success"]),
    "medium": ("info", "中风险", COLORS["warning"]),
    "high": ("warning", "高风险", "#ff8c00"),
    "critical": ("error", "极高风险", COLORS["danger"]),
    "unknown": ("warning", "不可用（未估计）", COLORS["warning"]),
}

# 共识层级 → 中文
TIER_CN: Dict[str, str] = {
    "force_hitl": "强制人工介入",
    "dma_veto": "DMA 一票否决",
    "auto_pass": "自动通过",
    "auto_pass_risk_noted": "通过（风险提示）",
    "escalation_risk_uncertainty": "升级人工干预（诊断不确定+存在风险）",
    "clinical_validation_gate": "临床验证门控（科研演示）",
}

# 常见症状快捷多选（兜底用，dataset 无症状列时）
COMMON_SYMPTOMS: List[str] = [
    "发热", "咳嗽", "头痛", "乏力", "胸痛", "腹痛", "恶心呕吐", "眩晕",
    "呼吸困难", "心悸", "关节疼痛", "皮疹", "食欲下降", "失眠", "体重下降",
]

# 本页 session_state 键前缀，避免与其它页冲突
_P = "dx_"


# ═══════════════════════════════════════════════════════════════════════════
# 小工具
# ═══════════════════════════════════════════════════════════════════════════

def _hex_rgba(hex_color: str, alpha: float = 0.14) -> str:
    """hex → rgba，用于气泡底色/边框的半透明处理。"""
    h = hex_color.lstrip("#")
    if len(h) != 6:
        return f"rgba(0,245,255,{alpha})"
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r},{g},{b},{alpha})"


def _fmt_pct(x: Any) -> str:
    try:
        return f"{float(x) * 100:.0f}%"
    except (TypeError, ValueError):
        return "—"


def _ensure_state() -> None:
    """初始化本页 session_state。"""
    defaults = {
        _P + "phase": "input",        # input | running | finished
        _P + "query": "",             # 主诉文本
        _P + "symptoms": [],          # 选中症状
        _P + "result": None,          # run_collaborative_task 返回值
        _P + "transcript": [],        # 会诊消息流
        _P + "error": "",
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


# ═══════════════════════════════════════════════════════════════════════════
# 区块A：输入区
# ═══════════════════════════════════════════════════════════════════════════

def _render_input(disabled: bool) -> None:
    """渲染症状输入区。disabled=True 时（已出结果）控件只读。"""
    section_header("演示案例输入", icon="🩺", color="cyan")
    st.markdown('<div class="glass-panel">', unsafe_allow_html=True)

    st.session_state[_P + "query"] = st.text_area(
        "主诉描述",
        value=st.session_state[_P + "query"],
        height=120,
        placeholder="请描述主要症状与不适，例如：持续三天高热 39℃，伴干咳、乏力、胸闷…",
        disabled=disabled,
        key=_P + "ta_query",
        label_visibility="collapsed",
    )

    st.session_state[_P + "symptoms"] = st.multiselect(
        "快速勾选常见症状（可选，会自动拼入主诉）",
        COMMON_SYMPTOMS,
        default=st.session_state[_P + "symptoms"],
        disabled=disabled,
        key=_P + "ms_symptoms",
    )

    if not disabled:
        c1, c2 = st.columns([3, 1])
        with c1:
            st.caption("生成推理由本地 Ollama 完成；仅限科研与竞赛演示，不能替代医生。刷新 PubMed 证据时会联网。")
        with c2:
            start = st.button(
                "🚀 开始科研分析", type="primary", use_container_width=True,
                key=_P + "btn_start",
            )
        st.markdown("</div>", unsafe_allow_html=True)
        if start:
            _on_start()
    else:
        st.markdown("</div>", unsafe_allow_html=True)


def _on_start() -> None:
    """开始诊断：校验输入 → 进入 running 阶段。"""
    query = (st.session_state[_P + "query"] or "").strip()
    symptoms = st.session_state[_P + "symptoms"] or []
    if not query and not symptoms:
        st.session_state[_P + "error"] = "请至少填写一句主诉，或勾选一个症状。"
        return
    if symptoms:
        query = (query + "。症状：" + "、".join(symptoms)).strip("。 ")
    st.session_state[_P + "query"] = query
    st.session_state[_P + "error"] = ""
    st.session_state[_P + "result"] = None
    st.session_state[_P + "transcript"] = []
    st.session_state[_P + "phase"] = "running"
    st.rerun()


# ═══════════════════════════════════════════════════════════════════════════
# 会诊消息流构造（从真实结果反推「发言」记录）
# ═══════════════════════════════════════════════════════════════════════════

def _build_transcript(r: Dict[str, Any]) -> List[Dict[str, Any]]:
    """把 final_result 各阶段数据转成会诊消息流，逐条映射一个智能体。"""
    t: List[Dict[str, Any]] = []
    t.append({"type": "system", "text": "会诊启动 —— 患者主诉已提交，多智能体流水线开始执行"})

    percep = r.get("perception") or {}
    t.append({
        "type": "agent", "agent": "Perception",
        "text": "已完成症状语义编码，生成上下文向量，向量范数 "
                f"{float(percep.get('context_norm', 0)):.2f}。",
    })

    retr = r.get("retrieval") or {}
    strat = retr.get("equilibrium_strategy", "—")
    rounds = retr.get("nash_rounds", 0)
    docs = retr.get("top_docs") or []
    t.append({
        "type": "agent", "agent": "RAA",
        "text": f"博弈论策略选型收敛于「{strat}」({rounds} 轮)，"
                f"检索命中 {len(docs)} 篇高相关证据，平均相关性 "
                f"{float(retr.get('avg_verified_relevance', 0)):.2f}。",
    })

    fusion = r.get("fusion") or {}
    t.append({
        "type": "agent", "agent": "Fusion",
        "text": "三源知识融合完成：输入 "
                f"{int(fusion.get('input_docs', 0))} 篇，去重后保留 "
                f"{int(fusion.get('deduplicated_docs', 0))} 篇，"
                f"检出冲突 {int(fusion.get('conflict_count', 0))} 处。",
    })

    veri = r.get("verification") or {}
    acc = int(veri.get("accepted_docs", veri.get("accepted", 0)))
    rej = int(veri.get("rejected_docs", veri.get("rejected", 0)))
    t.append({
        "type": "agent", "agent": "Verification",
        "text": f"证据核验：采纳 {acc} 篇、拒绝 {rej} 篇，"
                f"核验状态 {veri.get('verification_status', 'not_available')}；"
                "该步骤核验来源可追溯性，不等同于证明医学结论为真。",
    })

    dma = r.get("dma") or {}
    pred = dma.get("prediction", "未知")
    conf = dma.get("confidence", 0.0)
    sev = dma.get("disease_severity", "unknown")
    t.append({
        "type": "agent", "agent": "DMA",
        "text": f"候选分类：预测「{pred}」，模型自评分 {_fmt_pct(conf)}，"
                f"后端 {dma.get('dma_backend', 'unknown')}，"
                f"回退={'是' if dma.get('fallback_used') else '否'}。",
    })

    tfa = r.get("tfa") or {}
    if tfa and tfa.get("available", False):
        lvl = tfa.get("risk_level", "low")
        label = tfa.get("risk_label", RISK_META.get(lvl, ("", lvl, ""))[1])
        short = (tfa.get("short_term") or {}).get("risk_probability", 0.0)
        t.append({
            "type": "agent", "agent": "TFA",
            "text": f"多尺度时序预测：风险等级 {label}，短期恶化概率 {_fmt_pct(short)}。",
        })
    else:
        reason = (tfa or {}).get("blocked_reason", "时序模块未启用")
        t.append({
            "type": "agent", "agent": "TFA",
            "text": f"时序风险概率未生成：{reason} 结果中的0.0是占位值，不表示低风险。",
        })

    cons = r.get("consensus") or {}
    if cons:
        votes = cons.get("votes") or {}
        weights = cons.get("vote_weights") or {}
        vtxt = "  ".join(
            f"{k}{'✓' if v else '✗'}(权{weights.get(k, 1)})" for k, v in votes.items()
        )
        t.append({
            "type": "vote",
            "text": f"共识投票：{vtxt}，通过阈值 {cons.get('required_approvals', '—')}"
                    f"/{cons.get('total_weight', '—')}",
        })
        tier = cons.get("tier", "")
        t.append({
            "type": "system" if cons.get("approved") else "vote",
            "text": f"共识结论：{TIER_CN.get(tier, tier)} — {cons.get('reason', '')}",
        })

    hitl = r.get("hitl") or {}
    if hitl.get("triggered"):
        t.append({
            "type": "hilt",
            "text": "人工介入已触发：" + str(hitl.get("reason", "低置信度/高风险")).strip(),
        })

    t.append({
        "type": "system",
        "text": f"分析结束 —— 总耗时 {float(r.get('latency_seconds', 0)):.1f} 秒，生成可追溯科研记录",
    })
    return t


# ═══════════════════════════════════════════════════════════════════════════
# 区块B：会诊过程区
# ═══════════════════════════════════════════════════════════════════════════

def _render_consultation(r: Dict[str, Any]) -> None:
    """渲染多智能体会诊消息流 + 侧栏状态面板。"""
    transcript = st.session_state[_P + "transcript"]
    if not transcript:
        transcript = _build_transcript(r)
        st.session_state[_P + "transcript"] = transcript

    section_header("会诊过程", icon="🤖", color="magenta")

    left, right = st.columns([3, 1])

    with right:
        # ── 阶段 / 关键指标 ──
        cons = r.get("consensus") or {}
        dma = r.get("dma") or {}
        neon_metric_card(
            "共识层级",
            TIER_CN.get(cons.get("tier", ""), cons.get("tier", "—")),
            icon="⚖️",
            neon_color="cyan",
            key=_P + "m_tier",
        )
        neon_metric_card(
            "诊断置信度",
            _fmt_pct(dma.get("confidence", 0.0)),
            icon="🎯",
            neon_color="green",
            key=_P + "m_conf",
        )
        hitl = r.get("hitl") or {}
        neon_metric_card(
            "人工介入",
            "已触发" if hitl.get("triggered") else "未触发",
            icon="✋",
            neon_color="red" if hitl.get("triggered") else "green",
            key=_P + "m_hitl",
        )
        # ── 智能体列表（在席状态） ──
        st.markdown(
            '<div style="font-weight:600;margin:0.6rem 0 0.3rem;color:#e0e0ff;">智能体状态</div>',
            unsafe_allow_html=True,
        )
        for ag in PIPELINE:
            color = AGENT_PALETTE[ag]
            st.markdown(
                f'<div style="display:flex;align-items:center;gap:8px;padding:4px 0;">'
                f'<span class="pulse-dot dot-green"></span>'
                f'<span style="color:{color};font-size:0.82rem;font-weight:600;">{AGENT_CN[ag]}</span>'
                f'<span style="margin-left:auto;color:#4a5578;font-size:0.7rem;">已完成</span>'
                f"</div>",
                unsafe_allow_html=True,
            )

    with left:
        _render_transcript(transcript)


def _render_transcript(transcript: List[Dict[str, Any]]) -> None:
    """渲染消息流气泡，逐条 CSS 淡入（cascade 效果）。"""
    # 注入一次本页用的淡入动画 keyframe
    st.markdown("""
    <style>
    @keyframes dxFadeIn { from { opacity: 0; transform: translateY(8px); } to { opacity: 1; transform: none; } }
    .dx-msg { animation: dxFadeIn 0.35s ease both; }
    </style>
    """, unsafe_allow_html=True)

    for i, m in enumerate(transcript):
        delay = f"animation-delay:{i * 0.12}s;"
        mtype = m.get("type")
        if mtype == "system":
            st.markdown(
                f'<div class="dx-msg" style="{delay}text-align:center;color:#4a5578;'
                f'font-size:0.78rem;margin:0.8rem 0;">— {html.escape(str(m["text"]))} —</div>',
                unsafe_allow_html=True,
            )
        elif mtype == "agent":
            _agent_bubble(m["agent"], m["text"], delay)
        elif mtype == "vote":
            st.markdown(
                f'<div class="dx-msg" style="{delay}display:flex;justify-content:center;margin:0.5rem 0;">'
                f'<span style="background:rgba(255,140,0,0.14);color:#ff8c00;border:1px solid '
                f'rgba(255,140,0,0.4);border-radius:8px;padding:0.3rem 0.8rem;font-size:0.78rem;">'
                f"🗳️ {html.escape(str(m['text']))}</span></div>",
                unsafe_allow_html=True,
            )
        elif mtype == "hilt":
            st.markdown(
                f'<div class="dx-msg" style="{delay}">'
                f'<div class="info-box warning">✋ 人工介入 · {html.escape(str(m["text"]))}</div></div>',
                unsafe_allow_html=True,
            )


def _agent_bubble(agent: str, text: str, delay: str) -> None:
    """单个智能体发言气泡（左对齐，专属配色）。"""
    color = AGENT_PALETTE.get(agent, COLORS["cyan"])
    name = html.escape(AGENT_CN.get(agent, agent))
    safe_text = html.escape(str(text))
    initials = "".join(p[0] for p in agent.split()) if agent else "AI"
    st.markdown(
        f'<div class="dx-msg" style="{delay}display:flex;gap:10px;margin:0.6rem 0;align-items:flex-start;">'
        f'<div style="background:{color};color:#06060f;width:34px;height:34px;border-radius:50%;'
        f'display:flex;align-items:center;justify-content:center;font-weight:800;font-size:0.8rem;'
        f'flex-shrink:0;">{initials}</div>'
        f'<div style="background:{_hex_rgba(color, 0.12)};border:1px solid {_hex_rgba(color, 0.45)};'
        f'border-radius:12px;padding:0.5rem 0.9rem;max-width:82%;box-shadow:0 2px 10px rgba(0,0,0,0.35);">'
        f'<div style="color:{color};font-weight:700;font-size:0.78rem;margin-bottom:0.2rem;">{name}</div>'
        f'<div style="color:#e0e0ff;font-size:0.86rem;line-height:1.5;">{safe_text}</div>'
        f"</div></div>",
        unsafe_allow_html=True,
    )


# ═══════════════════════════════════════════════════════════════════════════
# 区块C：结果区
# ═══════════════════════════════════════════════════════════════════════════

def _render_result(r: Dict[str, Any]) -> None:
    """渲染带后端、回退与临床门控披露的科研结果。"""
    section_header("科研决策支持结果", icon="📋", color="green")

    readiness = r.get("clinical_readiness") or {}
    if not readiness.get("clinical_use_allowed", False):
        blockers = "；".join(readiness.get("blockers", [])) or "未通过临床验证门控"
        info_bar(f"仅限科研与竞赛演示：{blockers}", level="warning", icon="🛡️")

    comp = r.get("comprehensive_answer") or {}
    diag = comp.get("diagnosis") or {}
    risk = comp.get("risk_assessment") or {}
    dma = r.get("dma") or {}

    pred = diag.get("prediction", dma.get("prediction", "未知"))
    conf = diag.get("confidence", dma.get("confidence", 0.0))
    sev = diag.get("severity", dma.get("disease_severity", "unknown"))
    intent = diag.get("intent", dma.get("intent", "—"))

    lvl = risk.get("risk_level", "unknown")
    box_level, box_label, _ = RISK_META.get(lvl, ("info", lvl, COLORS["warning"]))
    risk_score = risk.get("risk_score", 0.0)
    factors = risk.get("primary_risk_factors", []) or []
    reasoning = risk.get("reasoning", "")
    recs = comp.get("recommendations", []) or []
    disclaimer = comp.get("disclaimer", "本系统输出为 AI 科研决策支持参考，不构成医疗建议，请及时就医。")
    safe_pred = html.escape(str(pred))
    safe_sev = html.escape(str(sev))
    safe_intent = html.escape(str(intent))

    left, right = st.columns([2, 1])

    with left:
        # ── 主诊断卡片 ──
        st.markdown(
            f'<div class="glass-panel" style="margin-bottom:0.8rem;">'
            f'<div style="font-size:0.72rem;color:#7a8ba8;text-transform:uppercase;'
            f'letter-spacing:0.05em;">候选标签 Candidate Label</div>'
            f'<div class="neon-text-cyan" style="font-size:1.9rem;font-weight:800;'
            f'margin:0.2rem 0;">{safe_pred}</div>'
            f'<div style="display:flex;align-items:center;gap:10px;margin:0.4rem 0;">'
            f'<div style="flex:1;background:rgba(0,245,255,0.08);border-radius:999px;height:8px;">'
            f'<div style="width:{min(float(conf), 1.0) * 100:.0f}%;background:linear-gradient(90deg,'
            f'{COLORS["cyan"]},{COLORS["success"]});height:8px;border-radius:999px;"></div></div>'
            f'<span style="color:{COLORS["cyan"]};font-weight:700;">{_fmt_pct(conf)}</span></div>'
            f'<div style="font-size:0.75rem;color:#7a8ba8;">模型自评分（未必经校准） · 严重程度 {safe_sev} · 意图 {safe_intent}</div>'
            f"</div>",
            unsafe_allow_html=True,
        )

        # ── 风险分级警示条 ──
        if lvl == "unknown" or not (r.get("tfa") or {}).get("available", False):
            info_bar("时序风险：不可用；未配置合格检查点，0.0不表示低风险。", level="warning", icon="⚠️")
        else:
            info_bar(f"风险分级：{box_label} · 风险评分 {float(risk_score):.2f}", level=box_level, icon="⚠️")

        # ── 推理说明 ──
        if reasoning:
            st.markdown(
                f'<div style="color:#e0e0ff;font-size:0.86rem;line-height:1.6;'
                f'padding:0.6rem 0;">{html.escape(str(reasoning))}</div>',
                unsafe_allow_html=True,
            )

        # ── 关键风险因素 ──
        if factors:
            st.markdown(
                '<div style="font-weight:600;color:#e0e0ff;margin:0.4rem 0 0.3rem;">关键风险因素</div>',
                unsafe_allow_html=True,
            )
            chips = "".join(
                f'<span style="display:inline-block;background:rgba(0,255,136,0.12);'
                f'color:{COLORS["success"]};border:1px solid rgba(0,255,136,0.3);'
                f'border-radius:999px;padding:0.15rem 0.6rem;font-size:0.76rem;'
                f'margin:0 0.3rem 0.3rem 0;">{f}</span>'
                for f in map(lambda value: html.escape(str(value)), factors)
            )
            st.markdown(f'<div>{chips}</div>', unsafe_allow_html=True)

        # ── 建议 ──
        if recs:
            st.markdown(
                '<div style="font-weight:600;color:#e0e0ff;margin:0.6rem 0 0.3rem;">建议</div>',
                unsafe_allow_html=True,
            )
            for rec in recs:
                st.markdown(
                    f'<div style="color:#e0e0ff;font-size:0.85rem;padding:0.15rem 0;">• {html.escape(str(rec))}</div>',
                    unsafe_allow_html=True,
                )

    with right:
        # ── 鉴别诊断置信度分布（水平条形图） ──
        st.markdown(
            '<div style="font-weight:600;color:#e0e0ff;margin-bottom:0.3rem;">鉴别诊断分布</div>',
            unsafe_allow_html=True,
        )
        _differential_chart(r, dma, pred)

    # ── 免责声明 ──
    st.markdown(
        f'<div style="text-align:center;color:#4a5578;font-size:0.72rem;'
        f'padding:0.8rem 0 0.2rem;border-top:1px solid rgba(0,245,255,0.08);margin-top:1rem;">'
        f"⚠️ {html.escape(str(disclaimer))}</div>",
        unsafe_allow_html=True,
    )
    st.caption(
        f"request_id={r.get('request_id', '—')} · backend={dma.get('dma_backend', 'unknown')} · "
        f"fallback={bool(dma.get('fallback_used', False))} · trace={r.get('trace_path', '未保存')}"
    )


def _differential_chart(r: Dict[str, Any], dma: Dict[str, Any], pred: str) -> None:
    """主诊断 + 鉴别诊断 水平条形图。

    数据来源优先级：
    1. fusion.area_consensus —— 三源融合后的疾病领域共识（软相关度分布，真·多候选）
    2. dma.probabilities —— 兜底（可能是 one-hot，此时至少补足主诊断一根柱）
    3. {pred: confidence} —— 最终兜底
    """
    fusion = r.get("fusion") or {}
    area_consensus: Dict[str, float] = fusion.get("area_consensus") or {}
    conf = float(dma.get("confidence", 0.0) or 0.0)

    # (名称, 分值, 是否主诊断)
    items: List[Tuple[str, float, bool]] = []
    seen: set = set()

    # 主诊断固定置顶
    if pred:
        items.append((pred, max(conf, 0.01), True))
        seen.add(pred)

    # 鉴别候选：领域共识（去主诊断同名、去 Unknown）
    for name, score in sorted(area_consensus.items(), key=lambda kv: -kv[1]):
        if name in seen or name == "Unknown" or float(score) <= 0:
            continue
        items.append((name, float(score), False))
        seen.add(name)
        if len(items) >= 8:
            break

    # 领域共识为空时，回退到 dma.probabilities（one-hot 也能补出主诊断）
    if len(items) <= 1:
        probs: Dict[str, float] = dma.get("probabilities", {}) or {}
        for name, p in sorted(probs.items(), key=lambda kv: -kv[1]):
            if name in seen or float(p) <= 0:
                continue
            items.append((name, float(p), False))
            seen.add(name)
            if len(items) >= 8:
                break

    if len(items) <= 1:
        st.caption("暂无鉴别诊断分布数据")
        return

    names = [k for k, _, _ in items]
    vals = [v for _, v, _ in items]
    colors = [COLORS["cyan"] if is_p else "#3b82f6" for _, _, is_p in items]

    fig = go.Figure(go.Bar(
        x=vals, y=names, orientation="h",
        marker=dict(color=colors, line=dict(width=0)),
        text=[f"{v * 100:.0f}%" for v in vals],
        textposition="outside",
        textfont=dict(color="#7a8ba8", size=11),
    ))
    configure_plotly_dark(fig)
    fig.update_layout(
        height=max(220, len(names) * 34),
        margin=dict(l=10, r=30, t=10, b=10),
        xaxis=dict(range=[0, 1], tickformat=".0%", title=None),
        yaxis=dict(autorange="reversed", title=None),
        showlegend=False,
    )
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
    st.caption("青=主诊断(置信度) · 蓝=鉴别候选(知识库相关度)")


# ═══════════════════════════════════════════════════════════════════════════
# 主渲染
# ═══════════════════════════════════════════════════════════════════════════

def render(eco: Any, config: Any, dataset: Any, monitor: Any) -> None:
    """诊断演示页主入口。"""
    _ensure_state()
    phase = st.session_state[_P + "phase"]

    # ── 顶部标题 ──
    st.markdown(
        '<div class="gradient-header" style="text-align:center;margin-bottom:0.4rem;">'
        '<span class="neon-text-cyan" style="font-size:1.2rem;font-weight:800;">'
        "🩺 MAPFM 医学科研决策支持演示</span>"
        '<div style="font-size:0.72rem;color:#7a8ba8;margin-top:2px;">'
        "输入演示案例 → 多智能体分析 → 可追溯候选结果 · 挑战杯科B现场演示</div></div>",
        unsafe_allow_html=True,
    )

    # ── 错误提示 ──
    if st.session_state[_P + "error"]:
        info_bar(st.session_state[_P + "error"], level="warning", icon="⚠️")
        st.session_state[_P + "error"] = ""

    if phase == "running":
        _run_and_finish(eco)
        return

    # 输入区（已出结果则只读）
    _render_input(disabled=(phase == "finished"))

    # 会诊区 + 结果区
    if phase == "finished" and st.session_state[_P + "result"]:
        r = st.session_state[_P + "result"]
        st.divider()
        _render_consultation(r)
        st.divider()
        _render_result(r)

        # ── 重新诊断 ──
        if st.button("🔁 重新诊断", use_container_width=True, key=_P + "btn_reset"):
            st.session_state[_P + "phase"] = "input"
            st.session_state[_P + "result"] = None
            st.session_state[_P + "transcript"] = []
            st.session_state[_P + "query"] = ""
            st.session_state[_P + "symptoms"] = []
            st.rerun()


def _run_and_finish(eco: Any) -> None:
    """执行真实多智能体会诊，成功后切换到 finished。"""
    if eco is None:
        info_bar("多智能体生态未加载（Ollama 或模型初始化失败），无法运行科研分析。", level="error")
        st.session_state[_P + "phase"] = "input"
        return

    with st.spinner("多智能体会诊流水线运行中…（首次可能需加载本地模型，约 30–60 秒）"):
        try:
            result = eco.run_collaborative_task(patient_query=st.session_state[_P + "query"])
        except Exception as exc:  # 降级：任何异常都不崩页
            import traceback
            st.session_state[_P + "error"] = f"分析失败：{exc}"
            st.session_state[_P + "phase"] = "input"
            st.markdown(
                f'<div class="info-box error">分析运行出错：{html.escape(str(exc))}</div>',
                unsafe_allow_html=True,
            )
            with st.expander("Traceback"):
                st.code(traceback.format_exc())
            return

    st.session_state[_P + "result"] = result
    st.session_state[_P + "transcript"] = _build_transcript(result)
    st.session_state[_P + "phase"] = "finished"
    st.rerun()
