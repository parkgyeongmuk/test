"""리포트 생성을 위한 정규화된 주문 데이터 모델."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass
class OrderItem:
    product_order_id: str
    product_name: str
    quantity: int
    amount: int  # 원 단위 결제 금액
    status: str
    ordered_at: datetime | None = None
