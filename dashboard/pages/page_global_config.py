"""Page 10: Global Configuration — 6 tabs, YAML save/load, JSON import/export, diff viewer."""

from __future__ import annotations

import copy
import difflib
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import streamlit as st
import yaml

from dashboard.components import (
    section_header,
    info_bar,
    neon_metric_card,
)
from dashboard.i18n import get_translator
from dashboard.theme import COLORS

# ── Constants ────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
CONFIG_PATH = PROJECT_ROOT / "config.yaml"
CONFIG_BACKUP_PATH = PROJECT_ROOT / "config_backup.yaml"

# ── Default configuration values ─────────────────────────────────────────
DEFAULT_CONFIG: Dict[str, Any] = {
    # Tab 1: Model & Embedding
    "ollama_model_name": "llama3:8b",
    "ollama_base_url": "http://localhost:11434",
    "ollama_temperature": 0.7,
    "ollama_num_ctx": 2048,
    "ollama_flash_attn": False,
    "ollama_max_retries": 2,
    "ollama_timeout_seconds": 120.0,
    "embedding_model_name": "sentence-transformers/all-MiniLM-L6-v2",
    "embedding_dim": 128,
    "max_tfidf_features": 2400,
    "allow_dma_legacy_fallback": True,
    "max_concurrent_requests": 4,

    # Tab 2: Agent Strategy
    "raa_strategy_combo": ["mixed", "rerank", "adaptive"],
    "nash_max_rounds": 6,
    "deep_retrieval_top_k": 10,
    "fast_retrieval_top_k": 5,
    "dma_centroid_weight": 0.50,
    "dma_retrieval_weight": 0.34,
    "dma_lexical_weight": 0.12,
    "dma_context_weight": 0.02,
    "dma_tfa_weight": 0.02,
    "consensus_threshold": 0.6,
    "topology_type": "hierarchical",
    "fusion_conflict_hamming_threshold": 0.3,
    "fusion_duplicate_hamming_threshold": 0.1,

    # Tab 3: Thresholds
    "confidence_threshold": 0.62,
    "retrieval_relevance_threshold": 0.24,
    "query_uncertainty_threshold": 0.58,
    "high_risk_tfa_threshold": 0.7,
    "verification_max_age_days": 365,
    "cost_lambda": 0.72,
    "agent_timeout_seconds": 120.0,

    # Tab 4: Feature Toggles
    "enable_hitl": True,
    "enable_interactive_hitl": True,
    "enable_tfa": True,
    "enable_medtsllm": True,
    "enable_multimodal": False,
    "enable_privacy": True,
    "enable_maintenance": True,
    "enable_consensus": True,
    "enable_dynamic_kb": True,
    "enable_distillation": False,
    "enable_tri_source_fusion": True,
    "enable_faiss_dense_index": True,

    # Tab 5: Clinical & Privacy
    "short_window_hours": 24.0,
    "mid_window_days": 30.0,
    "long_window_months": 12.0,
    "source_weights": [0.4, 0.3, 0.2, 0.1],
    "secure_gradient_noise_std": 0.015,
    "continuous_learning_min_feedback": 50,
    "acute_short_window_multiplier": 3.0,
    "chronic_long_window_multiplier": 2.0,

    # Tab 6: Experiment
    "target_classes": 21,
    "experiment_noise_levels": "0.0,0.05,0.1,0.15,0.2",
    "ablation_sample_count": 500,
    "robustness_sample_count": 500,
    "adaptability_sample_count": 500,
    "common_rare_sample_count": 500,
}


# ═══════════════════════════════════════════════════════════════════════════
# Data helpers
# ═══════════════════════════════════════════════════════════════════════════

def _load_current_config() -> Tuple[Dict[str, Any], Optional[float]]:
    """Load config from YAML file. Returns (config_dict, mtime_or_None)."""
    if not CONFIG_PATH.exists():
        return copy.deepcopy(DEFAULT_CONFIG), None
    try:
        raw = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8")) or {}
        mtime = CONFIG_PATH.stat().st_mtime
        # Merge with defaults so all keys exist
        merged = copy.deepcopy(DEFAULT_CONFIG)
        merged.update({k: v for k, v in raw.items() if k in merged})
        return merged, mtime
    except (yaml.YAMLError, OSError):
        return copy.deepcopy(DEFAULT_CONFIG), None


def _detect_concurrent_modification(original_mtime: Optional[float]) -> bool:
    """Return True if the config file mtime has changed since we loaded it."""
    if original_mtime is None:
        return CONFIG_PATH.exists()
    if not CONFIG_PATH.exists():
        return False
    try:
        current_mtime = CONFIG_PATH.stat().st_mtime
        return abs(current_mtime - original_mtime) > 0.01
    except OSError:
        return False


def _compute_weights_sum(cfg: Dict[str, Any]) -> float:
    """Compute sum of DMA weights."""
    return (
        cfg.get("dma_centroid_weight", 0)
        + cfg.get("dma_retrieval_weight", 0)
        + cfg.get("dma_lexical_weight", 0)
        + cfg.get("dma_context_weight", 0)
        + cfg.get("dma_tfa_weight", 0)
    )


# ═══════════════════════════════════════════════════════════════════════════
# Config diff viewer
# ═══════════════════════════════════════════════════════════════════════════

def _show_config_diff(file_config: Dict[str, Any], current_config: Dict[str, Any], t) -> None:
    """Render a unified diff between the file config and current session config."""
    file_lines = json.dumps(file_config, indent=2, ensure_ascii=False, sort_keys=True).splitlines()
    current_lines = json.dumps(current_config, indent=2, ensure_ascii=False, sort_keys=True).splitlines()

    diff = list(difflib.unified_diff(
        file_lines, current_lines,
        fromfile="config.yaml (file)",
        tofile="config.yaml (current)",
        lineterm="",
    ))

    if not diff:
        st.success(t("config.saved_ok"))
        return

    diff_text = "\n".join(diff)
    st.markdown(f"**{t('config.diff_title')}**")
    st.code(diff_text, language="diff", line_numbers=False)


# ═══════════════════════════════════════════════════════════════════════════
# Tab renderers
# ═══════════════════════════════════════════════════════════════════════════

def _render_tab_model(cfg: Dict[str, Any], t) -> None:
    """Tab 1: Model & Embedding."""
    col1, col2 = st.columns(2)
    with col1:
        cfg["ollama_model_name"] = st.text_input(
            "ollama_model_name", cfg.get("ollama_model_name", ""),
            help="Ollama model tag (e.g. llama3:8b, qwen2:7b)",
            key="cfg_ollama_model_name",
        )
        cfg["ollama_base_url"] = st.text_input(
            "ollama_base_url", cfg.get("ollama_base_url", ""),
            help="Ollama API endpoint",
            key="cfg_ollama_base_url",
        )
        cfg["ollama_temperature"] = st.slider(
            "ollama_temperature", 0.0, 2.0, float(cfg.get("ollama_temperature", 0.7)),
            0.05, key="cfg_ollama_temperature",
            help="LLM sampling temperature",
        )
        cfg["ollama_num_ctx"] = st.number_input(
            "ollama_num_ctx", 512, 32768, int(cfg.get("ollama_num_ctx", 2048)),
            256, key="cfg_ollama_num_ctx",
            help="Context window size (tokens)",
        )
        cfg["ollama_flash_attn"] = st.toggle(
            "ollama_flash_attn", bool(cfg.get("ollama_flash_attn", False)),
            key="cfg_ollama_flash_attn",
            help="Enable Flash Attention for faster inference",
        )
        cfg["ollama_max_retries"] = st.number_input(
            "ollama_max_retries", 0, 10, int(cfg.get("ollama_max_retries", 2)),
            key="cfg_ollama_max_retries",
            help="Max retries for Ollama API calls",
        )
    with col2:
        cfg["ollama_timeout_seconds"] = st.number_input(
            "ollama_timeout_seconds", 10.0, 600.0,
            float(cfg.get("ollama_timeout_seconds", 120.0)),
            10.0, key="cfg_ollama_timeout_seconds",
            help="Ollama request timeout in seconds",
        )
        cfg["embedding_model_name"] = st.text_input(
            "embedding_model_name", cfg.get("embedding_model_name", ""),
            help="Sentence-transformers model name",
            key="cfg_embedding_model_name",
        )
        cfg["embedding_dim"] = st.number_input(
            "embedding_dim", 32, 1024, int(cfg.get("embedding_dim", 128)),
            32, key="cfg_embedding_dim",
            help="Embedding vector dimension",
        )
        cfg["max_tfidf_features"] = st.number_input(
            "max_tfidf_features", 500, 20000, int(cfg.get("max_tfidf_features", 2400)),
            100, key="cfg_max_tfidf_features",
            help="Max TF-IDF feature count",
        )
        cfg["allow_dma_legacy_fallback"] = st.toggle(
            "allow_dma_legacy_fallback", bool(cfg.get("allow_dma_legacy_fallback", True)),
            key="cfg_allow_dma_legacy_fallback",
            help="Allow the explicitly labelled statistical DMA fallback when the configured local Ollama model is unavailable",
        )
        cfg["max_concurrent_requests"] = st.number_input(
            "max_concurrent_requests", 1, 32, int(cfg.get("max_concurrent_requests", 4)),
            key="cfg_max_concurrent_requests",
            help="Max concurrent inference requests",
        )


def _render_tab_strategy(cfg: Dict[str, Any], t) -> None:
    """Tab 2: Agent Strategy."""
    col1, col2 = st.columns(2)
    with col1:
        all_strategies = ["mixed", "rerank", "adaptive"]
        current_combo = cfg.get("raa_strategy_combo", [])
        if isinstance(current_combo, str):
            current_combo = [s.strip() for s in current_combo.split(",") if s.strip()]
        cfg["raa_strategy_combo"] = st.multiselect(
            "raa_strategy_combo", all_strategies,
            default=[s for s in current_combo if s in all_strategies],
            key="cfg_raa_strategy_combo",
            help="RAG retrieval strategies to use",
        )
        cfg["nash_max_rounds"] = st.slider(
            "nash_max_rounds", 1, 20, int(cfg.get("nash_max_rounds", 6)),
            key="cfg_nash_max_rounds",
            help="Maximum Nash negotiation rounds",
        )
        cfg["deep_retrieval_top_k"] = st.number_input(
            "deep_retrieval_top_k", 1, 50, int(cfg.get("deep_retrieval_top_k", 10)),
            key="cfg_deep_retrieval_top_k",
            help="Top-K for deep retrieval path",
        )
        cfg["fast_retrieval_top_k"] = st.number_input(
            "fast_retrieval_top_k", 1, 50, int(cfg.get("fast_retrieval_top_k", 5)),
            key="cfg_fast_retrieval_top_k",
            help="Top-K for fast retrieval path",
        )
        cfg["consensus_threshold"] = st.slider(
            "consensus_threshold", 0.0, 1.0, float(cfg.get("consensus_threshold", 0.6)),
            0.05, key="cfg_consensus_threshold",
            help="Minimum agreement ratio for consensus",
        )
        cfg["topology_type"] = st.selectbox(
            "topology_type",
            ["hierarchical", "mesh", "star", "ring", "hybrid"],
            index=["hierarchical", "mesh", "star", "ring", "hybrid"].index(
                cfg.get("topology_type", "hierarchical")
            ) if cfg.get("topology_type", "hierarchical") in ["hierarchical", "mesh", "star", "ring", "hybrid"] else 0,
            key="cfg_topology_type",
            help="Agent communication topology",
        )

    with col2:
        st.caption("DMA Weights (should sum to 1.0)")
        cfg["dma_centroid_weight"] = st.slider(
            "dma_centroid_weight", 0.0, 1.0,
            float(cfg.get("dma_centroid_weight", 0.5)),
            0.01, key="cfg_dma_centroid_weight",
        )
        cfg["dma_retrieval_weight"] = st.slider(
            "dma_retrieval_weight", 0.0, 1.0,
            float(cfg.get("dma_retrieval_weight", 0.34)),
            0.01, key="cfg_dma_retrieval_weight",
        )
        cfg["dma_lexical_weight"] = st.slider(
            "dma_lexical_weight", 0.0, 1.0,
            float(cfg.get("dma_lexical_weight", 0.12)),
            0.01, key="cfg_dma_lexical_weight",
        )
        cfg["dma_context_weight"] = st.slider(
            "dma_context_weight", 0.0, 1.0,
            float(cfg.get("dma_context_weight", 0.02)),
            0.01, key="cfg_dma_context_weight",
        )
        cfg["dma_tfa_weight"] = st.slider(
            "dma_tfa_weight", 0.0, 1.0,
            float(cfg.get("dma_tfa_weight", 0.02)),
            0.01, key="cfg_dma_tfa_weight",
        )
        dma_sum = _compute_weights_sum(cfg)
        sum_color = COLORS["success"] if abs(dma_sum - 1.0) < 0.02 else COLORS["danger"]
        st.markdown(
            f'<span style="color:{sum_color};font-weight:700;">DMA Weight Sum: {dma_sum:.3f}</span>'
            + (f' <span style="color:{COLORS["danger"]};">⚠️ {t("config.weights_sum_warning")}</span>'
               if abs(dma_sum - 1.0) >= 0.02 else ""),
            unsafe_allow_html=True,
        )

        st.markdown("---")
        cfg["fusion_conflict_hamming_threshold"] = st.slider(
            "fusion_conflict_hamming_threshold", 0.0, 1.0,
            float(cfg.get("fusion_conflict_hamming_threshold", 0.3)),
            0.05, key="cfg_fusion_conflict_hamming_threshold",
            help="Hamming distance threshold for conflict detection",
        )
        cfg["fusion_duplicate_hamming_threshold"] = st.slider(
            "fusion_duplicate_hamming_threshold", 0.0, 1.0,
            float(cfg.get("fusion_duplicate_hamming_threshold", 0.1)),
            0.05, key="cfg_fusion_duplicate_hamming_threshold",
            help="Hamming distance threshold for duplicate detection",
        )


def _render_tab_thresholds(cfg: Dict[str, Any], t) -> None:
    """Tab 3: Thresholds."""
    col1, col2 = st.columns(2)
    with col1:
        cfg["confidence_threshold"] = st.slider(
            "confidence_threshold", 0.0, 1.0,
            float(cfg.get("confidence_threshold", 0.62)),
            0.01, key="cfg_confidence_threshold",
            help="Minimum confidence to accept prediction",
        )
        cfg["retrieval_relevance_threshold"] = st.slider(
            "retrieval_relevance_threshold", 0.0, 1.0,
            float(cfg.get("retrieval_relevance_threshold", 0.24)),
            0.01, key="cfg_retrieval_relevance_threshold",
            help="Minimum relevance score for retrieved documents",
        )
        cfg["query_uncertainty_threshold"] = st.slider(
            "query_uncertainty_threshold", 0.0, 1.0,
            float(cfg.get("query_uncertainty_threshold", 0.58)),
            0.01, key="cfg_query_uncertainty_threshold",
            help="Uncertainty level triggering deep retrieval",
        )
        cfg["high_risk_tfa_threshold"] = st.slider(
            "high_risk_tfa_threshold", 0.0, 1.0,
            float(cfg.get("high_risk_tfa_threshold", 0.7)),
            0.01, key="cfg_high_risk_tfa_threshold",
            help="TFA risk score threshold for high-risk alert",
        )
    with col2:
        cfg["verification_max_age_days"] = st.number_input(
            "verification_max_age_days", 1, 3650,
            int(cfg.get("verification_max_age_days", 365)),
            key="cfg_verification_max_age_days",
            help="Max document age (days) for verification",
        )
        cfg["cost_lambda"] = st.slider(
            "cost_lambda", 0.0, 1.0, float(cfg.get("cost_lambda", 0.72)),
            0.01, key="cfg_cost_lambda",
            help="Cost-weighting factor for agent decision trade-off",
        )
        cfg["agent_timeout_seconds"] = st.number_input(
            "agent_timeout_seconds", 10.0, 600.0,
            float(cfg.get("agent_timeout_seconds", 120.0)),
            10.0, key="cfg_agent_timeout_seconds",
            help="Per-agent operation timeout",
        )


def _render_tab_features(cfg: Dict[str, Any], t) -> None:
    """Tab 4: Feature Toggles."""
    toggles = [
        ("enable_hitl", "Human-in-the-Loop"),
        ("enable_interactive_hitl", "Interactive HITL"),
        ("enable_tfa", "Temporal Foreseeing Agent (TFA)"),
        ("enable_medtsllm", "MedTsLLM Backend"),
        ("enable_multimodal", "Multimodal Input"),
        ("enable_privacy", "Privacy Protection"),
        ("enable_maintenance", "Auto-Maintenance Agent"),
        ("enable_consensus", "Hierarchical Consensus"),
        ("enable_dynamic_kb", "Dynamic Knowledge Base"),
        ("enable_distillation", "Model Distillation"),
        ("enable_tri_source_fusion", "Tri-Source Knowledge Fusion"),
        ("enable_faiss_dense_index", "FAISS Dense Index"),
    ]

    cols = st.columns(3)
    for i, (key, label) in enumerate(toggles):
        with cols[i % 3]:
            cfg[key] = st.toggle(
                f"{'🟢' if cfg.get(key, False) else '⚪'} {label}",
                bool(cfg.get(key, False)),
                key=f"cfg_{key}",
            )


def _render_tab_clinical(cfg: Dict[str, Any], t) -> None:
    """Tab 5: Clinical & Privacy."""
    col1, col2 = st.columns(2)
    with col1:
        cfg["short_window_hours"] = st.number_input(
            "short_window_hours", 1.0, 168.0,
            float(cfg.get("short_window_hours", 24.0)),
            1.0, key="cfg_short_window_hours",
            help="Short-term risk window (hours)",
        )
        cfg["mid_window_days"] = st.number_input(
            "mid_window_days", 1.0, 365.0,
            float(cfg.get("mid_window_days", 30.0)),
            1.0, key="cfg_mid_window_days",
            help="Mid-term risk window (days)",
        )
        cfg["long_window_months"] = st.number_input(
            "long_window_months", 1.0, 60.0,
            float(cfg.get("long_window_months", 12.0)),
            1.0, key="cfg_long_window_months",
            help="Long-term risk window (months)",
        )
        cfg["acute_short_window_multiplier"] = st.slider(
            "acute_short_window_multiplier", 1.0, 10.0,
            float(cfg.get("acute_short_window_multiplier", 3.0)),
            0.5, key="cfg_acute_short_window_multiplier",
            help="Multiplier for acute conditions on short window",
        )
        cfg["chronic_long_window_multiplier"] = st.slider(
            "chronic_long_window_multiplier", 1.0, 10.0,
            float(cfg.get("chronic_long_window_multiplier", 2.0)),
            0.5, key="cfg_chronic_long_window_multiplier",
            help="Multiplier for chronic conditions on long window",
        )
    with col2:
        st.caption("Source Weights (knowledge sources)")
        sw = cfg.get("source_weights", [0.4, 0.3, 0.2, 0.1])
        if not isinstance(sw, list) or len(sw) != 4:
            sw = [0.4, 0.3, 0.2, 0.1]
        sw_labels = ["Clinical Guidelines", "Research Papers", "Medical Textbooks", "Expert Knowledge"]
        new_sw = []
        for i, label in enumerate(sw_labels):
            val = st.slider(f"  {label}", 0.0, 1.0, float(sw[i]) if i < len(sw) else 0.25,
                            0.05, key=f"cfg_source_weight_{i}")
            new_sw.append(val)
        cfg["source_weights"] = new_sw

        st.markdown("---")
        cfg["secure_gradient_noise_std"] = st.slider(
            "secure_gradient_noise_std", 0.0, 0.5,
            float(cfg.get("secure_gradient_noise_std", 0.015)),
            0.001, key="cfg_secure_gradient_noise_std",
            help="Differential privacy noise standard deviation",
        )
        cfg["continuous_learning_min_feedback"] = st.number_input(
            "continuous_learning_min_feedback", 10, 1000,
            int(cfg.get("continuous_learning_min_feedback", 50)),
            key="cfg_continuous_learning_min_feedback",
            help="Minimum feedback samples before triggering continuous learning",
        )


def _render_tab_experiment(cfg: Dict[str, Any], t) -> None:
    """Tab 6: Experiment Settings."""
    col1, col2 = st.columns(2)
    with col1:
        cfg["target_classes"] = st.number_input(
            "target_classes", 1, 100, int(cfg.get("target_classes", 21)),
            key="cfg_target_classes",
            help="Number of target disease classes",
        )
        cfg["experiment_noise_levels"] = st.text_input(
            "experiment_noise_levels",
            str(cfg.get("experiment_noise_levels", "0.0,0.05,0.1,0.15,0.2")),
            key="cfg_experiment_noise_levels",
            help="Comma-separated noise levels for robustness testing",
        )
    with col2:
        cfg["ablation_sample_count"] = st.number_input(
            "ablation_sample_count", min_value=100, max_value=10000,
            value=max(100, int(cfg.get("ablation_sample_count", 500))),
            step=100, key="cfg_ablation_sample_count",
        )
        cfg["robustness_sample_count"] = st.number_input(
            "robustness_sample_count", min_value=100, max_value=10000,
            value=max(100, int(cfg.get("robustness_sample_count", 500))),
            step=100, key="cfg_robustness_sample_count",
        )
        cfg["adaptability_sample_count"] = st.number_input(
            "adaptability_sample_count", min_value=100, max_value=10000,
            value=max(100, int(cfg.get("adaptability_sample_count", 500))),
            step=100, key="cfg_adaptability_sample_count",
        )
        cfg["common_rare_sample_count"] = st.number_input(
            "common_rare_sample_count", min_value=100, max_value=10000,
            value=max(100, int(cfg.get("common_rare_sample_count", 500))),
            step=100, key="cfg_common_rare_sample_count",
        )


# ═══════════════════════════════════════════════════════════════════════════
# Main render
# ═══════════════════════════════════════════════════════════════════════════

def render(eco: Any, config: Any, dataset: Any, monitor: Any) -> None:
    """Render Global Configuration page."""
    t = get_translator()

    section_header(t("config.title"), "⚙️", "cyan")

    # ── Initialize session config ────────────────────────────────────
    if "cfg_working" not in st.session_state:
        loaded, mtime = _load_current_config()
        # Also overlay current runtime config if available
        if config is not None:
            try:
                for key in loaded:
                    val = getattr(config, key, None)
                    if val is not None:
                        loaded[key] = val
            except Exception:
                pass
        st.session_state.cfg_working = loaded
        st.session_state.cfg_mtime = mtime
        st.session_state.cfg_original = copy.deepcopy(loaded)

    cfg: Dict[str, Any] = st.session_state.cfg_working

    # ═══════════════════════════════════════════════════════════════════
    # 6 Tabs
    # ═══════════════════════════════════════════════════════════════════
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        f"🧠 {t('config.tab_model')}",
        f"🎯 {t('config.tab_strategy')}",
        f"📏 {t('config.tab_thresholds')}",
        f"🔘 {t('config.tab_features')}",
        f"🏥 {t('config.tab_clinical')}",
        f"🔬 {t('config.tab_experiment')}",
    ])

    with tab1:
        _render_tab_model(cfg, t)
    with tab2:
        _render_tab_strategy(cfg, t)
    with tab3:
        _render_tab_thresholds(cfg, t)
    with tab4:
        _render_tab_features(cfg, t)
    with tab5:
        _render_tab_clinical(cfg, t)
    with tab6:
        _render_tab_experiment(cfg, t)

    # ═══════════════════════════════════════════════════════════════════
    # Bottom Action Bar
    # ═══════════════════════════════════════════════════════════════════
    st.markdown("---")
    section_header(f"{t('common.save')} / {t('common.export')} / {t('common.import')}", "💾", "cyan")

    # ═══════════════════════════════════════════════════════════════
    # Row A: Save + Diff View
    # ═══════════════════════════════════════════════════════════════
    a1, a2, a3, a4 = st.columns([1, 1, 1, 1])

    with a1:
        if st.button(f"💾 {t('config.save_yaml')}", use_container_width=True, key="cfg_save"):
            original_mtime = st.session_state.get("cfg_mtime")
            if _detect_concurrent_modification(original_mtime):
                info_bar(t("config.conflict_warning"), "warning")
            else:
                # Validate weights
                dma_sum = _compute_weights_sum(cfg)
                if abs(dma_sum - 1.0) >= 0.02:
                    info_bar(t("config.weights_sum_warning"), "warning")

                # Backup existing config
                try:
                    if CONFIG_PATH.exists():
                        backup_content = CONFIG_PATH.read_text(encoding="utf-8")
                        CONFIG_BACKUP_PATH.write_text(backup_content, encoding="utf-8")
                        info_bar(t("config.backup_ok"), "success")
                except OSError as exc:
                    info_bar(f"{t('config.permission_denied')}: {exc}", "error")
                    st.stop()

                # Write config
                try:
                    yaml_text = yaml.dump(
                        dict(cfg), default_flow_style=False,
                        allow_unicode=True, sort_keys=False,
                    )
                    CONFIG_PATH.write_text(f"# MAPFM repaired configuration\n{yaml_text}", encoding="utf-8")
                    info_bar(t("config.saved_ok"), "success")
                    # Track diff
                    loaded_file, _ = _load_current_config()
                    st.session_state.cfg_original = copy.deepcopy(cfg)
                    st.session_state.cfg_mtime = CONFIG_PATH.stat().st_mtime if CONFIG_PATH.exists() else None
                    _show_config_diff(st.session_state.cfg_original, cfg, t)
                except OSError as exc:
                    info_bar(f"{t('config.permission_denied')}: {exc}", "error")

    with a2:
        if st.button(f"🔍 {t('config.view_diff')}", use_container_width=True, key="cfg_view_diff"):
            file_cfg, _ = _load_current_config()
            if file_cfg:
                _show_config_diff(file_cfg, cfg, t)
            else:
                info_bar(t("config.validation_error"), "warning")

    with a3:
        # Export JSON
        export_payload = json.dumps(dict(cfg), indent=2, ensure_ascii=False, default=str).encode("utf-8")
        st.download_button(
            f"📤 {t('config.export_json')}",
            export_payload,
            f"mapfm_config_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            "application/json",
            key="cfg_export_json",
            use_container_width=True,
        )

    with a4:
        # Reset to defaults
        if st.button(f"🔄 {t('config.reset_defaults')}", use_container_width=True, key="cfg_reset_defaults"):
            st.session_state.cfg_confirm_reset = True

    if st.session_state.get("cfg_confirm_reset"):
        st.warning(t("config.reset_confirm"))
        rc1, rc2 = st.columns(2)
        with rc1:
            if st.button(f"✅ {t('common.confirm')}", key="cfg_reset_confirm_yes", use_container_width=True):
                st.session_state.cfg_working = copy.deepcopy(DEFAULT_CONFIG)
                st.session_state.cfg_original = copy.deepcopy(DEFAULT_CONFIG)
                st.session_state.cfg_confirm_reset = False
                info_bar(t("config.saved_ok"), "success")
                st.rerun()
        with rc2:
            if st.button(f"❌ {t('common.cancel')}", key="cfg_reset_confirm_no", use_container_width=True):
                st.session_state.cfg_confirm_reset = False
                st.rerun()

    # ═══════════════════════════════════════════════════════════════
    # Row B: Import JSON
    # ═══════════════════════════════════════════════════════════════
    st.markdown("---")
    section_header(t("config.import_json"), "📥", "violet")

    uploaded_file = st.file_uploader(
        t("config.import_json"), type=["json"], key="cfg_import_file",
        label_visibility="collapsed",
    )
    if uploaded_file is not None:
        try:
            imported_data = json.loads(uploaded_file.read().decode("utf-8"))
            if not isinstance(imported_data, dict):
                info_bar(t("config.validation_error"), "error")
            else:
                # Validate fields: only accept known keys
                known_keys = set(DEFAULT_CONFIG.keys())
                unknown_keys = set(imported_data.keys()) - known_keys
                valid_data = {k: v for k, v in imported_data.items() if k in known_keys}

                if not valid_data:
                    info_bar(t("config.validation_error"), "error")
                else:
                    # Apply to working config
                    st.session_state.cfg_working.update(valid_data)
                    total_fields = len(valid_data)
                    info_bar(
                        t("config.import_ok", count=str(total_fields)),
                        "success",
                    )
                    if unknown_keys:
                        info_bar(
                            f"{t('config.import_unknown')}: {', '.join(sorted(unknown_keys)[:10])}",
                            "warning",
                        )
                    st.rerun()
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            info_bar(f"{t('config.validation_error')}: {exc}", "error")
