"""Consent-based project contact form. No applicant data is persisted locally."""

from __future__ import annotations

import json
import os
import re
import smtplib
import ssl
import threading
import time
import uuid
from collections import defaultdict, deque
from email.message import EmailMessage
from typing import Literal
from urllib.parse import urlsplit
from urllib.request import Request as UrlRequest, urlopen

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field, field_validator


router = APIRouter()
RECIPIENT = "yuanjiegu52@gmail.com"
TRACKS = (
    "产品与交互设计", "前端与创意技术", "后端与 AI 工程", "照护场景研究",
    "医学与合规咨询", "机构或项目合作", "其他合作",
)
AVAILABILITY = ("未确定", "远程协作", "线下交流", "短期项目", "长期合作")
_attempts: dict[str, deque[float]] = defaultdict(deque)
_attempt_lock = threading.Lock()


class JoinApplication(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    email: str = Field(min_length=5, max_length=254)
    phone: str = Field(default="", max_length=32)
    organization: str = Field(default="", max_length=120)
    city: str = Field(default="", max_length=80)
    track: Literal[
        "产品与交互设计", "前端与创意技术", "后端与 AI 工程", "照护场景研究",
        "医学与合规咨询", "机构或项目合作", "其他合作",
    ]
    availability: Literal["未确定", "远程协作", "线下交流", "短期项目", "长期合作"] = "未确定"
    portfolio: str = Field(default="", max_length=300)
    message: str = Field(min_length=20, max_length=2000)
    consent: bool
    website: str = Field(default="", max_length=100)

    @field_validator("name", "email", "phone", "organization", "city", "portfolio", "message", "website")
    @classmethod
    def trim_and_reject_controls(cls, value: str) -> str:
        value = value.strip()
        if any(ord(char) < 32 and char not in "\n\t" for char in value):
            raise ValueError("不支持控制字符")
        return value

    @field_validator("name")
    @classmethod
    def valid_name_after_trim(cls, value: str) -> str:
        if len(value) < 2:
            raise ValueError("称呼至少需要 2 个字符")
        return value

    @field_validator("message")
    @classmethod
    def valid_message_after_trim(cls, value: str) -> str:
        if len(value) < 20:
            raise ValueError("合作想法至少需要 20 个字符")
        return value

    @field_validator("email")
    @classmethod
    def valid_email(cls, value: str) -> str:
        if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", value):
            raise ValueError("邮箱格式不正确")
        return value

    @field_validator("portfolio")
    @classmethod
    def valid_portfolio(cls, value: str) -> str:
        if value and (urlsplit(value).scheme not in {"http", "https"} or not urlsplit(value).netloc):
            raise ValueError("作品链接必须是 http 或 https 地址")
        return value


def _delivery_config() -> tuple[str | None, dict[str, str]]:
    sender = os.getenv("CAREGUARD_MAIL_FROM", "").strip()
    if not sender or "\n" in sender or "\r" in sender or "@" not in sender:
        return None, {}
    resend_key = os.getenv("CAREGUARD_RESEND_API_KEY", "").strip()
    if resend_key:
        return "resend", {"sender": sender, "key": resend_key}
    host = os.getenv("CAREGUARD_SMTP_HOST", "").strip()
    user = os.getenv("CAREGUARD_SMTP_USER", "").strip()
    password = os.getenv("CAREGUARD_SMTP_PASSWORD", "")
    port = os.getenv("CAREGUARD_SMTP_PORT", "465").strip()
    if host and user and password and port in {"465", "587"}:
        return "smtp", {"sender": sender, "host": host, "user": user, "password": password, "port": port}
    return None, {}


def _mail_text(application: JoinApplication) -> str:
    fields = [
        ("称呼", application.name), ("邮箱", application.email), ("电话", application.phone or "未填写"),
        ("学校/机构", application.organization or "未填写"), ("城市", application.city or "未填写"),
        ("参与方向", application.track), ("合作方式", application.availability),
        ("作品链接", application.portfolio or "未填写"), ("自我介绍与合作想法", application.message),
    ]
    return "CareLink 加入我们 · 合作意向\n\n" + "\n\n".join(f"{label}：{value}" for label, value in fields)


def _send_resend(config: dict[str, str], application: JoinApplication) -> str:
    payload = json.dumps({
        "from": config["sender"], "to": [RECIPIENT], "reply_to": application.email,
        "subject": "CareLink · 新的合作意向", "text": _mail_text(application),
    }, ensure_ascii=False).encode("utf-8")
    request = UrlRequest(
        "https://api.resend.com/emails", data=payload, method="POST",
        headers={
            "Authorization": f"Bearer {config['key']}", "Content-Type": "application/json",
            "Idempotency-Key": f"careguard-join-{uuid.uuid4().hex}",
        },
    )
    with urlopen(request, timeout=12) as response:
        result = json.loads(response.read().decode("utf-8"))
    if not result.get("id"):
        raise RuntimeError("邮件服务未返回确认 ID")
    return str(result["id"])


def _send_smtp(config: dict[str, str], application: JoinApplication) -> str:
    message = EmailMessage()
    message["From"] = config["sender"]
    message["To"] = RECIPIENT
    message["Reply-To"] = application.email
    message["Subject"] = "CareLink · 新的合作意向"
    message.set_content(_mail_text(application))
    port = int(config["port"])
    if port == 465:
        with smtplib.SMTP_SSL(config["host"], port, timeout=12, context=ssl.create_default_context()) as server:
            server.login(config["user"], config["password"])
            server.send_message(message)
    else:
        with smtplib.SMTP(config["host"], port, timeout=12) as server:
            server.starttls(context=ssl.create_default_context())
            server.login(config["user"], config["password"])
            server.send_message(message)
    return message["Message-ID"] or "smtp-accepted"


@router.get("/site/join/status")
def join_status() -> dict:
    provider, _ = _delivery_config()
    return {"ready": provider is not None, "provider": provider or "unconfigured", "recipient": RECIPIENT}


@router.post("/site/join")
def submit_join(application: JoinApplication, request: Request) -> dict:
    origin = request.headers.get("origin")
    if origin and urlsplit(origin).netloc != request.url.netloc:
        raise HTTPException(status_code=403, detail="只接受本站表单提交。")
    if not application.consent:
        raise HTTPException(status_code=422, detail="请先同意将联系信息发送到项目邮箱。")
    if application.website:
        raise HTTPException(status_code=400, detail="表单校验未通过。")
    provider, config = _delivery_config()
    if not provider:
        raise HTTPException(status_code=503, detail="邮件通道尚未配置；未发送任何信息。")
    client_id = request.client.host if request.client else "unknown"
    now = time.monotonic()
    with _attempt_lock:
        recent = _attempts[client_id]
        while recent and now - recent[0] > 600:
            recent.popleft()
        if len(recent) >= 3:
            raise HTTPException(status_code=429, detail="提交过于频繁，请稍后再试。")
        recent.append(now)
    try:
        receipt = _send_resend(config, application) if provider == "resend" else _send_smtp(config, application)
    except Exception as exc:
        # Never return credentials, applicant data or provider response bodies to the browser.
        raise HTTPException(status_code=502, detail="邮件服务未确认接收；请检查发件配置或稍后重试。") from exc
    return {"accepted": True, "provider": provider, "receipt": receipt}
