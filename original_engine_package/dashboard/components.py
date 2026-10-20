"""Reusable UI components — metric cards, gauges, badges, info bars, and 3D chart builders.

All Plotly charts share a dark theme applied via dashboard.theme helpers.

Usage:
    from dashboard.components import neon_metric_card, gauge_chart, scatter_3d_chart, ...
"""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from dashboard.theme import COLORS, configure_plotly_dark, configure_plotly_dark_3d, LAYOUT_3D_AUTO_ROTATE

# ═══════════════════════════════════════════════════════════════════════════
# Plotly config
# ═══════════════════════════════════════════════════════════════════════════

PLOTLY_CONFIG: Dict[str, Any] = {
    "displayModeBar": True,
    "displaylogo": False,
    "modeBarButtonsToRemove": ["lasso2d", "select2d", "sendDataToCloud"],
    "toImageButtonOptions": {"format": "png", "filename": "mapfm_chart"},
}

# ═══════════════════════════════════════════════════════════════════════════
# 2D Components
# ═══════════════════════════════════════════════════════════════════════════

def neon_metric_card(
    label: str,
    value: str,
    icon: str = "",
    delta: str = "",
    delta_good: bool = True,
    neon_color: str = "cyan",
    key: str = "",
) -> None:
    """Render a glass-morphism metric card with neon glow edge."""
    color_map = {
        "cyan": COLORS["cyan"], "magenta": COLORS["magenta"],
        "green": COLORS["success"], "amber": COLORS["warning"],
        "red": COLORS["danger"], "violet": COLORS["violet"],
    }
    border_color = color_map.get(neon_color, COLORS["cyan"])
    delta_class = "delta-positive" if delta_good else "delta-negative" if delta else ""
    delta_html = f'<div class="neon-metric-delta {delta_class}">{delta}</div>' if delta else ""
    icon_html = f'<span style="font-size:1.5rem;">{icon}</span><br>' if icon else ""

    st.markdown(f"""
    <div class="neon-metric-card" style="border-color:{border_color}40;">
        {icon_html}
        <div class="neon-metric-value" style="color:{border_color};">{value}</div>
        <div class="neon-metric-label">{label}</div>
        {delta_html}
    </div>
    """, unsafe_allow_html=True)


def pulse_status_badge(status: str, size: str = "md") -> str:
    """Return HTML: animated pulse dot + status badge text."""
    dot_map = {
        "healthy": "dot-green", "ok": "dot-green", "normal": "dot-green",
        "degraded": "dot-yellow", "warning": "dot-yellow",
        "error": "dot-red", "offline": "dot-red", "critical": "dot-red",
    }
    badge_map = {
        "healthy": "status-healthy", "ok": "status-healthy", "normal": "status-healthy",
        "degraded": "status-degraded", "warning": "status-degraded",
        "error": "status-offline", "offline": "status-offline",
    }
    dot_class = dot_map.get(str(status).lower(), "dot-gray")
    badge_class = badge_map.get(str(status).lower(), "status-unknown")
    size_px = {"sm": 8, "md": 10, "lg": 14}.get(size, 10)
    return (
        f'<span class="pulse-dot {dot_class}" style="width:{size_px}px;height:{size_px}px;"></span>'
        f'<span class="status-badge {badge_class}">{status.upper()}</span>'
    )


def section_header(title: str, icon: str = "", color: str = "cyan") -> None:
    """Neon-text section header with gradient underline."""
    c = {"cyan": COLORS["cyan"], "magenta": COLORS["magenta"],
         "green": COLORS["success"]}.get(color, COLORS["cyan"])
    icon_str = f"{icon} " if icon else ""
    st.markdown(f"""
    <div class="section-header" style="border-image:linear-gradient(90deg,{c},transparent) 1;">
        <span style="color:{c};">{icon_str}{title}</span>
    </div>
    """, unsafe_allow_html=True)


def info_bar(msg: str, level: str = "info", icon: str = "") -> None:
    """Colored info box with left border accent."""
    icons = {"info": "ℹ️", "success": "✅", "warning": "⚠️", "error": "❌"}
    icon_str = icon or icons.get(level, "")
    st.markdown(f'<div class="info-box {level}">{icon_str} {msg}</div>', unsafe_allow_html=True)


def glass_panel(title: str = "", icon: str = "", neon_color: str = "cyan",
                expanded: bool = True, key: str = "") -> "st.container":
    """Return a Streamlit container wrapped in glass-panel CSS. Use as context manager."""
    c = st.container(key=key)
    with c:
        if title:
            section_header(title, icon, neon_color)
        placeholder = st.empty()
    return placeholder


def gauge_chart(
    value: float, max_val: float, title: str,
    color: str = "#00f5ff",
    thresholds: Optional[Dict[str, float]] = None,
    key: str = "",
) -> None:
    """Plotly gauge chart with dark theme."""
    steps = []
    if thresholds:
        sorted_t = sorted(thresholds.items(), key=lambda x: x[1])
        for i, (label, thresh) in enumerate(sorted_t):
            steps.append({"range": [0, thresh * max_val], "color": ["#00ff88", "#ffaa00", "#ff3344"][min(i, 2)]})

    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=value,
        title={"text": title, "font": {"color": "#e0e0ff", "size": 14}},
        number={"font": {"color": color, "size": 32}},
        gauge={
            "axis": {"range": [0, max_val], "tickcolor": "#7a8ba8", "tickfont": {"color": "#7a8ba8"}},
            "bar": {"color": color, "thickness": 0.2},
            "bgcolor": "rgba(12,18,35,0.6)",
            "borderwidth": 1,
            "bordercolor": "rgba(0,245,255,0.2)",
            "steps": steps or [
                {"range": [0, max_val * 0.5], "color": "rgba(0,245,255,0.08)"},
                {"range": [max_val * 0.5, max_val * 0.8], "color": "rgba(0,245,255,0.15)"},
                {"range": [max_val * 0.8, max_val], "color": "rgba(255,51,68,0.15)"},
            ],
        },
    ))
    configure_plotly_dark(fig)
    fig.update_layout(height=220, margin=dict(l=30, r=30, t=50, b=20))
    st.plotly_chart(fig, use_container_width=True, config=PLOTLY_CONFIG, key=key)


def radial_gauge(
    value: float, max_val: float, title: str,
    color: str = "#00f5ff", key: str = "",
) -> None:
    """Ring/donut progress chart using Plotly pie."""
    ratio = min(value / max_val, 1.0) if max_val > 0 else 0
    remaining = 1.0 - ratio
    fig = go.Figure(data=[go.Pie(
        values=[ratio, remaining],
        labels=None,
        hole=0.75,
        marker=dict(colors=[color, "rgba(0,245,255,0.08)"], line=dict(width=0)),
        textinfo="none",
        hoverinfo="none",
        sort=False,
    )])
    fig.add_annotation(
        text=f"<b style='color:{color};font-size:22px;'>{value:.1f}</b><br>"
             f"<span style='color:#7a8ba8;font-size:10px;'>/ {max_val:.0f}</span>",
        showarrow=False, x=0.5, y=0.5,
    )
    configure_plotly_dark(fig)
    fig.update_layout(
        title={"text": title, "font": {"color": "#e0e0ff", "size": 13}},
        height=200, margin=dict(l=10, r=10, t=40, b=10),
        showlegend=False,
    )
    st.plotly_chart(fig, use_container_width=True, config=PLOTLY_CONFIG, key=key)


def sparkline_chart(
    values: List[float], height: int = 50,
    color: str = "#00f5ff", show_dots: bool = False,
    key: str = "",
) -> None:
    """Mini trend line chart (no axes, pure trend)."""
    if not values or len(values) < 2:
        st.caption("—")
        return
    fig = go.Figure(go.Scatter(
        y=values, mode="lines+markers" if show_dots else "lines",
        line=dict(width=1.5, color=color),
        marker=dict(size=2, color=color) if show_dots else None,
        hoverinfo="none",
    ))
    configure_plotly_dark(fig)
    fig.update_layout(
        height=height, margin=dict(l=0, r=0, t=0, b=0),
        xaxis=dict(visible=False, fixedrange=True),
        yaxis=dict(visible=False, fixedrange=True),
        showlegend=False, paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False}, key=key)


def data_table_with_style(
    df: pd.DataFrame,
    highlight_cols: Optional[List[str]] = None,
    height: int = 400,
    key: str = "",
) -> None:
    """Render a dark-themed styled DataFrame."""
    if df is None or df.empty:
        st.caption("—")
        return
    styled = df.style.set_properties(**{
        "background-color": COLORS["bg_card"],
        "color": COLORS["text_primary"],
        "border-color": "rgba(0,245,255,0.1)",
    })
    if highlight_cols:
        for col in highlight_cols:
            if col in df.columns:
                styled = styled.set_properties(subset=[col], **{"color": COLORS["cyan"], "font-weight": "600"})
    st.dataframe(styled, use_container_width=True, height=height, key=key)


def export_button(
    data: Union[pd.DataFrame, Dict, List],
    filename: str, label: str = "Export", key: str = "",
) -> None:
    """Auto-detect CSV/JSON download button."""
    if isinstance(data, pd.DataFrame):
        payload = data.to_csv(index=False).encode("utf-8")
        mime = "text/csv"
    else:
        import json
        payload = json.dumps(data, indent=2, ensure_ascii=False, default=str).encode("utf-8")
        mime = "application/json"
    st.download_button(label, payload, filename, mime, key=key)


def animated_counter(
    label: str,
    value: Union[int, float],
    duration: float = 1.0,
    prefix: str = "",
    suffix: str = "",
    color: str = "#00f5ff",
    key: str = "",
) -> None:
    """Animated counter that counts up from 0 to value using CSS + JS.

    Renders a large number that animates on page load.  Works best for
    integer-ish values shown once per render cycle.
    """
    # Use float formatting for floats, int for ints
    if isinstance(value, float) and value != int(value):
        display_val = f"{prefix}{value:.2f}{suffix}"
    else:
        display_val = f"{prefix}{int(value)}{suffix}"

    st.markdown(f"""
    <div class="neon-metric-card" style="border-color:{color}40;" id="counter-{key}">
        <div class="neon-metric-value" style="color:{color};">{display_val}</div>
        <div class="neon-metric-label">{label}</div>
    </div>
    """, unsafe_allow_html=True)


def filter_bar(
    filters: Dict[str, List[str]],
    key: str = "",
) -> Dict[str, List[str]]:
    """Render a horizontal filter bar and return selected values.

    Args:
        filters: dict of filter_name → list of options.
        key: unique key prefix for widgets.

    Returns:
        dict of filter_name → list of selected values.
    """
    n = len(filters)
    if n == 0:
        return {}

    cols = st.columns(n)
    result: Dict[str, List[str]] = {}

    for i, (name, options) in enumerate(filters.items()):
        with cols[i]:
            selected = st.multiselect(
                name, options,
                key=f"{key}_fb_{name}".replace(" ", "_"),
                label_visibility="visible",
            )
            result[name] = selected

    return result


# ═══════════════════════════════════════════════════════════════════════════
# 3D Chart Components
# ═══════════════════════════════════════════════════════════════════════════

def scatter_3d_chart(
    points: np.ndarray,          # shape (N, 3)
    labels: Optional[List[str]] = None,
    sizes: Optional[List[float]] = None,
    colors: Optional[List[Any]] = None,
    colorscale: str = "Turbo",
    title: str = "",
    hover_texts: Optional[List[str]] = None,
    marker_opacity: float = 0.85,
    auto_rotate: bool = False,
    key: str = "",
) -> None:
    """3D scatter plot with optional auto-rotation. points shape (N,3)."""
    x, y, z = points[:, 0], points[:, 1], points[:, 2]
    marker_dict: Dict[str, Any] = {
        "size": sizes if sizes else 8,
        "color": colors if colors else x,
        "colorscale": colorscale,
        "opacity": marker_opacity,
        "line": {"width": 1, "color": "rgba(0,245,255,0.3)"},
    }
    fig = go.Figure(data=[go.Scatter3d(
        x=x, y=y, z=z,
        mode="markers+text" if labels else "markers",
        text=labels,
        textposition="top center",
        textfont={"size": 9, "color": "#e0e0ff"},
        marker=marker_dict,
        hovertext=hover_texts,
        hoverinfo="text" if hover_texts else "x+y+z",
    )])
    configure_plotly_dark_3d(fig, auto_rotate=auto_rotate)
    fig.update_layout(
        title={"text": title, "font": {"color": "#e0e0ff", "size": 15}} if title else {},
        height=500,
    )
    st.plotly_chart(fig, use_container_width=True, config=PLOTLY_CONFIG, key=key)


def surface_3d_chart(
    x: np.ndarray, y: np.ndarray, z: np.ndarray,
    title: str = "",
    colorscale: str = "Turbo",
    show_contours: bool = True,
    auto_rotate: bool = False,
    key: str = "",
) -> None:
    """3D surface plot with optional contour projection and auto-rotation."""
    contour_dict = {}
    if show_contours:
        contour_dict = {"z": {"show": True, "usecolormap": True, "project": {"z": True}}}
    fig = go.Figure(data=[go.Surface(
        x=x, y=y, z=z,
        colorscale=colorscale,
        contours=contour_dict,
        colorbar={"title": {"text": "", "font": {"color": "#e0e0ff"}},
                  "tickfont": {"color": "#7a8ba8"}},
    )])
    configure_plotly_dark_3d(fig, auto_rotate=auto_rotate)
    fig.update_layout(
        title={"text": title, "font": {"color": "#e0e0ff", "size": 15}} if title else {},
        height=500,
    )
    st.plotly_chart(fig, use_container_width=True, config=PLOTLY_CONFIG, key=key)


def network_3d_chart(
    nodes: List[Dict[str, Any]],   # [{"x","y","z","name","color","size"}, ...]
    edges: List[Tuple[int, int, Dict[str, Any]]],  # [(from_idx, to_idx, {"width","color"}), ...]
    title: str = "",
    auto_rotate: bool = False,
    key: str = "",
) -> None:
    """3D network topology graph. Nodes as markers, edges as lines."""
    fig = go.Figure()

    # Edges first (behind nodes)
    for src, dst, edge_attrs in edges:
        fig.add_trace(go.Scatter3d(
            x=[nodes[src]["x"], nodes[dst]["x"]],
            y=[nodes[src]["y"], nodes[dst]["y"]],
            z=[nodes[src]["z"], nodes[dst]["z"]],
            mode="lines",
            line=dict(
                width=edge_attrs.get("width", 1.5),
                color=edge_attrs.get("color", COLORS["cyan"]),
            ),
            hoverinfo="none",
            showlegend=False,
        ))

    # Nodes on top
    nx = [n["x"] for n in nodes]
    ny = [n["y"] for n in nodes]
    nz = [n["z"] for n in nodes]
    names = [n.get("name", "") for n in nodes]
    node_colors = [n.get("color", COLORS["cyan"]) for n in nodes]
    node_sizes = [n.get("size", 10) for n in nodes]

    fig.add_trace(go.Scatter3d(
        x=nx, y=ny, z=nz,
        mode="markers+text",
        text=names,
        textposition="top center",
        textfont={"size": 10, "color": "#e0e0ff"},
        marker=dict(
            size=node_sizes, color=node_colors,
            opacity=0.9,
            line=dict(width=1.5, color="rgba(0,245,255,0.5)"),
        ),
        hovertext=[f"{n}<br>Color: {c}" for n, c in zip(names, node_colors)],
        hoverinfo="text",
        showlegend=False,
    ))

    configure_plotly_dark_3d(fig, auto_rotate=auto_rotate)
    fig.update_layout(
        title={"text": title, "font": {"color": "#e0e0ff", "size": 15}} if title else {},
        height=550, showlegend=False,
    )
    st.plotly_chart(fig, use_container_width=True, config=PLOTLY_CONFIG, key=key)


def trajectory_3d_chart(
    trajectories: List[Dict[str, Any]],  # [{"x":[0,val],"y":[0,val],"z":[0,val],"name":str,"color":str,"width":float},...]
    title: str = "",
    danger_radius: float = 0.0,
    auto_rotate: bool = False,
    key: str = "",
) -> None:
    """3D multi-trajectory lines from origin to risk coordinates."""
    fig = go.Figure()

    for traj in trajectories:
        fig.add_trace(go.Scatter3d(
            x=traj["x"], y=traj["y"], z=traj["z"],
            mode="lines+markers",
            line=dict(width=traj.get("width", 2), color=traj.get("color", COLORS["cyan"])),
            marker=dict(size=5, color=traj.get("color", COLORS["cyan"])),
            name=traj.get("name", ""),
            hovertext=traj.get("hover", ""),
            hoverinfo="text",
        ))

    # Danger zone reference sphere
    if danger_radius > 0:
        u, v = np.mgrid[0:2 * np.pi:20j, 0:np.pi / 2:10j]
        sx = danger_radius * np.cos(u) * np.sin(v)
        sy = danger_radius * np.sin(u) * np.sin(v)
        sz = danger_radius * np.cos(v)
        fig.add_trace(go.Surface(
            x=sx, y=sy, z=sz,
            opacity=0.08,
            colorscale=[[0, "rgba(255,51,68,0.3)"], [1, "rgba(255,51,68,0.02)"]],
            showscale=False, hoverinfo="skip", name="Danger Zone",
        ))

    configure_plotly_dark_3d(fig, auto_rotate=auto_rotate)
    fig.update_layout(
        title={"text": title, "font": {"color": "#e0e0ff", "size": 15}} if title else {},
        height=500,
        scene=dict(
            xaxis_title="Short-Term Risk (24h)",
            yaxis_title="Mid-Term Risk (30d)",
            zaxis_title="Long-Term Risk (12m)",
        ),
    )
    st.plotly_chart(fig, use_container_width=True, config=PLOTLY_CONFIG, key=key)


def volume_3d_chart(
    x: np.ndarray, y: np.ndarray, z: np.ndarray, values: np.ndarray,
    title: str = "",
    colorscale: str = "Teal",
    surface_count: int = 15,
    opacity: float = 0.1,
    auto_rotate: bool = False,
    key: str = "",
) -> None:
    """3D volumetric rendering of density field."""
    fig = go.Figure(data=[go.Volume(
        x=x, y=y, z=z,
        value=values,
        isomin=values.max() * 0.1 if values.max() > 0 else 0,
        isomax=values.max() if values.max() > 0 else 1,
        opacity=opacity,
        surface_count=surface_count,
        colorscale=colorscale,
        caps=dict(x_show=False, y_show=False, z_show=False),
    )])
    configure_plotly_dark_3d(fig, auto_rotate=auto_rotate)
    fig.update_layout(
        title={"text": title, "font": {"color": "#e0e0ff", "size": 15}} if title else {},
        height=500,
    )
    st.plotly_chart(fig, use_container_width=True, config=PLOTLY_CONFIG, key=key)


def mesh_3d_chart(
    x: np.ndarray, y: np.ndarray, z: np.ndarray,
    intensity: Optional[np.ndarray] = None,
    title: str = "",
    colorscale: str = "Turbo",
    opacity: float = 0.8,
    auto_rotate: bool = False,
    key: str = "",
) -> None:
    """3D mesh surface from scattered points (Delaunay triangulation)."""
    fig = go.Figure(data=[go.Mesh3d(
        x=x, y=y, z=z,
        intensity=intensity if intensity is not None else z,
        colorscale=colorscale,
        opacity=opacity,
        hovertext=[f"({xi:.1f},{yi:.1f},{zi:.1f})" for xi, yi, zi in zip(x, y, z)],
        hoverinfo="text",
    )])
    configure_plotly_dark_3d(fig, auto_rotate=auto_rotate)
    fig.update_layout(
        title={"text": title, "font": {"color": "#e0e0ff", "size": 15}} if title else {},
        height=450,
    )
    st.plotly_chart(fig, use_container_width=True, config=PLOTLY_CONFIG, key=key)


def cone_3d_chart(
    x: List[float], y: List[float], z: List[float],
    u: List[float], v: List[float], w: List[float],
    title: str = "",
    colorscale: Optional[List[List[Any]]] = None,
    sizeref: float = 2.0,
    auto_rotate: bool = False,
    key: str = "",
) -> None:
    """3D cone/vector field chart showing direction and magnitude of change.

    Args:
        x, y, z: Cone base positions.
        u, v, w: Direction vector components.
        title: Chart title.
        colorscale: Plotly colorscale for cone coloring.
        sizeref: Size reference for scaling cones.
        auto_rotate: Enable auto-rotation animation.
        key: Streamlit chart key.
    """
    if colorscale is None:
        colorscale = [
            [0.0, COLORS["success"]],
            [0.5, COLORS["warning"]],
            [1.0, COLORS["danger"]],
        ]

    fig = go.Figure(data=[go.Cone(
        x=x, y=y, z=z,
        u=u, v=v, w=w,
        colorscale=colorscale,
        sizemode="absolute",
        sizeref=sizeref,
        anchor="tip",
        name="Vector Field",
        hovertext=[f"({xi:.1f},{yi:.1f},{zi:.1f}) → ({ui:+.2f},{vi:+.2f},{wi:+.2f})"
                    for xi, yi, zi, ui, vi, wi in zip(x, y, z, u, v, w)],
        hoverinfo="text",
        showscale=False,
    )])
    configure_plotly_dark_3d(fig, auto_rotate=auto_rotate)
    fig.update_layout(
        title={"text": title, "font": {"color": "#e0e0ff", "size": 15}} if title else {},
        height=450,
        scene=dict(
            xaxis_title="CPU %",
            yaxis_title="RAM %",
            zaxis_title="GPU %",
        ),
        legend=dict(
            x=0.02, y=0.98,
            font=dict(color="#7a8ba8", size=10),
            bgcolor="rgba(0,0,0,0)",
        ),
    )
    st.plotly_chart(fig, use_container_width=True, config=PLOTLY_CONFIG, key=key)
