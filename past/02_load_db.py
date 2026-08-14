import csv
import sqlite3

# VAT 검토 전용 DB 연결
con = sqlite3.connect("vat_review.db")
cur = con.cursor()

# CSV의 열 이름과 DB 표의 열 이름을 동일하게 만들었다.
# 그러면 INSERT할 때 열 이름을 직접 지정할 수 있어서
# CSV 열 수가 달라져도 "몇 columns but 몇 values" 오류가 나지 않는다.
cur.executescript("""
CREATE TABLE IF NOT EXISTS vat_screening_results ( --시험결과지
    "검토상태"     TEXT, --현재 검토 상태
    "전표번호"     TEXT PRIMARY KEY, --전표를 구분하는 고유번호
    "전표유형"     TEXT, --회계전표의 유형(과세매입 등)
    "계정과목"     TEXT, --
    "품목이름"     TEXT, --
    "금액"         INTEGER, -- 
    "적요"         TEXT, --
    "1차판정"      TEXT, -- 공제 가능,불가능,추가검토
    "판정신뢰도"   TEXT, -- 해당규칙이 얼마나 명확하게 적용되었는가
    "적용규칙ID"   TEXT, -- 어떤 법령 규칙으로 판정했는지
    "핵심쟁점"     TEXT, --주요 세무 문재
    "판정사유"     TEXT, --왜 그런결과가 나왔는지
    "법령근거"     TEXT, --관련 법률 조항
    "추가확인사항" TEXT, --사실관계 (불공제항목을 공제판정 받은 경우의 특수한 사실관계)
    "근거URL"      TEXT, -- 관련 법령이나 공식 자료 주소
    "매칭문구"     TEXT, -- 규칙이 실제로 감지한 적요의 문구
    "규칙버전"     TEXT --규칙의 기준일
);

CREATE TABLE IF NOT EXISTS vat_rules ( -- 채점기준표
    rule_id           TEXT PRIMARY KEY, --전표번호(기준)
    priority          INTEGER, --규칙 적용 순서
    active            TEXT, --규칙을 사용할지 여부
    decision          TEXT, --규칙이 적용됏을 때 반환할 판정
    confidence        TEXT, --규칙 판정의 신뢰도
    issue             TEXT, --규칙이 다루는 세무행정
    match_columns     TEXT, --검색할 항목
    include_regex     TEXT, --발견시 규칙을 적용할 문구 패턴
    exclude_regex     TEXT, --발견시 규칙을 제외할 문구 패턴
    legal_basis       TEXT, --법령 근거
    rule_description  TEXT, --규칙을 사람이 읽을 수 있게 설명
    follow_up_question TEXT, --추가검토를 하게된다면 확인할 질문
    source_url        TEXT, --법령 공식자료 출처
    rule_version      TEXT --규칙을 작성하거나 확인한 기준일
);

CREATE TABLE IF NOT EXISTS legal_references ( --정제된 판례 자료표
    document_type      TEXT, --판례
    source_target      TEXT, --자료구분
    source_id          INTEGER PRIMARY KEY, --판례구분 ID(법령정보센터)
    title              TEXT, --판례명
    reference_no       TEXT, --사건번호
    court_or_agency    TEXT, --판결법원
    issue_or_holding   TEXT, --판례의 핵심 쟁점 및 판시사항
    summary_or_answer  TEXT, --판결요지 또는 결론 요약
    facts_and_reasoning TEXT, --판례 관련된 법령 및 다른 판례
    related_law        TEXT, --판례와 관련된 다른 법령 및 판례
    full_text          TEXT, --판결문 전체 내용
    source_url         TEXT, --공식 판례 페이지 주소
    matched_queries    TEXT, --수집할때 어떤 검색어에 걸렸는지
    content_sha256     TEXT, -- 판례 본문을 구분하기 위한 해시값
    relevance_level    TEXT, -- VAT 관련수준
    matched_topics     TEXT, -- 매입세액 쟁점
    filter_basis       TEXT -- 사용가능 판례 선별사유
);
""")


def quote_name(name):
    """한글·숫자·특수문자가 있는 열 이름을 SQLite에서 안전하게 감싼다."""
    return '"' + name.replace('"', '""') + '"'


def load(table, name):
    """CSV 파일 하나를 읽어서 지정한 표에 넣는다."""
    with open(f"data/{name}", encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))

    if not rows:
        print(f"{table:24s} 데이터 없음")
        return

    cols = list(rows[0])
    column_names = ",".join(quote_name(col) for col in cols)
    marks = ",".join("?" for _ in cols)
    values = [tuple(row[col] for col in cols) for row in rows]

    # 열 이름을 명시하므로 CSV 열 순서가 바뀌어도 안전하다.
    # OR REPLACE는 같은 전표번호·규칙ID·판례ID를 다시 실행하면 최신 행으로 바꾼다.
    cur.executemany(
        f"INSERT OR REPLACE INTO {quote_name(table)} ({column_names}) VALUES ({marks})",
        values,
    )

    print(f"{table:24s} {len(rows):5d}줄")


load("vat_screening_results", "vat_screening_results.csv")
load("vat_rules", "vat_rules.csv")
load("legal_references", "precedents_usable.csv")

# 데이터 확정 및 연결 종료
con.commit()
con.close()
