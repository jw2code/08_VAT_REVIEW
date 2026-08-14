# csv는 파이썬에 기본으로 들어 있는 도구다. 따로 설치할 게 없다.
# 쉼표로 나뉜 파일을 알아서 칸별로 잘라준다.
import csv


def shorten(row, limit=100):
    """판례 본문처럼 긴 값은 앞부분만 보여준다."""
    return {
        key: value if len(value) <= limit else value[:limit] + "..."
        for key, value in row.items()
    }


# data 폴더 안에 있는 세 CSV 파일을 차례대로 확인한다.
for name in [
    "vat_screening_results.csv",
    "vat_rules.csv",
    "precedents_usable.csv",
]:

    # utf-8-sig는 UTF-8 CSV의 한글과 BOM 문제를 함께 처리한다.
    with open(f"data/{name}", encoding="utf-8-sig", newline="") as f:

        # 첫 줄을 칸 이름으로 사용하고 나머지 줄을 딕셔너리로 읽는다.
        rows = list(csv.DictReader(f))

    print("==", name, len(rows), "줄")

    if rows:
        print("칸 이름:", list(rows[0]))
        print("첫 줄  :", shorten(rows[0]))
    else:
        print("데이터가 없는 파일입니다.")

    print()
