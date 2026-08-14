import sqlite3

con = sqlite3.connect("vat_review.db")     # 02번에서 만든 파일을 연다
cur = con.cursor()

# 전표번호 하나의 1차 판정 결과를 확인한다.
print(cur.execute("""
    SELECT "전표번호", "계정과목", "품목이름", "적요", "1차판정", "핵심쟁점"
    FROM vat_screening_results
    WHERE "전표번호" = '18260102-1'
""").fetchone())

# GROUP BY로 공제 가능·불공제 가능·추가검토 건수를 센다.
for row in cur.execute("""
    SELECT "1차판정", COUNT(*) AS 건수
    FROM vat_screening_results
    GROUP BY "1차판정"
    ORDER BY 건수 DESC
""").fetchall():
    print(row)

# 전표 결과와 실제 적용된 규칙을 규칙ID로 붙인다.
rows = cur.execute("""
    SELECT
        results."전표번호",
        results."계정과목",
        results."적요",
        rules.decision,
        rules.legal_basis,
        rules.follow_up_question
    FROM vat_screening_results AS results
    JOIN vat_rules AS rules
      ON results."적용규칙ID" = rules.rule_id
    WHERE results."1차판정" = '추가검토'
    ORDER BY results."전표번호"
    LIMIT 5
""").fetchall()

for row in rows:
    print(row)

# LIKE는 특정 단어가 들어 있는 판례를 찾을 때 쓴다.
# 물음표에 값을 따로 넘기면 검색어에 따옴표가 들어 있어도 안전하다.
keyword = "비영업용 소형승용차"
for row in cur.execute("""
    SELECT reference_no, title, matched_topics, relevance_level
    FROM legal_references
    WHERE title LIKE ?
       OR matched_topics LIKE ?
       OR issue_or_holding LIKE ?
       OR full_text LIKE ?
    ORDER BY document_date DESC
    LIMIT 5
""", (f"%{keyword}%",) * 4).fetchall():
    print(row)

# 표마다 몇 줄이 들어 있는지 확인한다.
print("전표", cur.execute("SELECT COUNT(*) FROM vat_screening_results").fetchone()[0])
print("규칙", cur.execute("SELECT COUNT(*) FROM vat_rules").fetchone()[0])
print("판례", cur.execute("SELECT COUNT(*) FROM legal_references").fetchone()[0])

con.close()
