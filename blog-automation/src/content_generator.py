"""주문 데이터를 상품 단위로 집계해 블로그 글(제목/본문)을 생성한다.

개인정보 보호: 구매자명/연락처/배송지 등은 절대 사용하지 않는다.
상품명과 판매 수량만 집계 대상으로 삼는다.
"""
from collections import Counter
from datetime import date


def _extract_product_name(order: dict) -> str | None:
    # 커머스API 응답 스키마는 계정/버전에 따라 다를 수 있어 후보 키를 순서대로 탐색한다.
    product_order = order.get("productOrder", order)
    for key in ("productName", "productOrderName", "itemName"):
        name = product_order.get(key)
        if name:
            return name
    return None


def _extract_quantity(order: dict) -> int:
    product_order = order.get("productOrder", order)
    for key in ("quantity", "orderQuantity"):
        qty = product_order.get(key)
        if qty:
            return int(qty)
    return 1


def summarize_best_sellers(orders: list[dict], top_n: int = 5) -> list[tuple[str, int]]:
    counter: Counter[str] = Counter()
    for order in orders:
        name = _extract_product_name(order)
        if not name:
            continue
        counter[name] += _extract_quantity(order)
    return counter.most_common(top_n)


def build_blog_post(best_sellers: list[tuple[str, int]], days: int) -> tuple[str, str]:
    today = date.today().strftime("%Y.%m.%d")
    title = f"[{today}] 최근 {days}일 스마트스토어 베스트셀러 TOP {len(best_sellers)}"

    if not best_sellers:
        body = f"최근 {days}일간 집계된 판매 데이터가 없습니다."
        return title, body

    lines = [f"최근 {days}일간 가장 많이 판매된 상품을 소개합니다.", ""]
    for rank, (name, quantity) in enumerate(best_sellers, start=1):
        lines.append(f"{rank}위. {name} — {quantity}건 판매")
    lines.append("")
    lines.append("(자동 생성된 판매 요약이며, 구매자 개인정보는 포함하지 않습니다.)")
    return title, "\n".join(lines)
