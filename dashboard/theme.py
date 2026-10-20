"""Dark sci-fi CSS theme, particle animation, glassmorphism, neon effects.

Also provides Plotly dark templates for 2D and 3D charts.

Usage:
    from dashboard.theme import inject_dark_theme, configure_plotly_dark, configure_plotly_dark_3d
"""

from __future__ import annotations

from typing import Any, Dict

import plotly.graph_objects as go
import streamlit as st

# ═══════════════════════════════════════════════════════════════════════════
# Color system
# ═══════════════════════════════════════════════════════════════════════════

COLORS: Dict[str, str] = {
    "bg_deep": "#06060f",
    "bg_primary": "#0a0a14",
    "bg_panel": "rgba(12,18,35,0.85)",
    "bg_card": "rgba(16,24,48,0.75)",
    "bg_sidebar": "rgba(8,12,28,0.95)",
    "bg_input": "rgba(20,30,55,0.7)",
    "bg_hover": "rgba(25,38,68,0.8)",
    "cyan": "#00f5ff",
    "cyan_dim": "rgba(0,245,255,0.15)",
    "cyan_glow": "0 0 10px rgba(0,245,255,0.4), 0 0 40px rgba(0,245,255,0.1)",
    "magenta": "#ff00e5",
    "violet": "#7c3aed",
    "success": "#00ff88",
    "warning": "#ffaa00",
    "danger": "#ff3344",
    "text_primary": "#e0e0ff",
    "text_secondary": "#7a8ba8",
    "text_dim": "#4a5578",
}

CHART_PALETTE = [
    "#00f5ff", "#ff00e5", "#7c3aed", "#00ff88", "#ffaa00",
    "#ff3344", "#3b82f6", "#ff8c00", "#0ff", "#ff0",
]

# ═══════════════════════════════════════════════════════════════════════════
# Plotly templates
# ═══════════════════════════════════════════════════════════════════════════

PLOTLY_DARK_TEMPLATE: Dict[str, Any] = {
    "layout": {
        "paper_bgcolor": "rgba(0,0,0,0)",
        "plot_bgcolor": "rgba(12,18,35,0.6)",
        "font": {"color": "#e0e0ff", "size": 12},
        "title": {"font": {"color": "#e0e0ff", "size": 16}},
        "legend": {"font": {"color": "#7a8ba8"}, "bgcolor": "rgba(0,0,0,0)"},
        "xaxis": {
            "gridcolor": "rgba(0,245,255,0.08)",
            "zerolinecolor": "rgba(0,245,255,0.15)",
            "color": "#7a8ba8",
        },
        "yaxis": {
            "gridcolor": "rgba(0,245,255,0.08)",
            "zerolinecolor": "rgba(0,245,255,0.15)",
            "color": "#7a8ba8",
        },
        "margin": {"l": 40, "r": 20, "t": 50, "b": 40},
        "colorway": CHART_PALETTE,
    }
}

SCENE_3D_DARK: Dict[str, Any] = {
    "bgcolor": "rgba(6,6,15,0.95)",
    "xaxis": {
        "backgroundcolor": "rgba(0,0,0,0)",
        "gridcolor": "rgba(0,245,255,0.12)",
        "showbackground": True,
        "zerolinecolor": "rgba(0,245,255,0.25)",
        "color": "#7a8ba8",
        "title": {"font": {"color": "#e0e0ff", "size": 11}},
    },
    "yaxis": {
        "backgroundcolor": "rgba(0,0,0,0)",
        "gridcolor": "rgba(0,245,255,0.12)",
        "showbackground": True,
        "zerolinecolor": "rgba(0,245,255,0.25)",
        "color": "#7a8ba8",
        "title": {"font": {"color": "#e0e0ff", "size": 11}},
    },
    "zaxis": {
        "backgroundcolor": "rgba(0,0,0,0)",
        "gridcolor": "rgba(0,245,255,0.12)",
        "showbackground": True,
        "zerolinecolor": "rgba(0,245,255,0.25)",
        "color": "#7a8ba8",
        "title": {"font": {"color": "#e0e0ff", "size": 11}},
    },
    "camera": {"eye": {"x": 1.8, "y": 1.8, "z": 1.4}, "up": {"x": 0, "y": 0, "z": 1}},
    "dragmode": "orbit",
    "hovermode": "closest",
}

LAYOUT_3D_AUTO_ROTATE: Dict[str, Any] = {
    "updatemenus": [{
        "type": "buttons",
        "showactive": False,
        "x": 0.1,
        "y": 0,
        "xanchor": "right",
        "yanchor": "top",
        "bgcolor": "rgba(12,18,35,0.85)",
        "bordercolor": "rgba(0,245,255,0.3)",
        "font": {"color": "#e0e0ff", "size": 10},
        "buttons": [
            {
                "label": "▶ Auto-Rotate",
                "method": "animate",
                "args": [None, {
                    "frame": {"duration": 50, "redraw": True},
                    "transition": {"duration": 0},
                    "fromcurrent": True,
                    "mode": "immediate",
                }],
            },
            {
                "label": "⏸ Pause",
                "method": "animate",
                "args": [[None], {
                    "frame": {"duration": 0, "redraw": False},
                    "transition": {"duration": 0},
                    "mode": "immediate",
                }],
            },
        ],
    }],
}

# ═══════════════════════════════════════════════════════════════════════════
# CSS Injection
# ═══════════════════════════════════════════════════════════════════════════

def inject_dark_theme() -> None:
    """Inject all dark sci-fi CSS into the Streamlit app."""
    st.markdown(f"""
    <style>
    /* ══════════════════════════════════════════════════════════════════
       1. Base overrides
       ══════════════════════════════════════════════════════════════════ */
    .stApp {{
        background: {COLORS["bg_primary"]};
        font-family: 'Segoe UI', 'Microsoft YaHei', 'Courier New', monospace;
    }}
    #MainMenu {{ visibility: hidden; }}
    footer {{ visibility: hidden; }}
    header[data-testid="stHeader"] {{ background: transparent; }}

    /* ── Compact layout: override Streamlit's default ~6rem top padding ── */
    .block-container {{
        padding-top: 1rem !important;
        padding-bottom: 0.5rem !important;
        padding-left: 2rem !important;
        padding-right: 2rem !important;
        max-width: 100% !important;
    }}
    .main .block-container {{
        padding-top: 1rem !important;
    }}

    /* ── Tighten vertical rhythm ── */
    [data-testid="stVerticalBlock"] > div + div {{
        margin-top: 0.15rem;
    }}
    hr, [data-testid="stDivider"] {{
        margin: 0.2rem 0 !important;
    }}
    [data-testid="stExpander"] details summary {{
        padding: 0.25rem 0.5rem !important;
        font-size: 0.82rem;
    }}

    /* ══════════════════════════════════════════════════════════════════
       2. Particle background (CSS-only, ~50 light dots)
       ══════════════════════════════════════════════════════════════════ */
    .stApp::before {{
        content: "";
        position: fixed; top: 0; left: 0;
        width: 100vw; height: 100vh;
        pointer-events: none; z-index: 0;
        background:
            radial-gradient(1px 1px at 1% 3%, rgba(0,245,255,0.5), transparent),
            radial-gradient(1.2px 1.2px at 5% 10%, rgba(0,245,255,0.5), transparent),
            radial-gradient(1px 1px at 10% 22%, rgba(255,0,229,0.4), transparent),
            radial-gradient(1.2px 1.2px at 12% 25%, rgba(255,0,229,0.4), transparent),
            radial-gradient(1.4px 1.4px at 16% 8%, rgba(124,58,237,0.5), transparent),
            radial-gradient(1px 1px at 20% 8%, rgba(0,245,255,0.35), transparent),
            radial-gradient(1.3px 1.3px at 24% 48%, rgba(0,255,136,0.45), transparent),
            radial-gradient(1.4px 1.4px at 28% 45%, rgba(124,58,237,0.5), transparent),
            radial-gradient(1px 1px at 30% 15%, rgba(255,170,0,0.35), transparent),
            radial-gradient(1px 1px at 35% 15%, rgba(0,255,136,0.4), transparent),
            radial-gradient(1.2px 1.2px at 38% 72%, rgba(0,245,255,0.4), transparent),
            radial-gradient(1.3px 1.3px at 42% 62%, rgba(0,245,255,0.45), transparent),
            radial-gradient(1.1px 1.1px at 46% 28%, rgba(255,0,229,0.35), transparent),
            radial-gradient(1px 1px at 50% 30%, rgba(255,170,0,0.35), transparent),
            radial-gradient(1.4px 1.4px at 54% 68%, rgba(0,255,136,0.4), transparent),
            radial-gradient(1.5px 1.5px at 58% 70%, rgba(0,245,255,0.5), transparent),
            radial-gradient(1px 1px at 62% 22%, rgba(124,58,237,0.4), transparent),
            radial-gradient(1px 1px at 65% 18%, rgba(255,0,229,0.4), transparent),
            radial-gradient(1.3px 1.3px at 68% 58%, rgba(0,245,255,0.35), transparent),
            radial-gradient(1.2px 1.2px at 72% 55%, rgba(0,245,255,0.35), transparent),
            radial-gradient(1.1px 1.1px at 76% 32%, rgba(255,170,0,0.3), transparent),
            radial-gradient(1px 1px at 78% 35%, rgba(124,58,237,0.45), transparent),
            radial-gradient(1.2px 1.2px at 82% 78%, rgba(0,245,255,0.4), transparent),
            radial-gradient(1.3px 1.3px at 85% 68%, rgba(0,255,136,0.4), transparent),
            radial-gradient(1px 1px at 88% 12%, rgba(0,245,255,0.45), transparent),
            radial-gradient(1.4px 1.4px at 90% 12%, rgba(0,245,255,0.5), transparent),
            radial-gradient(1px 1px at 93% 48%, rgba(255,0,229,0.4), transparent),
            radial-gradient(1.4px 1.4px at 95% 42%, rgba(255,0,229,0.35), transparent),
            radial-gradient(1.1px 1.1px at 98% 8%, rgba(124,58,237,0.45), transparent),
            radial-gradient(1px 1px at 3% 92%, rgba(255,170,0,0.35), transparent),
            radial-gradient(1px 1px at 8% 80%, rgba(0,245,255,0.4), transparent),
            radial-gradient(1.2px 1.2px at 14% 88%, rgba(124,58,237,0.35), transparent),
            radial-gradient(1.1px 1.1px at 18% 92%, rgba(255,170,0,0.3), transparent),
            radial-gradient(1.3px 1.3px at 22% 85%, rgba(0,255,136,0.35), transparent),
            radial-gradient(1px 1px at 32% 78%, rgba(0,245,255,0.45), transparent),
            radial-gradient(1.1px 1.1px at 35% 98%, rgba(255,0,229,0.3), transparent),
            radial-gradient(1.2px 1.2px at 42% 82%, rgba(0,245,255,0.4), transparent),
            radial-gradient(1.2px 1.2px at 45% 88%, rgba(124,58,237,0.35), transparent),
            radial-gradient(1px 1px at 52% 78%, rgba(0,245,255,0.45), transparent),
            radial-gradient(1px 1px at 55% 82%, rgba(0,255,136,0.4), transparent),
            radial-gradient(1.3px 1.3px at 62% 95%, rgba(255,170,0,0.3), transparent),
            radial-gradient(1.3px 1.3px at 68% 90%, rgba(0,245,255,0.3), transparent),
            radial-gradient(1.2px 1.2px at 72% 82%, rgba(124,58,237,0.35), transparent),
            radial-gradient(1px 1px at 75% 75%, rgba(255,0,229,0.4), transparent),
            radial-gradient(1.4px 1.4px at 82% 88%, rgba(0,255,136,0.3), transparent),
            radial-gradient(1.1px 1.1px at 88% 85%, rgba(0,245,255,0.35), transparent),
            radial-gradient(1px 1px at 92% 92%, rgba(255,0,229,0.3), transparent),
            radial-gradient(1.2px 1.2px at 97% 82%, rgba(0,245,255,0.35), transparent);
        animation: particle-drift 60s linear infinite;
    }}

    @keyframes particle-drift {{
        0%   {{ transform: translateY(0) scale(1); opacity: 0.6; }}
        25%  {{ transform: translateY(-15px) scale(1.03); opacity: 0.8; }}
        50%  {{ transform: translateY(-20px) scale(1.06); opacity: 0.9; }}
        75%  {{ transform: translateY(-10px) scale(1.03); opacity: 0.7; }}
        100% {{ transform: translateY(0) scale(1); opacity: 0.6; }}
    }}

    /* ══════════════════════════════════════════════════════════════════
       3. Glassmorphism panels
       ══════════════════════════════════════════════════════════════════ */
    .glass-panel {{
        background: {COLORS["bg_panel"]};
        backdrop-filter: blur(12px);
        -webkit-backdrop-filter: blur(12px);
        border: 1px solid {COLORS["cyan_dim"]};
        border-radius: 12px;
        padding: 1.2rem;
        box-shadow: 0 8px 32px rgba(0,0,0,0.4);
    }}
    .glass-panel-hover {{
        transition: all 0.3s ease;
    }}
    .glass-panel-hover:hover {{
        border-color: rgba(0,245,255,0.4);
        box-shadow: 0 8px 32px rgba(0,0,0,0.5), 0 0 20px rgba(0,245,255,0.15);
    }}

    /* ══════════════════════════════════════════════════════════════════
       4. Neon text
       ══════════════════════════════════════════════════════════════════ */
    .neon-text-cyan {{
        color: {COLORS["cyan"]};
        text-shadow: 0 0 7px rgba(0,245,255,0.6), 0 0 20px rgba(0,245,255,0.3);
    }}
    .neon-text-magenta {{
        color: {COLORS["magenta"]};
        text-shadow: 0 0 7px rgba(255,0,229,0.6), 0 0 20px rgba(255,0,229,0.3);
    }}
    .neon-text-green {{
        color: {COLORS["success"]};
        text-shadow: 0 0 7px rgba(0,255,136,0.6), 0 0 20px rgba(0,255,136,0.3);
    }}
    .neon-text-danger {{
        color: {COLORS["danger"]};
        text-shadow: 0 0 7px rgba(255,51,68,0.6), 0 0 20px rgba(255,51,68,0.3);
    }}

    /* ══════════════════════════════════════════════════════════════════
       5. Neon border animation
       ══════════════════════════════════════════════════════════════════ */
    .neon-border {{
        border: 1px solid {COLORS["cyan_dim"]};
        border-radius: 12px;
        animation: neon-pulse 3s ease-in-out infinite;
    }}
    @keyframes neon-pulse {{
        0%, 100% {{ box-shadow: 0 0 5px rgba(0,245,255,0.3), inset 0 0 5px rgba(0,245,255,0.05); }}
        50%      {{ box-shadow: 0 0 20px rgba(0,245,255,0.6), inset 0 0 10px rgba(0,245,255,0.1); }}
    }}

    /* ══════════════════════════════════════════════════════════════════
       6. Neon metric cards
       ══════════════════════════════════════════════════════════════════ */
    .neon-metric-card {{
        background: {COLORS["bg_card"]};
        border: 1px solid {COLORS["cyan_dim"]};
        border-radius: 10px;
        padding: 0.45rem 0.55rem;
        text-align: center;
        box-shadow: 0 2px 12px rgba(0,0,0,0.3);
        transition: all 0.3s ease;
        margin: 0.1rem 0;
    }}
    .neon-metric-card:hover {{
        border-color: rgba(0,245,255,0.4);
        box-shadow: 0 4px 20px rgba(0,0,0,0.5), 0 0 15px rgba(0,245,255,0.15);
        transform: translateY(-2px);
    }}
    .neon-metric-value {{
        font-size: 1.4rem;
        font-weight: 700;
        color: {COLORS["text_primary"]};
        line-height: 1.2;
    }}
    .neon-metric-label {{
        font-size: 0.7rem;
        color: {COLORS["text_secondary"]};
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-top: 0.3rem;
    }}
    .neon-metric-delta {{
        font-size: 0.7rem;
        margin-top: 0.2rem;
    }}
    .delta-positive {{ color: {COLORS["success"]}; }}
    .delta-negative {{ color: {COLORS["danger"]}; }}
    .delta-neutral  {{ color: {COLORS["text_secondary"]}; }}

    /* ══════════════════════════════════════════════════════════════════
       7. Pulse status dots
       ══════════════════════════════════════════════════════════════════ */
    .pulse-dot {{
        display: inline-block;
        width: 10px; height: 10px;
        border-radius: 50%;
        margin-right: 6px;
        flex-shrink: 0;
    }}
    .dot-green  {{ background: {COLORS["success"]}; box-shadow: 0 0 8px {COLORS["success"]}; animation: pulse-dot-glow 2s ease-in-out infinite; }}
    .dot-yellow {{ background: {COLORS["warning"]}; box-shadow: 0 0 8px {COLORS["warning"]}; animation: pulse-dot-glow 2s ease-in-out infinite; }}
    .dot-red    {{ background: {COLORS["danger"]}; box-shadow: 0 0 8px {COLORS["danger"]}; animation: pulse-dot-glow 1.5s ease-in-out infinite; }}
    .dot-gray   {{ background: #4a5578; box-shadow: 0 0 4px #4a5578; }}
    @keyframes pulse-dot-glow {{
        0%, 100% {{ opacity: 1; transform: scale(1); }}
        50%      {{ opacity: 0.6; transform: scale(1.3); }}
    }}

    .status-badge {{
        display: inline-block;
        padding: 0.15rem 0.6rem;
        border-radius: 999px;
        font-size: 0.7rem;
        font-weight: 600;
        letter-spacing: 0.02em;
    }}
    .status-healthy  {{ background: rgba(0,255,136,0.15); color: {COLORS["success"]}; border: 1px solid rgba(0,255,136,0.3); }}
    .status-degraded {{ background: rgba(255,170,0,0.15); color: {COLORS["warning"]}; border: 1px solid rgba(255,170,0,0.3); }}
    .status-offline  {{ background: rgba(255,51,68,0.15); color: {COLORS["danger"]}; border: 1px solid rgba(255,51,68,0.3); }}
    .status-unknown  {{ background: rgba(74,85,120,0.15); color: {COLORS["text_dim"]}; border: 1px solid rgba(74,85,120,0.3); }}

    /* ══════════════════════════════════════════════════════════════════
       8. Sidebar styling
       ══════════════════════════════════════════════════════════════════ */
    [data-testid="stSidebar"] {{
        background: linear-gradient(180deg, {COLORS["bg_sidebar"]} 0%, rgba(8,12,28,0.98) 100%);
        border-right: 1px solid {COLORS["cyan_dim"]};
    }}
    [data-testid="stSidebar"] .stButton > button {{
        border-radius: 8px;
        transition: all 0.2s ease;
    }}

    /* ══════════════════════════════════════════════════════════════════
       9. Streamlit element overrides
       ══════════════════════════════════════════════════════════════════ */
    /* Buttons */
    .stButton > button {{
        border-radius: 8px;
        font-weight: 500;
        transition: all 0.3s ease;
    }}
    .stButton > button[kind="primary"] {{
        background: linear-gradient(135deg, #0d7377 0%, #0a4a5e 100%);
        border: 1px solid rgba(0,245,255,0.3);
        color: {COLORS["cyan"]};
    }}
    .stButton > button[kind="primary"]:hover {{
        background: linear-gradient(135deg, #0f8a8f 0%, #0c5c72 100%);
        border-color: rgba(0,245,255,0.6);
        box-shadow: 0 0 15px rgba(0,245,255,0.2);
        color: #fff;
    }}

    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {{ gap: 0; background: transparent; }}
    .stTabs [data-baseweb="tab"] {{
        font-weight: 500;
        padding: 0.5rem 1.2rem;
        color: {COLORS["text_secondary"]};
        background: transparent;
        border-bottom: 2px solid transparent;
    }}
    .stTabs [data-baseweb="tab"][aria-selected="true"] {{
        color: {COLORS["cyan"]};
        border-bottom-color: {COLORS["cyan"]};
    }}

    /* Expanders */
    .streamlit-expanderHeader {{
        background: {COLORS["bg_card"]};
        border: 1px solid {COLORS["cyan_dim"]};
        border-radius: 8px;
        font-weight: 500;
        color: {COLORS["text_primary"]};
    }}

    /* DataFrames */
    [data-testid="stDataFrame"] {{
        background: {COLORS["bg_card"]};
        border: 1px solid {COLORS["cyan_dim"]};
        border-radius: 8px;
    }}

    /* Inputs */
    .stTextInput > div > div > input,
    .stTextArea > div > div > textarea {{
        background: {COLORS["bg_input"]};
        border: 1px solid {COLORS["cyan_dim"]};
        border-radius: 8px;
        color: {COLORS["text_primary"]};
    }}
    .stSelectbox > div > div {{
        background: {COLORS["bg_input"]};
        border-radius: 8px;
    }}

    /* Slider */
    .stSlider > div > div > div > div {{
        background: {COLORS["cyan"]};
    }}

    /* Metric */
    [data-testid="stMetricValue"] {{
        color: {COLORS["text_primary"]};
        font-weight: 700;
    }}
    [data-testid="stMetricLabel"] {{
        color: {COLORS["text_secondary"]};
    }}

    /* ══════════════════════════════════════════════════════════════════
       10. Scrollbar
       ══════════════════════════════════════════════════════════════════ */
    ::-webkit-scrollbar {{ width: 6px; height: 6px; }}
    ::-webkit-scrollbar-track {{ background: {COLORS["bg_deep"]}; }}
    ::-webkit-scrollbar-thumb {{
        background: rgba(0,245,255,0.25);
        border-radius: 3px;
    }}
    ::-webkit-scrollbar-thumb:hover {{ background: rgba(0,245,255,0.5); }}

    /* ══════════════════════════════════════════════════════════════════
       11. Gradient header
       ══════════════════════════════════════════════════════════════════ */
    .gradient-header {{
        background: linear-gradient(90deg, transparent, rgba(0,245,255,0.08), transparent);
        padding: 0.5rem 0;
        margin: 0.3rem 0;
    }}

    /* ══════════════════════════════════════════════════════════════════
       12. Info box
       ══════════════════════════════════════════════════════════════════ */
    .info-box {{
        padding: 0.8rem 1rem;
        border-radius: 8px;
        margin: 0.4rem 0;
        font-size: 0.85rem;
    }}
    .info-box.info    {{ background: rgba(59,130,246,0.1); border-left: 3px solid #3b82f6; }}
    .info-box.success {{ background: rgba(0,255,136,0.08); border-left: 3px solid {COLORS["success"]}; }}
    .info-box.warning {{ background: rgba(255,170,0,0.1); border-left: 3px solid {COLORS["warning"]}; }}
    .info-box.error   {{ background: rgba(255,51,68,0.1); border-left: 3px solid {COLORS["danger"]}; }}

    /* ══════════════════════════════════════════════════════════════════
       13. Login page
       ══════════════════════════════════════════════════════════════════ */
    .login-card {{
        background: {COLORS["bg_panel"]};
        backdrop-filter: blur(16px);
        -webkit-backdrop-filter: blur(16px);
        border: 1px solid {COLORS["cyan_dim"]};
        border-radius: 16px;
        padding: 1.2rem 2rem 1.5rem;
        box-shadow: 0 16px 48px rgba(0,0,0,0.5), 0 0 30px rgba(0,245,255,0.08);
        max-width: 480px;
        margin: 1rem auto 0;
    }}
    .login-card input {{
        background: {COLORS["bg_input"]} !important;
        border: 1px solid {COLORS["cyan_dim"]} !important;
        border-radius: 8px !important;
        color: {COLORS["text_primary"]} !important;
        padding: 0.6rem 0.8rem !important;
        margin: 0.3rem 0 !important;
    }}

    /* ══════════════════════════════════════════════════════════════════
       14. Section header with gradient underline
       ══════════════════════════════════════════════════════════════════ */
    .section-header {{
        font-size: 0.9rem;
        font-weight: 700;
        color: {COLORS["text_primary"]};
        padding-bottom: 0.2rem;
        margin-bottom: 0.4rem;
        border-bottom: 2px solid;
        border-image: linear-gradient(90deg, {COLORS["cyan"]}, transparent) 1;
    }}

    /* ══════════════════════════════════════════════════════════════════
       15. Responsive media queries
       ══════════════════════════════════════════════════════════════════ */
    @media (max-width: 768px) {{
        .neon-metric-value {{ font-size: 1.3rem; }}
        .login-card {{ padding: 1rem; max-width: 90vw; }}
    }}
    </style>
    """, unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════
# Plotly configuration helpers
# ═══════════════════════════════════════════════════════════════════════════

def configure_plotly_dark(fig: go.Figure) -> go.Figure:
    """Apply dark theme to a 2D Plotly figure."""
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(12,18,35,0.6)",
        font=dict(color="#e0e0ff", size=12),
        margin=dict(l=40, r=20, t=50, b=40),
        legend=dict(font=dict(color="#7a8ba8"), bgcolor="rgba(0,0,0,0)"),
        xaxis=dict(
            gridcolor="rgba(0,245,255,0.08)",
            zerolinecolor="rgba(0,245,255,0.15)",
            color="#7a8ba8",
        ),
        yaxis=dict(
            gridcolor="rgba(0,245,255,0.08)",
            zerolinecolor="rgba(0,245,255,0.15)",
            color="#7a8ba8",
        ),
        colorway=CHART_PALETTE,
    )
    return fig


def configure_plotly_dark_3d(fig: go.Figure, auto_rotate: bool = False,
                              n_frames: int = 36) -> go.Figure:
    """Apply dark 3D scene template to a Plotly figure.

    Args:
        fig: Plotly figure to configure.
        auto_rotate: If True, add auto-rotation animation frames + play/pause button.
        n_frames: Number of rotation frames (default 36 = 10° per frame).
    """
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#e0e0ff", size=11),
        margin=dict(l=10, r=10, t=50, b=10),
        scene=SCENE_3D_DARK,
        colorway=CHART_PALETTE,
    )
    if auto_rotate:
        _add_3d_auto_rotate_frames(fig, n_frames)
        fig.update_layout(**LAYOUT_3D_AUTO_ROTATE)
    return fig


def _add_3d_auto_rotate_frames(fig: go.Figure, n_frames: int = 36) -> None:
    """Generate rotation frames orbiting the Y axis and attach them to the figure.

    The camera eye circles the origin at a fixed height (z=1.4) with radius ~2.5.
    """
    import numpy as np
    x_center, y_center, z_height = 0.0, 0.0, 1.4
    radius = 2.5

    frames = []
    for i in range(n_frames):
        angle = 2.0 * np.pi * i / n_frames
        eye_x = x_center + radius * np.cos(angle)
        eye_y = y_center + radius * np.sin(angle)
        frames.append(go.Frame(
            layout={
                "scene.camera": {
                    "eye": {"x": eye_x, "y": eye_y, "z": z_height},
                    "up": {"x": 0, "y": 0, "z": 1},
                }
            },
            name=f"frame_{i}",
        ))
    fig.frames = frames
