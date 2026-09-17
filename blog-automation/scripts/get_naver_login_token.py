"""최초 1회만 실행: 네이버 로그인 인가코드를 access/refresh token으로 교환한다.

사용법:
    python scripts/get_naver_login_token.py

1) 출력되는 URL을 브라우저에 열고 로그인/동의
2) 리다이렉트된 주소창의 `code=`와 `state=` 값을 콘솔에 붙여넣기
3) 출력된 refresh_token을 .env의 NAVER_LOGIN_REFRESH_TOKEN에 저장
"""
import os
import sys
import urllib.parse

import requests
from dotenv import load_dotenv

load_dotenv()

AUTH_URL = "https://nid.naver.com/oauth2.0/authorize"
TOKEN_URL = "https://nid.naver.com/oauth2.0/token"


def main() -> None:
    client_id = os.environ["NAVER_LOGIN_CLIENT_ID"]
    client_secret = os.environ["NAVER_LOGIN_CLIENT_SECRET"]
    redirect_uri = os.environ["NAVER_LOGIN_REDIRECT_URI"]
    state = "blog-automation-setup"

    query = urllib.parse.urlencode(
        {
            "response_type": "code",
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "state": state,
        }
    )
    print("아래 URL을 브라우저에 열어 로그인/동의하세요:\n")
    print(f"{AUTH_URL}?{query}\n")

    code = input("리다이렉트된 URL의 code 값을 입력하세요: ").strip()

    resp = requests.get(
        TOKEN_URL,
        params={
            "grant_type": "authorization_code",
            "client_id": client_id,
            "client_secret": client_secret,
            "code": code,
            "state": state,
            "redirect_uri": redirect_uri,
        },
        timeout=10,
    )
    resp.raise_for_status()
    data = resp.json()
    if "error" in data:
        print(f"토큰 발급 실패: {data}", file=sys.stderr)
        sys.exit(1)

    print("\n발급 성공. 아래 값을 .env의 NAVER_LOGIN_REFRESH_TOKEN에 저장하세요:\n")
    print(data["refresh_token"])


if __name__ == "__main__":
    main()
