import csv
import sqlite3

from app.config import DATA_DIR, DB_PATH


# 01_schema.py가 만든 것과 같은 DB 파일에 연결한다.
# 실행 순서: 01_schema.py -> 02_load_db.py
con = sqlite3.connect(DB_PATH)
con.execute("PRAGMA foreign_keys = ON")
cur = con.cursor()


# 01_schema.py가 파일명으로 만든 원천 테이블
# (laws, precedents, rag_documents, rag_chunks 등)은 여기서 다시 만들지 않는다.
# 이 파일에서는 VAT Review Agent가 직접 사용하는 서비스용 테이블만 만든다.
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
    reference_id    INTEGER PRIMARY KEY AUTOINCREMENT,
    reference_type  TEXT,
    title           TEXT,
    legal_principle TEXT,
    source_url      TEXT,

    UNIQUE(reference_type, title)
);


CREATE TABLE IF NOT EXISTS app_vat_rules (
    rule_id           TEXT PRIMARY KEY,
    priority          INTEGER NOT NULL DEFAULT 100,
    active            TEXT NOT NULL DEFAULT 'Y',
    decision          TEXT NOT NULL,
    confidence        TEXT,
    issue             TEXT,
    match_columns     TEXT,
    include_regex     TEXT,
    exclude_regex     TEXT,
    require_regex     TEXT,
    require_not_regex TEXT,
    keyword_weight    REAL,
    base_law          TEXT,
    detail_law        TEXT,
    source_url        TEXT,
    notes             TEXT,
    version           TEXT NOT NULL
);


CREATE TABLE IF NOT EXISTS app_vat_screening_results (
    voucher_id             TEXT PRIMARY KEY,
    review_status          TEXT NOT NULL DEFAULT '1차 검토',
    first_decision         TEXT,
    confidence             TEXT,
    applied_rule_id        TEXT,
    main_issue             TEXT,
    decision_reason        TEXT,
    legal_basis            TEXT,
    additional_information TEXT,
    source_url             TEXT,
    matched_text           TEXT,
    rule_version           TEXT,
    reviewed_at            TEXT DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (voucher_id)
        REFERENCES customer_inputs(voucher_id),
    FOREIGN KEY (applied_rule_id)
        REFERENCES app_vat_rules(rule_id)
);


CREATE TABLE IF NOT EXISTS app_screening_evidence (
    evidence_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    voucher_id      TEXT NOT NULL,
    chunk_id        TEXT,
    reference_id    INTEGER,
    evidence_rank   INTEGER,
    similarity_score REAL,
    evidence_text   TEXT,
    source_url      TEXT,

    FOREIGN KEY (voucher_id)
        REFERENCES customer_inputs(voucher_id),
    FOREIGN KEY (reference_id)
        REFERENCES legal_references(reference_id),
    UNIQUE(voucher_id, chunk_id, reference_id)
);


CREATE TABLE IF NOT EXISTS app_review_answers (
    answer_id        INTEGER PRIMARY KEY AUTOINCREMENT,
    voucher_id       TEXT NOT NULL,
    question         TEXT,
    answer            TEXT NOT NULL,
    revised_decision TEXT,
    revised_reason   TEXT,
    answered_at      TEXT DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (voucher_id)
        REFERENCES customer_inputs(voucher_id)
);


CREATE TABLE IF NOT EXISTS app_validation_answers (
    validation_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    row_number         INTEGER,
    voucher_id         TEXT,
    test_type          TEXT,
    expected_decision  TEXT,
    main_issue         TEXT,
    precedent_inserted TEXT,
    related_precedent  TEXT,
    precedent_fact     TEXT,
    source_url         TEXT,

    FOREIGN KEY (voucher_id)
        REFERENCES customer_inputs(voucher_id),
    UNIQUE(voucher_id, test_type)
);


CREATE INDEX IF NOT EXISTS idx_customer_inputs_account
    ON customer_inputs(account_name);

CREATE INDEX IF NOT EXISTS idx_screening_results_decision
    ON app_vat_screening_results(first_decision);

CREATE INDEX IF NOT EXISTS idx_screening_evidence_voucher
    ON app_screening_evidence(voucher_id);

CREATE INDEX IF NOT EXISTS idx_review_answers_voucher
    ON app_review_answers(voucher_id);
""")


def load(table, name, column_map, converters=None):
    """CSV에서 지정한 열만 골라 대상 테이블에 저장한다."""
    converters = converters or {}

    with open(DATA_DIR / name, encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))

    if not rows:
        print(f"{table:24s} 데이터 없음")
        return

    missing_columns = [
        csv_column
        for csv_column in column_map
        if csv_column not in rows[0]
    ]

    if missing_columns:
        raise ValueError(
            f"{name}에 필요한 컬럼이 없습니다: {missing_columns}"
        )

    csv_columns = list(column_map)
    table_columns = [column_map[column] for column in csv_columns]

    values = []
    for row in rows:
        converted_row = []

        for csv_column in csv_columns:
            value = row[csv_column]
            converter = converters.get(csv_column)

            if converter is not None:
                value = converter(value)

            converted_row.append(value)

        values.append(tuple(converted_row))

    quoted_columns = ", ".join(
        f'"{column}"' for column in table_columns
    )
    marks = ", ".join("?" for _ in table_columns)

    cur.executemany(
        f'INSERT OR IGNORE INTO "{table}" '
        f'({quoted_columns}) VALUES ({marks})',
        values,
    )

    print(f"{table:24s} {len(values):5d}줄 처리")


def to_integer(text):
    """쉼표가 포함된 금액 문자열을 정수로 바꾼다."""
    cleaned = (text or "").replace(",", "").strip()
    return int(cleaned) if cleaned else None


try:
    load(
        "customer_inputs",
        "customer.csv",
        {
            "전표번호": "voucher_id",
            "전표유형": "voucher_type",
            "계정과목": "account_name",
            "품목이름": "item_name",
            "금액": "amount",
            "적요": "description",
        },
        converters={"금액": to_integer},
    )

    load(
        "legal_references",
        "판례.csv",
        {
            "구분": "reference_type",
            "판례/법령": "title",
            "테스트에 반영한 핵심 법리": "legal_principle",
            "공식 출처": "source_url",
        },
    )

    con.commit()
    print(f"데이터 저장 완료: {DB_PATH}")

except Exception:
    con.rollback()
    raise

finally:
    con.close()
