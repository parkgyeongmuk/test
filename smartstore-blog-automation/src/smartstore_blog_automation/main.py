"""스마트스토어 주문 현황을 집계해 네이버 블로그에 자동 포스팅하는 진입점.

사용법:
    python -m smartstore_blog_automation.main            # 정상 실행 (블로그에 발행)
    python -m smartstore_blog_automation.main --dry-run   # 발행 없이 콘솔에만 출력
"""
from __future__ import annotations

import argparse
import logging
from datetime import datetime, timedelta

from .commerce_client import CommerceClient
from .config import BlogConfig, CommerceConfig, ReportConfig
from .naver_blog_client import NaverBlogClient
from .order_normalizer import normalize_order_items
from .report_generator import build_daily_sales_report

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def collect_order_items(commerce: CommerceClient, days: int):
    now = datetime.now()
    period_start = now - timedelta(days=days)

    changed = commerce.get_changed_product_orders(period_start, now)
    product_order_ids = sorted(
        {
            entry.get("productOrderId")
            for entry in changed
            if entry.get("productOrderId")
        }
    )
    logger.info("변경된 상품주문 %d건 감지", len(product_order_ids))

    details = commerce.get_product_orders_detail(list(product_order_ids))
    items = normalize_order_items(details)
    return items, period_start, now


def run(dry_run: bool = False) -> None:
    report_cfg = ReportConfig.from_env()
    commerce = CommerceClient(CommerceConfig.from_env())

    items, period_start, period_end = collect_order_items(commerce, report_cfg.days)
    post = build_daily_sales_report(items, period_start, period_end)

    if dry_run:
        logger.info("[dry-run] 아래 내용을 블로그에 발행하는 대신 콘솔에 출력합니다.")
        print(f"제목: {post.title}\n")
        print(post.contents_html)
        return

    blog = NaverBlogClient(BlogConfig.from_env())
    result = blog.write_post(post)
    logger.info("블로그 포스팅 완료: %s", result)


def main() -> None:
    parser = argparse.ArgumentParser(description="스마트스토어 -> 네이버 블로그 자동화")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="블로그에 실제로 발행하지 않고 결과만 콘솔에 출력합니다.",
    )
    args = parser.parse_args()
    run(dry_run=args.dry_run)


if __name__ == "__main__":
    main()
