"""Join form protects applicant data and never pretends to have sent mail."""

from __future__ import annotations

import json
from html.parser import HTMLParser

from fastapi.testclient import TestClient

import careguard_join
from careguard_site import app


client = TestClient(app)
PAYLOAD = {
    "name": "测试申请人", "email": "applicant@example.org", "phone": "", "organization": "",
    "city": "", "track": "前端与创意技术", "availability": "远程协作",
    "portfolio": "https://example.org/work", "message": "我希望参与可访问性与交互图谱设计，并愿意承担原型开发。",
    "consent": True, "website": "",
}


def test_join_page_and_photos_are_served():
    html = client.get("/?view=join").text
    assert 'id="join-view"' in html
    assert 'id="join-form"' in html
    assert 'class="join-editorial"' in html
    assert 'class="join-process"' in html
    assert 'id="join-track-preview"' in html
    assert 'id="join-message-count"' in html
    assert "04 / ONE CASE, END TO END" in html
    assert "yuanjiegu52@gmail.com" in html
    assert 'src="/assets/diagrams/input-flow.svg"' in html
    assert client.get("/assets/archive/field-pharmacy.jpg").status_code == 404
    for name in ("working-session.jpeg", "field-place.jpeg"):
        assert client.get(f"/assets/join/{name}").status_code == 404


def test_join_project_journey_is_chronological_and_source_bound():
    html = client.get("/?view=join").text
    journey = html.split('id="join-journey"', 1)[1].split('class="join-editorial"', 1)[0]
    assert journey.index('datetime="2026-02"') < journey.index('class="is-current"')
    assert 'RESEARCH TO PRACTICE / 02 CHAPTERS' in journey
    for text in ("MAPFM", "论文发布", "安护智链", "CareLink"):
        assert text in journey
    for text in ("智医算", "SmartNursing", "智弈护晓", "DawnGuard"):
        assert text not in journey
    for text in ("获奖", "铜奖", "三等奖", "旧奖项", "历史奖项"):
        assert text not in html
    assert 'href="/?view=home#architecture-handbook"' in journey
    assert client.get("/assets/research/mapfm-paper-first-page.png").status_code == 404


def test_join_story_links_assets_and_controls_are_grounded():
    class Elements(HTMLParser):
        def __init__(self):
            super().__init__()
            self.items = []

        def handle_starttag(self, tag, attrs):
            self.items.append((tag, dict(attrs)))

    html = client.get("/?view=join").text
    page = Elements()
    page.feed(html)
    ids = [attrs["id"] for _, attrs in page.items if "id" in attrs]
    for name in ("join-fieldwork", "join-build", "join-case-story", "join-agent-story", "join-contribute"):
        assert ids.count(name) == 1
    tabs = [attrs for _, attrs in page.items if "data-join-case" in attrs]
    assert len(tabs) == 5
    assert sum(tab["aria-selected"] == "true" for tab in tabs) == 1
    for tab in tabs:
        assert ids.count(tab["aria-controls"]) == 1
        assert tab["type"] == "button"
    roles = [attrs for _, attrs in page.items if "data-join-track" in attrs]
    assert len(roles) == 6
    assert all(role["data-join-track"] in careguard_join.TRACKS for role in roles)
    assert all(role["type"] == "button" for role in roles)
    for path in ("/join-story.css", "/join-story.js", "/assets/diagrams/input-flow.svg",
                 "/assets/diagrams/agent-map.svg", "/assets/diagrams/review-loop.svg"):
        assert client.get(path).status_code == 200
    for path in ("/?view=workspace&case=chest#input-title", "/?view=workspace&case=draft#input-title",
                 "/?view=home#architecture-handbook", "/?view=workspace#review-desk"):
        assert any(tag == "a" and attrs.get("href") == path for tag, attrs in page.items)
    assert "不代表十个独立训练的大模型" in html
    assert "流程导览不是实时运行回执" in html
    assert "不是实时运行截图、机构背书或临床效果证据" in html


def test_join_is_clearly_unavailable_without_mail_configuration(monkeypatch):
    for key in (
        "CAREGUARD_MAIL_FROM", "CAREGUARD_RESEND_API_KEY", "CAREGUARD_SMTP_HOST",
        "CAREGUARD_SMTP_USER", "CAREGUARD_SMTP_PASSWORD",
    ):
        monkeypatch.delenv(key, raising=False)
    assert client.get("/site/join/status").json()["ready"] is False
    response = client.post("/site/join", json=PAYLOAD)
    assert response.status_code == 503
    assert "未发送" in response.json()["detail"]


def test_join_requires_consent_and_rejects_invalid_input(monkeypatch):
    monkeypatch.setenv("CAREGUARD_MAIL_FROM", "CareLink <team@example.org>")
    monkeypatch.setenv("CAREGUARD_RESEND_API_KEY", "test-key-not-real")
    assert client.post("/site/join", json={**PAYLOAD, "consent": False}).status_code == 422
    assert client.post("/site/join", json={**PAYLOAD, "email": "not-an-email"}).status_code == 422
    assert client.post("/site/join", json={**PAYLOAD, "name": "   "}).status_code == 422
    assert client.post("/site/join", json={**PAYLOAD, "message": "                     "}).status_code == 422
    assert client.post("/site/join", json={**PAYLOAD, "portfolio": "file:///secret"}).status_code == 422
    assert client.post("/site/join", json={**PAYLOAD, "website": "spam"}).status_code == 400


def test_join_uses_fixed_recipient_and_server_side_resend_key(monkeypatch):
    monkeypatch.setenv("CAREGUARD_MAIL_FROM", "CareLink <team@example.org>")
    monkeypatch.setenv("CAREGUARD_RESEND_API_KEY", "test-key-not-real")
    careguard_join._attempts.clear()
    calls = []

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *_):
            return None

        def read(self):
            return b'{"id":"email-test-123"}'

    def fake_urlopen(request, timeout):
        calls.append((request, timeout))
        return FakeResponse()

    monkeypatch.setattr(careguard_join, "urlopen", fake_urlopen)
    response = client.post("/site/join", json=PAYLOAD)
    assert response.status_code == 200
    assert response.json() == {"accepted": True, "provider": "resend", "receipt": "email-test-123"}
    assert len(calls) == 1
    request, timeout = calls[0]
    body = json.loads(request.data.decode("utf-8"))
    assert request.full_url == "https://api.resend.com/emails"
    assert timeout == 12
    assert body["to"] == ["yuanjiegu52@gmail.com"]
    assert body["reply_to"] == PAYLOAD["email"]
    assert body["text"].find(PAYLOAD["message"]) >= 0
    assert "test-key-not-real" not in response.text
    assert client.get("/site/join/status").json() == {
        "ready": True, "provider": "resend", "recipient": "yuanjiegu52@gmail.com",
    }
