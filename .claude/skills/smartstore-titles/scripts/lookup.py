"""2단계: 아이템스카우트 키워드 DB에서 후보 단어의 검색수·상품수·경쟁강도를 조회합니다(비용 0원, PC 안에서 처리).
사용: python lookup.py <후보.json>
  후보.json 예: {"8": ["귀이개", "귀파개", "귀후비개", "귀청소"], "9": ["워터탭", "수도꼭지연장"]}
  각 상품의 첫 두 단어는 그 말이 들어간 인기 키워드도 함께 보여줍니다(동의어·용도 단어 찾기용).
또는: python lookup.py --words 귀파개 귀후비개"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import KeywordDB, fmt  # noqa: E402

db = KeywordDB()
if sys.argv[1] == "--words":
    groups = {"-": sys.argv[2:]}
else:
    groups = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8-sig"))
for row, words in groups.items():
    print(f"[{row}행]")
    for w in words:
        hit = db.get(w)
        print(f"   {w}: {fmt(hit) if hit else '검색 기록 없음'}")
    for w in words[:2]:
        rel = [r for r in db.containing(w, 10) if r[1] != w]
        if rel:
            print(f"   └ '{w}' 포함 인기: " + "; ".join(fmt(r) for r in rel))
