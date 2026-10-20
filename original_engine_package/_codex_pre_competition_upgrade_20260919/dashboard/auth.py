"""Login page, session management, and role-based access control.

Usage:
    from dashboard.auth import is_authenticated, get_user_role, render_login_page, render_sidebar_nav
"""

from __future__ import annotations

import time
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Tuple

import streamlit as st

# ═══════════════════════════════════════════════════════════════════════════
# Credentials
# ═══════════════════════════════════════════════════════════════════════════

CREDENTIALS: Dict[str, Dict[str, str]] = {
    "admin": {
        "password": "admin123",
        "role": "admin",
        "display_zh": "管理员",
        "display_en": "Administrator",
    },
    "client": {
        "password": "client123",
        "role": "customer",
        "display_zh": "客户",
        "display_en": "Client",
    },
    "auditor": {
        "password": "audit123",
        "role": "auditor",
        "display_zh": "审计员",
        "display_en": "Auditor",
    },
}

# ═══════════════════════════════════════════════════════════════════════════
# Page visibility matrix
# ═══════════════════════════════════════════════════════════════════════════

ROLE_PAGES: Dict[str, List[str]] = {
    "admin": [
        "diagnosis", "overview", "agent_monitor", "hardware_metrics", "experiments",
        "knowledge_base", "human_review", "clinical_safety",
        "history_logs", "audit_log", "global_config",
    ],
    "customer": ["diagnosis", "overview", "knowledge_base", "clinical_safety", "history_logs"],
    "auditor": ["diagnosis", "overview", "history_logs", "audit_log"],
}

PAGE_META: Dict[str, Dict[str, str]] = {
    "diagnosis":         {"icon": "🩺", "zh": "诊断演示",           "en": "Diagnosis Demo"},
    "overview":          {"icon": "📊", "zh": "系统概览",           "en": "System Overview"},
    "agent_monitor":     {"icon": "🤖", "zh": "智能体监控",         "en": "Agent Monitor"},
    "hardware_metrics":  {"icon": "💻", "zh": "硬件监控",           "en": "Hardware Metrics"},
    "experiments":       {"icon": "🔬", "zh": "实验诊断",           "en": "Experiments"},
    "knowledge_base":    {"icon": "📚", "zh": "知识库管理",         "en": "Knowledge Base"},
    "human_review":      {"icon": "✋", "zh": "人工审核与校准",      "en": "Human Review"},
    "clinical_safety":   {"icon": "🛡️", "zh": "临床安全监测",       "en": "Clinical Safety"},
    "history_logs":      {"icon": "📋", "zh": "历史任务日志",       "en": "History & Logs"},
    "audit_log":         {"icon": "🔍", "zh": "审计日志",           "en": "Audit Log"},
    "global_config":     {"icon": "⚙️", "zh": "全局配置",           "en": "Global Config"},
}


# ═══════════════════════════════════════════════════════════════════════════
# Session helpers
# ═══════════════════════════════════════════════════════════════════════════

def is_authenticated() -> bool:
    return st.session_state.get("authenticated", False)


def get_user_role() -> str:
    return st.session_state.get("role", "")


def get_username() -> str:
    return st.session_state.get("username", "")


def get_visible_pages(role: str) -> List[Tuple[str, str, str]]:
    """Return list of (page_key, icon, display_name) for the given role."""
    lang = st.session_state.get("lang", "zh")
    pages = ROLE_PAGES.get(role, [])
    result = []
    for p in pages:
        meta = PAGE_META.get(p, {})
        icon = meta.get("icon", "📄")
        name = meta.get(lang, p)
        result.append((p, icon, name))
    return result


# ═══════════════════════════════════════════════════════════════════════════
# Login page
# ═══════════════════════════════════════════════════════════════════════════

def render_login_page() -> None:
    """Full-screen sci-fi login page with glassmorphism card and particle background."""

    # Init session state
    if "lang" not in st.session_state:
        st.session_state.lang = "zh"
    if "login_error" not in st.session_state:
        st.session_state.login_error = ""

    lang = st.session_state.lang

    # ── Language toggle (top-right corner) ──
    _, col_lang = st.columns([5, 1])
    with col_lang:
        if st.button("🇨🇳 中文" if lang != "zh" else "🇬🇧 EN", key="login_lang_toggle",
                     use_container_width=True):
            st.session_state.lang = "en" if lang == "zh" else "zh"
            st.rerun()

    i18n = _login_i18n(lang)

    # Center card
    col1, col2, col3 = st.columns([1, 3, 1])
    with col2:
        st.markdown("""<div class="login-card">""", unsafe_allow_html=True)

        # Logo & title
        st.markdown(f"""
        <div style="text-align:center; padding:0.6rem 0 0.2rem;">
            <div style="font-size:4rem;">🏥</div>
            <div class="neon-text-cyan" style="font-size:1.6rem;font-weight:800;">
                {i18n["title"]}
            </div>
            <div style="font-size:0.8rem;color:#7a8ba8;margin-top:4px;">
                {i18n["subtitle"]}
            </div>
            <div style="font-size:0.65rem;color:#4a5578;margin-top:2px;">
                {i18n["version"]}
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("<hr style='border-color:rgba(0,245,255,0.12);margin:0.2rem 2rem;'>", unsafe_allow_html=True)

        # ── Login form ──
        username = st.text_input(
            i18n["username"], key="login_user",
            placeholder="admin / client / auditor",
            label_visibility="collapsed",
        )
        password = st.text_input(
            i18n["password"], key="login_pwd",
            type="password", placeholder="••••••••",
            label_visibility="collapsed",
        )

        # ── Role selection ──
        st.caption(i18n["role_label"])
        rc1, rc2, rc3 = st.columns(3)
        selected_role = st.session_state.get("login_selected_role", "admin")

        with rc1:
            if st.button(
                f"🛡️ {i18n['role_admin']}",
                key="role_admin_btn",
                use_container_width=True,
                type="primary" if selected_role == "admin" else "secondary",
            ):
                st.session_state.login_selected_role = "admin"
                st.rerun()
        with rc2:
            if st.button(
                f"👤 {i18n['role_customer']}",
                key="role_client_btn",
                use_container_width=True,
                type="primary" if selected_role == "customer" else "secondary",
            ):
                st.session_state.login_selected_role = "customer"
                st.rerun()
        with rc3:
            if st.button(
                f"🔍 {i18n['role_auditor']}",
                key="role_auditor_btn",
                use_container_width=True,
                type="primary" if selected_role == "auditor" else "secondary",
            ):
                st.session_state.login_selected_role = "auditor"
                st.rerun()

        # Description under selected role
        role_descs = {
            "admin": i18n["role_admin_desc"],
            "customer": i18n["role_customer_desc"],
            "auditor": i18n["role_auditor_desc"],
        }
        st.caption(f"💡 {role_descs.get(selected_role, '')}")

        # ── Sign in button ──
        if st.button(i18n["signin"], key="login_btn", type="primary", use_container_width=True):
            if not username.strip():
                st.session_state.login_error = i18n.get("login.error", "Invalid credentials")
            else:
                cred = CREDENTIALS.get(username.strip().lower())
                if cred and cred["password"] == password:
                    st.session_state.authenticated = True
                    st.session_state.role = cred["role"]
                    st.session_state.username = username.strip().lower()
                    st.session_state.login_time = datetime.now()
                    st.session_state.login_error = ""
                    st.session_state.current_page = "diagnosis"
                    st.rerun()
                else:
                    st.session_state.login_error = i18n.get("login.error", "Invalid credentials")

        # Error display
        if st.session_state.get("login_error"):
            st.markdown(f"""
            <div style="text-align:center;color:#ff3344;padding:0.5rem;
                        animation: neon-pulse 1.5s ease-in-out infinite;
                        font-size:0.85rem;">
                ⚠️ {st.session_state.login_error}
            </div>
            """, unsafe_allow_html=True)

        # ── Demo account hint ──
        st.markdown(f"""
        <div style="text-align:center;margin-top:0.6rem;padding:0.5rem;
                    background:rgba(0,245,255,0.05);border-radius:8px;
                    border:1px solid rgba(0,245,255,0.1);">
            <div style="font-size:0.7rem;color:#7a8ba8;margin-bottom:4px;">
                🔑 {i18n["demo_title"]}
            </div>
            <div style="font-size:0.65rem;color:#4a5578;line-height:1.6;">
                {i18n["demo_admin"]}<br>
                {i18n["demo_client"]}<br>
                {i18n["demo_auditor"]}
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("""</div>""", unsafe_allow_html=True)  # close login-card


def _login_i18n(lang: str) -> Dict[str, str]:
    """Inline i18n for login page (avoids circular import with dashboard.i18n)."""
    data = {
        "zh": {
            "title": "MAPFM HMAE 控制面板",
            "subtitle": "异构多智能体医学AI生态系统",
            "version": "版本 3.0",
            "username": "用户名",
            "password": "密码",
            "role_label": "选择角色",
            "signin": "登 录",
            "signing_in": "验证中...",
            "login.error": "用户名或密码错误",
            "role_admin": "管理员",
            "role_customer": "客户",
            "role_auditor": "审计员",
            "role_admin_desc": "全部功能模块访问",
            "role_customer_desc": "只读访问诊断与安全",
            "role_auditor_desc": "日志审计与合规审查",
            "demo_title": "演示账号",
            "demo_admin": "管理员: admin / admin123",
            "demo_client": "客户: client / client123",
            "demo_auditor": "审计员: auditor / audit123",
        },
        "en": {
            "title": "MAPFM HMAE Control Panel",
            "subtitle": "Heterogeneous Multi-Agent Medical AI Ecosystem",
            "version": "Version 3.0",
            "username": "Username",
            "password": "Password",
            "role_label": "Select Role",
            "signin": "Sign In",
            "signing_in": "Authenticating...",
            "login.error": "Invalid username or password",
            "role_admin": "Administrator",
            "role_customer": "Client",
            "role_auditor": "Auditor",
            "role_admin_desc": "Full access to all modules",
            "role_customer_desc": "Read-only diagnosis & safety",
            "role_auditor_desc": "Log auditing & compliance",
            "demo_title": "Demo Accounts",
            "demo_admin": "Admin: admin / admin123",
            "demo_client": "Client: client / client123",
            "demo_auditor": "Auditor: auditor / audit123",
        },
    }
    return data.get(lang, data["zh"])


# ═══════════════════════════════════════════════════════════════════════════
# Sidebar navigation
# ═══════════════════════════════════════════════════════════════════════════

def render_sidebar_nav() -> str:
    """Render role-filtered sidebar navigation. Returns the selected page key."""
    role = get_user_role()
    lang = st.session_state.get("lang", "zh")

    with st.sidebar:
        # ── User info header ──
        cred = CREDENTIALS.get(get_username(), {})
        display_name = cred.get(f"display_{lang}", get_username())

        st.markdown(f"""
        <div style="text-align:center;padding:0.8rem 0 0.4rem;">
            <div style="font-size:1.2rem;font-weight:800;color:#e0e0ff;">
                🏥 MAPFM HMAE
            </div>
            <div style="font-size:0.65rem;color:#7a8ba8;margin-top:2px;">
                Control Panel v3.0
            </div>
            <div style="margin-top:0.6rem;padding:0.4rem 0.8rem;
                        background:rgba(0,245,255,0.08);border-radius:20px;
                        display:inline-block;">
                <span style="font-size:0.7rem;color:#00f5ff;">{display_name}</span>
                <span style="font-size:0.6rem;color:#4a5578;margin:0 6px;">|</span>
                <span style="font-size:0.7rem;color:#7a8ba8;">
                    {_role_label(role, lang)}
                </span>
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.divider()

        # ── Navigation buttons ──
        if "current_page" not in st.session_state:
            st.session_state.current_page = "overview"

        pages = get_visible_pages(role)
        for page_key, icon, name in pages:
            is_active = st.session_state.current_page == page_key
            btn_type = "primary" if is_active else "secondary"
            if st.button(f"{icon} {name}", key=f"nav_{page_key}",
                         use_container_width=True, type=btn_type):
                st.session_state.current_page = page_key
                st.rerun()

        st.divider()

        # ── Language toggle ──
        st.caption("🌐 " + ("语言 / Language" if lang == "zh" else "Language / 语言"))
        lc1, lc2 = st.columns(2)
        with lc1:
            if st.button("🇨🇳 中文", key="sidebar_lang_zh", use_container_width=True,
                         type="primary" if lang == "zh" else "secondary"):
                st.session_state.lang = "zh"
                st.rerun()
        with lc2:
            if st.button("🇬🇧 EN", key="sidebar_lang_en", use_container_width=True,
                         type="primary" if lang == "en" else "secondary"):
                st.session_state.lang = "en"
                st.rerun()

        st.divider()

        # ── Auto-refresh ──
        auto_label = "🔄 " + ("自动刷新" if lang == "zh" else "Auto Refresh")
        st.session_state.auto_refresh = st.toggle(
            auto_label,
            value=st.session_state.get("auto_refresh", False),
            key="auto_refresh_toggle",
        )
        if st.session_state.auto_refresh:
            intervals = {"5s": 5, "10s": 10, "30s": 30, "60s": 60}
            interval_label = "⏱ " + ("间隔" if lang == "zh" else "Interval")
            selected = st.selectbox(
                interval_label,
                list(intervals.keys()), index=1,
                key="refresh_interval_select",
                label_visibility="collapsed",
            )
            st.session_state.refresh_interval = intervals[selected]

        st.divider()

        # ── System clock ──
        st.caption(f"🕐 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        st.divider()

        # ── Logout ──
        logout_label = "🚪 " + ("退出登录" if lang == "zh" else "Sign Out")
        if st.button(logout_label, key="logout_btn", use_container_width=True, type="secondary"):
            _do_logout()
            st.rerun()

    return st.session_state.current_page


def _role_label(role: str, lang: str) -> str:
    labels = {
        "admin": {"zh": "管理员", "en": "Admin"},
        "customer": {"zh": "客户", "en": "Client"},
        "auditor": {"zh": "审计员", "en": "Auditor"},
    }
    return labels.get(role, {}).get(lang, role)


def _do_logout() -> None:
    """Clear all session state and reset to login page."""
    keys_to_keep = {"lang"}
    for key in list(st.session_state.keys()):
        if key not in keys_to_keep:
            del st.session_state[key]
    st.session_state.authenticated = False
    st.session_state.login_error = ""
