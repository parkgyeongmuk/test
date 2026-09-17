# Instagram 카드뉴스 자동 업로드

매일 GitHub Actions가 자동으로 실행되어, `data/products.json`에 등록된 제품을
순서대로 하나씩 골라 카드뉴스 이미지를 만들고 Instagram 피드에 올립니다.

흐름: 제품 선택(순환) → 카드뉴스 이미지 생성(Pillow) → Imgur에 업로드해 공개 URL 확보
→ Instagram Graph API로 이미지+캡션 게시 → 다음 실행을 위해 순번 저장.

## 1. 사전 준비 (직접 해야 하는 부분)

자동화 코드는 이미 완성돼 있지만, Meta(페이스북) 쪽 계정 연결은 보안상
직접 하셔야 합니다. 한 번만 설정하면 이후엔 완전 자동입니다.

### 1-1. Instagram을 비즈니스/크리에이터 계정으로 전환

Instagram 앱 → 설정 → 계정 → "프로페셔널 계정으로 전환" → 비즈니스(또는
크리에이터) 선택.

### 1-2. Facebook 페이지 만들고 연결

Facebook에서 페이지가 없다면 하나 만드세요. Instagram 프로페셔널 계정
설정에서 "연결된 계정" → 방금 만든 Facebook 페이지와 연결합니다.

### 1-3. Meta 개발자 앱 생성

1. https://developers.facebook.com/apps 접속 → "앱 만들기"
2. 유형: **비즈니스** 선택
3. 앱 생성 후, 대시보드에서 "제품 추가" → **Instagram Graph API** 추가

### 1-4. 내 계정을 Instagram 테스터로 등록 (앱 심사 없이 바로 쓰는 핵심 단계)

개인/소규모 자동화에서는 Meta의 정식 앱 심사(App Review)를 받지 않아도
됩니다. 대신 내 계정을 테스터로 등록하면 됩니다.

1. 앱 대시보드 → "앱 역할" → "역할" → "Instagram 테스터 추가" → 내
   Instagram 계정 아이디 입력
2. Instagram 앱에서: 설정 → 앱 및 웹사이트 → 테스터 초대 → **수락**

### 1-5. 액세스 토큰 발급

1. https://developers.facebook.com/tools/explorer 접속, 방금 만든 앱 선택
2. 권한(permissions) 추가: `instagram_basic`, `instagram_content_publish`,
   `pages_show_list`, `pages_read_engagement`
3. "Generate Access Token" 클릭 → 로그인/권한 승인
4. 발급된 토큰은 유효기간이 짧으므로(1~2시간), **장기 토큰(60일)** 으로 교환:

```
GET https://graph.facebook.com/v21.0/oauth/access_token
    ?grant_type=fb_exchange_token
    &client_id={앱 ID}
    &client_secret={앱 시크릿}
    &fb_exchange_token={방금 발급받은 토큰}
```

응답의 `access_token`이 60일짜리 장기 토큰입니다. 이 값을 `IG_ACCESS_TOKEN`
으로 사용합니다.

> ⚠️ 60일마다 만료됩니다. 만료 전에 같은 방법으로 갱신해서 GitHub Secret을
> 다시 업데이트해주세요.

### 1-6. Instagram 비즈니스 계정 ID 확인

```
GET https://graph.facebook.com/v21.0/me/accounts?access_token={토큰}
```
→ 응답에서 내 페이지의 `id`(페이지 ID) 확인 후:

```
GET https://graph.facebook.com/v21.0/{페이지 ID}?fields=instagram_business_account&access_token={토큰}
```
→ `instagram_business_account.id` 값이 `IG_USER_ID` 입니다.

### 1-7. Imgur Client ID 발급 (이미지 공개 호스팅용)

Instagram Graph API는 이미지를 "공개 URL"로만 받을 수 있어서, 생성한
카드뉴스를 Imgur에 올려 URL을 얻습니다. 로그인 없이 바로 발급 가능합니다.

1. https://api.imgur.com/oauth2/addclient 접속
2. Application name: 아무거나 입력
3. Authorization type: **"Anonymous usage without user authorization"** 선택
4. 이메일 입력 후 제출 → 발급된 **Client ID** 값을 `IMGUR_CLIENT_ID` 로 사용

### 1-8. GitHub Secrets 등록

저장소 → Settings → Secrets and variables → Actions → New repository secret

| Secret 이름 | 값 |
|---|---|
| `IG_USER_ID` | 1-6에서 확인한 Instagram 비즈니스 계정 ID |
| `IG_ACCESS_TOKEN` | 1-5에서 발급한 장기 액세스 토큰 |
| `IMGUR_CLIENT_ID` | 1-7에서 발급한 Imgur Client ID |

여기까지 하면 끝입니다. 이후는 매일 자동으로 실행됩니다.

## 2. 자동 실행 스케줄

`.github/workflows/daily-instagram-post.yml` 에서 매일 09:00(KST)에 자동
실행되도록 설정되어 있습니다. 시간을 바꾸려면 `cron: "0 0 * * *"` 부분을
수정하세요 (cron은 UTC 기준입니다).

GitHub 저장소 → Actions 탭 → "Daily Instagram Post" → "Run workflow" 로
수동 실행도 가능합니다 (dry_run 체크박스로 실제 게시 없이 테스트 가능).

## 3. 제품 목록 수정하기

`data/products.json` 을 편집하면 됩니다. 각 항목:

```json
{
  "id": "고유id",
  "title": "전체 상품명",
  "headline": "카드 상단에 크게 들어갈 문구\n줄바꿈은 \\n으로",
  "features": ["특징 1", "특징 2", "특징 3"],
  "hashtags": ["추가", "해시태그"]
}
```

목록에 추가하면 자동으로 순환 로테이션에 포함됩니다 (`data/state.json`이
마지막으로 올린 순번을 기억해서 순서대로 하나씩 돌아갑니다).

## 4. 로컬에서 테스트하기

```bash
cd instagram-auto-post
pip install -r requirements.txt
sudo apt-get install -y fonts-nanum   # 한글 폰트 (최초 1회)

python3 scripts/main.py --dry-run     # 이미지+캡션만 생성, 업로드/게시 안 함
```

생성된 이미지는 `output/` 폴더에서 확인할 수 있습니다.

실제 게시까지 테스트하려면 환경변수를 설정하고 `--dry-run` 없이 실행하세요:

```bash
export IMGUR_CLIENT_ID=...
export IG_USER_ID=...
export IG_ACCESS_TOKEN=...
python3 scripts/main.py
```

## 5. 폴더 구조

```
instagram-auto-post/
  data/
    products.json   # 제품 목록 (직접 수정)
    state.json       # 마지막으로 올린 순번 (자동 생성/갱신)
  scripts/
    generate_card.py     # 카드뉴스 이미지 렌더링
    caption.py            # 캡션 텍스트 생성
    post_to_instagram.py  # Imgur 업로드 + Instagram Graph API 게시
    main.py                # 전체 흐름 실행
  output/            # 생성된 이미지 (git에는 포함 안 됨)
```
