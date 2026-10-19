"""3단계: 상품명을 규칙대로 검사하고, 통과하면 판매가·수량·원산지까지 고친 새 엑셀을 원본 옆에 저장합니다.
사용: python apply.py <원본 엑셀> <상품명.json> [--names-only]
  상품명.json 예: {"3": "도시락통 주머니 ...", "4": "..."}  (키 = 엑셀 행 번호)
  --names-only: 판매가·수량·원산지는 그대로 두고 상품명만 바꿈
검사에 걸리면(반복 단어, 기존 단어 빠짐, 40자 초과, 브랜드 등) 저장하지 않고 이유를 보여줍니다."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import check_title, clean, read_rows, updates_for, write_excel  # noqa: E402

src = Path(sys.argv[1])
titles = {int(k): str(v).strip() for k, v in json.loads(Path(sys.argv[2]).read_text(encoding="utf-8-sig")).items()}
rules = "--names-only" not in sys.argv
rows, cols = read_rows(src)

problems, report, updates = [], [], {}
for r in rows:
    title = titles.get(r["excel_row"])
    if not title:
        report.append((r, None, ["상품명 없음 · 원래 상품명 유지"]))
        updates[r["row"]] = updates_for(r, cols, None, rules)
        continue
    errors, notes = check_title(title, r["old"])
    if errors:
        problems.append(f"{r['excel_row']}행 '{title}': " + " / ".join(errors))
    report.append((r, title, notes))
    updates[r["row"]] = updates_for(r, cols, title, rules)

if problems:
    print("❌ 규칙에 걸려 저장하지 않았습니다. 고친 뒤 다시 실행하세요.")
    print("\n".join(problems))
    sys.exit(1)

dst = src.with_name(f"{src.stem}_상품정보수정{src.suffix}")
n = 2
while dst.exists():
    dst = src.with_name(f"{src.stem}_상품정보수정_{n}{src.suffix}")
    n += 1
write_excel(src, dst, updates)

# 저장한 파일을 다시 읽어 허용한 칸만 바뀌었는지 확인합니다.
before, _ = read_rows(src)
after, _ = read_rows(dst)
changed = set()
for b, a in zip(before, after):
    for key in ("old", "price", "quantity", "origin", "option_details"):
        if str(b[key]) != str(a[key]):
            changed.add(key)
allowed = {"old", "price", "quantity", "origin"} if rules else {"old"}
assert changed <= allowed, f"허용하지 않은 칸이 바뀜: {changed - allowed}"

print(f"✅ 저장: {dst}")
print("바뀐 칸:", ", ".join({"old": "상품명", "price": "판매가", "quantity": "수량", "origin": "원산지"}[k] for k in sorted(changed)) or "없음")
need = 0
for r, title, notes in report:
    flag = (" ⚠️ " + " / ".join(notes)) if notes else ""
    need += bool(notes)
    print(f"{r['excel_row']}행 ({len(title) if title else '-'}자) {title or r['old']}{flag}")
print(f"확인 필요 {need}개" if need else "확인 필요 없음")
