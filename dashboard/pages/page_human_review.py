"""Page 6: Human Review & Calibration — review queue, calibration, continuous learning."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict

import streamlit as st

from dashboard.components import (
    neon_metric_card, section_header, info_bar, pulse_status_badge,
    gauge_chart, sparkline_chart,
)
from dashboard.i18n import get_translator


def render(eco: Any, config: Any, dataset: Any, monitor: Any) -> None:
    t = get_translator()

    task_count = len(eco.task_history) if eco is not None and hasattr(eco, 'task_history') else 0
    # Get pending buffer
    buffer_size = 0
    buffer_list = []
    if eco is not None:
        try:
            buf = eco.learning_loop.feedback_buffer if hasattr(eco.learning_loop, 'feedback_buffer') else []
            buffer_list = list(buf) if buf else []
            buffer_size = len(buffer_list)
        except Exception:
            pass

    hitl_count = 0
    if eco is not None:
        try:
            hitl_count = eco.hitl_manager.intervention_count if hasattr(eco.hitl_manager, 'intervention_count') else 0
        except Exception:
            pass

    hitl_rate = 0.0
    if task_count > 0 and eco is not None:
        triggered = sum(1 for tk in eco.task_history if isinstance(tk, dict) and tk.get("hitl", {}).get("triggered", False))
        hitl_rate = triggered / task_count

    # ═══════════════════════════════════════════════════════════════════
    # Handle review actions via session_state
    # ═══════════════════════════════════════════════════════════════════
    _handle_review_actions(buffer_list, eco, t)

    # ═══════════════════════════════════════════════════════════════════
    # Row 1: Stats
    # ═══════════════════════════════════════════════════════════════════
    section_header(t("review.stats"), "📊", "cyan")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        neon_metric_card(t("review.total_diagnoses"), str(task_count), icon="📋",
                         neon_color="cyan", key="hr_total")
    with c2:
        color = "magenta" if buffer_size > 0 else "green"
        neon_metric_card(t("review.pending_review"), str(buffer_size), icon="⏳",
                         neon_color=color, key="hr_pending")
    with c3:
        # Count reviewed items from session state
        reviewed = st.session_state.get("hr_reviewed_count", 0)
        neon_metric_card(t("review.reviewed_count"), str(hitl_count + reviewed), icon="✅",
                         neon_color="green", key="hr_reviewed")
    with c4:
        neon_metric_card(t("review.hitl_rate"), f"{hitl_rate:.1%}", icon="⚠️",
                         neon_color="amber" if hitl_rate > 0.1 else "green", key="hr_rate")

    # ═══════════════════════════════════════════════════════════════════
    # Row 2: Review Queue
    # ═══════════════════════════════════════════════════════════════════
    section_header(t("review.review_queue"), "📝", "magenta")

    if buffer_size == 0:
        info_bar(t("review.no_pending"), "success")
    else:
        threshold = getattr(config, 'continuous_learning_min_feedback', 10) if config else 10
        if buffer_size >= threshold * 0.8:
            info_bar(t("review.buffer_warning"), "warning")

        for i, record in enumerate(buffer_list[:20]):  # Show top 20
            if not isinstance(record, dict):
                record = record.__dict__ if hasattr(record, '__dict__') else {}
            query = str(record.get("query", "—"))[:60]
            pred = str(record.get("predicted_label", "—"))
            conf = record.get("confidence", 0)
            risk = record.get("tfa_risk", record.get("risk_score", "—"))
            err_type = record.get("error_type", "—")
            ts = _fmt(record.get("timestamp", ""))

            # Detect urgency: high risk + low confidence = urgent
            is_urgent = False
            try:
                risk_val = float(risk) if risk not in ("—", None, "") else 0
                conf_val = float(conf) if conf not in ("—", None, "") else 1
                if risk_val > 0.5 and conf_val < 0.6:
                    is_urgent = True
            except (ValueError, TypeError):
                pass

            urgent_style = (
                "animation: pulse-dot-glow 1s ease-in-out infinite; "
                "border-left: 3px solid #ff3344; "
            ) if is_urgent else ""

            with st.container():
                st.markdown(f"""
                <div style="padding:0.3rem 0.5rem;margin:0.2rem 0;
                            background:rgba(16,24,48,0.6);border-radius:6px;
                            {urgent_style}">
                </div>
                """, unsafe_allow_html=True)

                cols = st.columns([2, 1, 1, 1, 1, 1, 2])
                with cols[0]:
                    urgent_marker = "🔴 " if is_urgent else ""
                    st.caption(f"{urgent_marker}{query}")
                with cols[1]:
                    st.caption(f"**{pred}**")
                with cols[2]:
                    st.caption(f"{conf:.3f}" if isinstance(conf, (int, float)) else "—")
                with cols[3]:
                    st.caption(str(risk)[:10])
                with cols[4]:
                    st.caption(str(err_type)[:20])
                with cols[5]:
                    st.caption(ts)
                with cols[6]:
                    ac1, ac2, ac3 = st.columns(3)
                    with ac1:
                        if st.button("✅", key=f"hr_app_{i}", help=t("review.approve")):
                            _apply_review(record, "approved", i, eco, t)
                            st.rerun()
                    with ac2:
                        if st.button("✏️", key=f"hr_cor_{i}", help=t("review.correct")):
                            st.session_state[f"hr_correcting_{i}"] = True
                            st.rerun()
                    with ac3:
                        if st.button("❌", key=f"hr_rej_{i}", help=t("review.reject")):
                            _apply_review(record, "rejected", i, eco, t)
                            st.rerun()

                # Correction dialog (shown when correct button clicked)
                if st.session_state.get(f"hr_correcting_{i}", False):
                    with st.expander(f"✏️ {t('review.correct')} — {query[:50]}...", expanded=True):
                        correct_label = st.text_input(
                            t("review.correct_label"),
                            value=str(pred),
                            key=f"hr_corr_label_{i}",
                        )
                        correct_reason = st.text_area(
                            t("review.correct_reason"),
                            placeholder="Why is this correction needed?",
                            key=f"hr_corr_reason_{i}",
                            height=80,
                        )
                        cc1, cc2 = st.columns(2)
                        with cc1:
                            if st.button(f"✅ {t('review.submit_correction')}", key=f"hr_corr_submit_{i}", use_container_width=True):
                                _apply_review(record, "corrected", i, eco, t,
                                              correct_label=correct_label,
                                              correct_reason=correct_reason)
                                st.session_state.pop(f"hr_correcting_{i}", None)
                                st.rerun()
                        with cc2:
                            if st.button("❌ Cancel", key=f"hr_corr_cancel_{i}", use_container_width=True):
                                st.session_state.pop(f"hr_correcting_{i}", None)
                                st.rerun()
                st.divider()

    # ═══════════════════════════════════════════════════════════════════
    # Row 3: Calibration Panel
    # ═══════════════════════════════════════════════════════════════════
    section_header(t("review.calibration"), "🔧", "violet")
    cc1, cc2 = st.columns(2)

    with cc1:
        st.markdown(f"**🔬 {t('review.platt_status')}**")
        try:
            if eco is not None and hasattr(eco, 'dma'):
                n_samples = len(getattr(eco.dma, '_calibration_pairs', []))
                st.caption(f"{t('review.platt_calibrated')}: {n_samples >= 10}")
                st.caption(f"{t('review.platt_samples')}: {n_samples}")
                st.caption(f"A={getattr(eco.dma, '_platt_A', 0.0):.4f}, B={getattr(eco.dma, '_platt_B', 0.0):.4f}")
            else:
                info_bar(t("review.platt_unavailable"), "info")
        except Exception:
            info_bar(t("review.platt_unavailable"), "info")

    with cc2:
        st.markdown(f"**🔄 Feedback calibration / offline LoRA**")
        try:
            if eco is not None and hasattr(eco, 'lora_finetuner') and eco.lora_finetuner is not None:
                ls = eco.lora_finetuner.get_stats()
                st.caption(f"Implementation: {ls.get('implementation','—')}")
                st.caption(f"Updates: {ls.get('update_count','—')}")
                st.caption(f"Calibration factor: {ls.get('calibration_factor','—')}")
                st.caption("Actual PEFT training is an offline, versioned train_lora.py job.")
            else:
                info_bar("LoRA fine-tuner not available", "info")
        except Exception:
            info_bar("LoRA fine-tuner not available", "info")

    # ═══════════════════════════════════════════════════════════════════
    # Row 4: Continuous Learning
    # ═══════════════════════════════════════════════════════════════════
    section_header(t("review.continuous_learning"), "🔄", "green")
    threshold = getattr(config, 'continuous_learning_min_feedback', 10) if config else 10
    progress = min(buffer_size / threshold, 1.0) if threshold > 0 else 0

    lc1, lc2, lc3, lc4 = st.columns(4)
    with lc1:
        st.metric(t("review.buffer_size"), f"{buffer_size}/{threshold}")
    with lc2:
        st.progress(progress, text=f"{progress:.0%}")
    with lc3:
        try:
            cycle_info = eco.learning_loop.get_stats() if eco is not None else {}
            st.metric(t("review.cycle_count"), str(cycle_info.get("cycle_count", 0)))
        except Exception:
            st.metric(t("review.cycle_count"), "—")
    with lc4:
        try:
            last_upd = cycle_info.get("last_update", "—")
            st.metric(t("review.last_cycle"), _fmt(last_upd))
        except Exception:
            st.metric(t("review.last_cycle"), "—")


# ═══════════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════════

def _handle_review_actions(buffer_list: list, eco: Any, t) -> None:
    """Process any pending review messages from session_state."""
    msg = st.session_state.pop("hr_action_msg", None)
    if msg:
        level = st.session_state.pop("hr_action_level", "success")
        info_bar(msg, level)


def _apply_review(record: dict, action: str, idx: int, eco: Any, t,
                  correct_label: str = "", correct_reason: str = "") -> None:
    """Apply a review action to a record in the feedback buffer."""
    try:
        if eco is not None and hasattr(eco, 'learning_loop'):
            buf = eco.learning_loop.feedback_buffer

            if action == "approved":
                # Mark as verified correct
                if hasattr(eco.learning_loop, 'record_feedback'):
                    eco.learning_loop.record_feedback(
                        record=record,
                        human_label=record.get("predicted_label", ""),
                        is_correct=True,
                        reviewer=st.session_state.get("username", "admin"),
                    )
                # Remove from buffer
                if hasattr(eco.learning_loop, 'remove_from_buffer'):
                    eco.learning_loop.remove_from_buffer(record)
                st.session_state["hr_action_msg"] = t("review.approved_msg")
                st.session_state["hr_action_level"] = "success"

            elif action == "rejected":
                if hasattr(eco.learning_loop, 'record_feedback'):
                    eco.learning_loop.record_feedback(
                        record=record,
                        human_label="REJECTED",
                        is_correct=False,
                        reviewer=st.session_state.get("username", "admin"),
                    )
                if hasattr(eco.learning_loop, 'remove_from_buffer'):
                    eco.learning_loop.remove_from_buffer(record)
                st.session_state["hr_action_msg"] = t("review.rejected_msg")
                st.session_state["hr_action_level"] = "warning"

            elif action == "corrected":
                if hasattr(eco.learning_loop, 'record_feedback'):
                    eco.learning_loop.record_feedback(
                        record=record,
                        human_label=correct_label,
                        is_correct=False,
                        correction_reason=correct_reason,
                        reviewer=st.session_state.get("username", "admin"),
                    )
                # Update the record with corrected label
                if isinstance(record, dict):
                    record["predicted_label"] = correct_label
                    record["correction_reason"] = correct_reason
                elif hasattr(record, '__dict__'):
                    setattr(record, 'predicted_label', correct_label)
                    setattr(record, 'correction_reason', correct_reason)
                if hasattr(eco.learning_loop, 'remove_from_buffer'):
                    eco.learning_loop.remove_from_buffer(record)
                st.session_state["hr_action_msg"] = t("review.corrected_msg")
                st.session_state["hr_action_level"] = "success"

            # Increment reviewed count
            if hasattr(eco, 'dma') and hasattr(eco.dma, 'record_calibration_feedback'):
                confidence = float(record.get("confidence", 0.0)) if isinstance(record, dict) else float(getattr(record, "confidence", 0.0))
                eco.dma.record_calibration_feedback(confidence, action == "approved")
            st.session_state["hr_reviewed_count"] = st.session_state.get("hr_reviewed_count", 0) + 1

    except Exception as exc:
        st.session_state["hr_action_msg"] = f"{t('common.failed')}: {exc}"
        st.session_state["hr_action_level"] = "error"


def _fmt(val: Any) -> str:
    if val is None:
        return "—"
    if isinstance(val, datetime):
        return val.strftime("%Y-%m-%d %H:%M")
    return str(val)[:19]
