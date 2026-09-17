"""네이버 커머스API(스마트스토어) 클라이언트: 인증 + 주문 조회.

인증 방식 (커머스API 센터 문서 기준):
    signature = Base64( bcrypt(f"{client_id}_{timestamp}", client_secret) )
여기서 client_secret 자체가 bcrypt salt 형식 문자열이고, bcrypt 결과 전체(문자열)를
다시 base64 인코딩해서 client_secret_sign으로 전송한다.
"""
import base64
import time
from datetime import datetime, timedelta

import bcrypt
import requests

from config import CommerceConfig

TOKEN_URL = "https://api.commerce.naver.com/external/v1/oauth2/token"
# 상품주문(발주) 목록 조회. 정확한 파라미터는 계정/API 버전에 따라 달라질 수 있으니
# 실제 연동 전 커머스API 센터 문서에서 최신 스펙을 확인할 것.
PRODUCT_ORDERS_URL = "https://api.commerce.naver.com/external/v1/pay-order/seller/product-orders"


class NaverCommerceClient:
    def __init__(self, config: CommerceConfig):
        self._config = config
        self._access_token: str | None = None
        self._expires_at: float = 0.0

    def _build_signature(self, timestamp_ms: int) -> str:
        password = f"{self._config.client_id}_{timestamp_ms}".encode("utf-8")
        salt = self._config.client_secret.encode("utf-8")
        hashed = bcrypt.hashpw(password, salt)
        return base64.b64encode(hashed).decode("utf-8")

    def _fetch_access_token(self) -> None:
        timestamp_ms = int(time.time() * 1000)
        payload = {
            "client_id": self._config.client_id,
            "timestamp": timestamp_ms,
            "client_secret_sign": self._build_signature(timestamp_ms),
            "grant_type": "client_credentials",
            "type": "SELF",
        }
        if self._config.account_id:
            payload["account_id"] = self._config.account_id

        resp = requests.post(TOKEN_URL, data=payload, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        self._access_token = data["access_token"]
        self._expires_at = time.time() + int(data.get("expires_in", 3600)) - 60

    def _get_access_token(self) -> str:
        if not self._access_token or time.time() >= self._expires_at:
            self._fetch_access_token()
        return self._access_token

    def get_recent_product_orders(self, days: int = 7) -> list[dict]:
        """최근 N일간 발생한 상품주문 목록을 반환한다."""
        headers = {"Authorization": f"Bearer {self._get_access_token()}"}
        now = datetime.utcnow()
        params = {
            "from": (now - timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%S.000Z"),
            "to": now.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
        }
        resp = requests.get(PRODUCT_ORDERS_URL, headers=headers, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        return data.get("data", data.get("content", []))
