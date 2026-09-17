"""Render a 1080x1080 card-news style image for one product."""

import shutil
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

SIZE = 1080

BG_TOP = (17, 24, 39)      # dark navy
BG_BOTTOM = (30, 41, 59)
ACCENT = (56, 189, 248)    # sky blue
WHITE = (248, 250, 252)
MUTED = (148, 163, 184)

FONT_CANDIDATES_BOLD = [
    "/usr/share/fonts/truetype/nanum/NanumGothicExtraBold.ttf",
    "/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
    "/usr/share/fonts/truetype/noto/NotoSansCJK-Bold.ttc",
]
FONT_CANDIDATES_REGULAR = [
    "/usr/share/fonts/truetype/nanum/NanumGothic.ttf",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
]


def _find_font(candidates: list[str]) -> str:
    for path in candidates:
        if Path(path).exists():
            return path
    if shutil.which("fc-match"):
        try:
            out = subprocess.run(
                ["fc-match", "-f", "%{file}", "NanumGothic:bold"],
                capture_output=True, text=True, check=True,
            ).stdout.strip()
            if out and Path(out).exists():
                return out
        except subprocess.CalledProcessError:
            pass
    raise FileNotFoundError(
        "No Korean-capable font found. Install one first, e.g. "
        "`sudo apt-get install -y fonts-nanum`."
    )


def _vertical_gradient(size: int, top: tuple, bottom: tuple) -> Image.Image:
    img = Image.new("RGB", (size, size), top)
    draw = ImageDraw.Draw(img)
    for y in range(size):
        t = y / (size - 1)
        color = tuple(int(top[c] + (bottom[c] - top[c]) * t) for c in range(3))
        draw.line([(0, y), (size, y)], fill=color)
    return img


def _truncate_to_width(draw, text, font, max_width):
    if draw.textlength(text, font=font) <= max_width:
        return text
    ellipsis = "…"
    kept = ""
    for ch in text:
        if draw.textlength(kept + ch + ellipsis, font=font) > max_width:
            break
        kept += ch
    return kept + ellipsis


def _draw_wrapped(draw, text, font, x, y, max_width, fill, line_spacing=1.25):
    lines = []
    for raw_line in text.split("\n"):
        if not raw_line:
            lines.append("")
            continue
        line = ""
        for ch in raw_line:
            test = line + ch
            if draw.textlength(test, font=font) > max_width and line:
                lines.append(line)
                line = ch
            else:
                line = test
        lines.append(line)

    ascent, descent = font.getmetrics()
    line_height = int((ascent + descent) * line_spacing)
    for i, line in enumerate(lines):
        draw.text((x, y + i * line_height), line, font=font, fill=fill)
    return y + len(lines) * line_height


def generate_card(product: dict, output_path: Path) -> Path:
    bold_font_path = _find_font(FONT_CANDIDATES_BOLD)
    regular_font_path = _find_font(FONT_CANDIDATES_REGULAR)

    headline_font = ImageFont.truetype(bold_font_path, 76)
    feature_font = ImageFont.truetype(regular_font_path, 40)
    badge_font = ImageFont.truetype(bold_font_path, 32)
    footer_font = ImageFont.truetype(regular_font_path, 30)

    img = _vertical_gradient(SIZE, BG_TOP, BG_BOTTOM)
    draw = ImageDraw.Draw(img)

    margin = 90

    # Top badge: "2매입" pill
    badge_text = "2매입 구성"
    badge_w = draw.textlength(badge_text, font=badge_font) + 48
    draw.rounded_rectangle(
        [margin, margin, margin + badge_w, margin + 64],
        radius=32, outline=ACCENT, width=2,
    )
    draw.text(
        (margin + 24, margin + 14), badge_text, font=badge_font, fill=ACCENT,
    )

    # Headline
    y = margin + 140
    y = _draw_wrapped(
        draw, product["headline"], headline_font,
        margin, y, SIZE - margin * 2, WHITE, line_spacing=1.2,
    )

    # Divider
    y += 30
    draw.line([(margin, y), (SIZE - margin, y)], fill=ACCENT, width=3)
    y += 50

    # Feature bullets
    for feat in product["features"]:
        bullet = f"•  {feat}"
        y = _draw_wrapped(
            draw, bullet, feature_font, margin, y, SIZE - margin * 2, WHITE,
        )
        y += 20

    # Footer: product line + brand
    footer_y = SIZE - margin - 90
    draw.line([(margin, footer_y), (SIZE - margin, footer_y)], fill=(51, 65, 85), width=2)
    wrapped_title = _truncate_to_width(draw, product["title"], footer_font, SIZE - margin * 2)
    draw.text((margin, footer_y + 20), wrapped_title, font=footer_font, fill=MUTED)
    draw.text((margin, footer_y + 55), "갤럭시퀀텀6 전용 액정보호필름", font=footer_font, fill=ACCENT)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(output_path, "PNG")
    return output_path
