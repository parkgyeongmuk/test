# -*- coding: utf-8 -*-
"""
PNG -> JPG 일괄 변환기

사용법
  1) 그냥 실행 (더블클릭)      : 폴더 선택 창이 뜸 -> 폴더 고르면 그 안의 PNG 전부 변환
  2) 폴더를 변환하기.bat 위에 드래그 : 해당 폴더 변환
  3) 명령줄: python png2jpg.py <폴더 또는 png파일...> [-r] [-q 95] [--delete]

옵션
  -r, --recursive : 하위 폴더까지 전부 변환
  -q, --quality   : JPG 화질 (1~100, 기본 95)
  --delete        : 변환 성공한 원본 PNG 삭제 (기본은 원본 유지)
  -o, --out       : 결과 저장 폴더 (기본: 원본과 같은 폴더)

투명 배경 PNG는 흰색 배경으로 채워서 저장합니다.
"""
import argparse
import sys
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    print("Pillow 가 필요합니다. 명령 프롬프트에서 다음을 실행하세요:\n  pip install pillow")
    input("엔터를 누르면 종료합니다...")
    sys.exit(1)


def to_jpg(src: Path, dst: Path, quality: int) -> None:
    with Image.open(src) as im:
        if im.mode in ("RGBA", "LA") or (im.mode == "P" and "transparency" in im.info):
            im = im.convert("RGBA")
            bg = Image.new("RGB", im.size, (255, 255, 255))
            bg.paste(im, mask=im.getchannel("A"))
            im = bg
        else:
            im = im.convert("RGB")
        dst.parent.mkdir(parents=True, exist_ok=True)
        im.save(dst, "JPEG", quality=quality, optimize=True, subsampling=0 if quality >= 90 else 2)


def collect(targets, recursive):
    files = []
    for t in targets:
        p = Path(t)
        if p.is_dir():
            it = p.rglob("*") if recursive else p.glob("*")
            files += [(f, p) for f in it if f.is_file() and f.suffix.lower() == ".png"]
        elif p.is_file() and p.suffix.lower() == ".png":
            files.append((p, p.parent))
    return sorted(set(files))


def pick_folder():
    try:
        import tkinter as tk
        from tkinter import filedialog
        root = tk.Tk()
        root.withdraw()
        d = filedialog.askdirectory(title="PNG 파일이 있는 폴더를 선택하세요")
        root.destroy()
        return [d] if d else []
    except Exception:
        d = input("PNG 폴더 경로를 입력하세요: ").strip().strip('"')
        return [d] if d else []


def main():
    ap = argparse.ArgumentParser(description="PNG -> JPG 일괄 변환")
    ap.add_argument("targets", nargs="*", help="폴더 또는 PNG 파일")
    ap.add_argument("-r", "--recursive", action="store_true")
    ap.add_argument("-q", "--quality", type=int, default=95)
    ap.add_argument("-o", "--out")
    ap.add_argument("--delete", action="store_true")
    args = ap.parse_args()

    interactive = not args.targets
    targets = args.targets or pick_folder()
    if not targets:
        print("선택된 폴더가 없습니다.")
        return

    files = collect(targets, args.recursive)
    if not files:
        print("PNG 파일을 찾지 못했습니다.")
    ok = fail = 0
    for i, (src, base) in enumerate(files, 1):
        if args.out:
            dst = Path(args.out) / src.relative_to(base).with_suffix(".jpg")
        else:
            dst = src.with_suffix(".jpg")
        try:
            to_jpg(src, dst, max(1, min(100, args.quality)))
            if args.delete:
                src.unlink()
            ok += 1
            print(f"[{i}/{len(files)}] {src.name} -> {dst.name}")
        except Exception as e:
            fail += 1
            print(f"[{i}/{len(files)}] 실패: {src} ({e})")

    print(f"\n완료: 성공 {ok}개, 실패 {fail}개")
    if interactive or sys.platform == "win32":
        input("엔터를 누르면 종료합니다...")


if __name__ == "__main__":
    main()
