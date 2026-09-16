# 출근길 버스 자동 알림

매일 아침 출근 전에 버스 도착정보를 직접 앱으로 확인하지 않아도, 정해진 시간에
텔레그램 메시지로 자동 전송해주는 스크립트입니다. GitHub Actions로 스케줄 실행되므로
컴퓨터나 휴대폰을 켜둘 필요가 없습니다.

데이터 출처: 국토교통부(TAGO) 국가대중교통정보센터 공공데이터 (전국 버스 도착정보)

## 1. 사전 준비

### 1-1. 공공데이터포털 API 키 발급
1. https://www.data.go.kr 회원가입 후 "국토교통부 (TAGO) 버스도착정보" 등 관련 API 활용신청
   (검색창에 "버스도착정보", "버스노선정보", "버스정류소정보" 3개 서비스 모두 신청)
2. 승인 후 마이페이지 > 개발계정에서 발급받은 **일반 인증키(Decoding)** 를 복사
   → 환경변수 `TAGO_SERVICE_KEY` 에 사용

### 1-2. 텔레그램 봇 만들기
1. 텔레그램에서 `@BotFather` 검색 → `/newbot` 으로 봇 생성 → 토큰 발급
   → 환경변수 `TELEGRAM_BOT_TOKEN`
2. 생성한 봇과 대화를 한 번 시작(아무 메시지나 전송)
3. `https://api.telegram.org/bot<토큰>/getUpdates` 를 브라우저로 열어
   `"chat":{"id": ...}` 값을 확인 → 환경변수 `TELEGRAM_CHAT_ID`

### 1-3. 내 정류장/노선 코드 찾기

```bash
pip install -r requirements.txt
export TAGO_SERVICE_KEY="발급받은 키"

# 1) 우리 동네 도시코드 찾기 (예: 서울, 성남 등 일부 이름으로 검색)
python bus_notifier.py find-city 성남

# 2) 도시코드로 정류장 이름 검색 → nodeId 확인
python bus_notifier.py find-station 23120 "OO아파트"

# 3) 도시코드로 버스 번호 검색 → routeId 확인
python bus_notifier.py find-route 23120 152
```

## 2. 설정 파일 작성

`config/routes.json.example` 을 복사해 `config/routes.json` 을 만들고,
위에서 찾은 값을 채워 넣습니다. 출근길에 갈아타거나 대체로 타는 버스가 여러 개면
배열에 항목을 추가하면 됩니다.

```bash
cp config/routes.json.example config/routes.json
```

로컬에서 바로 테스트하려면:

```bash
export TAGO_SERVICE_KEY="..."
export TELEGRAM_BOT_TOKEN="..."
export TELEGRAM_CHAT_ID="..."
python bus_notifier.py notify            # 실제 전송
python bus_notifier.py notify --dry-run  # 콘솔 출력만, 텔레그램 전송 안 함
```

## 3. 자동 실행 설정 (GitHub Actions)

저장소에 이미 포함된 `.github/workflows/bus-notify.yml` 이 매주 평일 07:30(KST)에
자동으로 알림을 보냅니다. 시간을 바꾸고 싶으면 워크플로 파일의 `cron` 값을 수정하세요
(cron은 UTC 기준이며 KST는 UTC+9입니다).

저장소 Settings → Secrets and variables → Actions 에서 아래 Repository secret을 등록하세요.

| Secret 이름 | 값 |
|---|---|
| `TAGO_SERVICE_KEY` | 1-1에서 발급받은 공공데이터포털 인증키 |
| `TELEGRAM_BOT_TOKEN` | 1-2에서 발급받은 텔레그램 봇 토큰 |
| `TELEGRAM_CHAT_ID` | 1-2에서 확인한 chat id |
| `BUS_ROUTES_JSON` | `config/routes.json` 파일 내용을 그대로 붙여넣기 (동네/노선 정보 노출 방지를 위해 저장소에는 커밋하지 않고 secret으로 관리) |

등록 후 Actions 탭에서 "출근길 버스 알림" 워크플로를 `workflow_dispatch` 로 한 번
수동 실행해 정상 동작하는지 확인해보세요.

## 참고
- `arrtime`(도착까지 남은 초)이 API에서 제공되지 않으면(막차 지남, 배차 간격 초과 등)
  "도착 예정 정보 없음"으로 표시됩니다.
- API 응답 필드명이나 엔드포인트는 공공데이터포털 정책에 따라 바뀔 수 있으니, 동작하지
  않으면 data.go.kr의 "국토교통부_(TAGO)_버스도착정보" 활용가이드 최신 스펙을 확인하세요.
