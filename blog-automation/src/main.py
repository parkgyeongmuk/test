import argparse

from config import load_blog_config, load_commerce_config
from content_generator import build_blog_post, summarize_best_sellers
from naver_blog_client import NaverBlogClient
from naver_commerce_client import NaverCommerceClient


def main() -> None:
    parser = argparse.ArgumentParser(description="스마트스토어 판매 요약을 네이버 블로그에 자동 발행")
    parser.add_argument("--days", type=int, default=7, help="집계할 최근 일수")
    parser.add_argument("--top", type=int, default=5, help="베스트셀러 상위 몇 개를 다룰지")
    parser.add_argument("--dry-run", action="store_true", help="발행하지 않고 생성된 글만 출력")
    args = parser.parse_args()

    commerce_client = NaverCommerceClient(load_commerce_config())
    orders = commerce_client.get_recent_product_orders(days=args.days)
    best_sellers = summarize_best_sellers(orders, top_n=args.top)
    title, contents = build_blog_post(best_sellers, days=args.days)

    if args.dry_run:
        print(f"[제목]\n{title}\n\n[본문]\n{contents}")
        return

    blog_client = NaverBlogClient(load_blog_config())
    result = blog_client.publish_post(title, contents)
    print(f"발행 완료: {result}")


if __name__ == "__main__":
    main()
