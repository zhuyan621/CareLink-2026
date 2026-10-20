#!/usr/bin/env python3
"""CareLink 2026 competition demo.

This entry point intentionally presents a narrow, verifiable workflow for the
2026 digital-media competition.  The original research dashboard remains
available in dashboard.py.
"""

from __future__ import annotations

import json
import hashlib
from html import escape
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict
from urllib.parse import urlparse

import streamlit as st
from xml.etree import ElementTree


st.set_page_config(
    page_title="安护智链 CareLink",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="collapsed",
    menu_items={
        "Get Help": None,
        "Report a Bug": None,
        "About": "安护智链 CareLink · 多智能体照护风险筛查与人工复核平台",
    },
)

PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from careguard_presenter import build_audit_report, build_screening_view, review_decisions
from careguard_cases import SAMPLE_CASES


INPUT_KEYS = ("cg_sample", "cg_note", "cg_hr", "cg_spo2", "cg_temp", "cg_rr", "cg_force")
CASE_ROUTES = {
    "chest": "夜间突发胸痛",
    "stroke": "疑似卒中表现",
    "change": "慢病状态变化",
}


def _inject_style() -> None:
    stylesheet = (PROJECT_ROOT / "demo_assets" / "careguard_theme.css").read_text(encoding="utf-8")
    st.markdown(f"<style>{stylesheet}</style>", unsafe_allow_html=True)


@st.cache_resource(show_spinner="正在加载本地多智能体引擎…")
def _ecosystem() -> Any:
    from config_loader import load_yaml_config
    from mapfm_ecosystem_repaired import (
        EcosystemConfig,
        HeterogeneousMultiAgentEcosystem,
        load_medical_dataset,
    )

    config = load_yaml_config(EcosystemConfig, PROJECT_ROOT / "config.yaml")
    dataset = load_medical_dataset(
        PROJECT_ROOT / "medNo.22.csv",
        target_classes=config.target_classes,
        seed=config.random_seed,
    )
    return HeterogeneousMultiAgentEcosystem(
        config=config,
        dataset=dataset,
        base_model=config.ollama_model_name,
        verbose=False,
    )


def _load_manifest() -> Dict[str, Any]:
    path = PROJECT_ROOT / "artifacts" / "competition" / "release_manifest_latest.json"
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _load_current_checks() -> tuple[Dict[str, Any], Dict[str, Any]]:
    smoke_path = PROJECT_ROOT / "artifacts" / "competition" / "careguard_live_smoke_latest.json"
    tests_path = PROJECT_ROOT / "artifacts" / "competition" / "careguard_pytest_latest.xml"
    smoke: Dict[str, Any] = {}
    tests: Dict[str, Any] = {}
    if smoke_path.exists():
        try:
            smoke = json.loads(smoke_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            pass
    if tests_path.exists():
        try:
            suite = ElementTree.parse(tests_path).getroot()
            if suite.tag == "testsuites":
                first_suite = suite.find("testsuite")
                if first_suite is not None:
                    suite = first_suite
            tests = {
                "total": int(suite.attrib.get("tests", 0)),
                "errors": int(suite.attrib.get("errors", 0)),
                "failures": int(suite.attrib.get("failures", 0)),
                "skipped": int(suite.attrib.get("skipped", 0)),
            }
        except (OSError, ElementTree.ParseError, ValueError):
            pass
    return smoke, tests


def _set_sample() -> None:
    sample = SAMPLE_CASES[st.session_state.cg_sample]
    st.session_state.cg_note = sample["note"]
    st.session_state.cg_hr = sample["vitals"]["heart_rate"]
    st.session_state.cg_spo2 = sample["vitals"]["spo2"]
    st.session_state.cg_temp = sample["vitals"]["temperature"]
    st.session_state.cg_rr = sample["vitals"]["respiratory_rate"]
    st.session_state.cg_force = sample["force_high_risk"]
    st.session_state.cg_raw = None
    st.session_state.cg_review = None
    st.session_state.cg_screened_token = None
    st.session_state.cg_stale_warning = False


def _remember_inputs() -> None:
    st.session_state.cg_saved_inputs = {
        key: st.session_state[key] for key in INPUT_KEYS if key in st.session_state
    }


def _restore_inputs() -> None:
    for key, value in st.session_state.cg_saved_inputs.items():
        st.session_state[key] = value


def _current_input_token() -> str:
    values = {
        "note": st.session_state.cg_note.strip(),
        "heart_rate": st.session_state.cg_hr,
        "spo2": st.session_state.cg_spo2,
        "temperature": st.session_state.cg_temp,
        "respiratory_rate": st.session_state.cg_rr,
        "force_high_risk": st.session_state.cg_force,
    }
    return hashlib.sha256(json.dumps(values, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()


def _init_state() -> None:
    defaults = {
        "cg_sample": "夜间突发胸痛",
        "cg_note": SAMPLE_CASES["夜间突发胸痛"]["note"],
        "cg_hr": 112,
        "cg_spo2": 91,
        "cg_temp": 36.8,
        "cg_rr": 25,
        "cg_force": True,
        "cg_raw": None,
        "cg_review": None,
        "cg_screened_token": None,
        "cg_stale_warning": False,
        "cg_saved_inputs": {},
        "cg_previous_page": "风险筛查演示",
        "cg_page": "风险筛查演示",
        "cg_url_focus": None,
        "cg_url_case": None,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def _hero() -> None:
    st.markdown(
        """
        <section class="cg-hero" aria-label="CareLink 项目介绍">
          <div class="cg-hero-copy">
            <div class="cg-eyebrow">CARELINK / COMPETITION EDITION 2026</div>
            <h1 class="cg-title">让照护风险<br><span class="accent">被看见。<br>被解释。<br>被复核。</span></h1>
            <p class="cg-subtitle">从交接班记录到人工决定，CareLink 将多智能体推理、来源核验与审计线索连成一条可追溯的协作链。系统提示风险，专业人员作最终判断。</p>
            <div class="cg-hero-actions">
              <a class="cg-cta" href="?focus=workspace" target="_self">进入合成案例演示&nbsp; ↗</a>
              <a class="cg-cta-secondary" href="?focus=boundary" target="_self">了解使用边界&nbsp; ↗</a>
            </div>
            <div class="cg-hero-foot"><span>LOCAL FIRST</span><span>HUMAN IN THE LOOP</span><span>AUDITABLE BY DESIGN</span></div>
          </div>
          <div class="cg-stage" aria-label="合成案例界面示意">
            <div class="cg-stage-glow" aria-hidden="true"></div>
            <div class="cg-stage-square" aria-hidden="true"></div>
            <span class="cg-stage-label">ILLUSTRATIVE / SYNTHETIC</span>
            <div class="cg-console">
              <div class="cg-console-top"><span class="cg-console-dots"><i></i><i></i><i></i></span><span>CARELINK / CASE PREVIEW</span></div>
              <div class="cg-console-body">
                <span class="cg-console-tag">合成案例界面示意</span>
                <div class="cg-console-title">一次交接，四步闭环</div>
                <div class="cg-console-sub">观察信息进入多智能体流程；未经验证的诊断标签不参与分流。</div>
                <div class="cg-console-alert"><b>P1</b><span>高风险线索 → 人工优先复核</span></div>
                <div class="cg-console-flow"><span>输入</span><i>→</i><span>推理</span><i>→</i><span>核验</span><i>→</i><span>复核</span></div>
              </div>
              <div class="cg-console-bottom">NOT A CLINICAL DIAGNOSIS  ·  HUMAN REVIEW REQUIRED</div>
            </div>
            <div class="cg-floating"><small>DECISION OWNERSHIP</small><b>专业人员</b><small>最终判断不交给算法</small></div>
          </div>
        </section>
        """,
        unsafe_allow_html=True,
    )


def _story() -> None:
    st.markdown(
        """
        <div class="cg-story" aria-label="照护协作流程">
          <div class="cg-story-item"><div class="cg-story-num">01 / OBSERVE</div><div class="cg-story-title">记录现场观察</div><div class="cg-story-description">把交接描述与生命体征放在同一视图，不遗漏上下文。</div></div>
          <div class="cg-story-item"><div class="cg-story-num">02 / REASON</div><div class="cg-story-title">多智能体协作</div><div class="cg-story-description">保留推理链路状态，隔离未验证的诊断标签。</div></div>
          <div class="cg-story-item"><div class="cg-story-num">03 / VERIFY</div><div class="cg-story-title">辨清证据来源</div><div class="cg-story-description">动态检索与人工整理的离线资料分开展示。</div></div>
          <div class="cg-story-item"><div class="cg-story-num">04 / DECIDE</div><div class="cg-story-title">人工复核留痕</div><div class="cg-story-description">高风险不能自动放行，审计记录不保存护理原文。</div></div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _context_section() -> None:
    """Explain the actual handover problem using an explicitly synthetic record."""
    case = SAMPLE_CASES["夜间突发胸痛"]
    vitals = case["vitals"]
    st.markdown(
        '<section class="cg-context" aria-label="交接班场景">'
        '<div class="cg-section-heading"><div class="cg-section-overline">THE MOMENT THAT MATTERS</div>'
        '<h2 class="cg-section-title">交接班不是一句“情况不好”</h2>'
        '<div class="cg-section-description">养老照护的关键时刻，信息往往分散在观察文字、生命体征和已经采取的行动里。'
        '这个项目要做的，是让下一位接手者看见完整线索，并知道什么必须由人决定。</div></div>'
        '<div class="cg-context-grid">'
        '<div class="cg-handover"><div class="cg-handover-head"><span>HANDOVER NOTE / SYNTHETIC</span><span>01:46</span></div>'
        f'<p>“{escape(case["note"])}”</p>'
        '<div class="cg-handover-line"></div>'
        f'<div class="cg-vital-strip"><span>HR <b>{vitals["heart_rate"]}</b></span>'
        f'<span>SpO₂ <b>{vitals["spo2"]}%</b></span>'
        f'<span>RR <b>{vitals["respiratory_rate"]}</b></span></div>'
        '<small>合成演示记录 · 非真实个案 · 时间仅作界面示意</small></div>'
        '<div class="cg-context-reading"><div class="cg-small-label">把自由文本拆成可复核的信息</div>'
        '<div class="cg-reading-row"><em>01</em><div><b>发生了什么</b><span>突发症状、持续情况与伴随表现，保留原始描述。</span></div></div>'
        '<div class="cg-reading-row"><em>02</em><div><b>现场观察到什么</b><span>心率、血氧、呼吸等输入与文本并置，便于人工交叉查看。</span></div></div>'
        '<div class="cg-reading-row"><em>03</em><div><b>已经做了什么</b><span>记录已采取的行动，避免只留下一个算法生成的标签。</span></div></div>'
        '<div class="cg-reading-row"><em>04</em><div><b>下一步由谁负责</b><span>系统给出复核入口，专业人员依据机构流程作判断。</span></div></div>'
        '</div></div></section>',
        unsafe_allow_html=True,
    )


def _case_gallery() -> None:
    """Make all three existing synthetic cases directly reachable from the story."""
    case_copy = [
        ("chest", "01 / ACUTE", "夜间突发胸痛", "识别急性警示线索", "展示文本、生命体征和已采取行动如何汇集到人工优先复核。", "case-chest"),
        ("stroke", "02 / SUDDEN", "疑似卒中表现", "强调起病时间与突发变化", "演示面部、言语和单侧肢体变化如何被保留为可解释线索。", "case-stroke"),
        ("change", "03 / GRADUAL", "慢病状态变化", "看见较平日的改变", "演示连续数日的症状变化；没有合格时序数据时不生成恶化概率。", "case-change"),
    ]
    cards = []
    for slug, index, title, headline, detail, theme in case_copy:
        case = SAMPLE_CASES[title]
        vitals = case["vitals"]
        cards.append(
            f'<a class="cg-case {theme}" href="?focus=workspace&amp;case={slug}" target="_self" '
            f'aria-label="载入{escape(title)}合成案例">'
            f'<span class="cg-case-index">{index}</span><span class="cg-case-symbol" aria-hidden="true">✳</span>'
            f'<span class="cg-case-title">{escape(title)}</span><strong>{escape(headline)}</strong>'
            f'<span class="cg-case-desc">{escape(detail)}</span>'
            f'<span class="cg-case-vitals">HR {vitals["heart_rate"]} <i>·</i> SpO₂ {vitals["spo2"]}% '
            f'<i>·</i> RR {vitals["respiratory_rate"]}</span>'
            '<span class="cg-case-link">载入此案例 <span aria-hidden="true">↗</span></span></a>'
        )
    st.markdown(
        '<section class="cg-cases" aria-label="合成案例库">'
        '<div class="cg-section-heading"><div class="cg-section-overline">THREE CASES, THREE QUESTIONS</div>'
        '<h2 class="cg-section-title">用三个合成情境，检验同一条责任链</h2>'
        '<div class="cg-section-description">不是病例数据库，也不是诊断准确率展示。每张卡片进入可运行工作台，'
        '重点观察信息是否完整、边界是否诚实、复核是否可追踪。</div></div>'
        f'<div class="cg-case-grid">{"".join(cards)}</div></section>',
        unsafe_allow_html=True,
    )


def _system_section() -> None:
    st.markdown(
        '<section class="cg-system" aria-label="系统工作方式">'
        '<div class="cg-system-lead"><div class="cg-section-overline">UNDER THE SURFACE</div>'
        '<h2>不是一个“给答案”的聊天框。<br><span>是一条有刹车的协作链。</span></h2>'
        '<p>比赛版沿用项目的多智能体流水线，但把对外展示收紧到能够解释和复核的范围。'
        '模型负责生成与整理，来源核验负责标注证据状态，人工负责最后决定。</p></div>'
        '<div class="cg-system-map">'
        '<div class="cg-system-node"><span>01 / INGEST</span><b>信息进入</b><p>交接记录与生命体征一起输入；演示只用合成或脱敏内容。</p></div>'
        '<div class="cg-system-node"><span>02 / COOPERATE</span><b>多智能体协作</b><p>检索、融合和核验组织线索；本地 Ollama 可用性单独显示。</p></div>'
        '<div class="cg-system-node"><span>03 / CONSTRAIN</span><b>验证门控</b><p>未适配的诊断标签不参与分流；时序检查点未验证就不输出风险概率。</p></div>'
        '<div class="cg-system-node"><span>04 / HAND OVER</span><b>人工接管</b><p>高风险不自动放行；复核决定与来源状态写入可导出的审计摘要。</p></div>'
        '</div><div class="cg-system-bottom"><span>核心原则</span><strong>可见的状态，比看似确定的答案更重要。</strong></div>'
        '</section>',
        unsafe_allow_html=True,
    )


def _trust_section() -> None:
    st.markdown(
        '<section class="cg-trust" aria-label="证据与责任边界">'
        '<div class="cg-section-heading"><div class="cg-section-overline">WHAT THE DEMO WILL — AND WILL NOT — SAY</div>'
        '<h2 class="cg-section-title">把“不知道”也设计进界面</h2>'
        '<div class="cg-section-description">可追溯，不等于已经证明有效。这里把参赛原型最容易混淆的几件事摊开说明。</div></div>'
        '<div class="cg-trust-grid">'
        '<div class="cg-trust-card"><span>01 / EVIDENCE</span><h3>两种资料，两个来源状态</h3>'
        '<p>动态检索只有通过来源核验才进入结果；人工整理的公共信息卡另列。没有有效动态证据时，显示空结果，不补造引用。</p>'
        '<div class="cg-trust-example"><b>动态检索</b><span>可为空</span><i></i><b>离线信息卡</b><span>明确标注</span></div></div>'
        '<div class="cg-trust-card"><span>02 / MODEL</span><h3>模型输出，不是临床结论</h3>'
        '<p>旧模型诊断标签未经过养老场景验证，比赛分流不使用；模型内部自评分也不称作患病概率或准确率。</p>'
        '<div class="cg-trust-example"><b>标签</b><span>隔离</span><i></i><b>自评分</b><span>不作概率</span></div></div>'
        '<div class="cg-trust-card"><span>03 / OWNERSHIP</span><h3>决定权留在人手里</h3>'
        '<p>高风险案例要求人工说明；修改输入会使旧结果失效。审计摘要不会自动带入交接原文，人工填写的复核说明仍需避免敏感信息。</p>'
        '<div class="cg-trust-example"><b>系统</b><span>提示与留痕</span><i></i><b>专业人员</b><span>最终判断</span></div></div>'
        '</div>'
        '<div class="cg-trust-end"><p>想看当前电脑上真正跑通了什么、还有哪些未完成？</p>'
        '<a href="?focus=boundary" target="_self">打开真实性证据板 <span aria-hidden="true">↗</span></a></div>'
        '</section>',
        unsafe_allow_html=True,
    )


def _closing_section() -> None:
    st.markdown(
        '<section class="cg-closing" aria-label="进入演示">'
        '<div class="cg-closing-label">FROM STORY TO SYSTEM</div>'
        '<h2>现在，用一条合成记录，<br>把整条链走一遍。</h2>'
        '<p>载入案例、运行本地流程、查看来源状态，最后由演示复核员留下决定。'
        '这才是 CareLink 希望呈现的产品体验。</p>'
        '<a href="?focus=workspace" target="_self">进入可操作工作台 <span aria-hidden="true">↗</span></a>'
        '</section>',
        unsafe_allow_html=True,
    )


def _run_screening() -> None:
    note = st.session_state.cg_note.strip()
    if not note:
        st.error("请填写交接班记录。")
        return
    vitals_text = (
        f"生命体征：心率 {st.session_state.cg_hr} 次/分，血氧 {st.session_state.cg_spo2}%，"
        f"体温 {st.session_state.cg_temp}℃，呼吸 {st.session_state.cg_rr} 次/分。"
    )
    clinical_text = f"{note}\n{vitals_text}"
    multimodal_input = {
        "clinical_text": clinical_text,
    }
    st.session_state.cg_raw = None
    st.session_state.cg_review = None
    st.session_state.cg_screened_token = None
    st.session_state.cg_stale_warning = False
    with st.status("多智能体正在协同筛查…", expanded=True) as status:
        st.write("① 输入检查与语义编码")
        st.write("② 多策略检索与证据融合")
        st.write("③ 警示线索筛查与验证门控")
        try:
            raw = _ecosystem().run_collaborative_task(
                patient_query=note,
                multimodal_input=multimodal_input,
                force_high_risk=bool(st.session_state.cg_force),
            )
        except Exception:
            status.update(label="筛查未完成", state="error", expanded=False)
            st.error("本次筛查未生成结果。请检查本地推理服务和项目数据后重试；系统没有保留旧结果。")
            return
        st.session_state.cg_raw = raw
        st.session_state.cg_screened_token = _current_input_token()
        status.update(label="筛查完成，等待专业人员复核", state="complete", expanded=False)


def _input_panel() -> None:
    st.markdown(
        '<div id="cg-input-panel" class="cg-pane-label">01 / INPUT</div><h2 class="cg-pane-title">交接班信息</h2>'
        '<div class="cg-pane-desc">选用合成案例，或填写不含个人身份信息的演示记录。</div>',
        unsafe_allow_html=True,
    )
    c1, c2 = st.columns([3, 1])
    with c1:
        st.selectbox("演示案例", list(SAMPLE_CASES), key="cg_sample")
    with c2:
        st.write("")
        st.button("载入案例", on_click=_set_sample, width="stretch")

    st.text_area(
        "护理交接记录",
        key="cg_note",
        height=155,
        placeholder="请填写观察到的症状、发生时间和已经采取的措施。",
    )
    st.caption("演示请使用合成病例，不输入真实姓名、身份证号、联系方式或病历号。")

    st.markdown("**生命体征（演示输入）**")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.number_input("心率 次/分", 30, 220, key="cg_hr")
    with c2:
        st.number_input("血氧 %", 50, 100, key="cg_spo2")
    with c3:
        st.number_input("体温 ℃", 32.0, 43.0, step=0.1, key="cg_temp")
    with c4:
        st.number_input("呼吸 次/分", 5, 60, key="cg_rr")

    st.checkbox("演示中强制进入高风险人工复核流程", key="cg_force")
    if st.button("开始风险筛查", type="primary", width="stretch"):
        _run_screening()


def _metric_card(label: str, value: str, note: str) -> None:
    st.markdown(
        f'<div class="cg-card"><div class="cg-kicker">{escape(label)}</div>'
        f'<div class="cg-value">{escape(value)}</div><div class="cg-note">{escape(note)}</div></div>',
        unsafe_allow_html=True,
    )


def _waiting_panel() -> None:
    st.markdown(
        """
        <div class="cg-empty" aria-live="polite">
          <div class="cg-empty-top"><span>WORKSPACE / READY</span><span>● LOCAL DEMO</span></div>
          <div class="cg-empty-orbit" aria-hidden="true">✳</div>
          <h3>等待一次安全的演示输入</h3>
          <p>载入合成案例并开始筛查。风险线索、来源状态和人工复核入口会在这里出现。</p>
          <div class="cg-empty-flow"><span>01 输入记录</span><span>02 核验链路</span><span>03 人工决定</span></div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _result_preview(raw: Dict[str, Any]) -> None:
    view = build_screening_view(raw)
    priority = view["priority"]
    st.markdown(
        f'<div class="cg-empty"><div class="cg-empty-top"><span>WORKSPACE / RESULT READY</span>'
        f'<span>● REVIEW REQUIRED</span></div><div class="cg-empty-orbit" aria-hidden="true">{escape(priority["code"])}</div>'
        f'<h3>{escape(priority["label"])}</h3><p>{escape(priority["reason"])}。'
        f'推理链路：{escape(view["engine_label"])}。下方可查看完整证据链和人工复核入口。</p>'
        f'<div class="cg-empty-flow"><span>风险线索已整理</span><span>证据状态可见</span><span>等待人工复核</span></div></div>',
        unsafe_allow_html=True,
    )


def _results(raw: Dict[str, Any]) -> None:
    view = build_screening_view(raw)
    st.markdown(
        '<div id="cg-results-panel" class="cg-pane-label">02 / OUTPUT</div><h2 class="cg-pane-title">筛查结果与证据链</h2>'
        '<div class="cg-pane-desc">优先级只是演示线索，不是诊断结论或经过验证的临床分诊。</div>',
        unsafe_allow_html=True,
    )
    p = view["priority"]
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        _metric_card("复核优先级", f'{p["code"]} · {p["label"]}', p["reason"])
    with c2:
        _metric_card("观察到的警示线索", str(view["candidate_risk_domain"]), "演示规则提示，不是诊断或验证过的分诊工具")
    with c3:
        _metric_card("推理链路", view["engine_label"], "诊断标签未验证，不参与风险分流")
    with c4:
        _metric_card("可核验资料", f'{view["evidence_count"]} 动态 / {view["reference_count"]} 离线', f'冲突 {view["conflict_count"]} 处 · 耗时 {view["runtime_seconds"]}s')

    if view["requires_human_review"]:
        st.error("系统未自动放行：请由现场专业人员按机构流程评估；急性警示症状应及时启动相应急救流程。")
    else:
        st.warning("算法筛查未触发强制升级，但比赛版仍要求专业人员确认。")
    if view["engine_label"] != "Ollama 已验证":
        st.warning(view["engine_status"])

    left, right = st.columns([1, 1.35], gap="large")
    with left:
        st.markdown("#### 决策过程")
        for step in view["pipeline"]:
            st.markdown(
                f'<div class="cg-step"><strong>{escape(step["name"])}</strong> · {escape(step["status"])}'
                f'<div class="cg-note">{escape(step["detail"])}</div></div>',
                unsafe_allow_html=True,
            )
        temporal = view["temporal_assessment"]
        st.markdown("#### 时序风险模块")
        if temporal["available"]:
            st.success(str(temporal["label"]))
        else:
            st.info(f'{temporal["label"]}：{temporal["reason"]}')
        with st.expander("技术诊断信息（非临床结果）"):
            st.caption(f'模型内部自评分：{view["model_self_score"]:.3f}；未经校准，不是患病概率。')
            st.caption(f'诊断标签状态：{view["legacy_model_suppression_reason"]}')
            st.caption(f'推理后端：{view["engine_backend"]}。{view["engine_status"]}')
            st.caption(f'核心人工门控原因：{view["review_reason"]}')

    with right:
        st.markdown("#### 动态检索证据")
        if not view["evidence"]:
            st.info("本次动态检索没有通过来源核验的资料。下面的离线信息卡是预先人工整理，不冒充实时检索结果。")
        for idx, row in enumerate(view["evidence"], start=1):
            title = escape(str(row["title"]))
            url = str(row["url"])
            if urlparse(url).scheme == "https":
                title = f'<a href="{escape(url, quote=True)}" target="_blank" rel="noopener noreferrer">{title}</a>'
            st.markdown(
                f'<div class="cg-evidence"><div class="cg-evidence-title">{idx}. {title}</div>'
                f'<div class="cg-evidence-meta">来源：{escape(str(row["source"]))} · 更新：{escape(str(row["updated"]))} · '
                f'相关性：{row["relevance"]:.3f} · {escape(str(row["scope"]))}</div></div>',
                unsafe_allow_html=True,
            )
        st.markdown("#### 离线公共信息卡")
        st.caption("2026-10-10 人工核对网页；仅支持识别演示线索。英国 NHS 资料不替代中国当地急救流程或机构规范。")
        for idx, row in enumerate(view["reference_cards"], start=1):
            title = escape(row["title"])
            url = escape(row["url"], quote=True)
            st.markdown(
                f'<div class="cg-evidence"><div class="cg-evidence-title">{idx}. <a href="{url}" target="_blank" rel="noopener noreferrer">{title}</a></div>'
                f'<div class="cg-note">{escape(row["summary"])}</div>'
                f'<div class="cg-evidence-meta">{escape(row["source"])} · 人工核对于 {row["checked_on"]} · 非实时检索结果</div></div>',
                unsafe_allow_html=True,
            )

    _review_panel(raw, view)

    with st.expander("使用边界与失败保护", expanded=False):
        for item in view["limitations"]:
            st.markdown(f"- {item}")


def _review_panel(raw: Dict[str, Any], view: Dict[str, Any]) -> None:
    st.markdown(
        '<div class="cg-pane-label">03 / HUMAN REVIEW</div><h2 class="cg-pane-title">人工复核与审计导出</h2>'
        '<div class="cg-pane-desc">最终决定归属于复核人员。高风险案例需要留下判断依据。</div>',
        unsafe_allow_html=True,
    )
    with st.form("cg_review_form"):
        c1, c2 = st.columns([1, 2])
        with c1:
            reviewer = st.text_input("复核人（演示）", value="竞赛演示复核员")
        with c2:
            decision = st.selectbox("复核决定", review_decisions(view["priority"]["code"]))
        notes = st.text_area("复核说明", placeholder="记录判断依据、补充信息或处置建议。")
        st.caption("复核说明会写入下载的审计文件；请勿粘贴交接原文或个人身份信息。")
        submitted = st.form_submit_button("确认复核并生成审计记录", type="primary")
    if submitted:
        if not reviewer.strip():
            st.error("请填写复核人。")
        elif view["priority"]["code"] == "P1" and not notes.strip():
            st.error("P1 案例必须填写复核说明。")
        else:
            st.session_state.cg_review = {
                "status": "completed",
                "reviewer": reviewer.strip(),
                "decision": decision,
                "notes": notes.strip(),
                "reviewed_at": datetime.now().astimezone().isoformat(),
            }
            st.success("人工复核已记录。最终决定归属于复核人员，而非算法。")

    audit = build_audit_report(raw, view, st.session_state.cg_review)
    payload = json.dumps(audit, ensure_ascii=False, indent=2, default=str).encode("utf-8")
    c1, c2 = st.columns([1, 2])
    with c1:
        st.download_button(
            "下载审计记录 JSON",
            payload,
            file_name=f'careguard_audit_{view["request_id"]}.json',
            mime="application/json",
            width="stretch",
        )
    with c2:
        status = "已完成人工复核" if st.session_state.cg_review else "等待人工复核"
        st.caption(f"当前状态：{status}。审计文件包含输入哈希、证据来源、模型边界和人工决定；不会自动写入护理原文，人工复核说明按填写内容导出。")


def _evidence_page() -> None:
    manifest = _load_manifest()
    release = manifest.get("release_decision") or {}
    observed = manifest.get("live_pipeline_observation") or {}
    live, tests = _load_current_checks()
    st.markdown(
        '<div class="cg-section-heading"><div class="cg-section-overline">PROOF, NOT PROMISES</div>'
        '<h1 class="cg-section-title">项目真实性证据板</h1>'
        '<div class="cg-section-description">只展示本机能核验的能力、带时间戳的测试记录与明确的未完成项。'
        '这里不是持续监控面板，也不把历史快照当作当前结果。</div></div>',
        unsafe_allow_html=True,
    )
    c1, c2, c3, c4 = st.columns(4)
    passed = tests.get("total", 0) - tests.get("errors", 0) - tests.get("failures", 0) - tests.get("skipped", 0)
    c1.metric("最近全量测试", f"{passed} 通过" if tests else "待复测")
    c2.metric("最近 Ollama 自检", "已验证" if live.get("ollama_generation_verified") and not live.get("fallback_used") else "待复测")
    c3.metric("临床用途", "未获准" if not release.get("clinical_use_ready") else "验证通过")
    c4.metric("最近链路自检", f'{live["latency_seconds"]} 秒' if live.get("latency_seconds") is not None else "待复测")
    if live:
        checked_at = live.get("generated_at_utc", "")
        try:
            checked_at = datetime.fromisoformat(checked_at).astimezone().strftime("%Y-%m-%d %H:%M")
        except (TypeError, ValueError):
            checked_at = "时间未记录"
        st.caption(f'合成案例自检：{checked_at}（本地时间） · '
                   f'后端 {live.get("dma_backend", "未知")} · 动态证据 {live.get("dynamic_evidence_count", 0)} 条。')
    st.caption(f'历史快照（2026-09-20）：{release.get("tests_passed", "—")} 项通过，'
               f'链路 {round(observed.get("latency_seconds", 0), 2)} 秒；不代表当前环境。')

    st.markdown('<div class="cg-pane-label">CAPABILITY MAP</div><h3 class="cg-pane-title">能做什么，不能宣称什么</h3>', unsafe_allow_html=True)
    truth_rows = [
        ("本地多智能体流水线", "已实现", "代码、测试与现场运行", "ok"),
        ("本地 Ollama 推理", "最近自检已验证" if live.get("ollama_generation_verified") and not live.get("fallback_used") else "待复测", "合成案例自检后端与生成状态；旧版快照另存", "ok" if live.get("ollama_generation_verified") and not live.get("fallback_used") else "wait"),
        ("证据来源追踪", "已实现", "动态检索与人工整理离线信息卡分开展示", "ok"),
        ("旧模型失配保护", "比赛版已实现", "未验证诊断标签隔离，不参与风险分流", "ok"),
        ("人工复核与审计导出", "比赛版已实现", "界面操作与 JSON 记录", "ok"),
        ("时序恶化概率", "未启用", "缺少任务匹配且完成验证的检查点", "wait"),
        ("临床诊疗效果", "不宣称", "缺少独立外部临床验证", "limit"),
        ("护理机器人与床头硬件", "不纳入", "当前参赛成果为软件应用", "limit"),
    ]
    truth_cards = "".join(
        f'<div class="cg-truth-row"><div class="cg-truth-info"><b>{escape(name)}</b><small>{escape(detail)}</small></div>'
        f'<span class="cg-status {status_class}">{escape(status)}</span></div>'
        for name, status, detail, status_class in truth_rows
    )
    st.markdown(f'<div class="cg-truth-list">{truth_cards}</div>', unsafe_allow_html=True)

    st.markdown("#### 现场答辩四条边界")
    boundaries = manifest.get("claim_boundary") or [
        "现场报告仅证明本机模型、数据与软件链路可运行。",
        "内部数据和合成场景不能替代独立外部临床验证。",
        "模型自报confidence不是临床校准概率。",
        "合作材料仅证明合作或使用场景，不证明临床疗效。",
    ]
    for item in boundaries:
        st.markdown(f'<div class="cg-boundary">{escape(str(item))}</div><div style="height:.45rem"></div>', unsafe_allow_html=True)


def _footer() -> None:
    st.markdown(
        '<div id="careguard-boundary" class="cg-footer">'
        '<span><strong>CARELINK / 安护智链</strong> · 2026 数媒创赛演示原型</span>'
        '<span>仅限科研与竞赛演示 · 不构成医疗建议 · 专业人员负责最终判断</span>'
        '</div>',
        unsafe_allow_html=True,
    )


def main() -> None:
    _init_state()
    _inject_style()
    focus = st.query_params.get("focus")
    if focus != st.session_state.cg_url_focus:
        st.session_state.cg_page = "真实性证据板" if focus == "boundary" else "风险筛查演示"
        st.session_state.cg_url_focus = focus
    brand, navigation = st.columns([1.1, 1], vertical_alignment="center")
    with brand:
        st.markdown(
            '<a class="cg-brand" href="?" target="_self" aria-label="CareLink 返回首页"><span class="cg-mark" aria-hidden="true">CL</span>'
            '<span class="cg-wordmark">CareLink</span><span class="cg-brand-sub">安护智链 / 2026</span></a>',
            unsafe_allow_html=True,
        )
    with navigation:
        page = st.radio("演示页面", ["风险筛查演示", "真实性证据板"], horizontal=True,
                        label_visibility="collapsed", key="cg_page")
    st.markdown('<div class="cg-topmeta">自主选题 · 移动与网络应用开发类 &nbsp; / &nbsp; 科研与竞赛演示，不构成医疗建议</div>', unsafe_allow_html=True)
    if page != st.session_state.cg_previous_page:
        if page == "真实性证据板":
            _remember_inputs()
        else:
            _restore_inputs()
        st.session_state.cg_previous_page = page
    case_slug = st.query_params.get("case")
    if case_slug != st.session_state.cg_url_case:
        if case_slug in CASE_ROUTES:
            st.session_state.cg_sample = CASE_ROUTES[case_slug]
            _set_sample()
        st.session_state.cg_url_case = case_slug
    if page == "真实性证据板":
        _evidence_page()
    else:
        if focus != "workspace":
            _hero()
            _story()
            _context_section()
            _case_gallery()
            _system_section()
            _trust_section()
            _closing_section()
        st.markdown(
            '<div id="careguard-workspace" class="cg-section-heading"><div class="cg-section-overline">THE LIVE WORKSPACE</div>'
            '<h2 class="cg-section-title">从一条交接记录，走向可复核的行动</h2>'
            '<div class="cg-section-description">下面是真正可操作的合成案例演示。输入、运行、查看来源，再由人完成复核。</div></div>',
            unsafe_allow_html=True,
        )
        if st.session_state.cg_raw and st.session_state.cg_screened_token != _current_input_token():
            st.session_state.cg_raw = None
            st.session_state.cg_review = None
            st.session_state.cg_screened_token = None
            st.session_state.cg_stale_warning = True
        left, right = st.columns([1, 1], gap="large")
        with left:
            with st.container(border=True):
                _input_panel()
        with right:
            if st.session_state.cg_stale_warning:
                st.warning("输入已变化，上一份筛查结果和人工复核记录已作废；请重新筛查。")
            if st.session_state.cg_raw:
                _result_preview(st.session_state.cg_raw)
            else:
                _waiting_panel()
        if st.session_state.cg_raw:
            st.markdown('<div id="careguard-results" class="cg-section-heading"><div class="cg-section-overline">TRACEABLE OUTPUT</div>'
                        '<h2 class="cg-section-title">每个结论，都要带着边界出现</h2></div>', unsafe_allow_html=True)
            with st.container(border=True):
                _results(st.session_state.cg_raw)
    _footer()


if __name__ == "__main__":
    main()
