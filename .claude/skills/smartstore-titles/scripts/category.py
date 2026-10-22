"""4단계: 아이템스카우트 키워드 DB의 '대표 카테고리'로 상품별 네이버 카테고리를 추천합니다(비용 0원, PC 안에서 처리).
사용: python category.py <물건이름.json> [--out <카테고리.json>]
  물건이름.json 예: {"8": ["귀이개", "귀파개", "귀후비개"], "9": ["세면대수전", "워터탭"]}
  상품 자체를 부르는 이름만 넣습니다(용도·장소 단어는 빼기). 단어별 카테고리를 검색수로 더해 가장 큰 것을 추천합니다.
대표 카테고리는 그 키워드 상품이 가장 많이 몰린 곳이라 엉뚱할 수 있으니, 같은 물건이 맞는지 직접 확인합니다.
추천 결과에는 네이버 카테고리 번호(code)도 붙습니다(naver_categories.csv.gz에 경로가 있을 때).
또는: python category.py --find 도마 레그워머   (카테고리 경로에 그 말이 들어간 네이버 카테고리와 번호 찾기)"""
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import KeywordDB, naver_categories, naver_code  # noqa: E402


def recommend(db: KeywordDB, words: list[str]) -> tuple[list[tuple[str, int]], list[str]]:
    """([(카테고리, 검색수 합)] 큰 순서, 단어별 설명 줄)."""
    votes, lines = Counter(), []
    for w in words:
        hit = db.get(w)
        cat = hit[2] if hit and hit[2] not in ("", "-") else ""
        if cat:
            votes[cat] += hit[3]
            lines.append(f"   {w}: {cat} (검색{hit[3]:,})")
        else:
            lines.append(f"   {w}: {'카테고리 없음' if hit else '검색 기록 없음'}")
    return votes.most_common(3), lines


def main() -> None:
    args = sys.argv[1:]
    out = Path(args[args.index("--out") + 1]) if "--out" in args else None
    groups = json.loads(Path(args[0]).read_text(encoding="utf-8-sig"))
    db = KeywordDB()
    cats = naver_categories()
    result = {}
    for row, words in groups.items():
        top, lines = recommend(db, words)
        if not top:
            print(f"[{row}행] 추천 없음 → 확인 필요")
            print("\n".join(lines))
            result[row] = {"category": "", "code": "", "share": 0, "others": []}
            continue
        share = round(top[0][1] / sum(n for _, n in top) * 100)
        code = naver_code(top[0][0], cats)
        flag = "" if share >= 70 else "  ← 확인 필요(단어마다 카테고리가 다름)"
        print(f"[{row}행] 추천: [{code or '번호 없음'}] {top[0][0]} ({share}%){flag}")
        print("\n".join(lines))
        result[row] = {"category": top[0][0], "code": code, "share": share, "others": [c for c, _ in top[1:]]}
    if out:
        out.write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"저장: {out}")


def search(terms: list[str]) -> None:
    """네이버 카테고리 목록에서 경로에 단어가 들어간 카테고리를 번호와 함께 보여줍니다."""
    cats = naver_categories()
    for t in terms:
        found = [(c, p) for c, p in cats.items() if t in p]
        print(f"[{t}] {len(found)}개" + ("" if found else " → 다른 말로 찾아보기"))
        for c, p in found[:15]:
            print(f"   {c} {p}")


if __name__ == "__main__":
    if sys.argv[1] == "--find":
        search(sys.argv[2:])
    else:
        main()
