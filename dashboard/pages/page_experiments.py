"""Page 4: Experiments — ablation, robustness, adaptability, common-vs-rare with 3D charts."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from dashboard.components import (
    section_header,
    info_bar,
    neon_metric_card,
    export_button,
    surface_3d_chart,
    scatter_3d_chart,
)
from dashboard.i18n import get_translator
from dashboard.theme import COLORS, configure_plotly_dark, configure_plotly_dark_3d

PLOTLY_CONFIG = {
    "displayModeBar": True,
    "displaylogo": False,
    "modeBarButtonsToRemove": ["lasso2d", "select2d", "sendDataToCloud"],
    "toImageButtonOptions": {"format": "png", "filename": "mapfm_experiment"},
}


def render(eco: Any, config: Any, dataset: Any, monitor: Any) -> None:
    """Render Experiments page with 4 tabs of 3D/comparison charts."""
    t = get_translator()

    section_header(t("experiments.title"), "🔬", "cyan")

    if eco is None:
        info_bar("Ecosystem not initialised — cannot run experiments.", "error")
        return

    tab1, tab2, tab3, tab4 = st.tabs([
        f"🔬 {t('experiments.ablation_tab')}",
        f"🌊 {t('experiments.robustness_tab')}",
        f"📈 {t('experiments.adaptability_tab')}",
        f"⚖️ {t('experiments.common_rare_tab')}",
    ])

    # ── Tab 1: Ablation ──────────────────────────────────────────────
    with tab1:
        _render_ablation_tab(eco, config, t)

    # ── Tab 2: Robustness ────────────────────────────────────────────
    with tab2:
        _render_robustness_tab(eco, config, t)

    # ── Tab 3: Adaptability ──────────────────────────────────────────
    with tab3:
        _render_adaptability_tab(eco, config, t)

    # ── Tab 4: Common vs Rare ────────────────────────────────────────
    with tab4:
        _render_common_rare_tab(eco, config, t)

    # ── Bottom: Run All + Export all results ──────────────────────────
    st.markdown("---")
    section_header(t("experiments.run_all"), "🚀", "green")
    col_runall, col_export = st.columns([1, 2])
    with col_runall:
        if st.button(f"🚀 {t('experiments.run_all')}", use_container_width=True, key="btn_run_all",
                     type="primary"):
            with st.spinner(t("experiments.running_hint")):
                errors = []
                for exp_name, run_fn in [
                    ("ablation", lambda: eco.run_ablation_experiments(
                        max_samples=getattr(config, "ablation_sample_count", 36))),
                    ("robustness", lambda: eco.run_robustness_experiments(
                        max_samples=getattr(config, "robustness_sample_count", 36))),
                    ("adaptability", lambda: eco.run_data_scale_adaptability(
                        max_test_samples=getattr(config, "adaptability_max_test_samples", 36))),
                    ("common_rare", lambda: eco.run_common_rare_analysis(
                        max_samples=getattr(config, "common_rare_sample_count", 72))),
                ]:
                    try:
                        run_fn()
                        st.caption(f"✅ {exp_name} complete")
                    except Exception as exc:
                        errors.append(f"{exp_name}: {exc}")
                        st.caption(f"❌ {exp_name}: {exc}")
                if errors:
                    info_bar(f"{len(errors)} experiment(s) failed: {'; '.join(errors)}", "warning")
                else:
                    info_bar("All 4 experiments completed successfully!", "success")
    with col_export:
        all_results = {
            "ablation": eco.ablation_results,
            "robustness": eco.robustness_results,
            "adaptability": eco.adaptability_results,
            "common_vs_rare": eco.common_rare_results,
        }
        export_button(all_results, "experiment_results.json", t("experiments.export_results"), key="exp_export_all")


# ═══════════════════════════════════════════════════════════════════════════════
# Tab 1: Ablation Study
# ═══════════════════════════════════════════════════════════════════════════════

def _render_ablation_tab(eco, config, t) -> None:
    """3D scatter-like bar chart + 2D grouped bar chart for ablation results."""

    c_btn, c_info = st.columns([2, 5])
    with c_btn:
        if st.button(f"▶ {t('experiments.run_ablation')}", use_container_width=True, key="btn_ablation"):
            with st.spinner(t("experiments.running_hint")):
                try:
                    eco.run_ablation_experiments(max_samples=getattr(config, "ablation_sample_count", 36))
                except Exception as exc:
                    info_bar(f"{t('common.failed')}: {exc}", "error")

    results = getattr(eco, "ablation_results", None) or {}

    with c_info:
        if results:
            info_bar(f"{len(results)} {t('experiments.config')}(s) evaluated", "success")
        else:
            info_bar(t("experiments.not_executed"), "info")

    if not results:
        return

    # ── Metrics cards ──
    _render_ablation_summary_cards(results, t)

    # ── 3D scatter-like bar chart ──
    _render_ablation_3d_bars(results, t)

    # ── 2D grouped bar chart (fallback / complementary) ──
    _render_ablation_2d_bars(results, t)


def _render_ablation_summary_cards(results, t) -> None:
    """Row of metric cards summarising key ablation findings."""
    best_config = max(results, key=lambda k: results[k].get("final_accuracy", 0))
    best_acc = results[best_config].get("final_accuracy", 0)
    best_f1 = results[best_config].get("macro_f1", 0)

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        neon_metric_card(
            t("experiments.config"), best_config.replace("_", " ").title(),
            icon="🏆", neon_color="cyan", key="abl_best_cfg",
        )
    with col2:
        neon_metric_card(
            t("experiments.accuracy"), f"{best_acc:.3f}",
            icon="🎯", neon_color="green", key="abl_best_acc",
        )
    with col3:
        neon_metric_card(
            t("experiments.f1_score"), f"{best_f1:.3f}",
            icon="🏅", neon_color="magenta", key="abl_best_f1",
        )
    with col4:
        min_interv = min(r.get("intervention_rate", 0) for r in results.values())
        neon_metric_card(
            "Intervention", f"{min_interv:.1%}",
            icon="🤝", neon_color="violet", key="abl_min_interv",
        )


def _render_ablation_3d_bars(results, t) -> None:
    """3D scatter-like bar chart: x=configs, y=metrics, z=values.

    Uses go.Scatter3d with vertical line segments to simulate bars.
    """
    config_names = list(results.keys())
    display_names = [
        cn.replace("full_ecosystem", "Full").replace("without_hitl", "-HITL")
           .replace("without_tfa", "-TFA").replace("without_multimodal", "-MM")
        for cn in config_names
    ]
    metric_names = [
        t("experiments.accuracy"),
        t("experiments.f1_score"),
        t("experiments.precision"),
        t("experiments.recall"),
    ]
    metric_keys = ["final_accuracy", "macro_f1", "autonomous_accuracy", "macro_f1"]

    # Build the 3D bar chart using vertical line segments
    fig = go.Figure()
    palette = ["#00f5ff", "#ff00e5", "#7c3aed", "#00ff88"]

    for xi, cn in enumerate(config_names):
        entry = results[cn]
        for yi, (mkey, mlabel) in enumerate(zip(metric_keys, metric_names)):
            val = float(entry.get(mkey, 0))
            if val <= 0:
                continue
            # Draw a vertical "bar" as 3 linked line segments for thickness illusion
            offset = 0.12
            for dx in [-offset, 0, offset]:
                fig.add_trace(go.Scatter3d(
                    x=[xi + dx, xi + dx],
                    y=[yi, yi],
                    z=[0, val],
                    mode="lines",
                    line=dict(width=4 if dx == 0 else 1.5, color=palette[yi % len(palette)]),
                    opacity=0.9 if dx == 0 else 0.4,
                    showlegend=False,
                    hoverinfo="skip",
                ))
            # Marker at top
            fig.add_trace(go.Scatter3d(
                x=[xi], y=[yi], z=[val],
                mode="markers+text",
                marker=dict(size=6, color=palette[yi % len(palette)], opacity=0.95,
                            line=dict(width=1, color="rgba(255,255,255,0.2)")),
                text=[f"{val:.3f}"],
                textposition="top center",
                textfont=dict(size=9, color="#e0e0ff"),
                hovertext=[f"<b>{display_names[xi]}</b><br>{mlabel}: {val:.3f}"],
                hoverinfo="text",
                showlegend=False,
            ))

    configure_plotly_dark_3d(fig)
    fig.update_layout(
        title={"text": t("experiments.ablation_3d"), "font": {"color": "#e0e0ff", "size": 15}},
        height=500,
        scene=dict(
            xaxis=dict(
                tickmode="array",
                tickvals=list(range(len(config_names))),
                ticktext=display_names,
                title={"text": t("experiments.config"), "font": {"color": "#e0e0ff", "size": 11}},
            ),
            yaxis=dict(
                tickmode="array",
                tickvals=list(range(len(metric_names))),
                ticktext=metric_names,
                title={"text": "Metric", "font": {"color": "#e0e0ff", "size": 11}},
            ),
            zaxis=dict(
                title={"text": "Value", "font": {"color": "#e0e0ff", "size": 11}},
                range=[0, 1.05],
            ),
            camera=dict(eye=dict(x=1.8, y=-2.0, z=1.2)),
        ),
    )
    st.plotly_chart(fig, use_container_width=True, config=PLOTLY_CONFIG, key="abl_3d_bars")


def _render_ablation_2d_bars(results, t) -> None:
    """2D grouped bar chart as complementary view."""
    config_names = list(results.keys())
    display_names = [
        cn.replace("full_ecosystem", "Full").replace("without_hitl", "-HITL")
           .replace("without_tfa", "-TFA").replace("without_multimodal", "-MM")
        for cn in config_names
    ]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        name=t("experiments.accuracy"),
        x=display_names,
        y=[results[cn].get("final_accuracy", 0) for cn in config_names],
        marker_color="#00f5ff",
        marker_line=dict(width=0),
        text=[f"{results[cn].get('final_accuracy', 0):.3f}" for cn in config_names],
        textposition="outside",
        textfont=dict(color="#e0e0ff", size=10),
    ))
    fig.add_trace(go.Bar(
        name=t("experiments.f1_score"),
        x=display_names,
        y=[results[cn].get("macro_f1", 0) for cn in config_names],
        marker_color="#ff00e5",
        marker_line=dict(width=0),
        text=[f"{results[cn].get('macro_f1', 0):.3f}" for cn in config_names],
        textposition="outside",
        textfont=dict(color="#e0e0ff", size=10),
    ))
    fig.add_trace(go.Bar(
        name="Autonomous Acc",
        x=display_names,
        y=[results[cn].get("autonomous_accuracy", 0) for cn in config_names],
        marker_color="#7c3aed",
        marker_line=dict(width=0),
        text=[f"{results[cn].get('autonomous_accuracy', 0):.3f}" for cn in config_names],
        textposition="outside",
        textfont=dict(color="#e0e0ff", size=10),
    ))

    configure_plotly_dark(fig)
    fig.update_layout(
        title={"text": "Ablation — Grouped Bar Comparison", "font": {"color": "#e0e0ff", "size": 14}},
        height=420,
        barmode="group",
        bargap=0.2, bargroupgap=0.08,
        yaxis=dict(range=[0, 1.1], tickformat=".2f"),
    )
    st.plotly_chart(fig, use_container_width=True, config=PLOTLY_CONFIG, key="abl_2d_bars")


# ═══════════════════════════════════════════════════════════════════════════════
# Tab 2: Robustness
# ═══════════════════════════════════════════════════════════════════════════════

def _render_robustness_tab(eco, config, t) -> None:
    """3D surface or 2D line chart for robustness across noise levels."""

    c_btn, c_info = st.columns([2, 5])
    with c_btn:
        if st.button(f"▶ {t('experiments.run_robustness')}", use_container_width=True, key="btn_robustness"):
            with st.spinner(t("experiments.running_hint")):
                try:
                    eco.run_robustness_experiments(max_samples=getattr(config, "robustness_sample_count", 36))
                except Exception as exc:
                    info_bar(f"{t('common.failed')}: {exc}", "error")

    results = getattr(eco, "robustness_results", None) or {}

    with c_info:
        if results:
            info_bar(f"{len(results)} {t('experiments.noise_level')}(s) tested", "success")
        else:
            info_bar(t("experiments.not_executed"), "info")

    if not results:
        return

    # Compute noise keys (sorted by noise level)
    noise_keys = sorted(results.keys(), key=lambda k: float(k.replace("noise_", "").replace("pct", "")) / 100)

    # Summary cards
    _render_robustness_summary_cards(results, noise_keys, t)

    # Determine if we can render a meaningful 3D surface
    # We have: noise levels × metrics. Treat metric types as the "data_scale" axis.
    metric_labels = ["Accuracy", "F1 Score", "Autonomous Acc", "Intervention"]
    metric_fields = ["final_accuracy", "macro_f1", "autonomous_accuracy", "intervention_rate"]

    if len(noise_keys) >= 2:
        _render_robustness_3d_surface(results, noise_keys, metric_labels, metric_fields, t)
    else:
        info_bar(t("common.insufficient_data"), "warning")

    # 2D line chart as always-available fallback
    _render_robustness_2d_line(results, noise_keys, t)


def _render_robustness_summary_cards(results, noise_keys, t) -> None:
    """Summary metric cards for robustness results."""
    worst_noise = max(results, key=lambda k: abs(1.0 - results[k].get("final_accuracy", 0)))
    best_noise = min(results, key=lambda k: abs(1.0 - results[k].get("final_accuracy", 0)))

    cols = st.columns(4)
    with cols[0]:
        neon_metric_card(
            "Best @ Noise",
            best_noise.replace("noise_", "").replace("pct", "%"),
            icon="🏆", neon_color="green", key="rob_best_noise",
        )
    with cols[1]:
        neon_metric_card(
            t("experiments.accuracy"),
            f"{results[best_noise].get('final_accuracy', 0):.3f}",
            icon="🎯", neon_color="cyan", key="rob_best_acc",
        )
    with cols[2]:
        drop = results[best_noise].get("final_accuracy", 0) - results[worst_noise].get("final_accuracy", 0)
        neon_metric_card(
            "Accuracy Drop",
            f"{drop:.3f}",
            icon="📉",
            delta=f"at {worst_noise.replace('noise_', '').replace('pct', '%')}",
            neon_color="amber", key="rob_drop",
        )
    with cols[3]:
        neon_metric_card(
            t("experiments.samples"),
            str(results[noise_keys[0] if noise_keys else best_noise].get("samples", "?")),
            icon="🧪", neon_color="violet", key="rob_samples",
        )


def _render_robustness_3d_surface(results, noise_keys, metric_labels, metric_fields, t) -> None:
    """3D surface chart: x=noise level, y=metric type, z=value."""
    noise_values = [float(k.replace("noise_", "").replace("pct", "")) / 100 for k in noise_keys]
    # Build a 2D grid for the surface
    z_vals = np.zeros((len(metric_labels), len(noise_values)))
    for yi, field in enumerate(metric_fields):
        for xi, nk in enumerate(noise_keys):
            z_vals[yi, xi] = float(results[nk].get(field, 0))

    # Surface needs x, y, z as 2D arrays
    x_grid, y_grid = np.meshgrid(noise_values, np.arange(len(metric_labels)))
    fig = go.Figure(data=[go.Surface(
        x=x_grid, y=y_grid, z=z_vals,
        colorscale="Turbo",
        contours={"z": {"show": True, "usecolormap": True, "project": {"z": True}}},
        colorbar={"title": {"text": "Value", "font": {"color": "#e0e0ff"}},
                  "tickfont": {"color": "#7a8ba8"}},
        hovertext=[[f"Noise: {nv:.0%}<br>{metric_labels[yi]}: {z_vals[yi, xi]:.3f}"
                    for xi, nv in enumerate(noise_values)]
                   for yi in range(len(metric_labels))],
        hoverinfo="text",
    )])
    configure_plotly_dark_3d(fig)
    fig.update_layout(
        title={"text": t("experiments.landscape_3d"), "font": {"color": "#e0e0ff", "size": 15}},
        height=480,
        scene=dict(
            xaxis=dict(title={"text": t("experiments.noise_level"), "font": {"color": "#e0e0ff", "size": 11}},
                       tickformat=".0%"),
            yaxis=dict(tickmode="array", tickvals=list(range(len(metric_labels))),
                       ticktext=metric_labels,
                       title={"text": "Metric", "font": {"color": "#e0e0ff", "size": 11}}),
            zaxis=dict(title={"text": "Value", "font": {"color": "#e0e0ff", "size": 11}}, range=[0, 1.05]),
            camera=dict(eye=dict(x=1.6, y=-1.6, z=1.1)),
        ),
    )
    st.plotly_chart(fig, use_container_width=True, config=PLOTLY_CONFIG, key="rob_3d_surface")


def _render_robustness_2d_line(results, noise_keys, t) -> None:
    """2D line chart: noise level vs accuracy/F1."""
    noise_labels = [k.replace("noise_", "").replace("pct", "% Noise") for k in noise_keys]

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=noise_labels, y=[results[nk].get("final_accuracy", 0) for nk in noise_keys],
        mode="lines+markers",
        name=t("experiments.accuracy"),
        line=dict(width=3, color="#00f5ff"),
        marker=dict(size=10, color="#00f5ff", line=dict(width=1, color="rgba(255,255,255,0.3)")),
        text=[f"{results[nk].get('final_accuracy', 0):.3f}" for nk in noise_keys],
        textposition="top center",
        textfont=dict(color="#e0e0ff", size=10),
    ))
    fig.add_trace(go.Scatter(
        x=noise_labels, y=[results[nk].get("macro_f1", 0) for nk in noise_keys],
        mode="lines+markers",
        name=t("experiments.f1_score"),
        line=dict(width=3, color="#ff00e5"),
        marker=dict(size=10, color="#ff00e5", line=dict(width=1, color="rgba(255,255,255,0.3)")),
        text=[f"{results[nk].get('macro_f1', 0):.3f}" for nk in noise_keys],
        textposition="top center",
        textfont=dict(color="#e0e0ff", size=10),
    ))
    fig.add_trace(go.Scatter(
        x=noise_labels, y=[results[nk].get("autonomous_accuracy", 0) for nk in noise_keys],
        mode="lines+markers",
        name="Autonomous Acc",
        line=dict(width=2, color="#7c3aed", dash="dot"),
        marker=dict(size=8, color="#7c3aed"),
        text=[f"{results[nk].get('autonomous_accuracy', 0):.3f}" for nk in noise_keys],
        textposition="bottom center",
        textfont=dict(color="#7a8ba8", size=9),
    ))

    configure_plotly_dark(fig)
    fig.update_layout(
        title={"text": "Robustness — Accuracy vs Noise Level", "font": {"color": "#e0e0ff", "size": 14}},
        height=400,
        yaxis=dict(range=[0, 1.1], tickformat=".2f"),
        xaxis=dict(title={"text": t("experiments.noise_level"), "font": {"color": "#7a8ba8"}}),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    st.plotly_chart(fig, use_container_width=True, config=PLOTLY_CONFIG, key="rob_2d_line")


# ═══════════════════════════════════════════════════════════════════════════════
# Tab 3: Adaptability
# ═══════════════════════════════════════════════════════════════════════════════

def _render_adaptability_tab(eco, config, t) -> None:
    """2D line chart: accuracy vs data scale (20%/50%/80%/100%)."""

    c_btn, c_info = st.columns([2, 5])
    with c_btn:
        if st.button(f"▶ {t('experiments.run_adaptability')}", use_container_width=True, key="btn_adaptability"):
            with st.spinner(t("experiments.running_hint")):
                try:
                    eco.run_data_scale_adaptability(
                        max_test_samples=getattr(config, "adaptability_max_test_samples", 36),
                    )
                except Exception as exc:
                    info_bar(f"{t('common.failed')}: {exc}", "error")

    results = getattr(eco, "adaptability_results", None) or {}

    with c_info:
        if results:
            info_bar(f"{len(results)} {t('experiments.data_scale')}(s) tested", "success")
        else:
            info_bar(t("experiments.not_executed"), "info")

    if not results:
        return

    # Summary cards
    _render_adaptability_summary_cards(results, t)

    # 2D line chart
    _render_adaptability_2d_line(results, t)

    # Data table
    _render_adaptability_table(results, t)


def _render_adaptability_summary_cards(results, t) -> None:
    """Summary metric cards for adaptability."""
    scale_keys = sorted(results.keys(), key=lambda k: int(k.replace("train_", "").replace("pct", "")))
    best_key = max(results, key=lambda k: results[k].get("accuracy", 0))
    worst_key = min(results, key=lambda k: results[k].get("accuracy", 0))

    cols = st.columns(4)
    with cols[0]:
        neon_metric_card(
            "Best Scale",
            best_key.replace("train_", "").replace("pct", "%"),
            icon="🏆", neon_color="green", key="adp_best_scale",
        )
    with cols[1]:
        neon_metric_card(
            t("experiments.accuracy"),
            f"{results[best_key].get('accuracy', 0):.3f}",
            icon="🎯", neon_color="cyan", key="adp_best_acc",
        )
    with cols[2]:
        gap = results[best_key].get("accuracy", 0) - results[worst_key].get("accuracy", 0)
        neon_metric_card(
            "Scale Gap",
            f"{gap:.3f}",
            icon="📏",
            delta=f"100% → 20%",
            neon_color="amber", key="adp_gap",
        )
    with cols[3]:
        full_train = results.get("train_100pct", {})
        neon_metric_card(
            t("experiments.samples"),
            str(full_train.get("train_samples", "?")),
            icon="📦", neon_color="violet", key="adp_samples",
        )


def _render_adaptability_2d_line(results, t) -> None:
    """2D line chart: accuracy and F1 vs data scale percentage."""
    scale_keys = sorted(results.keys(), key=lambda k: int(k.replace("train_", "").replace("pct", "")))
    scale_pcts = [int(k.replace("train_", "").replace("pct", "")) for k in scale_keys]
    scale_labels = [f"{p}%" for p in scale_pcts]

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=scale_labels,
        y=[results[k].get("accuracy", 0) for k in scale_keys],
        mode="lines+markers",
        name=t("experiments.accuracy"),
        line=dict(width=3, color="#00f5ff"),
        marker=dict(size=12, color="#00f5ff", line=dict(width=1.5, color="rgba(255,255,255,0.3)")),
        text=[f"{results[k].get('accuracy', 0):.3f}" for k in scale_keys],
        textposition="top center",
        textfont=dict(color="#e0e0ff", size=11),
    ))
    fig.add_trace(go.Scatter(
        x=scale_labels,
        y=[results[k].get("macro_f1", 0) for k in scale_keys],
        mode="lines+markers",
        name=t("experiments.f1_score"),
        line=dict(width=3, color="#ff00e5"),
        marker=dict(size=12, color="#ff00e5", line=dict(width=1.5, color="rgba(255,255,255,0.3)")),
        text=[f"{results[k].get('macro_f1', 0):.3f}" for k in scale_keys],
        textposition="bottom center",
        textfont=dict(color="#e0e0ff", size=11),
    ))

    configure_plotly_dark(fig)
    fig.update_layout(
        title={"text": "Adaptability — Accuracy vs Data Scale", "font": {"color": "#e0e0ff", "size": 14}},
        height=420,
        yaxis=dict(range=[0, 1.1], tickformat=".2f",
                   title={"text": "Score", "font": {"color": "#7a8ba8"}}),
        xaxis=dict(title={"text": t("experiments.data_scale"), "font": {"color": "#7a8ba8"}}),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    st.plotly_chart(fig, use_container_width=True, config=PLOTLY_CONFIG, key="adp_2d_line")


def _render_adaptability_table(results, t) -> None:
    """Data table of adaptability results."""
    scale_keys = sorted(results.keys(), key=lambda k: int(k.replace("train_", "").replace("pct", "")))
    rows = []
    for k in scale_keys:
        pct = k.replace("train_", "").replace("pct", "")
        entry = results[k]
        rows.append({
            t("experiments.data_scale"): f"{pct}%",
            t("experiments.samples"): int(entry.get("train_samples", 0)),
            t("experiments.accuracy"): round(float(entry.get("accuracy", 0)), 4),
            t("experiments.f1_score"): round(float(entry.get("macro_f1", 0)), 4),
            "Avg Confidence": round(float(entry.get("avg_confidence", 0)), 4),
        })
    df = pd.DataFrame(rows)
    st.dataframe(
        df.style.set_properties(**{
            "background-color": COLORS["bg_card"],
            "color": COLORS["text_primary"],
            "border-color": "rgba(0,245,255,0.1)",
        }),
        use_container_width=True, height=200, key="adp_table",
    )


# ═══════════════════════════════════════════════════════════════════════════════
# Tab 4: Common vs Rare
# ═══════════════════════════════════════════════════════════════════════════════

def _render_common_rare_tab(eco, config, t) -> None:
    """Side-by-side F1 bar chart comparing common vs rare disease classes."""

    c_btn, c_info = st.columns([2, 5])
    with c_btn:
        if st.button(f"▶ {t('experiments.run_common_rare')}", use_container_width=True, key="btn_common_rare"):
            with st.spinner(t("experiments.running_hint")):
                try:
                    eco.run_common_rare_analysis(max_samples=getattr(config, "common_rare_sample_count", 72))
                except Exception as exc:
                    info_bar(f"{t('common.failed')}: {exc}", "error")

    results = getattr(eco, "common_rare_results", None) or {}

    with c_info:
        if results:
            info_bar(f"Common={len(results.get('common_labels', []))} "
                     f"Rare={len(results.get('rare_labels', []))} classes", "success")
        else:
            info_bar(t("experiments.not_executed"), "info")

    if not results:
        return

    # ── Summary cards ──
    common_f1 = float(results.get("common_f1", 0))
    rare_f1 = float(results.get("rare_f1", 0))
    drop_rate = float(results.get("drop_rate", 0))

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        neon_metric_card(
            "Common F1", f"{common_f1:.3f}",
            icon="🟢", neon_color="green", key="cr_common_f1",
        )
    with col2:
        neon_metric_card(
            "Rare F1", f"{rare_f1:.3f}",
            icon="🟡", neon_color="amber" if rare_f1 < common_f1 else "green", key="cr_rare_f1",
        )
    with col3:
        neon_metric_card(
            t("experiments.drop_rate"), f"{drop_rate:.1%}",
            icon="📉",
            delta="F1 gap ratio" if drop_rate > 0.1 else "Acceptable",
            delta_good=drop_rate <= 0.1,
            neon_color="amber" if drop_rate > 0.1 else "green", key="cr_drop",
        )
    with col4:
        neon_metric_card(
            t("experiments.samples"), "",
            icon="🧬",
            delta=f"C: {len(results.get('common_labels', []))} / R: {len(results.get('rare_labels', []))}",
            neon_color="violet", key="cr_labels",
        )

    # ── Side-by-side F1 bar chart ──
    _render_common_rare_f1_bar(common_f1, rare_f1, t)

    # ── Label details ──
    _render_common_rare_labels(results, t)


def _render_common_rare_f1_bar(common_f1, rare_f1, t) -> None:
    """Side-by-side group bar chart for common vs rare F1."""
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=["Common"], y=[common_f1],
        name="Common Classes",
        marker_color="#00ff88",
        marker_line=dict(width=0),
        text=[f"{common_f1:.3f}"],
        textposition="outside",
        textfont=dict(color="#e0e0ff", size=18),
        width=0.4,
    ))
    fig.add_trace(go.Bar(
        x=["Rare"], y=[rare_f1],
        name="Rare Classes",
        marker_color="#ffaa00",
        marker_line=dict(width=0),
        text=[f"{rare_f1:.3f}"],
        textposition="outside",
        textfont=dict(color="#e0e0ff", size=18),
        width=0.4,
    ))

    max_val = max(common_f1, rare_f1, 0.1) * 1.3
    configure_plotly_dark(fig)
    fig.update_layout(
        title={"text": "Common vs Rare — F1 Score Comparison", "font": {"color": "#e0e0ff", "size": 14}},
        height=380,
        barmode="group",
        bargap=0.4,
        yaxis=dict(range=[0, max_val], tickformat=".2f",
                   title={"text": t("experiments.f1_score"), "font": {"color": "#7a8ba8"}}),
        showlegend=False,
    )
    st.plotly_chart(fig, use_container_width=True, config=PLOTLY_CONFIG, key="cr_f1_bar")


def _render_common_rare_labels(results, t) -> None:
    """Show common and rare label lists with chip-style display."""
    common_labels = results.get("common_labels", [])
    rare_labels = results.get("rare_labels", [])

    col_left, col_right = st.columns(2)
    with col_left:
        st.markdown(
            f'<div class="info-box success">'
            f'<b>🟢 Common Classes ({len(common_labels)})</b><br>'
            f'<span style="font-size:0.8rem;color:#7a8ba8;">'
            f'{", ".join(common_labels) if common_labels else "N/A"}'
            f'</span></div>',
            unsafe_allow_html=True,
        )
    with col_right:
        st.markdown(
            f'<div class="info-box warning">'
            f'<b>🟡 Rare Classes ({len(rare_labels)})</b><br>'
            f'<span style="font-size:0.8rem;color:#7a8ba8;">'
            f'{", ".join(rare_labels) if rare_labels else "N/A"}'
            f'</span></div>',
            unsafe_allow_html=True,
        )
