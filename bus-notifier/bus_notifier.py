#!/usr/bin/env python3
"""출근길 버스 도착정보를 조회해 텔레그램으로 알림을 보내는 스크립트.

데이터 소스: 국토교통부(TAGO) 국가대중교통정보센터 공공데이터 API
- 도시코드 조회:      BusSttnInfoInqireService/getCtyCodeList
- 정류소 이름 검색:    BusSttnInfoInqireService/getSttnNoList
- 노선 번호 검색:      BusRouteInfoInqireService/getRouteNoList
- 버스 도착정보 조회:  ArvlInfoInqireService/getSttnAcctoSpecifiedRouteBusArvlList

사용법은 README.md 참고.
"""
import argparse
import json
import os
import sys
from pathlib import Path
from typing import Optional
from urllib.parse import unquote

import requests

STTN_BASE = "http://apis.data.go.kr/1613000/BusSttnInfoInqireService"
ROUTE_BASE = "http://apis.data.go.kr/1613000/BusRouteInfoInqireService"
ARVL_BASE = "http://apis.data.go.kr/1613000/ArvlInfoInqireService"

DEFAULT_CONFIG_PATH = Path(__file__).parent / "config" / "routes.json"


def get_service_key() -> str:
    key = os.environ.get("TAGO_SERVICE_KEY")
    if not key:
        sys.exit("환경변수 TAGO_SERVICE_KEY 가 설정되어 있지 않습니다. (공공데이터포털에서 발급받은 인증키)")
    # 공공데이터포털 키는 이미 URL 인코딩된 형태로 발급되는 경우가 많아 requests가 이중 인코딩하지 않도록 디코딩해둔다.
    return unquote(key)


def call_api(url: str, params: dict) -> dict:
    params = {**params, "_type": "json", "numOfRows": params.get("numOfRows", 50), "pageNo": 1}
    resp = requests.get(url, params=params, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    header = data.get("response", {}).get("header", {})
    if header.get("resultCode") not in ("00", "0"):
        raise RuntimeError(f"API 오류: {header.get('resultMsg')} (요청: {url})")
    items = data.get("response", {}).get("body", {}).get("items", "")
    if items == "" or items is None:
        return []
    item = items.get("item", [])
    if isinstance(item, dict):
        return [item]
    return item


def find_city(name_filter: Optional[str] = None):
    items = call_api(f"{STTN_BASE}/getCtyCodeList", {"serviceKey": get_service_key()})
    for it in items:
        if name_filter and name_filter not in it.get("citynm", ""):
            continue
        print(f"{it['citycode']}\t{it['citynm']}")


def find_station(city_code: str, station_name: str):
    items = call_api(
        f"{STTN_BASE}/getSttnNoList",
        {"serviceKey": get_service_key(), "cityCode": city_code, "nodeNm": station_name},
    )
    for it in items:
        print(f"nodeId={it['nodeid']}\t{it['nodenm']}\t(정류소번호 {it.get('nodeno', '-')})")


def find_route(city_code: str, route_no: str):
    items = call_api(
        f"{ROUTE_BASE}/getRouteNoList",
        {"serviceKey": get_service_key(), "cityCode": city_code, "routeNo": route_no},
    )
    for it in items:
        print(
            f"routeId={it['routeid']}\t{it['routeno']}번\t"
            f"{it.get('startnodenm', '?')} -> {it.get('endnodenm', '?')}"
        )


def get_arrivals(city_code: str, node_id: str, route_id: str):
    return call_api(
        f"{ARVL_BASE}/getSttnAcctoSpecifiedRouteBusArvlList",
        {"serviceKey": get_service_key(), "cityCode": city_code, "nodeId": node_id, "routeId": route_id},
    )


def format_arrival_line(label: str, arrivals: list) -> str:
    if not arrivals:
        return f"🚌 {label}: 도착 예정 정보 없음 (운행 종료이거나 배차 간격이 넓을 수 있음)"
    lines = []
    for a in arrivals:
        minutes = int(a.get("arrtime", 0)) // 60
        stops_left = a.get("arrprevstationcnt", "?")
        lines.append(f"약 {minutes}분 후 도착 ({stops_left}정거장 전)")
    return f"🚌 {label}: " + " / ".join(lines)


def load_config(config_path: Path) -> list:
    if not config_path.exists():
        sys.exit(
            f"설정 파일을 찾을 수 없습니다: {config_path}\n"
            "config/routes.json.example 을 참고해 config/routes.json 을 만들어주세요."
        )
    with open(config_path, encoding="utf-8") as f:
        return json.load(f)


def send_telegram(text: str):
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        sys.exit("환경변수 TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID 가 설정되어 있지 않습니다.")
    resp = requests.post(
        f"https://api.telegram.org/bot{token}/sendMessage",
        json={"chat_id": chat_id, "text": text},
        timeout=10,
    )
    resp.raise_for_status()


def notify(config_path: Path, dry_run: bool):
    routes = load_config(config_path)
    lines = ["🚏 출근길 버스 도착정보"]
    for route in routes:
        arrivals = get_arrivals(route["cityCode"], route["nodeId"], route["routeId"])
        lines.append(format_arrival_line(route.get("label", route["routeId"]), arrivals))
    message = "\n".join(lines)
    print(message)
    if not dry_run:
        send_telegram(message)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    p_city = sub.add_parser("find-city", help="도시코드 검색 (예: 서울)")
    p_city.add_argument("name", nargs="?", help="도시명 일부 (생략 시 전체 출력)")

    p_station = sub.add_parser("find-station", help="정류소 nodeId 검색")
    p_station.add_argument("city_code")
    p_station.add_argument("station_name")

    p_route = sub.add_parser("find-route", help="노선 routeId 검색")
    p_route.add_argument("city_code")
    p_route.add_argument("route_no")

    p_notify = sub.add_parser("notify", help="설정된 노선들의 도착정보를 조회해 텔레그램으로 전송")
    p_notify.add_argument("--config", default=str(DEFAULT_CONFIG_PATH), help="routes.json 경로")
    p_notify.add_argument("--dry-run", action="store_true", help="텔레그램 전송 없이 콘솔 출력만")

    args = parser.parse_args()

    if args.command == "find-city":
        find_city(args.name)
    elif args.command == "find-station":
        find_station(args.city_code, args.station_name)
    elif args.command == "find-route":
        find_route(args.city_code, args.route_no)
    elif args.command == "notify":
        notify(Path(args.config), args.dry_run)


if __name__ == "__main__":
    main()
