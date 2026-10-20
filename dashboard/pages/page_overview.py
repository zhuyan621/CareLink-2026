"""Page 1: System Overview — health, dataset, 3D embeddings, experiments, resources."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from dashboard.components import (
    neon_metric_card, gauge_chart, radial_gauge, section_header,
    info_bar, scatter_3d_chart, mesh_3d_chart,
)
from dashboard.i18n import get_translator
from dashboard.theme import configure_plotly_dark


def render(eco: Any, config: Any, dataset: Any, monitor: Any) -> None:
    """Render System Overview page."""
    t = get_translator()

    # ── Health check ──
    try:
        health = monitor.check() if monitor else None
    except Exception:
        health = None

    # ═══════════════════════════════════════════════════════════════════
    # Row 1: 5 neon metric cards
    # ═══════════════════════════════════════════════════════════════════
    c1, c2, c3, c4, c5 = st.columns(5)

    with c1:
        ollama_ok = health.ollama_healthy if health else False
        neon_metric_card(
            t("overview.ollama"),
            "🟢 Online" if ollama_ok else "🔴 Offline",
            icon="🔌",
            delta=f"{health.ollama_latency_ms:.0f}ms" if health and ollama_ok else "",
            neon_color="green" if ollama_ok else "red",
            key="ov_ollama",
        )
    with c2:
        medtsllm_ok = health.medtsllm_loaded if health else False
        neon_metric_card(
            t("overview.medtsllm"),
            "🟢 Validated" if medtsllm_ok else "🟡 Unavailable",
            icon="🧬",
            neon_color="green" if medtsllm_ok else "amber",
            key="ov_medtsllm",
        )
    with c3:
        gpu_ok = health.gpu_available if health else False
        neon_metric_card(
            t("overview.gpu"),
            "🟢 Available" if gpu_ok else "⚪ N/A",
            icon="🎮",
            delta=f"{health.gpu_count} GPU(s)" if health and gpu_ok else "",
            neon_color="green" if gpu_ok else "cyan",
            key="ov_gpu",
        )
    with c4:
        level = health.degradation_level.name if health else "UNKNOWN"
        neon_metric_card(
            t("overview.degradation"),
            level,
            icon="⚠️",
            neon_color="green" if level == "NORMAL" else "amber" if "1" in level or "2" in level else "red",
            key="ov_degrad",
        )
    with c5:
        docs = len(dataset) if dataset is not None else 0
        neon_metric_card(
            t("overview.kb_size"),
            str(docs),
            icon="📚",
            delta=f"{dataset['area'].nunique()} actual classes" if dataset is not None else "",
            neon_color="cyan",
            key="ov_kb",
        )

    # ═══════════════════════════════════════════════════════════════════
    # Row 2: 3D Disease Embedding Space (2/3 width) + Class detail (1/3)
    # ═══════════════════════════════════════════════════════════════════
    section_header(t("overview.embeddings_3d"), "🌌", "cyan")
    if dataset is not None and eco is not None:
        try:
            col_3d, col_detail = st.columns([2, 1])
            with col_3d:
                _render_disease_3d_scatter(eco, dataset, t)
            with col_detail:
                _render_class_detail_panel(dataset, eco, t)
        except Exception:
            info_bar(t("overview.monitor_unavailable"), "warning")
    else:
        info_bar(t("overview.eco_degraded"), "warning")

    # ═══════════════════════════════════════════════════════════════════
    # Row 3: Dataset statistics
    # ═══════════════════════════════════════════════════════════════════
    section_header(t("overview.dataset_stats"), "📈", "cyan")
    if dataset is not None and eco is not None:
        c_left, c_right = st.columns([3, 2])
        with c_left:
            # Train/Test split bar
            train_n = len(eco.train_df) if hasattr(eco, 'train_df') and eco.train_df is not None else 0
            test_n = len(eco.test_df) if hasattr(eco, 'test_df') and eco.test_df is not None else 0
            fig_bar = go.Figure(data=[
                go.Bar(name=t("overview.train_samples"), x=["Samples"], y=[train_n],
                       marker_color="#00f5ff", marker_line_color="rgba(0,245,255,0.5)"),
                go.Bar(name=t("overview.test_samples"), x=["Samples"], y=[test_n],
                       marker_color="#ff00e5", marker_line_color="rgba(255,0,229,0.5)"),
            ])
            fig_bar.update_layout(barmode="group", height=300)
            configure_plotly_dark(fig_bar)
            st.plotly_chart(fig_bar, use_container_width=True, key="ov_train_test_bar")

        with c_right:
            # Class distribution pie
            area_counts = dataset["area"].value_counts()
            fig_pie = go.Figure(data=[go.Pie(
                labels=area_counts.index.tolist(),
                values=area_counts.values.tolist(),
                hole=0.45,
                marker=dict(colors=[
                    f"hsl({i*360/len(area_counts)},70%,60%)" for i in range(len(area_counts))
                ]),
                textinfo="label+percent",
                textfont=dict(size=9, color="#e0e0ff"),
            )])
            configure_plotly_dark(fig_pie)
            fig_pie.update_layout(height=300, showlegend=False)
            st.plotly_chart(fig_pie, use_container_width=True, key="ov_class_pie")
    else:
        info_bar(t("common.no_data"), "info")

    # ═══════════════════════════════════════════════════════════════════
    # Row 4: 3D System Performance Mesh
    # ═══════════════════════════════════════════════════════════════════
    section_header(t("overview.perf_mesh_3d"), "🔮", "magenta")
    if monitor and health:
        try:
            history = monitor.get_history(limit=60)
            if history and len(history) >= 5:
                x_vals = np.array([h.get("cpu_percent", 0) for h in history])
                y_vals = np.array([h.get("memory_ratio", 0) * 100 for h in history])
                z_vals = np.array([h.get("gpu_memory_ratio", 0) * 100 for h in history])
                deg_scores = np.array([
                    0 if h.get("degradation_level", "NORMAL") == "NORMAL" else
                    1 if "1" in str(h.get("degradation_level", "")) else
                    2 if "2" in str(h.get("degradation_level", "")) else 3
                    for h in history
                ])
                mesh_3d_chart(
                    x_vals, y_vals, z_vals,
                    intensity=deg_scores,
                    title="CPU % × RAM % × GPU Mem %",
                    colorscale=[[0, "#00ff88"], [0.33, "#ffaa00"], [0.66, "#ff3344"], [1, "#7c3aed"]],
                    opacity=0.7,
                    key="ov_perf_mesh",
                )
            else:
                info_bar(t("common.insufficient_data"), "info")
        except Exception:
            info_bar(t("overview.monitor_unavailable"), "warning")
    else:
        info_bar(t("overview.monitor_unavailable"), "warning")

    # ═══════════════════════════════════════════════════════════════════
    # Row 5: Experiment achievements
    # ═══════════════════════════════════════════════════════════════════
    section_header(t("overview.experiment_achievements"), "🏆", "green")
    if eco is not None:
        exps = [
            (t("overview.ablation"), eco.ablation_results, "ablation"),
            (t("overview.robustness"), eco.robustness_results, "robustness"),
            (t("overview.adaptability"), eco.adaptability_results, "adaptability"),
            (t("overview.common_rare"), eco.common_rare_results, "common_rare"),
        ]
        ec1, ec2, ec3, ec4 = st.columns(4)
        for col, (name, result, _key) in zip([ec1, ec2, ec3, ec4], exps):
            with col:
                if result and isinstance(result, dict) and len(result) > 0:
                    st.markdown(f"""
                    <div class="neon-metric-card glass-panel-hover">
                        <div style="font-size:0.75rem;color:#7a8ba8;margin-bottom:4px;">✅ {name}</div>
                        <div style="font-size:0.65rem;color:#4a5578;">{len(result)} configs tested</div>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.markdown(f"""
                    <div class="neon-metric-card" style="opacity:0.6;">
                        <div style="font-size:0.75rem;color:#4a5578;">{name}</div>
                        <div style="font-size:0.65rem;color:#4a5578;">{t('overview.not_run')}</div>
                    </div>
                    """, unsafe_allow_html=True)
    else:
        info_bar(t("overview.eco_degraded"), "warning")

    # ═══════════════════════════════════════════════════════════════════
    # Row 6: Privacy budget + Server resources
    # ═══════════════════════════════════════════════════════════════════
    col_privacy, col_resources = st.columns([1, 3])

    with col_privacy:
        section_header(t("overview.privacy_budget"), "🔐", "violet")
        noise_std = getattr(config, "secure_gradient_noise_std", 0.015) if config else 0.015
        budget_remaining = max(0, 1.0 - noise_std / 0.1)
        radial_gauge(
            budget_remaining, 1.0,
            t("overview.privacy_remaining"),
            color="#7c3aed" if budget_remaining > 0.5 else "#ffaa00" if budget_remaining > 0.2 else "#ff3344",
            key="ov_privacy_gauge",
        )

    with col_resources:
        section_header(t("overview.server_resources"), "🖥️", "cyan")
        if health:
            rc1, rc2, rc3, rc4 = st.columns(4)
            with rc1:
                gauge_chart(health.memory_ratio * 100, 100, t("overview.ram"),
                            thresholds={"warn": 80, "danger": 95}, key="ov_ram_gauge")
            with rc2:
                gauge_chart(health.cpu_percent, 100, t("overview.cpu"), key="ov_cpu_gauge")
            with rc3:
                gpu_pct = health.gpu_memory_ratio * 100 if health.gpu_available else 0
                gauge_chart(gpu_pct, 100, t("overview.gpu_mem"),
                            thresholds={"warn": 80, "danger": 95}, color="#ff00e5", key="ov_gpu_gauge")
            with rc4:
                disk_pct = (1 - health.disk_free_gb / max(health.disk_total_gb, 1)) * 100
                gauge_chart(disk_pct, 100, t("overview.disk"),
                            thresholds={"warn": 80, "danger": 95}, color="#00ff88", key="ov_disk_gauge")
        else:
            info_bar(t("overview.monitor_unavailable"), "warning")

    # ═══════════════════════════════════════════════════════════════════
    # Row 7: Quick actions
    # ═══════════════════════════════════════════════════════════════════
    section_header(t("overview.quick_actions"), "⚡", "cyan")
    a1, a2, a3, a4 = st.columns(4)
    with a1:
        if st.button(f"🔍 {t('overview.health_check')}", use_container_width=True, key="qa_health"):
            if monitor:
                try:
                    h = monitor.check()
                    ok = h.ollama_healthy
                    info_bar(
                        f"Ollama: {'OK' if ok else 'DOWN'} | "
                        f"MedTsLLM: {'Loaded' if h.medtsllm_loaded else 'Missing'} | "
                        f"Level: {h.degradation_level.name}",
                        "success" if ok else "warning",
                    )
                except Exception as exc:
                    info_bar(f"Health check failed: {exc}", "error")
            else:
                info_bar(t("overview.monitor_unavailable"), "warning")
    with a2:
        if st.button(f"🔄 {t('overview.reload_config')}", use_container_width=True, key="qa_reload"):
            st.cache_resource.clear()
            info_bar("✅ Config reloaded, ecosystem restarted.", "success")
            st.rerun()
    with a3:
        if st.button(f"📊 {t('overview.run_diagnosis')}", use_container_width=True, key="qa_diag"):
            st.session_state.current_page = "clinical_safety"
            st.rerun()
    with a4:
        if st.button(f"📋 {t('overview.view_logs')}", use_container_width=True, key="qa_logs"):
            st.session_state.current_page = "history_logs"
            st.rerun()


# ═══════════════════════════════════════════════════════════════════════════
# 3D scatter helper
# ═══════════════════════════════════════════════════════════════════════════

def _render_disease_3d_scatter(eco: Any, dataset: Any, t) -> None:
    """Render 3D disease embedding scatter using PCA on class centroids."""
    classes = sorted(dataset["area"].dropna().unique())
    if len(classes) < 3:
        info_bar("Need ≥3 classes for 3D visualization", "info")
        return

    # Project the actually fitted DMA TF-IDF class centroids; never draw random
    # coordinates and call them semantic embeddings.
    from sklearn.decomposition import PCA
    available_classes = [c for c in classes if c in getattr(eco.dma, "class_centroids", {})]
    if len(available_classes) < 3:
        info_bar("Fitted class centroids are unavailable", "warning")
        return
    classes = available_classes
    matrix = np.vstack([eco.dma.class_centroids[c] for c in classes]).astype(float)
    centroids = PCA(n_components=3, random_state=42).fit_transform(matrix)
    n = len(classes)

    sizes = [int(dataset["area"].value_counts().get(c, 1)) for c in classes]
    max_size = max(sizes) if sizes else 1
    scaled_sizes = [max(6, s / max_size * 30) for s in sizes]

    hover_texts = [
        f"<b>{c}</b><br>Samples: {s}<br>Test: {int(s*0.2)} (20%)"
        for c, s in zip(classes, sizes)
    ]

    scatter_3d_chart(
        points=centroids,
        labels=classes,
        sizes=scaled_sizes,
        colors=list(range(n)),
        colorscale="Turbo",
        title=f"{n}类真实训练质心的PCA三维投影（非临床性能图）",
        hover_texts=hover_texts,
        marker_opacity=0.85,
        auto_rotate=True,
        key="ov_disease_3d",
    )


def _render_class_detail_panel(dataset: Any, eco: Any, t) -> None:
    """Render a right-side panel showing class distribution legend + selected class detail."""
    from dashboard.theme import COLORS

    area_counts = dataset["area"].value_counts()
    classes = sorted(dataset["area"].dropna().unique())

    st.markdown(f"""
    <div style="
        background:{COLORS['bg_card']};
        border:1px solid {COLORS['cyan_dim']};
        border-radius:10px;padding:0.8rem;
        margin-top:2.5rem;
    ">
        <div style="font-size:0.85rem;font-weight:700;color:{COLORS['cyan']};
                    margin-bottom:0.6rem;">
            📋 {t('overview.class_distribution')}
        </div>
    """, unsafe_allow_html=True)

    # Legend-style class list
    for idx, cls in enumerate(classes[:15]):  # Show top 15
        count = int(area_counts.get(cls, 0))
        hue = idx * 360 / max(len(classes), 1)
        color = f"hsl({hue:.0f},70%,55%)"
        st.markdown(f"""
        <div style="display:flex;align-items:center;padding:0.15rem 0;
                    font-size:0.7rem;color:{COLORS['text_secondary']};">
            <span style="
                display:inline-block;width:10px;height:10px;border-radius:3px;
                background:{color};margin-right:6px;flex-shrink:0;
            "></span>
            <span style="flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">
                {cls}
            </span>
            <span style="color:{COLORS['text_dim']};margin-left:4px;">{count}</span>
        </div>
        """, unsafe_allow_html=True)

    if len(classes) > 15:
        st.caption(f"+ {len(classes) - 15} more classes")

    # Selected class detail (dropdown)
    st.markdown('<div style="margin-top:0.8rem;"></div>', unsafe_allow_html=True)
    selected_cls = st.selectbox(
        t("overview.class_detail"),
        classes,
        key="ov_class_select",
        label_visibility="visible",
    )

    if selected_cls:
        count = int(area_counts.get(selected_cls, 0))
        test_count = len(eco.test_df[eco.test_df["area"] == selected_cls]) if hasattr(eco, 'test_df') and eco.test_df is not None else 0
        train_count = count - test_count

        st.markdown(f"""
        <div style="
            background:{COLORS['bg_panel']};
            border:1px solid {COLORS['cyan_dim']};
            border-radius:8px;padding:0.6rem;margin-top:0.4rem;
            font-size:0.72rem;
        ">
            <div style="color:{COLORS['cyan']};font-weight:600;margin-bottom:0.3rem;">
                {selected_cls}
            </div>
            <div style="color:{COLORS['text_secondary']};line-height:1.6;">
                {t('overview.train_samples')}: {train_count}<br>
                {t('overview.test_samples')}: {test_count}<br>
                {t('overview.total_samples')}: {count}<br>
                Test Ratio: {test_count/max(count,1)*100:.1f}%
            </div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)
