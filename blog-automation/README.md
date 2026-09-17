# 스마트스토어 → 네이버 블로그 자동화

네이버 커머스API로 스마트스토어의 주문/판매 데이터를 가져와, 상품별 판매 요약(베스트셀러) 글을 만들어 네이버 블로그에 자동으로 올리는 스크립트입니다.

## 왜 "판매 요약"만 다루는가 (개인정보 주의)

주문 데이터에는 구매자 이름, 연락처, 배송지 등 **개인정보(PII)**가 포함됩니다. 이 스크립트는 주문 원본을 절대 블로그에 노출하지 않고, **상품별 판매 건수/수량만 집계**해서 "이번 주 베스트셀러 TOP N" 같은 형태로만 글을 생성합니다. `content_generator.py`를 수정하더라도 구매자 개인정보를 본문에 넣지 않도록 주의하세요.

## 사전 준비물 (반드시 사람이 직접 처리해야 하는 단계)

### 1. 네이버 커머스API 센터 (스마트스토어 주문 조회용)
1. https://apicenter.commerce.naver.com 가입 → 내 스토어 연동 → 애플리케이션 등록
2. 발급되는 `CLIENT_ID`, `CLIENT_SECRET`(bcrypt salt 형식 문자열)을 확인
3. 계정 유형이 여러 스토어를 묶은 "매니저 계정"이면 `ACCOUNT_ID`(스토어 식별자)도 필요

### 2. 네이버 개발자센터 (블로그 자동 포스팅용)
1. https://developers.naver.com/apps 에서 애플리케이션 등록, "네이버 로그인" + "블로그" API 사용 신청
2. **블로그 글쓰기 API는 네이버 로그인 심사를 통과해야 사용 가능**합니다 (심사에 시간이 걸릴 수 있음)
3. `NAVER_LOGIN_CLIENT_ID`, `NAVER_LOGIN_CLIENT_SECRET`, Redirect URI를 발급/등록
4. 최초 1회 `scripts/get_naver_login_token.py`를 실행해 사용자 인가 후 `refresh_token`을 받아 `.env`에 저장 (이후 자동 갱신)

## 설치

```bash
cd blog-automation
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # 위에서 발급받은 값들을 채워넣기
```

## 최초 1회: 블로그 로그인 토큰 발급

```bash
python scripts/get_naver_login_token.py
```
브라우저에서 로그인/동의 후 리다이렉트된 URL의 `code` 값을 콘솔에 붙여넣으면 `refresh_token`이 `.env`에 저장할 값으로 출력됩니다.

## 실행

```bash
python src/main.py --days 7 --top 5
```
최근 7일 주문을 집계해 베스트셀러 TOP 5 글을 생성하고 블로그에 발행합니다. `--dry-run`을 붙이면 실제 발행 없이 생성된 글만 출력합니다.

## 스케줄링

`cron` 또는 `.github/workflows/blog-automation.yml`(GitHub Actions 스케줄) 예시는 `scripts/` 폴더를 참고하세요. 비밀값(CLIENT_SECRET 등)은 절대 커밋하지 말고 GitHub Actions Secrets나 서버 환경변수로 주입하세요.

## 주의사항

- 네이버 커머스API의 정확한 엔드포인트/파라미터는 종종 개정됩니다. `src/naver_commerce_client.py`의 `get_recent_product_orders()`는 대표적인 조회 엔드포인트를 사용하지만, 실제 연동 전 [커머스API 센터 문서](https://apicenter.commerce.naver.com)에서 최신 스펙을 반드시 확인하세요.
- 블로그 자동 포스팅은 네이버 이용약관상 스팸/어뷰징으로 간주될 수 있는 과도한 자동 발행(예: 하루 수십 건)을 피해야 합니다.
