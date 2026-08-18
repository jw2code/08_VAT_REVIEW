import csv
import re
import sqlite3
import sys
from pathlib import Path


# 현재 파일: C:\jw_project2\pipeline\01_schema.py
# 프로젝트 루트: C:\jw_project2
ROOT = Path(__file__).resolve().parent.parent

# 프로젝트 루트에서 app 패키지를 찾을 수 있게 설정
sys.path.insert(0, str(ROOT))

from app.config import DATA_DIR, DB_PATH


# 실행할 때마다 기존 DB를 지우고 CSV 기준으로 새로 만든다.
if DB_PATH.exists():
    DB_PATH.unlink()

con = sqlite3.connect(DB_PATH)
con.execute("PRAGMA foreign_keys = ON")


def read_csv(path):
    """CSV의 컬럼명과 전체 행을 반환한다."""
    with open(path, encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        return reader.fieldnames or [], list(reader)


def looks_int(text):
    body = text[1:] if text.startswith("-") else text

    if not body.isdigit():
        return False

    # 001처럼 앞에 0이 붙은 값은 번호일 수 있으므로 TEXT로 둔다.
    return not (len(body) > 1 and body.startswith("0"))


def looks_float(text):
    try:
        float(text)
    except ValueError:
        return False

    return "." in text


def looks_date(text):
    return re.fullmatch(r"\d{4}-\d{2}-\d{2}", text) is not None


def infer_type(values):
    """한 컬럼의 값들을 보고 SQLite 자료형을 추론한다."""
    seen = [value for value in values if value != ""]

    if not seen:
        return "TEXT"

    if all(looks_int(value) for value in seen):
        return "INTEGER"

    if all(looks_float(value) for value in seen):
        return "FLOAT"

    if all(looks_date(value) for value in seen):
        return "DATE"

    return "TEXT"


def infer_pk(columns, rows):
    """이름이 _id로 끝나고 값이 고유한 컬럼을 기본키로 선택한다."""
    for column in columns:
        if not column.endswith("_id"):
            continue

        values = [row[column] for row in rows]

        if "" in values:
            continue

        if len(set(values)) == len(values):
            return column

    return None


def owner_of(column, tables):
    """외래키 컬럼 이름을 바탕으로 원본 테이블을 찾는다."""
    stem = column[:-3]

    for candidate in (stem, stem + "s", stem + "es"):
        if candidate in tables:
            return candidate

    return None


def sort_by_dependency(tables):
    """참조되는 테이블이 먼저 생성되도록 순서를 정한다."""
    done = set()
    order = []

    while len(order) < len(tables):
        moved = False

        for name, table in tables.items():
            if name in done:
                continue

            if all(owner in done for _, owner in table["fks"]):
                order.append(name)
                done.add(name)
                moved = True

        # 순환 참조가 있으면 남은 테이블을 원래 순서대로 추가한다.
        if not moved:
            order.extend(name for name in tables if name not in done)
            break

    return order


def convert(value, kind):
    """CSV 문자열을 추론한 SQLite 자료형에 맞게 변환한다."""
    if value == "":
        return None

    if kind == "INTEGER":
        return int(value)

    if kind == "FLOAT":
        return float(value)

    return value


def build_create(name, table):
    """테이블 생성 SQL을 만든다. 한글 컬럼명도 처리하도록 이름을 인용한다."""
    lines = []

    for column in table["columns"]:
        piece = f'    "{column}" {table["types"][column]}'

        if column == table["pk"]:
            piece += " PRIMARY KEY"

        lines.append(piece)

    for column, owner in table["fks"]:
        lines.append(
            f'    FOREIGN KEY ("{column}") '
            f'REFERENCES "{owner}"("{column}")'
        )

    return f'CREATE TABLE "{name}" (\n' + ",\n".join(lines) + "\n)"


# 1. CSV별 컬럼, 자료형, 기본키 정보를 수집한다.
tables = {}

for path in sorted(DATA_DIR.glob("*.csv")):
    columns, rows = read_csv(path)

    if not columns:
        print(f"{path.name}: 컬럼이 없어 건너뜁니다.")
        continue

    tables[path.stem] = {
        "columns": columns,
        "rows": rows,
        "types": {
            column: infer_type([row[column] for row in rows])
            for column in columns
        },
        "pk": infer_pk(columns, rows),
    }


# 2. 각 테이블의 외래키를 찾는다.
for name, table in tables.items():
    fks = []

    for column in table["columns"]:
        if not column.endswith("_id"):
            continue

        owner = owner_of(column, tables)

        if not owner or owner == name:
            continue

        if tables[owner]["pk"] != column:
            continue

        fks.append((column, owner))

    table["fks"] = fks


# 3. 테이블 생성 순서를 정한다.
table_order = sort_by_dependency(tables)


# 4. 모든 테이블을 만들고, 각 CSV의 데이터를 해당 테이블에 저장한다.
try:
    for name in table_order:
        table = tables[name]
        sql = build_create(name, table)

        print(sql)
        con.execute(sql)

        columns = table["columns"]
        quoted_columns = ", ".join(f'"{column}"' for column in columns)
        placeholders = ", ".join("?" for _ in columns)

        values = [
            tuple(
                convert(row[column], table["types"][column])
                for column in columns
            )
            for row in table["rows"]
        ]

        if values:
            con.executemany(
                f'INSERT INTO "{name}" ({quoted_columns}) '
                f'VALUES ({placeholders})',
                values,
            )

        for column, _owner in table["fks"]:
            con.execute(
                f'CREATE INDEX "idx_{name}_{column}" '
                f'ON "{name}"("{column}")'
            )

        print(f"{name}: {len(values)}줄 저장 완료")

    con.commit()
    print(f"DB 생성 완료: {DB_PATH}")

except Exception:
    con.rollback()
    raise


# 지금 처럼 해당 파일에서 데이터 확인 SQL문을 실행하면 안되는 이유
# 01_schema.py 하는일은 다음과 같음
# csv파일 모두 불러옴 -> 파일별로 테이블명과 들어갈 데이터분리 -> 각 데이터벼로 타입 추론
# 테이블 생성 sql문 제작 -> sql문 실행해서 테이블 생성 -> 생성된 테이블에 각 csv파일 데이터를
# 데이터 타입에 맞게 변환해서 저장 -> 생성된 데이터의 외래키 컬럼에 인덱싱 처리

# 그래서 해당 파일에 단지 데이터 확인하는 쿼리문을 날리면 그거 하나때문에 위의 무거운 프로세스 매번 실행됨
# 해결 : 별도의 db.py를 app폴더 안쪽에 만들어서 파이프라인을 건들지 않으면서 데이터 조회하는 함수를 호출해 사용

finally:
    con.close()
