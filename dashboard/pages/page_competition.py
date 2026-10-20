"""Challenge Cup Track-B evidence board backed only by observed local state."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

import pandas as pd
import streamlit as st

from competition_readiness import build_competition_readiness_report
from dashboard.components import info_bar, neon_metric_card, section_header


PROJECT_ROOT = Path(__file__).resolve().parents[2]


@st.cache_data(ttl=10, show_spinner=False)
def _snapshot() -> Dict[str, Any]:
    return build_competition_readiness_report(
        project_root=PROJECT_ROOT, run_live_inference=False, persist=False,
    )


def render(eco: Any, config: Any, dataset: Any, monitor: Any) -> None:
    section_header("挑战杯科B真实性证据板", "🏆", "cyan")
    st.caption("仅展示本机实测状态；合同/感谢材料不作为性能或临床疗效证据。")

    report = st.session_state.get("competition_live_report") or _snapshot()
    readiness = report["readiness"]
    ollama = report["ollama"]
    validation = report["validation"]

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        neon_metric_card(
            "科B演示", "可运行" if readiness["competition_demo_ready"] else "未就绪",
            icon="🧪", neon_color="green" if readiness["competition_demo_ready"] else "red",
            key="competition_demo_ready",
        )
    with c2:
        neon_metric_card(
            "Ollama", "在线" if ollama["reachable"] else "离线",
            icon="🧠", neon_color="green" if ollama["reachable"] else "red",
            key="competition_ollama",
        )
    with c3:
        neon_metric_card(
            "配置模型", "已安装" if ollama["configured_model_installed"] else "缺失",
            icon="📦", neon_color="green" if ollama["configured_model_installed"] else "red",
            key="competition_model",
        )
    with c4:
        neon_metric_card(
            "临床用途", "未获准" if not readiness["clinical_use_ready"] else "验证工件通过",
            icon="🛡️", neon_color="amber" if not readiness["clinical_use_ready"] else "green",
            key="competition_clinical",
        )

    if not readiness["clinical_use_ready"]:
        info_bar(
            "当前结论：系统可作为科研与竞赛原型演示；缺少合格外部临床验证/时序检查点，不能宣称临床可用。",
            "warning",
        )

    left, right = st.columns([1, 2])
    with left:
        if st.button("运行真实 Ollama 随机数挑战", type="primary", use_container_width=True):
            with st.spinner("正在调用配置的本地模型并核验返回随机数…"):
                st.session_state["competition_live_report"] = build_competition_readiness_report(
                    project_root=PROJECT_ROOT, run_live_inference=True, persist=False,
                )
            st.rerun()
        if st.button("刷新只读状态", use_container_width=True):
            st.session_state.pop("competition_live_report", None)
            _snapshot.clear()
            st.rerun()
    with right:
        live = ollama.get("live_inference", {})
        if live.get("attempted"):
            level = "success" if live.get("passed") else "error"
            info_bar(
                f"真实生成核验：{'通过' if live.get('passed') else '失败'}；"
                f"墙钟 {live.get('wall_seconds', '—')} 秒；"
                f"nonce匹配={live.get('nonce_verified', False)}；"
                f"响应SHA-256={str(live.get('response_sha256', ''))[:16]}…",
                level,
            )
        else:
            info_bar("尚未运行生成核验；当前只确认服务与模型清单。", "info")

    section_header("可复核资产", "🔎", "magenta")
    models = ollama.get("models", [])
    if models:
        st.dataframe(pd.DataFrame(models), use_container_width=True, hide_index=True)
    col_data, col_git = st.columns(2)
    with col_data:
        st.json(report["dataset"], expanded=True)
    with col_git:
        st.json(report["reproducibility"]["git"], expanded=True)

    section_header("申报口径边界", "📌", "amber")
    for item in report["claim_boundary"]:
        st.markdown(f"- {item}")

    serialized = json.dumps(report, ensure_ascii=False, indent=2, default=str)
    st.download_button(
        "下载本次真实性报告 JSON",
        data=serialized.encode("utf-8"),
        file_name="mapfm_competition_readiness.json",
        mime="application/json",
        use_container_width=True,
    )
