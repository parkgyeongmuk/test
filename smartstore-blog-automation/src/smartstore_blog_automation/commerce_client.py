"""네이버 커머스API센터(스마트스토어) 클라이언트.

인증: OAuth2 Client Credentials Grant + bcrypt 전자서명 방식.
문서: https://apicenter.commerce.naver.com (커머스API센터)
"""
from __future__ import annotations

import base64
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import bcrypt
import requests

from .config import CommerceConfig

BASE_URL = "https://api.commerce.naver.com/external"


class CommerceApiError(RuntimeError):
    """커머스 API 호출이 실패했을 때 발생."""


@dataclass
class AccessToken:
    value: str
    expires_at: float  # epoch seconds

    def is_expired(self, skew_seconds: int = 30) -> bool:
        return time.time() >= (self.expires_at - skew_seconds)


def _build_client_secret_sign(client_id: str, client_secret: str, timestamp_ms: int) -> str:
    """client_id_timestamp 를 client_secret 를 salt 로 bcrypt 해싱 후 base64 인코딩."""
    password = f"{client_id}_{timestamp_ms}".encode("utf-8")
    hashed = bcrypt.hashpw(password, client_secret.encode("utf-8"))
    return base64.b64encode(hashed).decode("utf-8")


class CommerceClient:
    def __init__(self, config: CommerceConfig, session: requests.Session | None = None):
        self._config = config
        self._session = session or requests.Session()
        self._token: AccessToken | None = None

    def _fetch_token(self) -> AccessToken:
        timestamp_ms = int(time.time() * 1000)
        signature = _build_client_secret_sign(
            self._config.client_id, self._config.client_secret, timestamp_ms
        )
        data = {
            "client_id": self._config.client_id,
            "timestamp": timestamp_ms,
            "client_secret_sign": signature,
            "grant_type": "client_credentials",
            "type": self._config.account_type,
        }
        if self._config.account_type == "SELLER" and self._config.account_id:
            data["account_id"] = self._config.account_id

        resp = self._session.post(f"{BASE_URL}/v1/oauth2/token", data=data, timeout=10)
        if not resp.ok:
            raise CommerceApiError(f"토큰 발급 실패 ({resp.status_code}): {resp.text}")
        body = resp.json()
        expires_in = float(body.get("expires_in", 3600))
        return AccessToken(value=body["access_token"], expires_at=time.time() + expires_in)

    def _access_token(self) -> str:
        if self._token is None or self._token.is_expired():
            self._token = self._fetch_token()
        return self._token.value

    def _get(self, path: str, params: dict[str, Any]) -> dict[str, Any]:
        resp = self._session.get(
            f"{BASE_URL}{path}",
            params=params,
            headers={"Authorization": f"Bearer {self._access_token()}"},
            timeout=10,
        )
        if not resp.ok:
            raise CommerceApiError(f"API 호출 실패 {path} ({resp.status_code}): {resp.text}")
        return resp.json()

    def get_changed_product_orders(
        self, changed_from: datetime, changed_to: datetime
    ) -> list[dict[str, Any]]:
        """지정 구간(최대 24시간) 동안 상태가 변경된 상품주문 목록을 조회.

        참고: 이 API는 변경 이력만 반환하므로, 상세 주문 정보가 필요하면
        product_order_ids 를 모아 별도의 상세 조회 API 를 호출해야 합니다.
        (여기서는 리포트 목적상 변경 이력에 포함된 필드만 사용합니다.)
        """
        params = {
            "lastChangedFrom": changed_from.strftime("%Y-%m-%dT%H:%M:%S.000+09:00"),
            "lastChangedTo": changed_to.strftime("%Y-%m-%dT%H:%M:%S.000+09:00"),
        }
        body = self._get("/v1/pay-order/seller/product-orders/last-changed-statuses", params)
        return body.get("data", {}).get("lastChangeStatuses", []) or []

    def get_product_orders_detail(self, product_order_ids: list[str]) -> list[dict[str, Any]]:
        """상품주문번호 목록으로 상세 주문 정보를 조회."""
        if not product_order_ids:
            return []
        resp = self._session.post(
            f"{BASE_URL}/v1/pay-order/seller/product-orders/query",
            json={"productOrderIds": product_order_ids},
            headers={"Authorization": f"Bearer {self._access_token()}"},
            timeout=10,
        )
        if not resp.ok:
            raise CommerceApiError(f"주문 상세 조회 실패 ({resp.status_code}): {resp.text}")
        return resp.json().get("data", []) or []
