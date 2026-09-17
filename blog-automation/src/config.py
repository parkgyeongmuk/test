import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


def _get(name: str, required: bool = True, default: str = "") -> str:
    value = os.getenv(name, default)
    if required and not value:
        raise RuntimeError(f"환경변수 {name}이(가) 설정되지 않았습니다. .env를 확인하세요.")
    return value


@dataclass(frozen=True)
class CommerceConfig:
    client_id: str
    client_secret: str
    account_id: str


@dataclass(frozen=True)
class BlogConfig:
    login_client_id: str
    login_client_secret: str
    redirect_uri: str
    refresh_token: str
    category_no: str


def load_commerce_config() -> CommerceConfig:
    return CommerceConfig(
        client_id=_get("COMMERCE_CLIENT_ID"),
        client_secret=_get("COMMERCE_CLIENT_SECRET"),
        account_id=_get("COMMERCE_ACCOUNT_ID", required=False),
    )


def load_blog_config(require_refresh_token: bool = True) -> BlogConfig:
    return BlogConfig(
        login_client_id=_get("NAVER_LOGIN_CLIENT_ID"),
        login_client_secret=_get("NAVER_LOGIN_CLIENT_SECRET"),
        redirect_uri=_get("NAVER_LOGIN_REDIRECT_URI"),
        refresh_token=_get("NAVER_LOGIN_REFRESH_TOKEN", required=require_refresh_token),
        category_no=_get("BLOG_CATEGORY_NO", required=False),
    )
