"""1단계: 이셀러스 엑셀에서 상품 목록을 읽어 보여줍니다.
사용: python extract.py <엑셀 경로>"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import TITLE_MAX, brands, bundle_suffix, clean, option_stock, price_plan, pricing, read_rows  # noqa: E402

path = Path(sys.argv[1])
if "_상품정보수정" in path.stem:
    print("⚠️ 이미 수정된 엑셀로 보입니다(파일 이름에 '_상품정보수정'). 판매가가 한 번 더 25% 오를 수 있으니 원본 엑셀인지 확인하세요.")
rows, cols = read_rows(path)
missing = [k for k in ("price", "quantity", "origin", "option_details") if cols[k] is None]
rule = pricing()
print(f"파일: {path.name} | 상품 {len(rows)}개 | 제외 브랜드: {', '.join(brands())}")
print(f"판매가 규칙: 원가 +{(rule['markup'] - 1) * 100:g}%, 수수료 {rule['fee_rate'] * 100:g}% 떼고 "
      f"한 건당 {rule['min_margin']:,}원 이상 남게(모자라면 최대 {rule['max_bundle']}개까지 묶음)")
if missing:
    print("참고: 찾지 못한 열(수정 안 함):", ", ".join(missing))
for r in rows:
    stock = option_stock(r["option_details"])
    options = [line.split("*")[0] for line in r["option_details"].replace("\r", "\n").split("\n") if line.strip()]
    plan = price_plan(r["price"])
    if plan:
        suffix = bundle_suffix(plan["bundle"])
        bundle = (f" | {plan['bundle']}개 묶음: 상품명 끝에 '{suffix.strip()}' 자동, 상품명은 {TITLE_MAX - len(suffix)}자까지"
                  if suffix else "")
        money = f"판매가 {r['price']} → {plan['bundle']}개 {plan['price']:,}원 (마진 {plan['margin']:,}원){bundle}"
    else:
        money = f"판매가 {r['price'] or '-'}"
    print(f"{r['excel_row']}행 | {clean(r['old'])} ({len(clean(r['old']))}자) | {money}"
          f" | 원산지 {r['origin'] or '-'} | 옵션재고합 {stock if stock is not None else '-'}"
          f" | 옵션명: {', '.join(options[:4]) or '-'}")
