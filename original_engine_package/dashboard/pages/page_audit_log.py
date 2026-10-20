"""Page 9: Audit Log — compliance dashboard, daily trend, event filtering, retention policy."""

from __future__ import annotations

import json
from datetime import datetime, timedelta
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
)
from dashboard.i18n import get_translator
from dashboard.theme import configure_plotly_dark, COLORS, CHART_PALETTE

# ── Constants ────────────────────────────────────────────────────────────
MAX_EVENTS = 5000
EVENTS_PER_PAGE = 50
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
AUDIT_LOG_PATH = PROJECT_ROOT / "logs" / "audit.log"
LARGE_FILE_THRESHOLD_MB = 100


# ── Desensitization helper ───────────────────────────────────────────────
def _desensitize_payload(payload: Any) -> Any:
    """Apply desensitization to payload text fields if desensitizer is available."""
    try:
        from desensitizer import desensitize_text
    except ImportError:
        return payload

    if isinstance(payload, str):
        return desensitize_text(payload)
    elif isinstance(payload, dict):
        return {k: _desensitize_payload(v) for k, v in payload.items()}
    elif isinstance(payload, list):
        return [_desensitize_payload(v) for v in payload]
    return payload


def render(eco: Any, config: Any, dataset: Any, monitor: Any) -> None:
    """Render Audit Log page."""
    t = get_translator()

    section_header(t("audit.title"), "🔍", "cyan")

    # ── Load audit log ───────────────────────────────────────────────
    events: List[Dict[str, Any]] = []
    file_size_mb: float = 0
    large_file: bool = False
    malformed_count: int = 0
    load_error: Optional[str] = None

    if not AUDIT_LOG_PATH.exists():
        info_bar(t("audit.no_logs"), "info")
        _render_retention_card(t, AUDIT_LOG_PATH, 0, 0)
        return

    try:
        file_size_mb = AUDIT_LOG_PATH.stat().st_size / (1024 * 1024)
        large_file = file_size_mb > LARGE_FILE_THRESHOLD_MB

        raw_text = AUDIT_LOG_PATH.read_text(encoding="utf-8")
        if not raw_text.strip():
            info_bar(t("audit.empty_log"), "info")
            _render_retention_card(t, AUDIT_LOG_PATH, 0, 0)
            return

        lines = raw_text.strip().split("\n")
        # If large file, only read last MAX_EVENTS lines
        if large_file:
            lines = lines[-MAX_EVENTS:]

        for line in lines:
            line = line.strip()
            if not line:
                continue
            try:
                evt = json.loads(line)
                events.append(evt)
            except (json.JSONDecodeError, TypeError):
                malformed_count += 1
    except OSError as exc:
        load_error = str(exc)
        info_bar(f"{t('common.error')}: {load_error}", "error")
        return

    if not events and not malformed_count:
        info_bar(t("audit.empty_log"), "info")
        _render_retention_card(t, AUDIT_LOG_PATH, file_size_mb, 0)
        return

    # ── Warnings ─────────────────────────────────────────────────────
    if large_file:
        info_bar(t("audit.large_file_warning"), "warning")
    if malformed_count > 0:
        info_bar(f"{t('audit.malformed_entries')}: {malformed_count}", "warning")

    # ── Normalize events ─────────────────────────────────────────────
    def _normalize_event(evt: Dict[str, Any]) -> Dict[str, Any]:
        ts_str = evt.get("timestamp", "")
        ts_dt = None
        try:
            ts_dt = datetime.fromisoformat(ts_str.replace("Z", "+00:00").split("+")[0])
        except (ValueError, TypeError):
            pass
        event_type = evt.get("event", evt.get("type", "unknown"))
        operator = evt.get("operator", evt.get("user", evt.get("username", evt.get("actor", "system"))))
        payload = evt.get("payload", evt.get("data", evt.get("detail", {})))
        return {
            "timestamp": ts_str,
            "timestamp_dt": ts_dt,
            "event": event_type,
            "operator": operator,
            "payload": payload,
            "_raw": evt,
        }

    normalized = [_normalize_event(evt) for evt in events]

    # ═══════════════════════════════════════════════════════════════════
    # Row 1: Compliance dashboard cards
    # ═══════════════════════════════════════════════════════════════════
    total_events = len(normalized)

    # Today's events
    today = datetime.now().date()
    today_events = sum(
        1 for evt in normalized
        if evt["timestamp_dt"] and evt["timestamp_dt"].date() == today
    )

    # Event type count
    event_types = sorted(set(evt["event"] for evt in normalized))

    c1, c2, c3 = st.columns(3)
    with c1:
        neon_metric_card(
            t("audit.total_events"), str(total_events),
            icon="📋", neon_color="cyan", key="audit_total",
        )
    with c2:
        neon_metric_card(
            t("audit.today_events"), str(today_events),
            icon="📅", neon_color="green" if today_events > 0 else "cyan",
            key="audit_today",
        )
    with c3:
        neon_metric_card(
            t("audit.event_types"), str(len(event_types)),
            icon="🏷️", neon_color="violet", key="audit_types",
        )

    # ═══════════════════════════════════════════════════════════════════
    # Row 2: Daily operation trend chart
    # ═══════════════════════════════════════════════════════════════════
    section_header(t("audit.daily_trend"), "📈", "cyan")

    # Aggregate events by day
    daily_counts: Dict[str, int] = {}
    for evt in normalized:
        if evt["timestamp_dt"]:
            day_key = evt["timestamp_dt"].strftime("%Y-%m-%d")
            daily_counts[day_key] = daily_counts.get(day_key, 0) + 1

    if daily_counts:
        sorted_days = sorted(daily_counts.keys())
        counts = [daily_counts[d] for d in sorted_days]

        # Anomaly line: mean + 2*sigma
        mean_val = np.mean(counts) if counts else 0
        std_val = np.std(counts) if counts else 0
        anomaly_threshold = mean_val + 2 * std_val

        fig_trend = go.Figure()

        # Bar chart
        fig_trend.add_trace(go.Bar(
            x=sorted_days, y=counts,
            name=t("audit.daily_trend"),
            marker_color=COLORS["cyan"],
            marker_line_color="rgba(0,245,255,0.3)",
            hovertemplate="%{x}<br>Events: %{y}<extra></extra>",
        ))

        # Anomaly line
        fig_trend.add_trace(go.Scatter(
            x=[sorted_days[0], sorted_days[-1]],
            y=[anomaly_threshold, anomaly_threshold],
            mode="lines",
            name=t("audit.anomaly_line"),
            line=dict(color=COLORS["danger"], width=2, dash="dash"),
            hovertemplate=f"μ+2σ = {anomaly_threshold:.1f}<extra></extra>",
        ))

        # Highlight anomaly days
        anomaly_x = [d for d, c in zip(sorted_days, counts) if c > anomaly_threshold]
        anomaly_y = [c for c in counts if c > anomaly_threshold]
        if anomaly_x:
            fig_trend.add_trace(go.Scatter(
                x=anomaly_x, y=anomaly_y,
                mode="markers",
                name=f"{t('common.warning')}",
                marker=dict(color=COLORS["danger"], size=10, symbol="x"),
                hovertemplate="%{x}<br>ANOMALY: %{y}<extra></extra>",
            ))

        configure_plotly_dark(fig_trend)
        fig_trend.update_layout(
            height=320,
            xaxis=dict(title="", tickangle=-45),
            yaxis=dict(title=t("audit.total_events")),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            margin=dict(l=40, r=20, t=10, b=60),
            bargap=0.15,
        )
        st.plotly_chart(fig_trend, use_container_width=True, key="audit_daily_trend")
    else:
        info_bar(t("common.insufficient_data"), "info")

    # ═══════════════════════════════════════════════════════════════════
    # Row 3: Filter bar
    # ═══════════════════════════════════════════════════════════════════
    st.markdown("---")
    with st.container():
        fc1, fc2, fc3, fc4 = st.columns([2, 2, 2, 2])
        with fc1:
            type_filter = st.multiselect(
                t("audit.filter_event"), event_types,
                key="audit_type_filter", label_visibility="visible",
            )
        with fc2:
            audit_date_range = st.date_input(
                t("audit.filter_date"), value=(),
                key="audit_daterange",
            )
        with fc3:
            operators = sorted(set(
                str(evt["operator"]) for evt in normalized
            ))
            operator_filter = st.selectbox(
                t("audit.filter_user"),
                [t("common.all")] + operators,
                key="audit_op_filter", label_visibility="visible",
            )
        with fc4:
            payload_keyword = st.text_input(
                t("audit.filter_payload"),
                key="audit_payload_kw", placeholder=t("audit.filter_payload"),
                label_visibility="visible",
            )

    # ── Apply filters ────────────────────────────────────────────────
    filtered = list(normalized)
    if type_filter:
        filtered = [evt for evt in filtered if evt["event"] in type_filter]
    if audit_date_range and len(audit_date_range) == 2:
        start_d, end_d = audit_date_range
        start_ts = datetime.combine(start_d, datetime.min.time())
        end_ts = datetime.combine(end_d, datetime.max.time())
        filtered = [
            evt for evt in filtered
            if evt["timestamp_dt"] and start_ts <= evt["timestamp_dt"] <= end_ts
        ]
    if operator_filter and operator_filter != t("common.all"):
        filtered = [evt for evt in filtered if str(evt["operator"]) == operator_filter]
    if payload_keyword:
        kw = payload_keyword.lower()
        filtered = [
            evt for evt in filtered
            if kw in json.dumps(evt["payload"], ensure_ascii=False, default=str).lower()
        ]

    # ═══════════════════════════════════════════════════════════════════
    # Row 4: Paginated audit log table
    # ═══════════════════════════════════════════════════════════════════
    st.markdown("---")
    section_header(t("audit.log_table"), "📜", "cyan")

    if not filtered:
        info_bar(t("common.no_data"), "info")
    else:
        total_pages = max(1, (len(filtered) + EVENTS_PER_PAGE - 1) // EVENTS_PER_PAGE)
        page = st.number_input(
            t("common.page", current="{current}", total="{total}").format(
                current="1", total=str(total_pages)
            ),
            min_value=1, max_value=total_pages, value=1,
            key="audit_page",
        )
        start_idx = (page - 1) * EVENTS_PER_PAGE
        page_events = filtered[start_idx : start_idx + EVENTS_PER_PAGE]

        # Build table
        table_rows = []
        for evt in page_events:
            ts_display = "—"
            if evt["timestamp_dt"]:
                ts_display = evt["timestamp_dt"].strftime("%Y-%m-%d %H:%M:%S")
            elif evt["timestamp"]:
                ts_display = str(evt["timestamp"])[:19]

            payload_str = json.dumps(evt["payload"], ensure_ascii=False, default=str)
            payload_summary = payload_str[:80] + ("..." if len(payload_str) > 80 else "")

            # Color-code event type
            evt_type = evt["event"]
            if "security" in evt_type.lower() or "auth" in evt_type.lower():
                badge = "🔐"
            elif "config" in evt_type.lower():
                badge = "⚙️"
            elif "diagnos" in evt_type.lower() or "task" in evt_type.lower() or "collab" in evt_type.lower():
                badge = "🩺"
            else:
                badge = "📌"

            table_rows.append({
                t("audit.event_type"): f"{badge} {evt_type}",
                "Timestamp": ts_display,
                t("audit.operator"): str(evt["operator"]),
                t("audit.payload_summary"): payload_summary,
            })

        table_df = pd.DataFrame(table_rows)
        data_table_with_style(
            table_df,
            highlight_cols=[t("audit.event_type"), t("audit.operator")],
            height=min(500, 35 * len(table_rows) + 40),
            key="audit_table",
        )

        st.caption(t("common.total", count=str(len(filtered))))

        # ── Expandable JSON payload for selected row ─────────────────
        st.markdown("---")
        st.caption(t("common.view") + " " + t("audit.payload_summary"))
        evt_labels = [
            f"[{i + start_idx + 1}] {evt.get('timestamp_dt', evt.get('timestamp', '—'))} — {evt['event']}"
            for i, evt in enumerate(page_events)
        ]
        if evt_labels:
            selected_evt_label = st.selectbox(
                t("common.view"), evt_labels,
                key="audit_detail_select", label_visibility="collapsed",
            )
            if selected_evt_label:
                sel_idx = evt_labels.index(selected_evt_label)
                sel_evt = page_events[sel_idx]
                with st.expander(f"📋 {sel_evt['event']} — {sel_evt.get('timestamp_dt', sel_evt.get('timestamp', '—'))}", expanded=False):
                    # Apply desensitization
                    safe_payload = _desensitize_payload(sel_evt["payload"])
                    st.json(safe_payload)
                    st.caption(t("audit.desensitized"))

    # ═══════════════════════════════════════════════════════════════════
    # Row 5: Export buttons
    # ═══════════════════════════════════════════════════════════════════
    st.markdown("---")
    section_header(f"{t('common.export')} / {t('common.download')}", "📥", "cyan")
    ec1, ec2 = st.columns(2)
    with ec1:
        export_json_data = [_desensitize_payload(evt["_raw"]) for evt in filtered]
        export_button(
            export_json_data,
            f"audit_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            label=f"📋 {t('audit.export_json')}",
            key="audit_export_json",
        )
    with ec2:
        export_csv_rows = [
            {
                "timestamp": evt.get("timestamp", ""),
                "event": evt["event"],
                "operator": evt["operator"],
                "payload": json.dumps(
                    _desensitize_payload(evt["payload"]),
                    ensure_ascii=False, default=str,
                ),
            }
            for evt in filtered
        ]
        export_button(
            pd.DataFrame(export_csv_rows),
            f"audit_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            label=f"📄 {t('audit.export_csv')}",
            key="audit_export_csv",
        )

    # ═══════════════════════════════════════════════════════════════════
    # Row 6: Data retention policy card
    # ═══════════════════════════════════════════════════════════════════
    _render_retention_card(t, AUDIT_LOG_PATH, file_size_mb, total_events)


def _render_retention_card(
    t, log_path: Path, file_size_mb: float, total_events: int
) -> None:
    """Render the data retention policy card with archive action."""
    st.markdown("---")
    section_header(t("audit.retention_policy"), "🗄️", "violet")

    retention_days = 365  # default, could come from config

    created_date = "—"
    if log_path.exists():
        try:
            mtime = log_path.stat().st_mtime
            created_date = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M")
        except OSError:
            pass

    rc1, rc2, rc3, rc4 = st.columns(4)
    with rc1:
        neon_metric_card(
            t("audit.retention_days", days=str(retention_days)),
            f"{retention_days}d",
            icon="📅",
            neon_color="cyan",
            key="ret_policy_days",
        )
    with rc2:
        neon_metric_card(
            t("audit.log_size"),
            f"{file_size_mb:.1f} MB" if file_size_mb > 0 else "0 MB",
            icon="💾",
            neon_color="amber" if file_size_mb > 50 else "green",
            key="ret_log_size",
        )
    with rc3:
        neon_metric_card(
            t("audit.log_created"),
            created_date,
            icon="🕐",
            neon_color="cyan",
            key="ret_created",
        )
    with rc4:
        neon_metric_card(
            t("audit.total_events"),
            str(total_events),
            icon="📋",
            neon_color="violet",
            key="ret_total",
        )

    # Archive button
    st.markdown("")
    col_archive, _ = st.columns([1, 3])
    with col_archive:
        if st.button(f"📦 {t('audit.archive')}", use_container_width=True,
                     key="audit_archive_btn",
                     disabled=not log_path.exists() or file_size_mb < 1.0,
                     help="Archive old log entries (> retention period) to .archive/"):
            try:
                archive_dir = log_path.parent / ".archive"
                archive_dir.mkdir(parents=True, exist_ok=True)
                archive_name = f"audit_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
                archive_path = archive_dir / archive_name

                # Read, filter by retention, write fresh + old
                cutoff = datetime.now() - timedelta(days=retention_days)
                fresh_lines = []
                archived_lines = []

                for line in log_path.read_text(encoding="utf-8").strip().split("\n"):
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        evt = json.loads(line)
                        ts_str = evt.get("timestamp", "")
                        dt = datetime.fromisoformat(ts_str.replace("Z", "+00:00").split("+")[0])
                        if dt < cutoff:
                            archived_lines.append(line)
                        else:
                            fresh_lines.append(line)
                    except (json.JSONDecodeError, ValueError, TypeError):
                        fresh_lines.append(line)  # keep malformed in fresh

                # Write archived entries
                if archived_lines:
                    archive_path.write_text("\n".join(archived_lines) + "\n", encoding="utf-8")
                # Write back only fresh entries
                log_path.write_text("\n".join(fresh_lines) + "\n" if fresh_lines else "", encoding="utf-8")

                info_bar(
                    f"Archived {len(archived_lines)} old entries to {archive_name}. "
                    f"Kept {len(fresh_lines)} recent entries.",
                    "success",
                )
            except OSError as exc:
                info_bar(f"Archive failed: {exc}", "error")
