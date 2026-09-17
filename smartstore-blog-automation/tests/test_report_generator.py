from datetime import datetime

from smartstore_blog_automation.models import OrderItem
from smartstore_blog_automation.report_generator import build_daily_sales_report


def _items():
    return [
        OrderItem("1", "무선 이어폰", 2, 59800, "PAYED"),
        OrderItem("2", "무선 이어폰", 1, 29900, "DELIVERED"),
        OrderItem("3", "텀블러", 3, 45000, "PAYED"),
    ]


def test_build_daily_sales_report_totals():
    start = datetime(2024, 1, 1)
    end = datetime(2024, 1, 2)

    post = build_daily_sales_report(_items(), start, end, now=datetime(2024, 1, 2, 9, 0))

    assert "3건" in post.contents_html
    assert "6개" in post.contents_html
    assert "134,700원" in post.contents_html
    assert "무선 이어폰" in post.contents_html
    assert "2024-01-01" in post.title


def test_build_daily_sales_report_empty_orders():
    start = datetime(2024, 1, 1)
    end = datetime(2024, 1, 2)

    post = build_daily_sales_report([], start, end, now=datetime(2024, 1, 2, 9, 0))

    assert "0건" in post.contents_html
    assert "0원" in post.contents_html


def test_top_products_ranked_by_amount():
    post = build_daily_sales_report(
        _items(), datetime(2024, 1, 1), datetime(2024, 1, 2), now=datetime(2024, 1, 2)
    )

    idx_earphone = post.contents_html.index("무선 이어폰")
    idx_tumbler = post.contents_html.index("텀블러")
    assert idx_earphone < idx_tumbler
