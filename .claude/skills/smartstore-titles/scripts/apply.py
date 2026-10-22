"""3단계: 상품명을 규칙대로 검사하고, 통과하면 판매가·수량·원산지까지 고친 새 엑셀을 원본 옆에 저장합니다.
사용: python apply.py <원본 엑셀> <상품명.json> [--names-only] [--categories <카테고리.json>]
  상품명.json 예: {"3": "도시락통 주머니 ...", "4": "..."}  (키 = 엑셀 행 번호)
  --names-only: 판매가·수량·원산지는 그대로 두고 상품명만 바꿈
  --categories: category.py --out 결과(행번호 → category·code)를 '폴더명' 칸에 "[번호] 경로"로 적음.
                항목에 "markets"(시트 이름 → 번호)가 있으면 확장정보 '마켓 카테고리번호' 칸을
                config.json 마켓만 "마켓명*번호" 줄로 새로 적음(원래 값은 지움)
검사에 걸리면(반복 단어, 기존 단어 빠짐, 40자 초과, 브랜드 등) 저장하지 않고 이유를 보여줍니다."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import (check_title, clean, ext_market_text, ext_rows, market_categories, markets,  # noqa: E402
                    naver_categories, read_rows, updates_for, write_excel)

src = Path(sys.argv[1])
titles = {int(k): str(v).strip() for k, v in json.loads(Path(sys.argv[2]).read_text(encoding="utf-8-sig")).items()}
rules = "--names-only" not in sys.argv
cat_file = sys.argv[sys.argv.index("--categories") + 1] if "--categories" in sys.argv else None
categories = json.loads(Path(cat_file).read_text(encoding="utf-8-sig")) if cat_file else {}
rows, cols = read_rows(src)
if categories and cols["folder"] is None:
    sys.exit("❌ '폴더명' 열을 찾지 못해 카테고리를 적을 수 없습니다.")
known = naver_categories()
market_cats = market_categories()
use_markets = any("markets" in (item or {}) for item in categories.values())
ext = ext_rows(src) if use_markets else {}
if use_markets and not ext:
    sys.exit("❌ '확장정보' 시트를 찾지 못해 마켓 카테고리를 적을 수 없습니다.")


def folder_text(row: int) -> str | None:
    """카테고리.json 항목 → '[번호] 경로'. 번호가 목록에 있으면 경로는 목록 것을 씁니다."""
    item = categories.get(str(row)) or {}
    code, path = str(item.get("code") or "").strip(), str(item.get("category") or "").strip()
    if code and code in known:
        path = known[code]
    elif code:
        problems.append(f"{row}행 카테고리 번호 {code}: 네이버 카테고리 목록에 없음")
    if not path:
        return None
    return f"[{code}] {path}" if code else path


def market_text(row: dict) -> str | None:
    """카테고리.json 항목 → 확장정보 '마켓명*번호' 줄들(config.json 마켓 순서). 빠진 마켓은 '확인 필요'."""
    item = categories.get(str(row["excel_row"])) or {}
    if "markets" not in item:
        return None
    if row["no"] not in ext:
        problems.append(f"{row['excel_row']}행 원본번호 {row['no']}: 확장정보 시트에 없음")
        return None
    lines = []
    for m in markets():
        code = item.get("code") if m["sheet"] == "스마트스토어" else item["markets"].get(m["sheet"])
        code = str(code or "").strip()
        if not code:
            missing.append(f"{row['excel_row']}행 {m['name']}")
        elif code not in market_cats.get(m["sheet"], {}):
            problems.append(f"{row['excel_row']}행 {m['name']} 카테고리 번호 {code}: 마켓 카테고리 목록에 없음")
        else:
            lines.append(f"{m['name']}*{code}")
    return "\n".join(lines)


problems, report, updates, market_cells, missing = [], [], {}, {}, []
for r in rows:
    title = titles.get(r["excel_row"])
    if title:
        errors, notes = check_title(title, r["old"])
        if errors:
            problems.append(f"{r['excel_row']}행 '{title}': " + " / ".join(errors))
        report.append((r, title, notes))
    else:
        report.append((r, None, ["상품명 없음 · 원래 상품명 유지"]))
    updates[r["row"]] = updates_for(r, cols, title, rules)
    folder = folder_text(r["excel_row"])
    if folder:
        updates[r["row"]][cols["folder"]] = folder
    text = market_text(r)
    if text is not None:
        market_cells[r["no"]] = text

if problems:
    print("❌ 규칙에 걸려 저장하지 않았습니다. 고친 뒤 다시 실행하세요.")
    print("\n".join(problems))
    sys.exit(1)

dst = src.with_name(f"{src.stem}_상품정보수정{src.suffix}")
n = 2
while dst.exists():
    dst = src.with_name(f"{src.stem}_상품정보수정_{n}{src.suffix}")
    n += 1
write_excel(src, dst, updates, market_cells)

# 저장한 파일을 다시 읽어 허용한 칸만 바뀌었는지 확인합니다.
before, _ = read_rows(src)
after, _ = read_rows(dst)
changed = set()
for b, a in zip(before, after):
    for key in ("old", "price", "quantity", "origin", "folder", "option_details"):
        if str(b[key]) != str(a[key]):
            changed.add(key)
allowed = ({"old", "price", "quantity", "origin"} if rules else {"old"}) | ({"folder"} if categories else set())
assert changed <= allowed, f"허용하지 않은 칸이 바뀜: {changed - allowed}"
if use_markets:
    old_ext, new_ext = ext_market_text(src), ext_market_text(dst)
    wrong = [no for no in new_ext if new_ext[no] != market_cells.get(no, old_ext[no])]
    assert not wrong, f"확장정보 마켓 카테고리가 예상과 다름: {wrong}"
    if any(old_ext[no] != text for no, text in market_cells.items()):
        changed.add("markets")

print(f"✅ 저장: {dst}")
print("바뀐 칸:", ", ".join({"old": "상품명", "price": "판매가", "quantity": "수량", "origin": "원산지", "folder": "폴더명(카테고리)",
                        "markets": "확장정보 마켓 카테고리"}[k] for k in sorted(changed)) or "없음")
need = 0
for r, title, notes in report:
    flag = (" ⚠️ " + " / ".join(notes)) if notes else ""
    need += bool(notes)
    print(f"{r['excel_row']}행 ({len(title) if title else '-'}자) {title or r['old']}{flag}")
print(f"확인 필요 {need}개" if need else "확인 필요 없음")
if missing:
    print("⚠️ 마켓 카테고리 번호가 없어 빼고 적은 곳:", ", ".join(missing))
