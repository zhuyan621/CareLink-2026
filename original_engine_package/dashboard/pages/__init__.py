"""Page registry and routing for the MAPFM HMAE Control Panel.

Each page module exposes a function with signature:
    render(eco, config, dataset, monitor) -> None
"""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Tuple

# ═══════════════════════════════════════════════════════════════════════════
PAGE_REGISTRY: Dict[str, Dict[str, Any]] = {
    "competition": {
        "icon": "🏆",
        "zh": "科B真实性证据",
        "en": "Track-B Evidence",
        "module": "dashboard.pages.page_competition",
        "handler_name": "render",
    },
    "diagnosis": {
        "icon": "🩺",
        "zh": "科研分析演示",
        "en": "Research Analysis Demo",
        "module": "dashboard.pages.page_diagnosis",
        "handler_name": "render",
    },
    "overview": {
        "icon": "📊",
        "zh": "系统概览",
        "en": "System Overview",
        "module": "dashboard.pages.page_overview",
        "handler_name": "render",
    },
    "agent_monitor": {
        "icon": "🤖",
        "zh": "智能体监控",
        "en": "Agent Monitor",
        "module": "dashboard.pages.page_agent_monitor",
        "handler_name": "render",
    },
    "hardware_metrics": {
        "icon": "💻",
        "zh": "硬件监控",
        "en": "Hardware Metrics",
        "module": "dashboard.pages.page_hardware_metrics",
        "handler_name": "render",
    },
    "experiments": {
        "icon": "🔬",
        "zh": "实验诊断",
        "en": "Experiments",
        "module": "dashboard.pages.page_experiments",
        "handler_name": "render",
    },
    "knowledge_base": {
        "icon": "📚",
        "zh": "知识库管理",
        "en": "Knowledge Base",
        "module": "dashboard.pages.page_knowledge_base",
        "handler_name": "render",
    },
    "human_review": {
        "icon": "✋",
        "zh": "人工审核与校准",
        "en": "Human Review",
        "module": "dashboard.pages.page_human_review",
        "handler_name": "render",
    },
    "clinical_safety": {
        "icon": "🛡️",
        "zh": "临床安全监测",
        "en": "Clinical Safety",
        "module": "dashboard.pages.page_clinical_safety",
        "handler_name": "render",
    },
    "history_logs": {
        "icon": "📋",
        "zh": "历史任务日志",
        "en": "History & Logs",
        "module": "dashboard.pages.page_history_logs",
        "handler_name": "render",
    },
    "audit_log": {
        "icon": "🔍",
        "zh": "审计日志",
        "en": "Audit Log",
        "module": "dashboard.pages.page_audit_log",
        "handler_name": "render",
    },
    "global_config": {
        "icon": "⚙️",
        "zh": "全局配置",
        "en": "Global Config",
        "module": "dashboard.pages.page_global_config",
        "handler_name": "render",
    },
}

ALL_PAGES: List[str] = list(PAGE_REGISTRY.keys())


# ═══════════════════════════════════════════════════════════════════════════

def get_page_meta(page_key: str, lang: str) -> Tuple[str, str]:
    """Return (icon, display_name) for a page key in the given language."""
    meta = PAGE_REGISTRY.get(page_key, {})
    icon = meta.get("icon", "📄")
    name = meta.get(lang, page_key)
    return icon, name


def get_page_handler(page_key: str) -> "Callable":
    """Lazy-import and return the render function for a page key."""
    meta = PAGE_REGISTRY.get(page_key)
    if not meta:
        from dashboard.pages.page_overview import render
        return render

    module_name = meta["module"]
    handler_name = meta["handler_name"]

    import importlib
    mod = importlib.import_module(module_name)
    return getattr(mod, handler_name)
