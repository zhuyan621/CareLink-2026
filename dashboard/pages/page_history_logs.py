"""Page 8: History & Logs — task history, search/filter, decision traces viewer."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from dashboard.components import (
    section_header,
    info_bar,
    neon_metric_card,
    data_table_with_style,
    export_button,
    sparkline_chart,
)
from dashboard.i18n import get_translator
from dashboard.theme import configure_plotly_dark, COLORS

# ── Constants ────────────────────────────────────────────────────────────
MAX_DISPLAY_TASKS = 500
TASKS_PER_PAGE = 25
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
TRACES_DIR = PROJECT_ROOT / "logs" / "traces"


def render(eco: Any, config: Any, dataset: Any, monitor: Any) -> None:
    """Render History & Logs page."""
    t = get_translator()

    section_header(t("history.title"), "📋", "cyan")

    # ── Role-based filtering ─────────────────────────────────────────
    role = st.session_state.get("role", "admin")

    # ── Load task history ─────────────────────────────────────────────
    raw_tasks: List[Dict[str, Any]] = []
    if eco is not None and hasattr(eco, "task_history") and eco.task_history:
        raw_tasks = list(eco.task_history)
    elif eco is not None:
        try:
            raw_tasks = list(eco.task_history) if eco.task_history else []
        except Exception:
            raw_tasks = []

    # Customer role: filter to only that user's tasks (lenient matching)
    if role == "customer":
        username = st.session_state.get("username", "")
        if username:
            raw_tasks = [
                tsk for tsk in raw_tasks
                if (isinstance(tsk, dict) and (
                    tsk.get("user", "") == username or
                    tsk.get("username", "") == username or
                    tsk.get("operator", "") == username
                ))
            ]

    # Normalize tasks: fill missing fields with defaults
    def _normalize_task(task: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "timestamp": task.get("timestamp", task.get("time", "")),
            "query": task.get("query", task.get("input", "")),
            "prediction": task.get("prediction", task.get("output", task.get("pred", ""))),
            "true_label": task.get("true_label", task.get("label", task.get("ground_truth", ""))),
            "confidence": float(task.get("confidence", task.get("conf", 0))),
            "latency": float(task.get("latency", task.get("latency_ms", task.get("elapsed", 0)))),
            "hitl": bool(task.get("hitl", task.get("hitl_triggered", False))),
            "correct": task.get("correct", task.get("is_correct", None)),
            "perception": task.get("perception", task.get("perception_result", {})),
            "retrieval": task.get("retrieval", task.get("retrieval_result", {})),
            "dma": task.get("dma", task.get("dma_detail", {})),
            "tfa": task.get("tfa", task.get("tfa_detail", {})),
            "fusion": task.get("fusion", task.get("fusion_result", {})),
            "verification": task.get("verification", task.get("verification_result", {})),
            "consensus": task.get("consensus", task.get("consensus_votes", {})),
            "hitl_detail": task.get("hitl_detail", task.get("hitl_intervention", {})),
            "comprehensive_answer": task.get("comprehensive_answer", task.get("answer", "")),
            "_raw": task,
        }

    tasks = [_normalize_task(tsk) for tsk in raw_tasks]
    capped = len(tasks) > MAX_DISPLAY_TASKS
    if capped:
        tasks = tasks[-MAX_DISPLAY_TASKS:]

    # ── Empty state ──────────────────────────────────────────────────
    if not tasks:
        info_bar(t("history.no_tasks"), "warning")
        if eco is not None and st.button("🩺 运行样本诊断生成历史", key="hist_run_sample",
                                         type="primary", use_container_width=True):
            with st.spinner("正在运行样本诊断..."):
                samples = [
                    "fever with cough and fatigue",
                    "lower back pain radiating to legs",
                    "skin rash with itching and redness",
                    "blurred vision with eye pain",
                    "joint swelling with morning stiffness",
                ]
                for q in samples:
                    try:
                        if hasattr(eco, 'collaborative_diagnose'):
                            eco.collaborative_diagnose(q)
                    except Exception:
                        pass
            st.rerun()
        return

    if capped:
        info_bar(t("history.capped_notice"), "info")

    # ═══════════════════════════════════════════════════════════════════
    # Row 1: Stats cards
    # ═══════════════════════════════════════════════════════════════════
    total = len(tasks)
    correct_count = sum(
        1 for tsk in tasks
        if tsk["correct"] is True or (
            isinstance(tsk["correct"], (int, float)) and tsk["correct"]
        ) or (
            tsk["correct"] is None and tsk["prediction"] and tsk["true_label"]
            and str(tsk["prediction"]).strip().lower() == str(tsk["true_label"]).strip().lower()
        )
    )
    success_rate = (correct_count / total * 100) if total > 0 else 0
    confidences = [tsk["confidence"] for tsk in tasks if tsk["confidence"] > 0]
    avg_conf = np.mean(confidences) if confidences else 0
    latencies = [tsk["latency"] for tsk in tasks if tsk["latency"] > 0]
    avg_latency = np.mean(latencies) if latencies else 0

    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        neon_metric_card(t("history.total_tasks"), str(total), icon="📦", neon_color="cyan", key="hist_total")
    with c2:
        neon_metric_card(
            t("history.accuracy"), f"{success_rate:.1f}%", icon="🎯",
            delta=f"{correct_count}/{total}" if total > 0 else "",
            neon_color="green" if success_rate >= 80 else "amber" if success_rate >= 50 else "red",
            key="hist_success",
        )
    with c3:
        neon_metric_card(
            t("history.avg_confidence"), f"{avg_conf:.2f}", icon="📊",
            neon_color="cyan", key="hist_avgconf",
        )
    with c4:
        neon_metric_card(
            t("history.avg_latency"), f"{avg_latency:.1f}s", icon="⏱️",
            neon_color="cyan", key="hist_avglat",
        )
    with c5:
        # Confidence trend sparkline
        st.caption(t("history.confidence_trend"))
        sparkline_chart(
            confidences[-60:] if len(confidences) > 60 else confidences,
            height=55, color=COLORS["cyan"], key="hist_spark_conf",
        )

    st.markdown("---")

    # ═══════════════════════════════════════════════════════════════════
    # Row 2: Search / Filter bar
    # ═══════════════════════════════════════════════════════════════════
    with st.container():
        fc1, fc2, fc3, fc4, fc5 = st.columns([2, 2, 2, 1.5, 1.5])
        with fc1:
            text_search = st.text_input(
                t("history.search_placeholder"),
                key="hist_search", placeholder=t("history.search_placeholder"),
                label_visibility="collapsed",
            )
        with fc2:
            date_range = st.date_input(
                t("history.filter_date"), value=(),
                key="hist_daterange",
            )
        with fc3:
            all_preds = sorted(set(
                str(tsk["prediction"]) for tsk in tasks if tsk["prediction"]
            ))
            pred_filter = st.multiselect(
                t("history.filter_prediction"), all_preds,
                key="hist_pred_filter", label_visibility="collapsed",
            )
        with fc4:
            conf_range = st.slider(
                t("history.filter_confidence"), 0.0, 1.0, (0.0, 1.0), 0.05,
                key="hist_conf_slider",
            )
        with fc5:
            hitl_filter = st.selectbox(
                t("history.filter_hitl"),
                [t("history.hitl_all"), t("history.hitl_triggered"), t("history.hitl_not_triggered")],
                key="hist_hitl_filter", label_visibility="collapsed",
            )

    # ── Apply filters ────────────────────────────────────────────────
    filtered = list(tasks)
    if text_search:
        q = text_search.lower()
        filtered = [
            tsk for tsk in filtered
            if q in str(tsk["query"]).lower() or q in str(tsk["prediction"]).lower()
        ]
    if date_range and len(date_range) == 2:
        start_d, end_d = date_range
        start_ts = datetime.combine(start_d, datetime.min.time())
        end_ts = datetime.combine(end_d, datetime.max.time())
        def _ts_in_range(tsk: Dict) -> bool:
            ts_str = str(tsk.get("timestamp", ""))
            if not ts_str:
                return True
            try:
                dt = datetime.fromisoformat(ts_str.replace("Z", "+00:00").split("+")[0].split("[")[0])
                return start_ts <= dt.replace(tzinfo=None) <= end_ts
            except (ValueError, TypeError):
                return True
        filtered = [tsk for tsk in filtered if _ts_in_range(tsk)]
    if pred_filter:
        filtered = [tsk for tsk in filtered if str(tsk["prediction"]) in pred_filter]
    if conf_range != (0.0, 1.0):
        filtered = [
            tsk for tsk in filtered
            if conf_range[0] <= tsk["confidence"] <= conf_range[1]
        ]
    if hitl_filter == t("history.hitl_triggered"):
        filtered = [tsk for tsk in filtered if tsk["hitl"]]
    elif hitl_filter == t("history.hitl_not_triggered"):
        filtered = [tsk for tsk in filtered if not tsk["hitl"]]

    if not filtered:
        info_bar(t("history.no_results"), "info")
        return

    # ═══════════════════════════════════════════════════════════════════
    # Row 3: Paginated task table
    # ═══════════════════════════════════════════════════════════════════
    total_pages = max(1, (len(filtered) + TASKS_PER_PAGE - 1) // TASKS_PER_PAGE)
    page = st.number_input(
        t("common.page", current="{current}", total="{total}").format(current="1", total=str(total_pages)),
        min_value=1, max_value=total_pages, value=1,
        key="hist_page",
    )

    start_idx = (page - 1) * TASKS_PER_PAGE
    page_tasks = filtered[start_idx : start_idx + TASKS_PER_PAGE]

    # Build table DataFrame
    table_rows = []
    for tsk in page_tasks:
        ts_str = str(tsk.get("timestamp", ""))
        try:
            dt = datetime.fromisoformat(ts_str.replace("Z", "+00:00").split("+")[0])
            ts_display = dt.strftime("%m-%d %H:%M:%S")
        except (ValueError, TypeError):
            ts_display = ts_str[:19] if ts_str else "—"

        query_text = str(tsk["query"])[:60] + ("..." if len(str(tsk["query"])) > 60 else "")

        correct_val = tsk["correct"]
        if correct_val is True or (isinstance(correct_val, (int, float)) and correct_val):
            correct_display = "✅"
        elif correct_val is False or (isinstance(correct_val, (int, float)) and not correct_val):
            correct_display = "❌"
        else:
            # Auto-detect
            pred = str(tsk["prediction"]).strip().lower()
            true_l = str(tsk["true_label"]).strip().lower()
            if pred and true_l:
                correct_display = "✅" if pred == true_l else "❌"
            else:
                correct_display = "—"

        hitl_display = "⚠️" if tsk["hitl"] else "—"
        lat_display = f"{tsk['latency']:.2f}s" if isinstance(tsk["latency"], (int, float)) and tsk["latency"] > 0 else "—"
        conf_display = f"{tsk['confidence']:.2f}"

        table_rows.append({
            t("history.query_col"): ts_display,
            "Query": query_text,
            t("history.prediction_col"): str(tsk["prediction"]) if tsk["prediction"] else "—",
            t("history.true_label"): str(tsk["true_label"]) if tsk["true_label"] else "—",
            t("history.confidence_col"): conf_display,
            t("history.latency_col"): lat_display,
            t("history.hitl_col"): hitl_display,
            t("history.correct"): correct_display,
        })

    table_df = pd.DataFrame(table_rows)
    data_table_with_style(
        table_df,
        highlight_cols=[t("history.confidence_col"), t("history.correct")],
        height=min(450, 35 * len(table_rows) + 40),
        key="hist_table",
    )

    st.caption(t("common.total", count=str(len(filtered))))

    # ═══════════════════════════════════════════════════════════════════
    # Row 4: Per-task expander (pipeline detail)
    # ═══════════════════════════════════════════════════════════════════
    if page_tasks:
        st.markdown("---")
        section_header(t("history.task_detail"), "🔍", "magenta")
        task_timestamps = [
            tsk.get("timestamp", f"Task {i + start_idx + 1}")
            for i, tsk in enumerate(page_tasks)
        ]
        selected_ts = st.selectbox(
            t("history.task_detail"), task_timestamps,
            key="hist_detail_select",
        )
        selected_idx = task_timestamps.index(selected_ts) if selected_ts in task_timestamps else 0
        detail_task = page_tasks[selected_idx]

        with st.expander(f"📋 {str(detail_task['query'])[:80]}", expanded=True):
            pipeline_stages = [
                (t("history.perception_result"), "perception"),
                (t("history.retrieval_result"), "retrieval"),
                (t("history.dma_detail"), "dma"),
                (t("history.tfa_detail"), "tfa"),
                (t("history.fusion_result"), "fusion"),
                (t("history.verification_result"), "verification"),
                (t("history.consensus_votes"), "consensus"),
                (t("history.hitl_detail"), "hitl_detail"),
                (t("history.comprehensive_answer"), "comprehensive_answer"),
            ]

            cols = st.columns(3)
            for i, (label, key) in enumerate(pipeline_stages):
                with cols[i % 3]:
                    data = detail_task.get(key)
                    if isinstance(data, str) and data:
                        st.markdown(f"**{label}**")
                        st.text(data[:500] + ("..." if len(data) > 500 else ""))
                    elif isinstance(data, dict) and data:
                        st.markdown(f"**{label}**")
                        st.json(data)
                    elif isinstance(data, (list, tuple)) and data and len(data) > 0:
                        st.markdown(f"**{label}**")
                        st.json(data[:5])
                    else:
                        st.caption(f"{label}: —")

    # ═══════════════════════════════════════════════════════════════════
    # Row 5: Export buttons + Batch Rediagnose
    # ═══════════════════════════════════════════════════════════════════
    st.markdown("---")
    section_header(f"{t('common.export')} / {t('common.download')}", "📥", "cyan")
    ec1, ec2, ec3 = st.columns(3)
    with ec1:
        export_csv_data = [
            {
                "timestamp": tsk.get("timestamp", ""),
                "query": str(tsk["query"]),
                "prediction": str(tsk["prediction"]),
                "true_label": str(tsk["true_label"]),
                "confidence": tsk["confidence"],
                "latency": tsk["latency"],
                "hitl": tsk["hitl"],
                "correct": tsk["correct"],
            }
            for tsk in filtered
        ]
        export_button(
            pd.DataFrame(export_csv_data),
            f"task_history_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            label=f"📄 {t('history.export_csv')}",
            key="hist_export_csv",
        )
    with ec2:
        export_button(
            [tsk["_raw"] for tsk in filtered],
            f"task_history_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            label=f"📋 {t('history.export_json')}",
            key="hist_export_json",
        )
    with ec3:
        if st.button(f"🔄 {t('history.batch_rediagnose')}", use_container_width=True,
                     key="hist_batch_rediag", type="primary",
                     disabled=(role == "customer"),
                     help=t("history.batch_rediagnose")):
            if eco is not None and filtered:
                with st.spinner(f"Re-diagnosing {len(filtered)} task(s)..."):
                    rediag_count = 0
                    rediag_errors = 0
                    for tsk in filtered[:50]:  # Cap at 50 for safety
                        try:
                            query = str(tsk.get("query", tsk.get("input", "")))
                            if query and query != "—":
                                if hasattr(eco, 'collaborative_diagnose'):
                                    eco.collaborative_diagnose(query)
                                elif hasattr(eco, 'diagnose'):
                                    eco.diagnose(query)
                                rediag_count += 1
                        except Exception:
                            rediag_errors += 1
                    msg = f"Re-diagnosed {rediag_count} task(s)"
                    if rediag_errors:
                        msg += f" ({rediag_errors} errors)"
                    info_bar(msg, "success" if rediag_errors == 0 else "warning")

    # ═══════════════════════════════════════════════════════════════════
    # Row 6: Decision traces section
    # ═══════════════════════════════════════════════════════════════════
    st.markdown("---")
    section_header(t("history.decision_traces"), "🧬", "violet")

    if TRACES_DIR.exists() and TRACES_DIR.is_dir():
        trace_files = sorted(TRACES_DIR.glob("decision_trace_*.json"), reverse=True)
        if not trace_files:
            trace_files = sorted(TRACES_DIR.glob("*.json"), reverse=True)

        if trace_files:
            trace_names = [tf.name for tf in trace_files]
            selected_trace_name = st.selectbox(
                t("history.select_trace"), trace_names,
                key="hist_trace_select",
            )
            if selected_trace_name:
                trace_path = TRACES_DIR / selected_trace_name
                try:
                    trace_data = json.loads(trace_path.read_text(encoding="utf-8"))
                    with st.expander(f"🧬 {selected_trace_name}", expanded=True):
                        # Summary section
                        summary_cols = st.columns(4)
                        with summary_cols[0]:
                            st.metric(
                                t("history.query_col"),
                                str(trace_data.get("query", "—"))[:40],
                            )
                        with summary_cols[1]:
                            st.metric(
                                t("history.prediction_col"),
                                str(trace_data.get("prediction", trace_data.get("output", "—"))),
                            )
                        with summary_cols[2]:
                            st.metric(
                                t("history.true_label"),
                                str(trace_data.get("true_label", trace_data.get("label", "—"))),
                            )
                        with summary_cols[3]:
                            conf_val = trace_data.get("confidence", trace_data.get("conf", "—"))
                            st.metric(t("history.confidence_col"), str(conf_val))

                        # Full trace viewer
                        st.json(trace_data)
                except (json.JSONDecodeError, OSError) as exc:
                    info_bar(f"Failed to read trace: {exc}", "error")
        else:
            info_bar(t("common.no_data"), "info")
    else:
        info_bar(t("common.no_data"), "info")
