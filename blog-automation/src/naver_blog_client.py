"""네이버 로그인(네아로) 기반 블로그 글쓰기 API 클라이언트.

블로그 글쓰기(/blog/writePost)는 반드시 '네이버 아이디로 로그인' 심사를
통과한 애플리케이션의 access token으로만 호출 가능하다.
"""
import time

import requests

from config import BlogConfig

TOKEN_URL = "https://nid.naver.com/oauth2.0/token"
WRITE_POST_URL = "https://openapi.naver.com/blog/writePost.json"


class NaverBlogClient:
    def __init__(self, config: BlogConfig):
        self._config = config
        self._access_token: str | None = None
        self._expires_at: float = 0.0

    def _refresh_access_token(self) -> None:
        params = {
            "grant_type": "refresh_token",
            "client_id": self._config.login_client_id,
            "client_secret": self._config.login_client_secret,
            "refresh_token": self._config.refresh_token,
        }
        resp = requests.get(TOKEN_URL, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        if "error" in data:
            raise RuntimeError(f"네이버 로그인 토큰 갱신 실패: {data}")
        self._access_token = data["access_token"]
        self._expires_at = time.time() + int(data.get("expires_in", 3600)) - 60

    def _get_access_token(self) -> str:
        if not self._access_token or time.time() >= self._expires_at:
            self._refresh_access_token()
        return self._access_token

    def publish_post(self, title: str, contents: str) -> dict:
        headers = {"Authorization": f"Bearer {self._get_access_token()}"}
        data = {"title": title, "contents": contents}
        if self._config.category_no:
            data["categoryNo"] = self._config.category_no

        resp = requests.post(WRITE_POST_URL, headers=headers, data=data, timeout=10)
        resp.raise_for_status()
        return resp.json()
