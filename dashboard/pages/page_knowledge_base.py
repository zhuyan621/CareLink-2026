"""Page 5: Knowledge Base Management — 3D volume rendering + document search/filter."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from dashboard.components import (
    neon_metric_card, section_header, info_bar, volume_3d_chart,
    data_table_with_style, export_button, pulse_status_badge,
)
from dashboard.i18n import get_translator
from dashboard.theme import configure_plotly_dark, COLORS


def render(eco: Any, config: Any, dataset: Any, monitor: Any) -> None:
    t = get_translator()

    # ── Check KB availability ──
    kb_available = eco is not None and hasattr(eco, 'online_kb') and eco.online_kb is not None

    # ═══════════════════════════════════════════════════════════════════
    # Row 1: 3D Semantic Density Volume
    # ═══════════════════════════════════════════════════════════════════
    section_header(t("kb.density_3d"), "🌌", "magenta")
    if kb_available:
        try:
            _render_kb_density_3d(eco, t)
        except Exception:
            info_bar("3D volume render unavailable — insufficient data", "info")
    else:
        info_bar(t("kb.kb_unavailable"), "warning")

    # ═══════════════════════════════════════════════════════════════════
    # Row 2: KB Stats
    # ═══════════════════════════════════════════════════════════════════
    section_header(t("kb.stats"), "📊", "cyan")
    if kb_available:
        try:
            stats = eco.online_kb.get_stats()
            c1, c2, c3, c4 = st.columns(4)
            with c1:
                neon_metric_card(t("kb.total_docs"), str(stats.get("document_count", 0)),
                                 icon="📄", neon_color="cyan", key="kb_total")
            with c2:
                neon_metric_card(t("kb.verified_docs"), str(stats.get("verified_count", 0)),
                                 icon="✅", neon_color="green", key="kb_verified")
            with c3:
                sources = stats.get("source_counts", {})
                neon_metric_card(t("kb.sources"), str(len(sources)),
                                 icon="📁", neon_color="violet", key="kb_sources")
            with c4:
                avg_w = stats.get("avg_weight", 0)
                neon_metric_card(t("kb.avg_weight"), f"{avg_w:.3f}" if avg_w else "—",
                                 icon="⚖️", neon_color="amber", key="kb_avgw")
        except Exception:
            info_bar("Stats unavailable", "warning")
    else:
        info_bar(t("kb.kb_unavailable"), "warning")

    # ═══════════════════════════════════════════════════════════════════
    # Row 3: Search + Filters
    # ═══════════════════════════════════════════════════════════════════
    search_query = st.text_input(
        t("kb.search_placeholder"), key="kb_search",
        placeholder=t("kb.search_placeholder"),
    )

    fc1, fc2, fc3, fc4 = st.columns(4)
    with fc1:
        source_filter = st.multiselect(t("kb.filter_source"), _get_sources(eco), key="kb_fsrc")
    with fc2:
        area_filter = st.multiselect(t("kb.filter_area"), _get_areas(eco, dataset), key="kb_farea")
    with fc3:
        verified_filter = st.selectbox(
            t("kb.filter_verified"),
            [t("kb.all"), t("kb.verified_only"), t("kb.unverified_only")],
            key="kb_fver",
        )
    with fc4:
        sort_by = st.selectbox(
            t("kb.sort_by"),
            [t("kb.sort_relevance"), t("kb.sort_date"), t("kb.sort_weight"), t("kb.sort_fact_score")],
            key="kb_sort",
        )

    # ═══════════════════════════════════════════════════════════════════
    # Row 4: Source Distribution Pie + Refresh
    # ═══════════════════════════════════════════════════════════════════
    col_pie, col_refresh = st.columns([3, 1])
    with col_pie:
        if kb_available and sources:
            fig_pie = go.Figure(data=[go.Pie(
                labels=list(sources.keys()), values=list(sources.values()),
                hole=0.4, textinfo="label+percent", textfont=dict(size=10, color="#e0e0ff"),
            )])
            configure_plotly_dark(fig_pie)
            fig_pie.update_layout(height=250, showlegend=False,
                                  title=t("kb.source_distribution"))
            st.plotly_chart(fig_pie, use_container_width=True, key="kb_source_pie")
    with col_refresh:
        st.markdown("<br>" * 3, unsafe_allow_html=True)
        if st.button(f"🔄 {t('kb.refresh_kb')}", use_container_width=True, key="kb_refresh_btn"):
            if kb_available:
                with st.spinner(t("kb.refreshing")):
                    try:
                        new_ids = eco.refresh_online_knowledge(n_per_source=5)
                        info_bar(t("kb.docs_added", count=len(new_ids)), "success")
                    except Exception as exc:
                        info_bar(f"Refresh failed: {exc}", "error")

    # ═══════════════════════════════════════════════════════════════════
    # Row 5: Paginated Document List
    # ═══════════════════════════════════════════════════════════════════
    section_header(t("kb.doc_list"), "📋", "cyan")

    if not kb_available:
        info_bar(t("kb.kb_unavailable"), "warning")
        return

    try:
        docs = _get_filtered_docs(eco, search_query, source_filter, area_filter,
                                  verified_filter, sort_by, t)
    except Exception:
        info_bar(t("kb.kb_unavailable"), "warning")
        return

    if not docs:
        info_bar(t("kb.no_docs") if not search_query else t("kb.no_results"), "info")
        return

    # Pagination
    page_size = 20
    total_pages = max(1, (len(docs) + page_size - 1) // page_size)
    page_key = "kb_page"
    if page_key not in st.session_state:
        st.session_state[page_key] = 0
    page = st.session_state[page_key]

    # Pagination controls
    pc1, pc2, pc3, pc4, pc5 = st.columns([1, 1, 2, 1, 1])
    with pc1:
        if st.button("◀◀", key="kb_first", disabled=page == 0):
            st.session_state[page_key] = 0; st.rerun()
    with pc2:
        if st.button("◀", key="kb_prev", disabled=page == 0):
            st.session_state[page_key] = max(0, page - 1); st.rerun()
    with pc3:
        st.caption(t("common.page", current=page + 1, total=total_pages))
    with pc4:
        if st.button("▶", key="kb_next", disabled=page >= total_pages - 1):
            st.session_state[page_key] = min(total_pages - 1, page + 1); st.rerun()
    with pc5:
        if st.button("▶▶", key="kb_last", disabled=page >= total_pages - 1):
            st.session_state[page_key] = total_pages - 1; st.rerun()

    start = page * page_size
    page_docs = docs[start:start + page_size]

    for doc in page_docs:
        verified = doc.get("verification_passed", False)
        badge = pulse_status_badge("healthy" if verified else "degraded")
        with st.expander(
            f"#{doc.get('doc_id','?')} — {str(doc.get('question',''))[:80]}  {badge}",
            expanded=False,
        ):
            c_left, c_right = st.columns([2, 1])
            with c_left:
                st.markdown(f"**{t('kb.question')}:** {doc.get('question','—')}")
                answer = doc.get("answer", "—")
                if len(str(answer)) > 300:
                    show_more = st.checkbox(t("kb.show_more"), key=f"kb_more_{doc.get('doc_id')}")
                    st.markdown(f"**{t('kb.answer')}:** {answer if show_more else str(answer)[:300]}...")
                else:
                    st.markdown(f"**{t('kb.answer')}:** {answer}")
            with c_right:
                st.caption(f"**{t('kb.area')}:** {doc.get('area','—')}")
                st.caption(f"**{t('kb.source')}:** {doc.get('source','—')}")
                st.caption(f"**{t('kb.last_updated')}:** {_fmt(doc.get('last_updated'))}")
                st.caption(f"**{t('kb.doc_weight')}:** {doc.get('doc_weight','—')}")
                st.caption(f"**{t('kb.fact_score')}:** {doc.get('fact_score','—')}")
                st.caption(f"**{t('kb.rerank_score')}:** {doc.get('rerank_score','—')}")


# ═══════════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════════

def _get_sources(eco: Any) -> list:
    try:
        stats = eco.online_kb.get_stats()
        return list(stats.get("source_counts", {}).keys())
    except Exception:
        return []


def _get_areas(eco: Any, dataset: Any) -> list:
    if dataset is not None:
        return sorted(dataset["area"].dropna().unique().tolist())
    if eco is not None and hasattr(eco, 'label_set'):
        return eco.label_set
    return []


def _get_filtered_docs(eco: Any, query: str, sources: list, areas: list,
                        verified_str: str, sort_str: str, t) -> list:
    """Get and filter documents from online_kb."""
    try:
        docs = list(eco.online_kb.documents) if hasattr(eco.online_kb, 'documents') else []
    except Exception:
        return []

    if not docs:
        return []

    # Text search
    if query.strip():
        q = query.strip().lower()
        docs = [d for d in docs if q in str(d.get("question", "")).lower()
                or q in str(d.get("answer", "")).lower()]

    # Source filter
    if sources:
        docs = [d for d in docs if d.get("source", "") in sources]

    # Area filter
    if areas:
        docs = [d for d in docs if d.get("area", "") in areas]

    # Verification filter
    ver_all = t("kb.all")
    ver_only = t("kb.verified_only")
    ver_un = t("kb.unverified_only")
    if verified_str == ver_only:
        docs = [d for d in docs if d.get("verification_passed", False)]
    elif verified_str == ver_un:
        docs = [d for d in docs if not d.get("verification_passed", False)]

    # Sort
    sort_date = t("kb.sort_date")
    sort_weight = t("kb.sort_weight")
    sort_fact = t("kb.sort_fact_score")
    if sort_str == sort_date:
        docs.sort(key=lambda d: str(d.get("last_updated", "")), reverse=True)
    elif sort_str == sort_weight:
        docs.sort(key=lambda d: float(d.get("doc_weight", 0) or 0), reverse=True)
    elif sort_str == sort_fact:
        docs.sort(key=lambda d: float(d.get("fact_score", 0) or 0), reverse=True)

    return docs


def _fmt(val: Any) -> str:
    if val is None:
        return "—"
    from datetime import datetime
    if isinstance(val, datetime):
        return val.strftime("%Y-%m-%d %H:%M")
    return str(val)[:19]


def _render_kb_density_3d(eco: Any, t) -> None:
    """3D volume rendering of document semantic density."""
    try:
        docs = list(eco.online_kb.documents) if hasattr(eco.online_kb, 'documents') else []
    except Exception:
        docs = []

    if len(docs) < 10:
        info_bar("Need ≥10 documents for 3D density visualization", "info")
        return

    dense = np.asarray(getattr(eco.online_kb, "dense_matrix", np.zeros((0, 0))), dtype=float)
    n = min(len(docs), len(dense), 200)
    if n < 10 or dense.ndim != 2 or dense.shape[1] < 3:
        info_bar("Need ≥10 measured document embeddings for 3D density visualization", "info")
        return
    from sklearn.decomposition import PCA
    projected = PCA(n_components=3, random_state=42).fit_transform(dense[:n])
    x, y, z = projected[:, 0], projected[:, 1], projected[:, 2]

    # 3D histogram for density
    hist, edges = np.histogramdd(np.column_stack([x, y, z]), bins=20)
    X, Y, Z = np.meshgrid(
        edges[0][:-1], edges[1][:-1], edges[2][:-1], indexing='ij',
    )

    volume_3d_chart(
        X.flatten(), Y.flatten(), Z.flatten(), hist.flatten().astype(float),
        title="真实文档向量的PCA三维密度场（最多200条）",
        colorscale="Teal", surface_count=12, opacity=0.08,
        key="kb_volume_3d",
    )
