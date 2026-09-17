"""환경변수 기반 설정 로딩."""
from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


def _require(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError(f"환경변수 {name} 가 설정되지 않았습니다. .env.example 을 참고하세요.")
    return value


@dataclass(frozen=True)
class CommerceConfig:
    client_id: str
    client_secret: str
    account_type: str
    account_id: str | None

    @classmethod
    def from_env(cls) -> "CommerceConfig":
        return cls(
            client_id=_require("NAVER_COMMERCE_CLIENT_ID"),
            client_secret=_require("NAVER_COMMERCE_CLIENT_SECRET"),
            account_type=os.environ.get("NAVER_COMMERCE_ACCOUNT_TYPE", "SELF").strip() or "SELF",
            account_id=os.environ.get("NAVER_COMMERCE_ACCOUNT_ID", "").strip() or None,
        )


@dataclass(frozen=True)
class BlogConfig:
    client_id: str
    client_secret: str
    refresh_token: str
    blog_id: str | None

    @classmethod
    def from_env(cls) -> "BlogConfig":
        return cls(
            client_id=_require("NAVER_BLOG_CLIENT_ID"),
            client_secret=_require("NAVER_BLOG_CLIENT_SECRET"),
            refresh_token=_require("NAVER_BLOG_REFRESH_TOKEN"),
            blog_id=os.environ.get("NAVER_BLOG_ID", "").strip() or None,
        )


@dataclass(frozen=True)
class ReportConfig:
    days: int

    @classmethod
    def from_env(cls) -> "ReportConfig":
        raw = os.environ.get("REPORT_DAYS", "1").strip() or "1"
        try:
            days = int(raw)
        except ValueError as exc:
            raise RuntimeError("REPORT_DAYS 는 정수여야 합니다.") from exc
        if days <= 0:
            raise RuntimeError("REPORT_DAYS 는 1 이상이어야 합니다.")
        return cls(days=days)
