"""Build the Instagram caption text for a product entry."""

BASE_HASHTAGS = [
    "갤럭시퀀텀6", "갤럭시퀀텀6필름", "액정보호필름", "강화유리필름",
    "휴대폰액세서리", "핸드폰필름", "갤럭시액세서리",
]


def build_caption(product: dict) -> str:
    headline = product["headline"]
    feature_lines = "\n".join(f"✔ {f}" for f in product["features"])
    hashtags = " ".join(f"#{tag}" for tag in BASE_HASHTAGS + product["hashtags"])

    return (
        f"{headline}\n\n"
        f"{product['title']}\n\n"
        f"{feature_lines}\n\n"
        f"프로필 링크에서 자세히 확인하세요 🔗\n\n"
        f"{hashtags}"
    )
