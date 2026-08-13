import csv
import sqlite3

# shop.db 연결
con = sqlite3.connect("shop.db")
cur = con.cursor()

# IF NOT EXISTS 구문을 추가하여 재실행 시 오류 발생 방지
cur.executescript("""
CREATE TABLE IF NOT EXISTS customer_inputs (
    voucher_id   TEXT PRIMARY KEY,
    voucher_type TEXT,
    account_name TEXT,
    item_name    TEXT,
    amount       INTEGER,
    description  TEXT
);


CREATE TABLE IF NOT EXISTS legal_references (
    reference_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    reference_type TEXT,
    title          TEXT,
    legal_principle TEXT,
    source_url      TEXT,

    UNIQUE(reference_type, title)
);
""")

def load(table, name):
    """CSV 파일 하나를 읽어서 표 하나에 통째로 넣는다."""
    with open(f"data/{name}", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    if not rows:
        print(f"{table:10s} 데이터 없음")
        return

    cols = list(rows[0])
    marks = ",".join("?" * len(cols))
    values = [tuple(row[c] for c in cols) for row in rows]

    # 중복 실행 시 Primary Key 충돌 에러를 방지하려면 INSERT OR IGNORE 구문 사용 가능
    cur.executemany(
        f"INSERT OR IGNORE INTO {table} VALUES ({marks})",
        values,
    )

    print(f"{table:10s} {len(rows):5d}줄")


load("customer_inputs", "customer.csv")
load("legal_references", "판례.csv")

# 데이터 확정 및 연결 종료
con.commit()
con.close()