"""Page 2: Agent Monitor — 3D network topology, health gauge, agent cards, maintenance alerts."""

from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import streamlit as st

from dashboard.components import (
    neon_metric_card,
    gauge_chart,
    pulse_status_badge,
    section_header,
    info_bar,
    network_3d_chart,
    sparkline_chart,
)
from dashboard.i18n import get_translator
from dashboard.theme import COLORS


# ═══════════════════════════════════════════════════════════════════════════
# Agent registry — icons, names (i18n keys), layout order
# ═══════════════════════════════════════════════════════════════════════════

AGENT_SPECS: List[Dict[str, Any]] = [
    {"key": "Perception",   "icon": "\U0001F441️", "label_key": "agents.perception",   "neon": "cyan"},
    {"key": "RAA",          "icon": "\U0001F50D",        "label_key": "agents.raa",          "neon": "magenta"},
    {"key": "DMA",          "icon": "\U0001F9E0",        "label_key": "agents.dma",          "neon": "violet"},
    {"key": "TFA",          "icon": "⏳",            "label_key": "agents.tfa",          "neon": "amber"},
    {"key": "Fusion",       "icon": "\U0001F504",        "label_key": "agents.fusion",       "neon": "cyan"},
    {"key": "Verification", "icon": "✅",            "label_key": "agents.verification", "neon": "green"},
    {"key": "Privacy",      "icon": "\U0001F512",        "label_key": "agents.privacy",      "neon": "violet"},
    {"key": "Maintenance",  "icon": "\U0001F6E1️",  "label_key": "agents.maintenance",  "neon": "amber"},
    {"key": "Topology",     "icon": "\U0001F310",        "label_key": "agents.topology",     "neon": "cyan"},
    {"key": "Consensus",    "icon": "⚖️",      "label_key": "agents.consensus",    "neon": "green"},
]

STATUS_COLOR_MAP: Dict[str, str] = {
    "healthy":  COLORS["success"],
    "ok":       COLORS["success"],
    "normal":   COLORS["success"],
    "degraded": COLORS["warning"],
    "warning":  COLORS["warning"],
    "faulty":   COLORS["danger"],
    "error":    COLORS["danger"],
    "offline":  COLORS["danger"],
    "critical": COLORS["danger"],
}


# ═══════════════════════════════════════════════════════════════════════════
# Fibonacci sphere helpers
# ═══════════════════════════════════════════════════════════════════════════

def _fibonacci_sphere(n: int, radius: float = 1.0) -> List[Tuple[float, float, float]]:
    """Return n approximately-evenly-distributed points on a sphere of given radius."""
    points: List[Tuple[float, float, float]] = []
    phi = math.pi * (3.0 - math.sqrt(5.0))  # golden angle in radians

    for i in range(n):
        y = 1.0 - (i / float(n - 1)) * 2.0 if n > 1 else 0.0  # y goes from 1 to -1
        radius_at_y = math.sqrt(1.0 - y * y)
        theta = phi * i
        x = math.cos(theta) * radius_at_y
        z = math.sin(theta) * radius_at_y
        points.append((x * radius, y * radius, z * radius))

    return points


# ═══════════════════════════════════════════════════════════════════════════
# Safe data extractors
# ═══════════════════════════════════════════════════════════════════════════

def _safe_agent_data(
    agents_report: Optional[Dict[str, Any]],
    agent_key: str,
) -> Dict[str, Any]:
    """Safely extract agent stats dict, returning empty dict on missing data."""
    if agents_report is None:
        return {}
    return agents_report.get(agent_key, {}) or {}


def _resolve_status(stats: Dict[str, Any]) -> str:
    """Return canonical status string from agent stats."""
    raw = str(stats.get("status", "")).lower()
    if not raw:
        # Infer from failures vs calls
        total = stats.get("total_calls", 0)
        fails = stats.get("failures", 0)
        if total == 0:
            return "unknown"
        return "degraded" if fails > 0 else "healthy"
    return raw


def _resolve_metric_color(status: str) -> str:
    """Return neon color key for an agent status."""
    s = status.lower()
    if s in ("healthy", "ok", "normal"):
        return "green"
    elif s in ("degraded", "warning"):
        return "amber"
    else:
        return "red"


def _resolve_node_color(status: str) -> str:
    """Return hex color for 3D node based on status."""
    return STATUS_COLOR_MAP.get(status.lower(), COLORS["cyan"])  # healthy=#00ff88, degraded=#ffaa00, offline=#ff3344


# ═══════════════════════════════════════════════════════════════════════════
# 3D topology builder
# ═══════════════════════════════════════════════════════════════════════════

def _build_topology_3d(
    agents_report: Dict[str, Any],
    t: Any,
) -> Optional[Dict[str, Any]]:
    """Build node/edge data for network_3d_chart.

    Returns None when agents_report is empty (graceful fallback).
    """
    if not agents_report or "DMA" not in agents_report:
        return None

    # ── Order agents: DMA at index 0 (center), rest on Fibonacci sphere ──
    ordered: List[str] = ["DMA"]
    for spec in AGENT_SPECS:
        if spec["key"] != "DMA":
            ordered.append(spec["key"])

    # ── Sphere radius ──
    radius = 2.5

    # ── Build node list ──
    nodes: List[Dict[str, Any]] = []
    sphere_points = _fibonacci_sphere(len(ordered) - 1, radius=radius)  # 9 points

    for i, agent_key in enumerate(ordered):
        stats = _safe_agent_data(agents_report, agent_key)
        status = _resolve_status(stats)
        total_calls = stats.get("total_calls", 0)
        size = max(8, min(30, 10 + total_calls * 0.5))  # scale node size

        if i == 0:  # DMA at center
            x, y, z = 0.0, 0.0, 0.0
        else:
            x, y, z = sphere_points[i - 1]

        # Look up the agent icon from AGENT_SPECS
        icon = ""
        agent_label = agent_key
        for spec_inner in AGENT_SPECS:
            if spec_inner["key"] == agent_key:
                icon = spec_inner["icon"]
                agent_label = t(spec_inner["label_key"])
                break

        # Build hover text
        hover_lines = [
            f"<b>{agent_key}</b>",
            f"Status: {status.upper()}",
            f"Calls: {total_calls}",
            f"Failures: {stats.get('failures', 0)}",
            f"Runtime: {stats.get('total_runtime_seconds', 0):.2f}s",
        ]
        # Include type-specific extras
        if "ollama_model_name" in stats:
            hover_lines.append(f"Model: {stats['ollama_model_name']}")
        if "forecast_calls" in stats:
            hover_lines.append(f"Forecasts: {stats['forecast_calls']}")

        nodes.append({
            "x": x,
            "y": y,
            "z": z,
            "name": f"{icon} {agent_key}",
            "color": _resolve_node_color(status),
            "size": size,
        })

    # ── Build edges: DMA (index 0) to every other agent ──
    edges: List[Tuple[int, int, Dict[str, Any]]] = []
    for j in range(1, len(ordered)):
        stats = _safe_agent_data(agents_report, ordered[j])
        target_status = _resolve_status(stats)

        # Edge width = message frequency (calls-based scaling)
        total_calls = stats.get("total_calls", 0)
        edge_width = 1.2 + min(total_calls * 0.08, 4.0)  # 1.2 → 5.2

        # Edge color = latency gradient (cyan=fast, magenta=slow)
        total_runtime = stats.get("total_runtime_seconds", 0.0)
        avg_latency = (total_runtime / max(total_calls, 1)) * 1000 if total_calls > 0 else 0  # ms
        latency_ratio = min(avg_latency / 500.0, 1.0) if avg_latency > 0 else 0
        # Interpolate: cyan(#00f5ff) → magenta(#ff00e5)
        r = int(0 + latency_ratio * 255)
        g = int(245 * (1 - latency_ratio))
        b = int(255 + latency_ratio * (229 - 255))
        edge_color = f"rgb({r},{g},{b})"

        edges.append((0, j, {"width": edge_width, "color": edge_color}))

    return {"nodes": nodes, "edges": edges}


# ═══════════════════════════════════════════════════════════════════════════
# Main render function
# ═══════════════════════════════════════════════════════════════════════════

def render(eco: Any, config: Any, dataset: Any, monitor: Any) -> None:
    """Render Agent Monitor page with 3D network topology."""
    t = get_translator()

    # ── Fetch data ──
    if eco is None:
        info_bar(t("common.no_data"), "error")
        return

    try:
        full_report = eco.get_full_report()
    except Exception:
        info_bar(t("common.no_data"), "error")
        return

    agents_report: Dict[str, Any] = full_report.get("agents", {}) or {}
    maintenance_monitor: Dict[str, Any] = full_report.get("maintenance_monitor", {}) or {}
    tasks: List[Dict[str, Any]] = full_report.get("tasks", {}).get("recent_task_predictions", []) or []

    if not agents_report:
        info_bar(t("common.no_data"), "warning")
        return

    # ═══════════════════════════════════════════════════════════════════════
    # Row 1: 3D Network Topology (full width)
    # ═══════════════════════════════════════════════════════════════════════
    section_header(t("agents.topology_3d"), "\U0001F578️", "cyan")

    topology_data = _build_topology_3d(agents_report, t)
    if topology_data:
        network_3d_chart(
            nodes=topology_data["nodes"],
            edges=topology_data["edges"],
            title="10-Agent Star Topology — DMA · Central Hub",
            auto_rotate=True,
            key="agent_topology_3d",
        )
    else:
        info_bar(t("common.insufficient_data"), "info")

    # ═══════════════════════════════════════════════════════════════════════
    # Row 2: Global health gauge + online/degraded/offline counts
    # ═══════════════════════════════════════════════════════════════════════
    section_header(t("agents.global_health"), "❤️", "green")

    # Compute aggregate stats
    online_count = 0
    degraded_count = 0
    offline_count = 0
    total_agent_count = 0
    agent_statuses: Dict[str, str] = {}

    for spec in AGENT_SPECS:
        key = spec["key"]
        stats = _safe_agent_data(agents_report, key)
        if not stats:
            continue
        total_agent_count += 1
        status = _resolve_status(stats)
        agent_statuses[key] = status
        if status in ("healthy", "ok", "normal"):
            online_count += 1
        elif status in ("degraded", "warning"):
            degraded_count += 1
        else:
            offline_count += 1

    health_pct = (online_count / max(total_agent_count, 1)) * 100

    # Handle isolated agents from maintenance monitor
    isolated = maintenance_monitor.get("isolated_agents", {}) or {}
    if isinstance(isolated, dict):
        for agent_name in isolated:
            if agent_name not in agent_statuses:
                offline_count += 1
                total_agent_count += 1

    col_gauge, col_online, col_degraded, col_offline = st.columns([2, 1, 1, 1])

    with col_gauge:
        gauge_chart(
            value=health_pct,
            max_val=100,
            title=t("agents.global_health"),
            color=COLORS["success"] if health_pct >= 80 else COLORS["warning"] if health_pct >= 50 else COLORS["danger"],
            thresholds={"warn": 80, "danger": 50},
            key="agent_health_gauge",
        )

    with col_online:
        neon_metric_card(
            t("agents.online_count"),
            str(online_count),
            icon="\U0001F7E2",
            delta=f"{t('agents.total_agents')}: {total_agent_count}",
            neon_color="green",
            key="ag_online",
        )

    with col_degraded:
        neon_metric_card(
            t("common.degraded"),
            str(degraded_count),
            icon="\U0001F7E1",
            delta=f"{degraded_count / max(total_agent_count, 1) * 100:.0f}%" if total_agent_count > 0 else "",
            delta_good=(degraded_count == 0),
            neon_color="amber",
            key="ag_degraded",
        )

    with col_offline:
        neon_metric_card(
            t("common.offline") if offline_count > 0 else "Isolated",
            str(offline_count),
            icon="\U0001F534",
            delta=t("agents.isolated") if isolated else "",
            delta_good=(offline_count == 0),
            neon_color="red",
            key="ag_offline",
        )

    # ═══════════════════════════════════════════════════════════════════════
    # Row 3: 10 Agent cards in 2x5 grid
    # ═══════════════════════════════════════════════════════════════════════
    section_header(t("agents.stats"), "\U0001F4CA", "cyan")

    # Render in 2 rows of 5
    for row_idx in range(2):
        cols = st.columns(5)
        for col_idx, spec in enumerate(AGENT_SPECS[row_idx * 5 : (row_idx + 1) * 5]):
            with cols[col_idx]:
                _render_agent_card(spec, agents_report, tasks, t)

    # ═══════════════════════════════════════════════════════════════════════
    # Row 4: Maintenance alerts (only if alerts exist)
    # ═══════════════════════════════════════════════════════════════════════
    alerts = maintenance_monitor.get("alerts", []) or []
    if alerts:
        section_header(t("agents.alerts"), "\U0001F6A8", "red")
        for alert in alerts:
            agent_name = alert.get("agent", "Unknown")
            reason = alert.get("reason", "unknown")
            age = alert.get("age_seconds", 0)
            age_str = f"{age:.0f}s" if age < 120 else f"{age / 60:.1f}min"
            info_bar(
                f"**{agent_name}** — {reason} — {age_str}",
                level="error",
                icon="⚠️",
            )

    # ── Refresh button (right-aligned via css, no empty column) ──
    if st.button(f"\U0001F504 {t('agents.refresh')}", key="agent_refresh_btn",
                 use_container_width=True):
        st.rerun()


# ═══════════════════════════════════════════════════════════════════════════
# Individual agent card renderer
# ═══════════════════════════════════════════════════════════════════════════

def _render_agent_card(
    spec: Dict[str, Any],
    agents_report: Dict[str, Any],
    tasks: List[Dict[str, Any]],
    t: Any,
) -> None:
    """Render a single agent card with icon, status, metrics, and sparkline.

    Card header + 2 KPI metrics are merged into ONE st.markdown to avoid
    Streamlit's per-widget wrapper divs (st.columns + 2×neon_metric_card
    would generate 5+ nested div blocks per card — merged into 1).
    """
    agent_key = spec["key"]
    icon = spec["icon"]
    stats = _safe_agent_data(agents_report, agent_key)
    status = _resolve_status(stats)
    status_badge_html = pulse_status_badge(status, size="sm")
    neon_color = _resolve_metric_color(status)
    label = t(spec["label_key"])

    color_map = {
        "cyan": COLORS["cyan"], "magenta": COLORS["magenta"],
        "green": COLORS["success"], "amber": COLORS["warning"],
        "red": COLORS["danger"], "violet": COLORS["violet"],
    }
    metric_color = color_map.get(neon_color, COLORS["cyan"])

    total_calls = stats.get("total_calls", 0)
    failures = stats.get("failures", 0)
    success_rate = (1.0 - failures / max(total_calls, 1)) * 100

    # ── Single markdown block: header + 2 inline metrics ──
    st.markdown(f"""
    <div style="
        background:{COLORS['bg_card']};
        border:1px solid {COLORS['cyan_dim']};
        border-radius:8px;
        padding:0.25rem 0.35rem;
        margin-bottom:0.15rem;
        text-align:center;
    ">
        <div style="font-size:1.2rem;line-height:1.1;">{icon}</div>
        <div style="font-size:0.65rem;font-weight:600;color:{COLORS['text_primary']};margin:0.05rem 0;">
            {agent_key}
        </div>
        <div style="font-size:0.55rem;color:{COLORS['text_secondary']};">
            {label}
        </div>
        <div style="font-size:0.58rem;margin:0.1rem 0;">{status_badge_html}</div>
        <div style="display:flex;gap:0.25rem;margin-top:0.2rem;">
            <div style="flex:1;background:{COLORS['bg_input']};border-radius:6px;padding:0.2rem 0.15rem;
                        border:1px solid {metric_color}20;">
                <div style="font-size:0.8rem;font-weight:700;color:{metric_color};">{total_calls}</div>
                <div style="font-size:0.5rem;color:{COLORS['text_secondary']};">{t('agents.calls')}</div>
            </div>
            <div style="flex:1;background:{COLORS['bg_input']};border-radius:6px;padding:0.2rem 0.15rem;
                        border:1px solid {metric_color}20;">
                <div style="font-size:0.8rem;font-weight:700;color:{metric_color};">{success_rate:.1f}%</div>
                <div style="font-size:0.5rem;color:{COLORS['text_secondary']};">{t('agents.success_rate')}</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Sparkline ──
    _render_agent_sparkline(agent_key, stats, neon_color, t)


def _render_agent_sparkline(
    agent_key: str,
    stats: Dict[str, Any],
    neon_color: str,
    t: Any,
) -> None:
    """Render only measured recent agent latencies; never synthesize a trend."""
    color_map = {
        "green":  COLORS["success"],
        "amber":  COLORS["warning"],
        "red":    COLORS["danger"],
        "cyan":   COLORS["cyan"],
        "violet": COLORS["violet"],
        "magenta": COLORS["magenta"],
    }
    line_color = color_map.get(neon_color, COLORS["cyan"])

    latencies = [float(value) for value in stats.get("runtime_history_ms", [])]
    if not latencies:
        st.caption("暂无实测延迟历史")
        return

    sparkline_chart(
        latencies,
        height=40,
        color=line_color,
        show_dots=False,
        key=f"ag_{agent_key}_spark",
    )
