"""Contracts for the non-clinical, reproducible 3D research atlas."""

import json
import shutil
import subprocess
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from careguard_site import app
from careguard_presenter import _priority


ROOT = Path(__file__).resolve().parent.parent


def test_lab_is_served_and_integrated_with_the_site():
    client = TestClient(app)
    home = client.get("/").text
    assert 'data-nav="lab"' in home
    assert 'id="lab-view"' in home
    assert 'id="lab-canvas-observation"' in home
    assert 'id="lab-canvas-gate"' in home
    assert 'id="lab-canvas-source"' in home
    assert 'id="lab-density-input"' in home
    assert 'id="lab-medical-wave"' in home
    assert 'id="lab-monitor-spo2"' in home
    assert "只改变视觉层，不改变 173 个可操作数据中心" in home
    for path in ["/lab-data.js", "/lab3d.js"]:
        assert client.get(path).status_code == 200
    assert "loadLabVariant(point)" in client.get("/site.js").text
    assert "RESEARCH_LAB_METHOD.md" in home


def test_lab_data_is_deterministic_and_gate_logic_matches_presenter():
    if not shutil.which("node"):
        pytest.skip("Node.js is required to exercise browser data generation")
    script = """
const d=require('./careguard_web/lab-data.js');
const a=d.observationPoints(), b=d.gatePoints(), c=d.sourcePoints();
const counts=b.reduce((out,p)=>(out[p.code]=(out[p.code]||0)+1,out),{});
console.log(JSON.stringify({lengths:[a.length,b.length,c.length],
  centers:a.filter(p=>p.central).map(p=>[p.caseId,p.x,p.y,p.z]),
  unique:[new Set(a.map(p=>p.id)).size,new Set(b.map(p=>p.id)).size,new Set(c.map(p=>p.id)).size],
  counts,gap:c.find(p=>p.id==='clinical-gap').group,
  designs:c.filter(p=>p.group==='design').map(p=>({key:p.materialKey,image:p.image,color:p.color})),
  gates:b.map(p=>({conflicts:p.conflicts,acute:p.acute,highRisk:p.highRisk,
    hitl:p.hitl,consensusApproved:p.consensusApproved,code:p.code}))}));
"""
    result = subprocess.run(
        ["node", "-e", script], cwd=ROOT, check=True,
        capture_output=True, text=True, timeout=10,
    )
    report = json.loads(result.stdout)
    assert report["lengths"] == [81, 80, 12]
    assert report["unique"] == [81, 80, 12]
    assert report["centers"] == [
        ["chest", 112, 91, 25], ["stroke", 96, 95, 20], ["change", 102, 93, 23]
    ]
    assert report["counts"] == {"P1": 76, "P2": 3, "P3": 1}
    assert report["gap"] == "gap"
    assert {point["key"] for point in report["designs"]} == {"input", "agents", "sources", "review", "research"}
    assert all(point["image"].startswith("/assets/diagrams/") and point["color"] for point in report["designs"])
    for gate in report["gates"]:
        raw = {
            "high_risk": gate["highRisk"],
            "verification": {"serious_conflicts": gate["conflicts"]},
            "hitl": {"triggered": gate["hitl"]},
            "consensus": {"approved": gate["consensusApproved"]},
        }
        clue = {"level": "P1" if gate["acute"] else "P3"}
        assert _priority(raw, "", clue)["code"] == gate["code"]
