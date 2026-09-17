"""주문 데이터 -> 네이버 블로그 포스트(HTML) 변환."""
from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from .models import OrderItem
from .naver_blog_client import BlogPost

_TEMPLATE_DIR = Path(__file__).parent / "templates"
_env = Environment(
    loader=FileSystemLoader(str(_TEMPLATE_DIR)),
    autoescape=select_autoescape(["html", "j2"]),
)


@dataclass
class ProductAggregate:
    product_name: str
    quantity: int
    amount: int


def _aggregate_products(items: list[OrderItem], top_n: int = 5) -> list[ProductAggregate]:
    totals: dict[str, ProductAggregate] = {}
    for item in items:
        agg = totals.setdefault(
            item.product_name, ProductAggregate(item.product_name, 0, 0)
        )
        agg.quantity += item.quantity
        agg.amount += item.amount
    return sorted(totals.values(), key=lambda a: a.amount, reverse=True)[:top_n]


def _status_breakdown(items: list[OrderItem]) -> list[tuple[str, int]]:
    counter = Counter(item.status for item in items)
    return sorted(counter.items(), key=lambda kv: kv[1], reverse=True)


def build_daily_sales_report(
    items: list[OrderItem],
    period_start: datetime,
    period_end: datetime,
    now: datetime | None = None,
) -> BlogPost:
    now = now or datetime.now()
    total_orders = len(items)
    total_quantity = sum(item.quantity for item in items)
    total_amount = sum(item.amount for item in items)

    period_label = period_start.strftime("%Y-%m-%d")
    if period_start.date() != period_end.date():
        period_label = f"{period_start:%Y-%m-%d} ~ {period_end:%Y-%m-%d}"

    template = _env.get_template("daily_sales_report.html.j2")
    html = template.render(
        period_label=period_label,
        total_orders=total_orders,
        total_quantity=total_quantity,
        total_amount=total_amount,
        top_products=_aggregate_products(items),
        status_breakdown=_status_breakdown(items),
        generated_at=now.strftime("%Y-%m-%d %H:%M"),
    )

    title = f"[스마트스토어 주문 현황] {period_label} ({total_orders}건, {total_amount:,}원)"
    return BlogPost(title=title, contents_html=html)
