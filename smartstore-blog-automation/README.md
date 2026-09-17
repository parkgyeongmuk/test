# 스마트스토어 → 네이버 블로그 자동화

네이버 스마트스토어의 **주문/판매 현황**을 집계해서 **네이버 블로그**에 자동으로
포스팅하는 파이썬 스크립트입니다. 매일 GitHub Actions 스케줄로 실행되도록
구성되어 있습니다.

```
스마트스토어(커머스API) --조회--> 주문 데이터 --집계--> 리포트(HTML) --발행--> 네이버 블로그
```

## 동작 방식

1. [네이버 커머스API센터](https://apicenter.commerce.naver.com) 로 주문 상태가
   변경된 상품주문 목록을 조회하고, 상세 정보를 가져옵니다.
2. 주문 건수 / 판매 수량 / 결제 금액 / 인기 상품 / 상태별 현황을 집계합니다.
3. 집계 결과를 HTML 리포트로 만들어 [네이버 오픈API 블로그
   글쓰기](https://developers.naver.com) 로 자동 발행합니다.

## 사전 준비 (최초 1회)

### 1) 네이버 커머스API센터 (스마트스토어)

1. https://apicenter.commerce.naver.com 에서 애플리케이션을 등록합니다.
2. 발급받은 `client_id`, `client_secret` 을 확인합니다.
3. 인증 방식은 OAuth2 Client Credentials + bcrypt 전자서명 방식을 사용합니다
   (이 저장소의 `commerce_client.py` 가 처리합니다).

> 커머스API는 계정/약관 동의 등 추가 설정이 필요할 수 있습니다. 네이버 정책
> 변경으로 필드명이나 엔드포인트가 바뀔 수 있으니, 최초 실행 시
> `--dry-run` 으로 결과를 확인하고 `order_normalizer.py` 의 필드 경로를
> 실제 응답에 맞게 조정하세요.

### 2) 네이버 오픈API (블로그 글쓰기)

1. https://developers.naver.com 에서 애플리케이션을 등록하고 **네이버
   로그인**과 **블로그** API 사용을 설정합니다. (블로그 글쓰기 API는 네이버
   심사가 필요할 수 있습니다)
2. 애플리케이션의 Callback URL 에 `http://localhost:8080/callback` (또는
   원하는 값)을 등록합니다.
3. `.env` 에 `NAVER_BLOG_CLIENT_ID`, `NAVER_BLOG_CLIENT_SECRET` 을 채운 뒤
   아래 스크립트로 `refresh_token` 을 최초 1회 발급받습니다.

```bash
cp .env.example .env   # 값 채우기
pip install -r requirements.txt
python scripts/get_blog_refresh_token.py
```

출력된 `refresh_token` 을 `.env` 의 `NAVER_BLOG_REFRESH_TOKEN` 에 저장하세요.
이 토큰이 있으면 이후로는 로그인 없이 access token을 자동 갱신합니다.

## 로컬 실행

```bash
pip install -r requirements.txt
python -m smartstore_blog_automation.main --dry-run   # 발행 없이 콘솔 출력으로 확인
python -m smartstore_blog_automation.main              # 실제 블로그에 발행
```

## 자동 실행 (GitHub Actions)

`.github/workflows/smartstore-blog-automation.yml` 워크플로우가 매일 KST
09:00 에 자동 실행됩니다. 저장소 **Settings → Secrets and variables →
Actions** 에서 아래 값을 등록하세요.

**Secrets**

| 이름 | 설명 |
|---|---|
| `NAVER_COMMERCE_CLIENT_ID` | 커머스API 클라이언트 ID |
| `NAVER_COMMERCE_CLIENT_SECRET` | 커머스API 클라이언트 시크릿 |
| `NAVER_COMMERCE_ACCOUNT_ID` | (SELLER 계정 유형인 경우만) |
| `NAVER_BLOG_CLIENT_ID` | 오픈API 클라이언트 ID |
| `NAVER_BLOG_CLIENT_SECRET` | 오픈API 클라이언트 시크릿 |
| `NAVER_BLOG_REFRESH_TOKEN` | `get_blog_refresh_token.py` 로 발급받은 값 |

**Variables (선택)**

| 이름 | 설명 | 기본값 |
|---|---|---|
| `NAVER_COMMERCE_ACCOUNT_TYPE` | `SELF` 또는 `SELLER` | `SELF` |
| `NAVER_BLOG_ID` | 발행할 블로그 아이디 | 로그인 계정 블로그 |
| `REPORT_DAYS` | 며칠치 주문을 집계할지 | `1` |

수동으로 한 번 실행해보고 싶다면 Actions 탭에서 워크플로우를
`Run workflow` 로 실행하면서 `dry_run` 을 `true` 로 지정하면 발행 없이
로그로만 결과를 확인할 수 있습니다.

## 프로젝트 구조

```
smartstore-blog-automation/
├── src/smartstore_blog_automation/
│   ├── config.py              # 환경변수 설정 로딩
│   ├── commerce_client.py     # 커머스API(스마트스토어) 클라이언트
│   ├── naver_blog_client.py   # 네이버 블로그 글쓰기 클라이언트
│   ├── order_normalizer.py    # API 응답 -> 정규화된 주문 데이터
│   ├── report_generator.py    # 주문 데이터 -> 블로그 포스트(HTML)
│   ├── main.py                # 전체 흐름 오케스트레이션 (CLI)
│   └── templates/              # Jinja2 리포트 템플릿
├── scripts/get_blog_refresh_token.py  # 블로그 refresh_token 최초 발급
└── tests/                     # pytest 단위 테스트 (외부 API 호출 없음)
```

## 커스터마이징

- 리포트 문구/구성을 바꾸려면
  `src/smartstore_blog_automation/templates/daily_sales_report.html.j2` 를
  수정하세요.
- 상품 리뷰 요약, 신규 등록 상품 소개 등 다른 유형의 글로 확장하려면
  `report_generator.py` 에 새 빌더 함수를 추가하고 `main.py` 에서
  호출하도록 바꾸면 됩니다.
- 발행 대상 블로그 플랫폼을 바꾸려면 `naver_blog_client.py` 자리에 새
  클라이언트(예: 티스토리, 워드프레스)를 추가하고 `main.py` 에서
  교체하면 됩니다.

## 참고 문서

- 네이버 커머스API센터: https://apicenter.commerce.naver.com
- 네이버 커머스API 저장소/문의: https://github.com/commerce-api-naver/commerce-api
- 네이버 오픈API 가이드: https://github.com/naver/naver-openapi-guide

> ⚠️ 이 코드의 API 필드명/엔드포인트는 공개 문서와 커뮤니티 자료를 기반으로
> 작성했습니다. 네이버 API는 정책/스키마가 변경될 수 있으므로, 실제 계정으로
> 연동하기 전에 `--dry-run` 으로 응답을 확인하고 필요 시 위 문서를 참고해
> 조정하세요.
