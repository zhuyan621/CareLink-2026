"""The reviewed handover artifact is generated from a real local result only."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from careguard_site import app


ROOT = Path(__file__).resolve().parents[1]


def _run_node(script: str) -> None:
    if not shutil.which("node"):
        pytest.skip("Node.js is required for the browser helper contract check")
    subprocess.run(["node", "-e", script], cwd=ROOT, check=True, capture_output=True, text=True)


def test_reviewed_handover_panel_and_helper_are_served():
    client = TestClient(app)
    html = client.get("/?view=workspace").text
    js = client.get("/site.js").text
    assert '<script src="/handoff.js?' in html
    assert 'id="handover-packet"' in html
    assert 'id="download-handover"' in html
    assert 'id="handover-packet-sources"' in html
    assert client.get("/handoff.js").status_code == 200
    assert 'state.audit?.human_review?.status !== "completed"' in js
    assert '$("#handover-packet").hidden = true' in js
    assert 'renderHandoverPacket();' in js


def test_handover_helper_requires_review_and_keeps_zero_dynamic_evidence_zero():
    _run_node(r"""
const assert = require('node:assert/strict');
const { build, toText } = require('./careguard_web/handoff.js');
const record = { title: '合成夜班案例', note: '观察变化，已通知值班负责人。',
  eventTime: '2026-10-11T21:00', observedChange: '状态变化', actionTaken: '已交接',
  heartRate: 112, spo2: 91, temperature: 37.2, respiratoryRate: 25 };
const screening = { request_id: 'demo-001', priority: { code: 'P1' },
  observed_clue: '胸痛及伴随症状', engine_label: 'Ollama 已验证',
  evidence_count: 0, reference_count: 1 };
assert.throws(() => build(record, screening, null), /人工复核/);
assert.throws(() => build(record, screening, { status: 'completed', decision: '维持常规观察', notes: '说明' }), /不得自动放行/);
assert.throws(() => build(record, screening, { status: 'completed', decision: '立即转专业人员评估', notes: '' }), /必须保留/);
const packet = build(record, screening, { status: 'completed', reviewer: '演示复核员',
  decision: '立即转专业人员评估', notes: '已人工确认演示流程', reviewed_at: '2026-10-11T12:00:00Z' });
assert.equal(packet.dynamicEvidence, 0);
assert.equal(packet.offlineReferences, 1);
assert.equal(packet.eventTime, '2026-10-11 21:00');
const text = toText(packet);
assert.match(text, /动态核验 0 条；人工整理的离线参考 1 条/);
assert.match(text, /不是病历、诊断、医嘱或临床交接凭证/);
assert.doesNotMatch(text, /动态核验 1 条/);
""")
