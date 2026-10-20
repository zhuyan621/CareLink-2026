"""Page 7: Clinical Safety Monitoring — 3D risk trajectories, high-risk patients, alerts."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, List

import numpy as np
import plotly.graph_objects as go
import streamlit as st

from dashboard.components import (
    neon_metric_card, section_header, info_bar, trajectory_3d_chart,
    data_table_with_style, pulse_status_badge,
)
from dashboard.i18n import get_translator
from dashboard.theme import configure_plotly_dark, COLORS


def render(eco: Any, config: Any, dataset: Any, monitor: Any) -> None:
    t = get_translator()

    if eco is None or not hasattr(eco, 'task_history') or not eco.task_history:
        info_bar(t("safety.no_data"), "warning")
        if eco is not None and st.button("🩺 运行样本科研分析", key="cs_run_sample",
                                         type="primary", use_container_width=True):
            with st.spinner("正在运行样本科研分析..."):
                samples = [
                    "chest pain with shortness of breath and dizziness",
                    "persistent headache with blurred vision and nausea",
                    "abdominal pain with fever and loss of appetite",
                ]
                for q in samples:
                    try:
                        eco.run_collaborative_task(q)
                    except Exception:
                        pass
            st.rerun()
        return

    # ── Collect high-risk tasks ──
    all_tasks = eco.task_history
    temporal_available = [
        tk for tk in all_tasks
        if isinstance(tk, dict) and (tk.get("tfa") or {}).get("available", False)
    ]
    high_risk_tasks = [
        tk for tk in all_tasks
        if isinstance(tk, dict)
        and (tk.get("tfa") or {}).get("available", False)
        and (tk.get("tfa") or {}).get("risk_level") in ("high", "critical")
    ]
    screening_flags = [
        tk for tk in all_tasks if isinstance(tk, dict) and tk.get("high_risk", False)
    ]
    hitl_triggered = [
        tk for tk in all_tasks
        if isinstance(tk, dict) and tk.get("hitl", {}).get("triggered", False)
    ]
    if len(temporal_available) < len(all_tasks):
        info_bar(
            f"{len(all_tasks) - len(temporal_available)} 条记录未生成时序风险概率；"
            "未验证检查点时不绘制0风险轨迹。关键词筛查标记不等于临床风险分层。",
            "warning",
        )

    # ═══════════════════════════════════════════════════════════════════
    # Row 1: 3D Risk Trajectory
    # ═══════════════════════════════════════════════════════════════════
    section_header(t("safety.trajectory_3d"), "🌌", "red")
    if high_risk_tasks:
        _render_trajectory_3d(high_risk_tasks, t)
    else:
        info_bar(t("safety.no_high_risk"), "success")

    # ═══════════════════════════════════════════════════════════════════
    # Row 2: Emergency stats
    # ═══════════════════════════════════════════════════════════════════
    section_header(t("safety.emergency_stats"), "🚨", "red")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        neon_metric_card(t("safety.high_risk_count"), str(len(high_risk_tasks)),
                         icon="🔴", neon_color="red", key="cs_hrc")
    with c2:
        neon_metric_card(t("safety.hitl_triggered"), str(len(hitl_triggered)),
                         icon="⚠️", neon_color="amber", key="cs_hitl")
    with c3:
        neon_metric_card("关键词筛查标记", str(len(screening_flags)),
                         icon="🆕", neon_color="magenta", key="cs_today")
    with c4:
        unresolved = len([tk for tk in high_risk_tasks
                          if not tk.get("hitl", {}).get("triggered", False)])
        neon_metric_card(t("safety.unresolved"), str(unresolved),
                         icon="❓", neon_color="red" if unresolved > 0 else "green", key="cs_unresolved")

    # ═══════════════════════════════════════════════════════════════════
    # Row 3: Risk distribution pie + filters
    # ═══════════════════════════════════════════════════════════════════
    col_pie, col_filter = st.columns([2, 1])

    with col_pie:
        risk_dist = _count_risk_levels(all_tasks)
        if risk_dist:
            fig = go.Figure(data=[go.Pie(
                labels=list(risk_dist.keys()),
                values=list(risk_dist.values()),
                hole=0.4,
                marker=dict(colors=["#ff3344", "#ffaa00", "#00f5ff", "#00ff88"]),
                textinfo="label+percent",
                textfont=dict(size=10, color="#e0e0ff"),
            )])
            configure_plotly_dark(fig)
            fig.update_layout(height=250, showlegend=True,
                              title=t("safety.risk_distribution"))
            st.plotly_chart(fig, use_container_width=True, key="cs_risk_pie")

    with col_filter:
        risk_filter = st.multiselect(
            t("safety.filter_risk"),
            [t("safety.risk_critical"), t("safety.risk_high"),
             t("safety.risk_medium"), t("safety.risk_low")],
            key="cs_frisk",
        )
        time_filter = st.selectbox(
            t("safety.filter_time"),
            [t("safety.time_all"), t("safety.time_24h"), t("safety.time_7d"), t("safety.time_30d")],
            key="cs_ftime",
        )
        area_filter = st.multiselect(
            t("safety.filter_area"),
            sorted(set(
                tk.get("dma", {}).get("prediction", "?")
                for tk in all_tasks if isinstance(tk, dict)
            )),
            key="cs_farea",
        )

    # ═══════════════════════════════════════════════════════════════════
    # Row 4: High-risk patient list
    # ═══════════════════════════════════════════════════════════════════
    section_header(t("safety.high_risk_list"), "🔴", "red")

    if not high_risk_tasks:
        info_bar(t("safety.no_high_risk"), "success")
    else:
        display_tasks = _filter_high_risk(high_risk_tasks, risk_filter, area_filter, time_filter, t)
        if not display_tasks:
            info_bar("No matching patients", "info")
        else:
            # Pin highest-risk patient at top
            highest_risk = max(display_tasks, key=lambda tk: (
                tk.get("tfa", {}).get("short_term", {}).get("risk_probability", 0) +
                tk.get("tfa", {}).get("mid_term", {}).get("risk_probability", 0) +
                tk.get("tfa", {}).get("long_term", {}).get("risk_probability", 0)
            ))
            highest_id = id(highest_risk)

            for tk in display_tasks[:30]:
                is_pinned = (id(tk) == highest_id)
                dma = tk.get("dma", {})
                tfa = tk.get("tfa", {})
                hitl = tk.get("hitl", {})
                risk_level = tfa.get("risk_level", "—")
                risk_color = {
                    "critical": "#ff3344", "high": "#ffaa00",
                    "medium": "#00f5ff", "low": "#00ff88",
                }.get(str(risk_level).lower(), "#4a5578")

                pin_marker = " 📌" if is_pinned else ""
                pin_style = "border: 2px solid #ff3344; box-shadow: 0 0 12px rgba(255,51,68,0.4);" if is_pinned else ""

                with st.expander(
                    f"🔴{pin_marker} {str(tk.get('query',''))[:70]} | "
                    f"Pred: {dma.get('prediction','?')} | "
                    f"Risk: {risk_level} | "
                    f"Conf: {dma.get('confidence',0):.2f}",
                    expanded=is_pinned,
                ):
                    c1, c2, c3, c4 = st.columns(4)
                    with c1:
                        st.metric(t("safety.short_risk"),
                                  f"{tfa.get('short_term',{}).get('risk_probability',0):.3f}")
                    with c2:
                        st.metric(t("safety.mid_risk"),
                                  f"{tfa.get('mid_term',{}).get('risk_probability',0):.3f}")
                    with c3:
                        st.metric(t("safety.long_risk"),
                                  f"{tfa.get('long_term',{}).get('risk_probability',0):.3f}")
                    with c4:
                        st.metric(t("safety.hitl_status"),
                                  "⚠️ Triggered" if hitl.get("triggered") else "✅ OK")

                    st.markdown(f"**{t('safety.risk_factors')}:** "
                                f"{', '.join(tfa.get('primary_risk_factors', ['N/A']))}")
                    st.markdown(f"**{t('safety.recommendations')}:** "
                                f"{tfa.get('recommendations', ['N/A'])}")

                    # Mini trajectory inline
                    short_v = tfa.get('short_term', {}).get('risk_probability', 0)
                    mid_v = tfa.get('mid_term', {}).get('risk_probability', 0)
                    long_v = tfa.get('long_term', {}).get('risk_probability', 0)
                    fig_mini = go.Figure(data=[go.Scatter3d(
                        x=[0, short_v], y=[0, mid_v], z=[0, long_v],
                        mode='lines+markers',
                        line=dict(width=3, color=risk_color),
                        marker=dict(size=4, color=risk_color),
                    )])
                    configure_plotly_dark(fig_mini)
                    fig_mini.update_layout(
                        height=200, margin=dict(l=0, r=0, t=0, b=0),
                        scene=dict(
                            xaxis_title="Short", yaxis_title="Mid", zaxis_title="Long",
                            bgcolor="rgba(6,6,15,0.95)",
                        ),
                    )
                    st.plotly_chart(fig_mini, use_container_width=True, key=f"cs_mini_{id(tk)}")

    # ═══════════════════════════════════════════════════════════════════
    # Row 5: Safety incident timeline
    # ═══════════════════════════════════════════════════════════════════
    section_header(t("safety.safety_timeline"), "📅", "amber")
    if hitl_triggered:
        for incident in hitl_triggered[-15:]:
            hitl_data = incident.get("hitl", {})
            st.markdown(f"""
            <div style="padding:0.4rem 0.8rem;margin:0.2rem 0;
                        border-left:3px solid #ffaa00;
                        background:rgba(255,170,0,0.05);border-radius:4px;">
                <span style="color:#7a8ba8;font-size:0.7rem;">{_fmt(incident.get('request_id',''))}</span>
                <span style="color:#e0e0ff;font-size:0.8rem;">{str(incident.get('query',''))[:80]}</span>
                <span style="color:#ffaa00;font-size:0.7rem;"> — {hitl_data.get('reason','N/A')}</span>
            </div>
            """, unsafe_allow_html=True)
    else:
        info_bar("No safety incidents recorded", "success")

    # ═══════════════════════════════════════════════════════════════════
    # Row 6: Emergency alert toggle
    # ═══════════════════════════════════════════════════════════════════
    st.divider()
    emergency = st.toggle(
        f"🚨 {t('safety.emergency_alert')}",
        value=st.session_state.get("emergency_alert", False),
        key="cs_emergency",
    )
    st.session_state.emergency_alert = emergency
    if emergency:
        info_bar(t("safety.emergency_active"), "error")


# ═══════════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════════

def _render_trajectory_3d(high_risk_tasks: list, t) -> None:
    """Build 3D multi-trajectory chart for high-risk patients with time-gradient coloring."""
    trajectories: List[dict] = []

    # Sort by timestamp if available, so oldest = cyan, newest = red
    def _extract_ts(tk: dict) -> float:
        ts_str = str(tk.get("timestamp", tk.get("request_id", "")))
        try:
            return datetime.fromisoformat(ts_str.replace("Z", "+00:00").split("+")[0]).timestamp()
        except (ValueError, TypeError):
            return 0.0

    sorted_tasks = sorted(high_risk_tasks[:30], key=_extract_ts)
    n = len(sorted_tasks)

    for i, tk in enumerate(sorted_tasks):
        tfa = tk.get("tfa", {})
        short = tfa.get("short_term", {}).get("risk_probability", 0)
        mid = tfa.get("mid_term", {}).get("risk_probability", 0)
        long_v = tfa.get("long_term", {}).get("risk_probability", 0)
        dma = tk.get("dma", {})

        # Color gradient: early=cyan, late=red (HSL interpolation)
        hue = 180 - (180 * i / max(n - 1, 1))  # cyan(180°) → red(0°)
        color = f"hsl({hue:.0f},80%,55%)"

        trajectories.append({
            "x": [0, short],
            "y": [0, mid],
            "z": [0, long_v],
            "name": str(tk.get("query", "?"))[:30],
            "color": color,
            "width": 1.5 + dma.get("confidence", 0.5) * 3,
            "hover": (
                f"Query: {str(tk.get('query',''))[:60]}<br>"
                f"Prediction: {dma.get('prediction','?')}<br>"
                f"Short: {short:.3f} | Mid: {mid:.3f} | Long: {long_v:.3f}<br>"
                f"Confidence: {dma.get('confidence',0):.3f}"
            ),
        })

    if trajectories:
        trajectory_3d_chart(
            trajectories,
            title="High-Risk Patient Risk Trajectories (3D)",
            danger_radius=0.7,
            key="cs_traj_3d",
        )


def _count_risk_levels(tasks: list) -> dict:
    """Count risk levels across all tasks."""
    counts = {}
    for tk in tasks:
        if not isinstance(tk, dict):
            continue
        level = str(tk.get("tfa", {}).get("risk_level", "unknown")).lower()
        counts[level] = counts.get(level, 0) + 1
    return counts


def _filter_high_risk(tasks: list, risk_filter: list, area_filter: list,
                       time_filter: str, t) -> list:
    """Apply filters to high-risk task list including time-based filtering."""
    result = list(tasks)

    if risk_filter:
        risk_map = {
            t("safety.risk_critical"): "critical",
            t("safety.risk_high"): "high",
            t("safety.risk_medium"): "medium",
            t("safety.risk_low"): "low",
        }
        allowed = {risk_map.get(r, r.lower()) for r in risk_filter}
        result = [tk for tk in result
                  if str(tk.get("tfa", {}).get("risk_level", "")).lower() in allowed]

    if area_filter:
        result = [tk for tk in result
                  if tk.get("dma", {}).get("prediction", "") in area_filter]

    # Apply time filter
    time_all = t("safety.time_all")
    time_24h = t("safety.time_24h")
    time_7d = t("safety.time_7d")
    time_30d = t("safety.time_30d")

    if time_filter and time_filter != time_all:
        now = datetime.now()
        if time_filter == time_24h:
            cutoff = now - timedelta(hours=24)
        elif time_filter == time_7d:
            cutoff = now - timedelta(days=7)
        elif time_filter == time_30d:
            cutoff = now - timedelta(days=30)
        else:
            cutoff = None

        if cutoff is not None:
            filtered_result = []
            for tk in result:
                ts = _extract_timestamp(tk)
                if ts and ts >= cutoff:
                    filtered_result.append(tk)
            result = filtered_result

    return result


def _extract_timestamp(tk: dict):
    """Extract datetime from a task dict, trying multiple fields."""
    ts_str = str(tk.get("timestamp", tk.get("request_id", "")))
    if not ts_str:
        return None
    try:
        return datetime.fromisoformat(ts_str.replace("Z", "+00:00").split("+")[0])
    except (ValueError, TypeError):
        pass
    # Try request_id as date format YYYYMMDD
    rid = str(tk.get("request_id", ""))
    if len(rid) >= 8 and rid[:8].isdigit():
        try:
            return datetime.strptime(rid[:8], "%Y%m%d")
        except ValueError:
            pass
    return None


def _is_today(tk: dict) -> bool:
    """Check if a task's timestamp falls on today's date."""
    ts = _extract_timestamp(tk)
    if ts is None:
        return False
    return ts.date() == datetime.now().date()


def _fmt(val: Any) -> str:
    if val is None:
        return "—"
    if isinstance(val, datetime):
        return val.strftime("%Y-%m-%d %H:%M")
    return str(val)[:19]
