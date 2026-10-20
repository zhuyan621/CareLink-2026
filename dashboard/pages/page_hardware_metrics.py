"""Page 3: Hardware Metrics — 3D resource surface, cone vector field, gauges, degradation."""

from __future__ import annotations

from typing import Any, Dict, List

import numpy as np
import plotly.graph_objects as go
import streamlit as st

from dashboard.components import (
    gauge_chart,
    section_header,
    info_bar,
    surface_3d_chart,
    sparkline_chart,
    neon_metric_card,
    mesh_3d_chart,
    PLOTLY_CONFIG,
)
from dashboard.i18n import get_translator
from dashboard.theme import configure_plotly_dark_3d, COLORS

# Optional scipy import
try:
    from scipy.interpolate import griddata as _scipy_griddata
    _HAS_SCIPY = True
except ImportError:
    _HAS_SCIPY = False


def render(eco: Any, config: Any, dataset: Any, monitor: Any) -> None:
    """Render Hardware Metrics page — 3D surface, cone vector field, gauges, degradation."""
    t = get_translator()

    # ── Health check ──
    try:
        health = monitor.check() if monitor else None
    except Exception:
        health = None

    # ── History ──
    try:
        history: List[Dict[str, Any]] = monitor.get_history(limit=120) if monitor else []
    except Exception:
        history = []

    # ── Permission / psutil guard ──
    _psutil_ok = True
    if monitor is not None and health is not None:
        try:
            _ = health.cpu_percent  # may be 0 if psutil missing
        except Exception:
            _psutil_ok = False

    if monitor is None:
        info_bar(t("hardware.psutil_required"), "warning")
    elif not _psutil_ok:
        info_bar(t("hardware.permission_denied"), "warning")

    # ═══════════════════════════════════════════════════════════════════════
    # Row 1: 3D Resource Utilization Surface (full width)
    # ═══════════════════════════════════════════════════════════════════════
    section_header(t("hardware.surface_3d"), "\U0001f3d4️", "cyan")

    if history and len(history) >= 3:
        _render_resource_surface(history, health, t)
    else:
        info_bar(t("common.insufficient_data"), "info")

    # ═══════════════════════════════════════════════════════════════════════
    # Row 2: 4 gauge charts (CPU / GPU / RAM / Disk)
    # ═══════════════════════════════════════════════════════════════════════
    if health:
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            gauge_chart(
                health.cpu_percent, 100,
                t("hardware.cpu_util"),
                color=COLORS["cyan"],
                key="hw_cpu_gauge",
            )
        with c2:
            gpu_pct = health.gpu_memory_ratio * 100 if health.gpu_available else 0
            gauge_chart(
                gpu_pct, 100,
                t("hardware.gpu_mem_usage"),
                thresholds={"warn": 80, "danger": 95},
                color=COLORS["magenta"],
                key="hw_gpu_gauge",
            )
        with c3:
            gauge_chart(
                health.memory_ratio * 100, 100,
                t("hardware.ram_usage"),
                thresholds={"warn": 80, "danger": 95},
                color=COLORS["cyan"],
                key="hw_ram_gauge",
            )
        with c4:
            disk_total = max(health.disk_total_gb, 1.0)
            disk_pct = max(0, min(100, (1 - health.disk_free_gb / disk_total) * 100))
            gauge_chart(
                disk_pct, 100,
                t("hardware.disk_usage"),
                thresholds={"warn": 80, "danger": 95},
                color=COLORS["success"],
                key="hw_disk_gauge",
            )
    else:
        info_bar(t("hardware.psutil_required"), "warning")

    # ═══════════════════════════════════════════════════════════════════════
    # Row 3: 3D Cone Vector Field (CPU x RAM x GPU deltas)
    # ═══════════════════════════════════════════════════════════════════════
    section_header(t("hardware.vector_3d"), "\U0001f32a️", "magenta")

    if history and len(history) >= 2:
        _render_cone_vector_field(history, health, t)
    else:
        info_bar(t("common.insufficient_data"), "info")

    # ═══════════════════════════════════════════════════════════════════════
    # Row 4: Degradation Level Display with Thresholds
    # ═══════════════════════════════════════════════════════════════════════
    section_header(t("hardware.degradation_level"), "⚠️", "cyan")
    _render_degradation_display(health, history, t)

    # ═══════════════════════════════════════════════════════════════════════
    # Row 5: Sparkline trends (RAM + GPU history)
    # ═══════════════════════════════════════════════════════════════════════
    if history and len(history) >= 2:
        sc1, sc2 = st.columns(2)
        with sc1:
            st.caption(t("hardware.ram_history"))
            ram_vals = [h.get("memory_ratio", 0) * 100 for h in history]
            sparkline_chart(ram_vals, height=60, color=COLORS["cyan"], key="hw_ram_spark")
        with sc2:
            st.caption(t("hardware.gpu_mem_history"))
            gpu_vals = [h.get("gpu_memory_ratio", 0) * 100 for h in history]
            sparkline_chart(gpu_vals, height=60, color=COLORS["magenta"], key="hw_gpu_spark")

    # ═══════════════════════════════════════════════════════════════════
    # Row 6: Per-resource detail tabs
    # ═══════════════════════════════════════════════════════════════════
    st.markdown("---")
    section_header(t("hardware.resource_detail"), "🔍", "violet")

    tab_cpu, tab_gpu, tab_ram, tab_disk = st.tabs([
        f"🖥️ {t('hardware.cpu_tab')}",
        f"🎮 {t('hardware.gpu_tab')}",
        f"🧠 {t('hardware.ram_tab')}",
        f"💾 {t('hardware.disk_tab')}",
    ])

    with tab_cpu:
        _render_cpu_detail(health, history, t)
    with tab_gpu:
        _render_gpu_detail(health, history, t)
    with tab_ram:
        _render_ram_detail(health, history, t)
    with tab_disk:
        _render_disk_detail(health, history, t)


# ═══════════════════════════════════════════════════════════════════════════════
# Row 1 helper: 3D Resource Utilization Surface
# ═══════════════════════════════════════════════════════════════════════════════

def _render_resource_surface(
    history: List[Dict[str, Any]],
    health: Any,
    t,
) -> None:
    """Build a 3D surface from history: X=time, Y=resource type, Z=utilization %.

    Uses scipy.interpolate.griddata (cubic) for a smooth surface when scipy is
    available, and falls back to Mesh3d raw triangulation otherwise.
    """
    n = len(history)
    if n < 2:
        info_bar(t("common.insufficient_data"), "info")
        return

    # Resource types: 0=CPU, 1=GPU, 2=RAM, 3=Disk
    resource_labels = ["CPU", "GPU", "RAM", "Disk"]
    resource_y = [0, 1, 2, 3]

    # Current snapshot values for metrics not tracked in history
    current_cpu: float = float(getattr(health, "cpu_percent", 50) or 50)
    current_gpu: float = (
        float(getattr(health, "gpu_memory_ratio", 0) or 0) * 100
        if getattr(health, "gpu_available", False)
        else 0.0
    )
    current_disk_pct: float = 30.0
    if health is not None:
        disk_total = max(getattr(health, "disk_total_gb", 100.0) or 100.0, 1.0)
        disk_free = getattr(health, "disk_free_gb", 70.0) or 70.0
        current_disk_pct = max(0, min(100, (1 - disk_free / disk_total) * 100))

    # Build scattered data points: (time_idx, resource_type, value)
    points_x: List[float] = []
    points_y: List[float] = []
    points_z: List[float] = []

    for i, h in enumerate(history):
        cpu_val = current_cpu
        gpu_val = float(h.get("gpu_memory_ratio", 0) or 0) * 100
        ram_val = float(h.get("memory_ratio", 0) or 0) * 100
        disk_val = current_disk_pct

        for res_idx, val in enumerate([cpu_val, gpu_val, ram_val, disk_val]):
            points_x.append(float(i))
            points_y.append(float(res_idx))
            points_z.append(float(val))

    arr_x = np.array(points_x, dtype=np.float64)
    arr_y = np.array(points_y, dtype=np.float64)
    arr_z = np.array(points_z, dtype=np.float64)

    # ── Interpolated surface (scipy) ──
    if _HAS_SCIPY:
        try:
            grid_x = np.arange(n, dtype=np.float64)
            grid_y = np.array(resource_y, dtype=np.float64)
            grid_xx, grid_yy = np.meshgrid(grid_x, grid_y)

            grid_z = _scipy_griddata(
                (arr_x, arr_y), arr_z,
                (grid_xx, grid_yy),
                method="cubic",
                fill_value=np.nan,
            )

            # Fill any remaining NaN cells with nearest-neighbour
            nan_mask = np.isnan(grid_z)
            if np.any(nan_mask):
                grid_z_nn = _scipy_griddata(
                    (arr_x, arr_y), arr_z,
                    (grid_xx, grid_yy),
                    method="nearest",
                )
                grid_z = np.where(nan_mask, grid_z_nn, grid_z)

            # Build a custom figure with labelled axes (surface_3d_chart doesn't set
            # axis titles, so we replicate its logic and add labels)
            fig = go.Figure(data=[go.Surface(
                x=grid_x,
                y=grid_y,
                z=grid_z,
                colorscale="Turbo",
                contours={"z": {"show": True, "usecolormap": True, "project": {"z": True}}},
                colorbar={
                    "title": {"text": "%", "font": {"color": "#e0e0ff"}},
                    "tickfont": {"color": "#7a8ba8"},
                },
                hovertext=np.array([
                    [f"t={int(x)}<br>{resource_labels[int(yi)]}: {v:.1f}%"
                     for x, yi, v in zip(gx_row, gy_row, gz_row)]
                    for gx_row, gy_row, gz_row in zip(grid_xx, grid_yy, grid_z)
                ]),
                hoverinfo="text",
            )])
            configure_plotly_dark_3d(fig)
            fig.update_layout(
                title={
                    "text": t("hardware.surface_3d"),
                    "font": {"color": "#e0e0ff", "size": 15},
                },
                height=480,
                scene=dict(
                    xaxis_title="Time Index",
                    yaxis_title="Resource Type",
                    zaxis_title="Utilization %",
                    yaxis=dict(
                        tickmode="array",
                        tickvals=resource_y,
                        ticktext=resource_labels,
                    ),
                ),
            )
            st.plotly_chart(fig, use_container_width=True, config=PLOTLY_CONFIG, key="hw_surface_3d")
            return
        except Exception:
            # Fall through to Mesh3d fallback on any scipy error
            pass

    # ── Mesh3d fallback (no scipy) ──
    mesh_3d_chart(
        arr_x, arr_y, arr_z,
        intensity=arr_z,
        title=t("hardware.surface_3d"),
        colorscale="Turbo",
        opacity=0.8,
        key="hw_surface_3d",
    )


# ═══════════════════════════════════════════════════════════════════════════════
# Row 3 helper: 3D Cone Vector Field
# ═══════════════════════════════════════════════════════════════════════════════

def _render_cone_vector_field(
    history: List[Dict[str, Any]],
    health: Any,
    t,
) -> None:
    """Render a 3D Cone chart showing resource usage direction + magnitude.

    Positions cones along the history trajectory.  Each cone's base is at
    (CPU%, RAM%, GPU%) and its direction vector is (delta_CPU, delta_RAM,
    delta_GPU) computed from adjacent history snapshots.
    """
    if len(history) < 2:
        info_bar(t("common.insufficient_data"), "info")
        return

    current_cpu = float(getattr(health, "cpu_percent", 50) or 50)
    current_gpu_pct = float(getattr(health, "gpu_memory_ratio", 0) or 0) * 100
    current_ram_pct = float(getattr(health, "memory_ratio", 50) or 50)
    if getattr(health, "gpu_available", False) is False and current_gpu_pct == 0:
        current_gpu_pct = 0.0

    # Place cones at regular intervals along the history
    n_cones = min(15, len(history) - 1)
    step = max(1, (len(history) - 1) // n_cones)

    cone_x: List[float] = []
    cone_y: List[float] = []
    cone_z: List[float] = []
    cone_u: List[float] = []
    cone_v: List[float] = []
    cone_w: List[float] = []

    indices_used: List[int] = []

    for i in range(0, len(history) - 1, step):
        h0 = history[i]
        h1 = history[min(i + 1, len(history) - 1)]

        ram_val = float(h0.get("memory_ratio", 0) or 0) * 100
        gpu_val = float(h0.get("gpu_memory_ratio", 0) or 0) * 100

        delta_ram = (float(h1.get("memory_ratio", 0) or 0) -
                     float(h0.get("memory_ratio", 0) or 0)) * 100
        delta_gpu = (float(h1.get("gpu_memory_ratio", 0) or 0) -
                     float(h0.get("gpu_memory_ratio", 0) or 0)) * 100

        cone_x.append(current_cpu)
        cone_y.append(ram_val)
        cone_z.append(gpu_val)
        cone_u.append(0.0)       # no CPU history deltas available
        cone_v.append(delta_ram)
        cone_w.append(delta_gpu)
        indices_used.append(i)

    # If only one cone was produced, add a second at the current position to
    # ensure the chart has visual substance
    if len(cone_x) < 2:
        last_ram = float(history[-1].get("memory_ratio", 0) or 0) * 100
        last_gpu = float(history[-1].get("gpu_memory_ratio", 0) or 0) * 100
        cone_x.append(current_cpu * 0.9)
        cone_y.append(last_ram * 0.9)
        cone_z.append(last_gpu * 0.9)
        cone_u.append(0.0)
        cone_v.append(0.0)
        cone_w.append(0.0)

    # Also add a scatter trace showing the full trajectory as context
    traj_cpu = [current_cpu] * len(history)
    traj_ram = [float(h.get("memory_ratio", 0) or 0) * 100 for h in history]
    traj_gpu = [float(h.get("gpu_memory_ratio", 0) or 0) * 100 for h in history]

    fig = go.Figure()

    # Trajectory line
    fig.add_trace(go.Scatter3d(
        x=traj_cpu, y=traj_ram, z=traj_gpu,
        mode="lines",
        line=dict(width=1.5, color=COLORS["cyan_dim"]),
        name="History",
        hoverinfo="skip",
        showlegend=True,
    ))

    # Trajectory markers at cone positions
    fig.add_trace(go.Scatter3d(
        x=cone_x, y=cone_y, z=cone_z,
        mode="markers",
        marker=dict(size=4, color=COLORS["warning"], opacity=0.9),
        name="Sample Points",
        hoverinfo="skip",
        showlegend=True,
    ))

    # Cone vectors
    # Scale up small deltas so cones are visible; absolute sizeref keeps
    # large deltas from dominating.
    max_delta = max(
        max(abs(v) for v in cone_v) if cone_v else 1.0,
        max(abs(v) for v in cone_w) if cone_w else 1.0,
        1.0,
    )
    sizeref_val = max_delta * 0.5 if max_delta > 0 else 1.0

    fig.add_trace(go.Cone(
        x=cone_x, y=cone_y, z=cone_z,
        u=cone_u, v=cone_v, w=cone_w,
        colorscale=[
            [0.0, COLORS["success"]],
            [0.5, COLORS["warning"]],
            [1.0, COLORS["danger"]],
        ],
        sizemode="absolute",
        sizeref=sizeref_val,
        anchor="tip",
        name="Change Vector",
        hovertext=[
            f"t={idx}<br>RAM: {cy:.1f}% (d={cv:+.1f})<br>GPU: {cz:.1f}% (d={cw:+.1f})"
            for idx, cy, cz, cv, cw in zip(indices_used, cone_y, cone_z, cone_v, cone_w)
        ],
        hoverinfo="text",
        showlegend=True,
        showscale=False,
    ))

    configure_plotly_dark_3d(fig)
    fig.update_layout(
        title={
            "text": t("hardware.vector_3d"),
            "font": {"color": "#e0e0ff", "size": 15},
        },
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
    st.plotly_chart(fig, use_container_width=True, config=PLOTLY_CONFIG, key="hw_cone_3d")


# ═══════════════════════════════════════════════════════════════════════════════
# Row 4 helper: Degradation Level Display
# ═══════════════════════════════════════════════════════════════════════════════

def _render_degradation_display(
    health: Any,
    history: List[Dict[str, Any]],
    t,
) -> None:
    """Show the current degradation level, reason, thresholds, and trend."""
    dlevel = getattr(health, "degradation_level", None) if health else None
    if dlevel is not None:
        level_name = dlevel.name if hasattr(dlevel, "name") else str(dlevel)
    else:
        level_name = "UNKNOWN"

    reason = getattr(health, "degradation_reason", "") if health else ""

    # Colour-code by severity
    if level_name == "NORMAL":
        level_color = COLORS["success"]
        level_bg = "rgba(0,255,136,0.08)"
        level_icon = "✅"
    elif "1" in level_name or level_name == "LEVEL_1":
        level_color = COLORS["warning"]
        level_bg = "rgba(255,170,0,0.08)"
        level_icon = "⚠️"
    elif "2" in level_name:
        level_color = "#ff8c00"
        level_bg = "rgba(255,140,0,0.08)"
        level_icon = "❗"
    else:
        level_color = COLORS["danger"]
        level_bg = "rgba(255,51,68,0.08)"
        level_icon = "\U0001f6a8"

    # ── Degradation status card ──
    d1, d2 = st.columns([2, 3])
    with d1:
        st.markdown(f"""
        <div class="neon-metric-card" style="border-color:{level_color}40;">
            <div style="font-size:1.1rem;color:{level_color};font-weight:700;">
                {level_icon} {level_name}
            </div>
            <div style="font-size:0.7rem;color:#7a8ba8;margin-top:6px;">
                {reason if reason else t("common.na")}
            </div>
        </div>
        """, unsafe_allow_html=True)

    with d2:
        # Degradation history sparkline (last 30 entries, encoded as numeric)
        deg_history = []
        if history:
            for h in history[-30:]:
                dl = str(h.get("degradation_level", "NORMAL"))
                if dl == "NORMAL":
                    deg_history.append(0)
                elif "1" in dl:
                    deg_history.append(1)
                elif "2" in dl:
                    deg_history.append(2)
                else:
                    deg_history.append(3)
        if deg_history:
            sparkline_chart(
                deg_history, height=50,
                color=level_color,
                show_dots=len(deg_history) <= 15,
                key="hw_degrad_spark",
            )
            st.caption(t("hardware.degradation_level") + " (30-tick trend)")
        else:
            st.caption(t("common.no_data"))

    # ── Threshold cards ──
    st.markdown('<div style="margin-top:12px;"></div>', unsafe_allow_html=True)
    t1, t2, t3 = st.columns(3)

    # GPU threshold
    with t1:
        gpu_pct = (getattr(health, "gpu_memory_ratio", 0) or 0) * 100 if health else 0
        gpu_exceeded = gpu_pct > 90
        neon_metric_card(
            t("hardware.threshold_gpu"),
            f"{gpu_pct:.1f}%",
            icon="\U0001f3ae",
            delta="⚠ EXCEEDED" if gpu_exceeded else "✅ OK",
            delta_good=not gpu_exceeded,
            neon_color="red" if gpu_exceeded else "green",
            key="hw_thresh_gpu",
        )

    # RAM threshold
    with t2:
        ram_pct = (getattr(health, "memory_ratio", 0) or 0) * 100 if health else 0
        ram_exceeded = ram_pct > 95
        neon_metric_card(
            t("hardware.threshold_ram"),
            f"{ram_pct:.1f}%",
            icon="\U0001f9e0",
            delta="⚠ EXCEEDED" if ram_exceeded else "✅ OK",
            delta_good=not ram_exceeded,
            neon_color="red" if ram_exceeded else "green",
            key="hw_thresh_ram",
        )

    # Disk threshold
    with t3:
        disk_free = getattr(health, "disk_free_gb", 100) or 100 if health else 100
        disk_exceeded = disk_free < 5.0
        neon_metric_card(
            t("hardware.threshold_disk"),
            f"{disk_free:.1f} GB",
            icon="\U0001f4be",
            delta="⚠ LOW" if disk_exceeded else "✅ OK",
            delta_good=not disk_exceeded,
            neon_color="red" if disk_exceeded else "green",
            key="hw_thresh_disk",
        )

    # ── GPU unavailable note ──
    if health is not None and not getattr(health, "gpu_available", False):
        info_bar(t("hardware.gpu_unavailable"), "info")


# ═══════════════════════════════════════════════════════════════════════════════
# Row 6 helpers: Per-resource detail tabs
# ═══════════════════════════════════════════════════════════════════════════════

def _render_cpu_detail(health: Any, history: list, t) -> None:
    """CPU tab: per-core utilization, frequency, temperature."""
    if health is None:
        info_bar(t("common.no_data"), "info")
        return

    # Per-core utilization heatmap
    import plotly.graph_objects as go
    per_core = getattr(health, "cpu_per_core", None)
    if per_core and len(per_core) > 0:
        # Render as horizontal bar chart of per-core usage
        fig = go.Figure(data=[go.Bar(
            x=list(per_core),
            y=[f"Core {i}" for i in range(len(per_core))],
            orientation="h",
            marker=dict(
                color=list(per_core),
                colorscale="Turbo",
                showscale=True,
                colorbar=dict(title="%", tickfont=dict(color="#7a8ba8")),
            ),
            text=[f"{v:.1f}%" for v in per_core],
            textposition="outside",
            textfont=dict(color="#e0e0ff", size=10),
        )])
        from dashboard.theme import configure_plotly_dark
        configure_plotly_dark(fig)
        fig.update_layout(
            height=max(160, 25 * len(per_core)),
            title={"text": t("hardware.cpu_per_core"), "font": {"color": "#e0e0ff", "size": 13}},
            xaxis=dict(range=[0, 105], title="%"),
        )
        st.plotly_chart(fig, use_container_width=True, key="hw_cpu_cores")
    else:
        # Show simple metrics
        c1, c2, c3 = st.columns(3)
        with c1:
            st.metric(t("hardware.cpu_util"), f"{health.cpu_percent:.1f}%")
        with c2:
            freq = getattr(health, "cpu_freq_mhz", None)
            st.metric("Frequency", f"{freq:.0f} MHz" if freq else "—")
        with c3:
            temp = getattr(health, "cpu_temp_c", getattr(health, "temperature", None))
            st.metric(t("hardware.temperature"), f"{temp:.0f}°C" if temp else "—")


def _render_gpu_detail(health: Any, history: list, t) -> None:
    """GPU tab: memory, utilization, temperature."""
    if health is None:
        info_bar(t("common.no_data"), "info")
        return

    if not getattr(health, "gpu_available", False):
        info_bar(t("hardware.gpu_unavailable"), "info")
        return

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        gpu_mem = getattr(health, "gpu_memory_ratio", 0) * 100
        st.metric(t("hardware.gpu_mem_usage"), f"{gpu_mem:.1f}%")
    with c2:
        gpu_util = getattr(health, "gpu_utilization", None)
        st.metric("GPU Util", f"{gpu_util:.1f}%" if gpu_util else "—")
    with c3:
        gpu_temp = getattr(health, "gpu_temp_c", getattr(health, "gpu_temperature", None))
        st.metric(t("hardware.temperature"), f"{gpu_temp:.0f}°C" if gpu_temp else "—")
    with c4:
        gpu_count = getattr(health, "gpu_count", 1)
        st.metric("GPU Count", str(gpu_count))


def _render_ram_detail(health: Any, history: list, t) -> None:
    """RAM tab: usage breakdown, swap."""
    if health is None:
        info_bar(t("common.no_data"), "info")
        return

    mem_pct = getattr(health, "memory_ratio", 0) * 100
    total_gb = getattr(health, "memory_total_gb", 0)
    used_gb = total_gb * getattr(health, "memory_ratio", 0) if total_gb > 0 else 0

    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric(t("hardware.ram_usage"), f"{mem_pct:.1f}%")
    with c2:
        st.metric("Total RAM", f"{total_gb:.1f} GB" if total_gb > 0 else "—")
    with c3:
        st.metric("Used RAM", f"{used_gb:.1f} GB" if used_gb > 0 else "—")

    # RAM history sparkline
    if history and len(history) >= 2:
        ram_vals = [h.get("memory_ratio", 0) * 100 for h in history]
        sparkline_chart(ram_vals, height=60, color=COLORS["cyan"], key="hw_ram_tab_spark")


def _render_disk_detail(health: Any, history: list, t) -> None:
    """Disk tab: usage, free space, I/O if available."""
    if health is None:
        info_bar(t("common.no_data"), "info")
        return

    total_gb = getattr(health, "disk_total_gb", 100)
    free_gb = getattr(health, "disk_free_gb", 0)
    used_gb = max(0, total_gb - free_gb)
    pct = (used_gb / max(total_gb, 1)) * 100

    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric(t("hardware.disk_usage"), f"{pct:.1f}%")
    with c2:
        st.metric("Free Space", f"{free_gb:.1f} GB")
    with c3:
        st.metric("Total Disk", f"{total_gb:.1f} GB")

    # Network I/O if available
    net_io = getattr(health, "network_io_bytes", None)
    if net_io:
        st.caption(t("hardware.network_io"))
        st.metric("Network I/O", f"{net_io / 1024 / 1024:.1f} MB")
