"""네이버 오픈API - 블로그 글쓰기 클라이언트.

인증: 네이버 아이디 로그인(OAuth2 Authorization Code) 후 발급받은 refresh_token 을
이용해 access_token 을 갱신하며 사용합니다. (blog.writePost API 사용에는
네이버 개발자센터에서 '네이버 로그인' + '블로그' API 사용 신청/심사가 필요합니다)

문서: https://developers.naver.com , https://github.com/naver/naver-openapi-guide
"""
from __future__ import annotations

from dataclasses import dataclass

import requests

from .config import BlogConfig

TOKEN_URL = "https://nid.naver.com/oauth2.0/token"
WRITE_POST_URL = "https://openapi.naver.com/blog/writePost.json"
AUTHORIZE_URL = "https://nid.naver.com/oauth2.0/authorize"


class NaverBlogApiError(RuntimeError):
    """블로그 API 호출이 실패했을 때 발생."""


@dataclass
class BlogPost:
    title: str
    contents_html: str
    category_no: int | None = None
    open_type: str = "all"  # all(공개) | closed(비공개) | neighbor | agreedNeighbor


class NaverBlogClient:
    def __init__(self, config: BlogConfig, session: requests.Session | None = None):
        self._config = config
        self._session = session or requests.Session()
        self._access_token: str | None = None

    def _refresh_access_token(self) -> str:
        resp = self._session.get(
            TOKEN_URL,
            params={
                "grant_type": "refresh_token",
                "client_id": self._config.client_id,
                "client_secret": self._config.client_secret,
                "refresh_token": self._config.refresh_token,
            },
            timeout=10,
        )
        if not resp.ok:
            raise NaverBlogApiError(f"액세스 토큰 갱신 실패 ({resp.status_code}): {resp.text}")
        body = resp.json()
        if "access_token" not in body:
            raise NaverBlogApiError(f"액세스 토큰 갱신 응답 이상: {body}")
        return body["access_token"]

    def _token(self) -> str:
        if self._access_token is None:
            self._access_token = self._refresh_access_token()
        return self._access_token

    def write_post(self, post: BlogPost) -> dict:
        data = {
            "title": post.title,
            "contents": post.contents_html,
            "openType": post.open_type,
        }
        if self._config.blog_id:
            data["blogId"] = self._config.blog_id
        if post.category_no is not None:
            data["categoryNo"] = post.category_no

        resp = self._session.post(
            WRITE_POST_URL,
            headers={"Authorization": f"Bearer {self._token()}"},
            data=data,
            timeout=15,
        )
        if not resp.ok:
            raise NaverBlogApiError(f"블로그 글 작성 실패 ({resp.status_code}): {resp.text}")
        return resp.json()
