"""Daily entry point: pick the next product, render a card, post to Instagram.

Usage:
    python scripts/main.py            # real run (needs env vars set)
    python scripts/main.py --dry-run  # generate image + caption only, no upload/post
"""

import argparse
import json
import os
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from caption import build_caption
from generate_card import generate_card
from post_to_instagram import post_image, upload_to_imgur

PRODUCTS_PATH = ROOT / "data" / "products.json"
STATE_PATH = ROOT / "data" / "state.json"
OUTPUT_DIR = ROOT / "output"


def load_products() -> list[dict]:
    return json.loads(PRODUCTS_PATH.read_text(encoding="utf-8"))


def next_product_index(count: int) -> int:
    if STATE_PATH.exists():
        state = json.loads(STATE_PATH.read_text(encoding="utf-8"))
        last_index = state.get("last_index", -1)
    else:
        last_index = -1
    return (last_index + 1) % count


def save_state(index: int) -> None:
    STATE_PATH.write_text(json.dumps({"last_index": index}, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Skip Imgur upload and Instagram publish")
    args = parser.parse_args()

    products = load_products()
    index = next_product_index(len(products))
    product = products[index]

    today = date.today().isoformat()
    image_path = OUTPUT_DIR / f"{today}-{product['id']}.png"
    generate_card(product, image_path)
    caption = build_caption(product)

    print(f"[{today}] product #{index}: {product['id']}")
    print(f"image: {image_path}")
    print("caption:\n" + caption)

    if args.dry_run:
        print("\n--dry-run set: skipping Imgur upload and Instagram publish.")
        return

    imgur_client_id = os.environ["IMGUR_CLIENT_ID"]
    ig_user_id = os.environ["IG_USER_ID"]
    ig_access_token = os.environ["IG_ACCESS_TOKEN"]

    image_url = upload_to_imgur(str(image_path), imgur_client_id)
    print(f"uploaded to: {image_url}")

    media_id = post_image(ig_user_id, ig_access_token, image_url, caption)
    print(f"published Instagram media id: {media_id}")

    save_state(index)


if __name__ == "__main__":
    main()
