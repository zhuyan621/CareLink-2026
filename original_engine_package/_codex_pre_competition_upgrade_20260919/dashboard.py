#!/usr/bin/env python3
"""MAPFM HMAE Control Panel v3.0 — Industrial-Grade Medical AI Dashboard.

Sci-fi dark theme, 3D dynamic charts, 10 pages, 3 role-based views,
bilingual (中文/English).

Launch:
    streamlit run dashboard.py
"""

from __future__ import annotations

import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

import streamlit as st

# ═══════════════════════════════════════════════════════════════════════════
# Page config — MUST be the first Streamlit call
# ═══════════════════════════════════════════════════════════════════════════
st.set_page_config(
    page_title="MAPFM HMAE Control Panel",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        "Get Help": None,
        "Report a Bug": None,
        "About": "MAPFM HMAE v3.0 — Medical Multi-Agent Ecosystem Control Panel",
    },
)

# ═══════════════════════════════════════════════════════════════════════════
# Path injection
# ═══════════════════════════════════════════════════════════════════════════
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# ═══════════════════════════════════════════════════════════════════════════
# Lazy ecosystem loader (cached)
# ═══════════════════════════════════════════════════════════════════════════

@st.cache_resource(show_spinner="Initializing multi-agent ecosystem...")
def _get_ecosystem() -> "tuple[Any, Any, Any] | tuple[None, None, None]":
    """Lazy-init the ecosystem — cached so it only boots once."""
    try:
        from mapfm_ecosystem_repaired import (
            EcosystemConfig,
            HeterogeneousMultiAgentEcosystem,
            load_medical_dataset,
        )
        config = EcosystemConfig()
        csv_path = PROJECT_ROOT / "medNo.22.csv"
        dataset = load_medical_dataset(
            csv_path if csv_path.exists() else None, seed=config.random_seed,
        )
        eco = HeterogeneousMultiAgentEcosystem(
            config=config, dataset=dataset,
            base_model=config.ollama_model_name, verbose=False,
        )
        return eco, config, dataset
    except Exception:
        return None, None, None


@st.cache_resource(show_spinner=False)
def _get_monitor() -> "Any | None":
    """Lazy-init system monitor."""
    try:
        from mapfm_utils.system_monitor import get_system_monitor
        return get_system_monitor()
    except Exception:
        return None


# ═══════════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════════

def _format_dt(ts: Any) -> str:
    """Safely format a timestamp."""
    if ts is None:
        return "—"
    if isinstance(ts, datetime):
        return ts.strftime("%H:%M:%S")
    return str(ts)[:19]


# ═══════════════════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════════════════

def main() -> None:
    """Main Streamlit application entry point."""

    from dashboard.theme import inject_dark_theme
    from dashboard.auth import is_authenticated, render_login_page, render_sidebar_nav
    from dashboard.pages import get_page_handler

    # ── Inject dark theme (always, even on login page) ──
    inject_dark_theme()

    # ── Init session defaults ──
    if "lang" not in st.session_state:
        st.session_state.lang = "zh"
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    if "current_page" not in st.session_state:
        st.session_state.current_page = "diagnosis"
    if "auto_refresh" not in st.session_state:
        st.session_state.auto_refresh = False
    if "refresh_interval" not in st.session_state:
        st.session_state.refresh_interval = 10

    # ── Login gate ──
    if not is_authenticated():
        render_login_page()
        return

    # ── Sidebar navigation ──
    page_key = render_sidebar_nav()

    # ── Load ecosystem ──
    eco, config, dataset = _get_ecosystem()
    monitor = _get_monitor()

    # ── Header ──
    lang = st.session_state.get("lang", "zh")
    title = "MAPFM HMAE 控制面板" if lang == "zh" else "MAPFM HMAE Control Panel"
    subtitle = (
        "异构多智能体医学AI生态系统 · 工业级管理平台"
        if lang == "zh"
        else "Heterogeneous Multi-Agent Medical AI Ecosystem · Industrial Platform"
    )
    st.title(title)
    st.caption(subtitle)
    st.divider()

    # ── Page routing ──
    try:
        handler = get_page_handler(page_key)
        handler(eco, config, dataset, monitor)
    except Exception as exc:
        import traceback
        st.error(f"Page render error: {exc}")
        with st.expander("Traceback"):
            st.code(traceback.format_exc())

    # ── Footer ──
    footer_text = (
        "MAPFM HMAE v3.0 | 7-Agent MedTsLLM BioBERT | 全离线隐私保护 | 22类疾病诊断"
        if lang == "zh"
        else "MAPFM HMAE v3.0 | 7-Agent MedTsLLM BioBERT | Fully Offline Privacy-Preserving | 22-Class Diagnosis"
    )
    st.markdown(f"""
    <div style="text-align:center;color:#4a5578;font-size:0.7rem;
                padding:1.5rem 0 0.5rem;border-top:1px solid rgba(0,245,255,0.08);
                margin-top:2rem;">
        {footer_text}
    </div>
    """, unsafe_allow_html=True)

    # ── Auto-refresh ──
    if st.session_state.get("auto_refresh", False):
        interval = st.session_state.get("refresh_interval", 10)
        time.sleep(interval)
        st.rerun()


if __name__ == "__main__":
    main()
