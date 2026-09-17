"""네이버 블로그 글쓰기 API 사용을 위한 refresh_token 최초 1회 발급 스크립트.

사전 준비:
  1. https://developers.naver.com 에서 애플리케이션을 등록하고
     '네이버 로그인' + '블로그' API 사용 설정을 합니다.
  2. 등록한 애플리케이션의 '서비스 URL'/'Callback URL' 에
     아래 REDIRECT_URI 와 동일한 값을 등록해 둡니다. (기본값: http://localhost:8080/callback)
  3. .env 파일에 NAVER_BLOG_CLIENT_ID, NAVER_BLOG_CLIENT_SECRET 을 채워둡니다.

실행:
    python scripts/get_blog_refresh_token.py

브라우저에서 로그인을 완료하면 리다이렉트된 주소를 터미널에 붙여넣으라는
안내가 나옵니다. 그 주소를 붙여넣으면 refresh_token 을 출력해줍니다.
출력된 값을 .env 의 NAVER_BLOG_REFRESH_TOKEN 에 저장하세요.
"""
from __future__ import annotations

import os
import secrets
import sys
import urllib.parse
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv()

REDIRECT_URI = os.environ.get("NAVER_BLOG_REDIRECT_URI", "http://localhost:8080/callback")
AUTHORIZE_URL = "https://nid.naver.com/oauth2.0/authorize"
TOKEN_URL = "https://nid.naver.com/oauth2.0/token"


def main() -> None:
    client_id = os.environ.get("NAVER_BLOG_CLIENT_ID", "").strip()
    client_secret = os.environ.get("NAVER_BLOG_CLIENT_SECRET", "").strip()
    if not client_id or not client_secret:
        sys.exit(".env 에 NAVER_BLOG_CLIENT_ID / NAVER_BLOG_CLIENT_SECRET 을 먼저 설정하세요.")

    state = secrets.token_urlsafe(16)
    auth_url = (
        f"{AUTHORIZE_URL}?"
        + urllib.parse.urlencode(
            {
                "response_type": "code",
                "client_id": client_id,
                "redirect_uri": REDIRECT_URI,
                "state": state,
            }
        )
    )

    print("아래 주소를 브라우저에서 열고 네이버 로그인 및 동의를 완료하세요:\n")
    print(auth_url)
    print(
        "\n로그인 후 리다이렉트된 주소 전체(예: http://localhost:8080/callback?code=...&state=...)를"
        " 붙여넣으세요:"
    )
    redirected = input("> ").strip()

    parsed = urllib.parse.urlparse(redirected)
    query = urllib.parse.parse_qs(parsed.query)
    code = (query.get("code") or [None])[0]
    returned_state = (query.get("state") or [None])[0]

    if not code:
        sys.exit("code 파라미터를 찾을 수 없습니다. 주소를 다시 확인하세요.")
    if returned_state != state:
        sys.exit("state 값이 일치하지 않습니다. 다시 시도하세요 (재사용 금지).")

    resp = requests.get(
        TOKEN_URL,
        params={
            "grant_type": "authorization_code",
            "client_id": client_id,
            "client_secret": client_secret,
            "code": code,
            "state": state,
        },
        timeout=10,
    )
    resp.raise_for_status()
    body = resp.json()
    if "refresh_token" not in body:
        sys.exit(f"토큰 발급 응답에 refresh_token 이 없습니다: {body}")

    print("\n발급 성공! 아래 값을 .env 의 NAVER_BLOG_REFRESH_TOKEN 에 저장하세요:\n")
    print(body["refresh_token"])

    env_path = Path(__file__).resolve().parent.parent / ".env"
    print(f"\n(.env 파일 위치 예상 경로: {env_path})")


if __name__ == "__main__":
    main()
