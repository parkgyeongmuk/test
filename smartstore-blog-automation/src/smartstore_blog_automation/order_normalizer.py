"""커머스API 응답을 리포트용 OrderItem 으로 정규화.

주의: 네이버 커머스API의 상세 응답 필드명은 계정/버전에 따라 다소 차이가
있을 수 있습니다. 최초 연동 시 --dry-run 옵션으로 원본 응답을 한 번
확인하고, 아래 _dig() 경로가 실제 응답과 다르면 맞게 수정하세요.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from .models import OrderItem


def _dig(data: dict[str, Any], *paths: str) -> Any:
    """paths 에 나열된 후보 키 경로(dot 표기) 중 처음 발견되는 값을 반환."""
    for path in paths:
        node: Any = data
        found = True
        for key in path.split("."):
            if isinstance(node, dict) and key in node:
                node = node[key]
            else:
                found = False
                break
        if found and node is not None:
            return node
    return None


def _parse_datetime(value: Any) -> datetime | None:
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    text = str(value)
    for fmt in ("%Y-%m-%dT%H:%M:%S.%f%z", "%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    return None


def normalize_order_items(raw_orders: list[dict[str, Any]]) -> list[OrderItem]:
    items: list[OrderItem] = []
    for raw in raw_orders:
        product_order_id = _dig(raw, "productOrder.productOrderId", "productOrderId") or ""
        product_name = _dig(raw, "productOrder.productName", "productName") or "(상품명 없음)"
        quantity = int(_dig(raw, "productOrder.quantity", "quantity") or 0)
        amount = int(
            _dig(
                raw,
                "productOrder.totalPaymentAmount",
                "productOrder.totalPaymentAmt",
                "totalPaymentAmount",
            )
            or 0
        )
        status = _dig(raw, "productOrder.productOrderStatus", "productOrderStatus") or "UNKNOWN"
        ordered_at = _parse_datetime(
            _dig(raw, "order.orderDate", "orderDate", "productOrder.orderDate")
        )
        items.append(
            OrderItem(
                product_order_id=str(product_order_id),
                product_name=str(product_name),
                quantity=quantity,
                amount=amount,
                status=str(status),
                ordered_at=ordered_at,
            )
        )
    return items
