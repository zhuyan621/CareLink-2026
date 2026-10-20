"""Basic contract checks for the standalone competition frontend."""

import csv
from pathlib import Path

from fastapi.testclient import TestClient

from careguard_site import app


def test_site_serves_product_frontend_and_local_assets():
    client = TestClient(app)
    home = client.get("/")
    assert home.status_code == 200
    assert "让照护风险" in home.text
    assert "把一次交接" in home.text
    assert "本机最近留下的" in home.text
    assert 'data-workflow-stage="review"' in home.text
    assert 'data-claim-filter="limited"' in home.text
    assert 'data-launch-case="stroke"' in home.text
    assert 'data-launch-case="baseline"' in home.text
    assert 'data-open-case="recheck"' in home.text
    assert 'data-case="context"' in home.text
    assert 'id="dataset-questions"' in home.text
    assert 'id="dataset-search"' in home.text
    assert 'medNo.22.csv' in home.text
    assert "安护智链 CareLink" in home.text
    assert 'id="launch-open-case"' in home.text
    assert 'id="clinical-readout-title"' in home.text
    assert 'id="home-medical-wave"' in home.text
    assert 'id="workspace-medical-wave"' in home.text
    assert 'id="workspace-guidance"' in home.text
    assert 'href="#workspace-guidance"' in home.text
    assert 'id="join-medical-wave"' in home.text
    assert "图形节律非实测波形" in home.text
    assert 'id="global-test-count"' in home.text
    assert 'id="evidence-faq-title"' in home.text
    assert 'id="audience-panel"' in home.text
    assert 'data-audience="reviewer"' in home.text
    assert 'id="run-phase"' in home.text
    assert 'id="run-sources"' in home.text
    assert 'id="claim-inspector"' in home.text
    assert 'id="claim-file-boundary"' in home.text
    assert 'id="case-brief-title"' in home.text
    assert 'id="session-events"' in home.text
    assert 'id="diag-fallback"' in home.text
    assert 'id="material-image"' in home.text
    assert 'data-material="interface"' in home.text
    assert "case=stroke" not in home.text  # routing is handled by the local UI, not fake links

    css = client.get("/site.css")
    js = client.get("/site.js")
    particles = client.get("/particles.js")
    medical = client.get("/medical.js")
    dataset = client.get("/dataset.js")
    assert css.status_code == 200
    assert js.status_code == 200
    assert particles.status_code == 200
    assert medical.status_code == 200
    assert dataset.status_code == 200
    assert "not sampled ECG" in medical.text
    assert "prefers-reduced-motion" in medical.text
    assert "fonts.googleapis.com" not in css.text
    assert 'fetch("/screening/engineering"' in js.text
    assert 'id="engineering-bridge-title"' in home.text
    assert client.get("/engineering.css").status_code == 200
    guidance_css = client.get("/workspace-guidance.css")
    assert guidance_css.status_code == 200
    assert ".workspace-guidance-row" in guidance_css.text
    assert ".review-context" in guidance_css.text
    assert "medquad-audit-details" in client.get("/medquad.js").text
    assert "function selectClaim(row)" in js.text
    assert "function setAudience(key)" in js.text
    assert "function addSessionEvent(" in js.text
    assert "function setMaterial(key)" in js.text
    assert "function sensitiveInputReason(value)" in js.text
    assert "function updateInputPreflight()" in js.text
    assert "function renderSessionProof(" in js.text
    assert '$(".source-chain").before(proof)' in js.text
    assert "EXECUTION TRACE / THIS REQUEST" in js.text
    assert ".trace-pipeline" in css.text
    assert ".live-proof-path" in css.text
    assert 'id="hero-particles"' in home.text
    assert 'id="atlas-particles"' in home.text
    assert 'id="atlas-open-case"' in home.text
    assert "prefers-reduced-motion" in particles.text
    assert "visibilitychange" in particles.text
    assert client.get("/assets/archive/field-visit.jpeg").status_code == 200
    assert client.get("/assets/archive/legacy-interface.jpeg").status_code == 200


def test_dataset_browser_preserves_source_rows_without_claiming_patient_cases():
    client = TestClient(app)
    response = client.get("/site/dataset/questions", params={"featured": "true"})
    assert response.status_code == 200
    data = response.json()
    assert data["dataset"] == "medNo.22.csv"
    assert data["kind"] == "medical_qa_not_patient_records"
    assert data["total_rows"] == 605
    assert [item["id"] for item in data["items"]] == [641, 506, 753, 250, 19, 433]
    assert all(item["source"] == "NIHSeniorHealth" for item in data["items"])
    filtered = client.get("/site/dataset/questions", params={"area": "Stroke", "q": "symptoms"}).json()
    assert filtered["matched"] > 0
    assert all(item["area"] == "Stroke" and "symptoms" in item["question"].lower() for item in filtered["items"])
    exact = client.get("/site/dataset/questions", params={"q": "#381"}).json()
    assert exact["matched"] == 1
    assert exact["items"][0]["id"] == 381
    assert client.get("/site/dataset/questions", params={"q": "#999999"}).json()["matched"] == 0


def test_all_605_original_question_rows_are_indexed_and_downloadable():
    client = TestClient(app)
    source = Path(__file__).resolve().parents[1] / "medNo.22.csv"
    with source.open(encoding="utf-8-sig", newline="") as handle:
        original = list(csv.DictReader(handle))
    manifest = client.get("/site/dataset/manifest").json()
    assert manifest["total_rows"] == manifest["unique_ids"] == len(original) == 605
    assert sum(topic["count"] for topic in manifest["topics"]) == 605
    assert manifest["topic_count"] == len({row["area"].casefold() for row in original}) == 21
    indexed = []
    for offset in range(0, 605, 24):
        response = client.get("/site/dataset/questions", params={"offset": offset, "limit": 24})
        assert response.status_code == 200
        assert response.json()["matched"] == 605
        indexed.extend(response.json()["items"])
    assert [row["id"] for row in indexed] == [int(row["id"]) for row in original]
    for row in (original[0], original[302], original[-1]):
        assert client.get(f"/site/dataset/questions/{row['id']}").json() == {key: value.strip() for key, value in row.items()}
    assert client.get("/site/dataset/source").content == source.read_bytes()
    assert client.get("/site/dataset/questions/999999").status_code == 404


def test_handover_and_local_library_controls_are_present():
    client = TestClient(app)
    home = client.get("/").text
    script = client.get("/site.js").text
    for control in ("handover-title", "event-time", "observed-change", "action-taken", "custom-case-list", "new-case-button"):
        assert f'id="{control}"' in home
    assert "MAX_LIBRARY_ITEMS = 10" in script
    assert "localStorage.setItem(CASE_LIBRARY_KEY" in script
    assert "state.audit?.human_review?.status !== \"completed\"" in script
    assert "护理交接记录：${note}" in script
    assert "caseInputSignature()" in script
    assert "当前交接内容尚未保存" in script
    for asset in ("field-pharmacy.jpg", "team-work.jpg"):
        assert client.get(f"/assets/archive/{asset}").status_code == 200


def test_dataset_pager_and_manual_mail_fallback_are_explicit():
    client = TestClient(app)
    home = client.get("/").text
    dataset = client.get("/dataset.js").text
    join = client.get("/join.js").text
    for control in ("dataset-page-form", "dataset-prev", "dataset-next", "dataset-page"):
        assert f'id="{control}"' in home
    assert "PAGE_SIZE = 24" in dataset
    assert "load(page - 1)" in dataset
    assert 'id="join-mail-fallback"' in home
    assert "此入口不会自动发送" in home
    assert "fallback.hidden = deliveryReady" in join


def test_site_status_discloses_timestamped_snapshot_and_clinical_boundary():
    response = TestClient(app).get("/site/status")
    assert response.status_code == 200
    data = response.json()
    assert set(data) == {"tests", "smoke", "clinical_use_ready"}
    assert data["clinical_use_ready"] is False
    assert "checked_at_local" in data["smoke"]
