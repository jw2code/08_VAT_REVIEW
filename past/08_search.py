import json
import sqlite3
import sys
import time

import numpy as np
from sentence_transformers import SentenceTransformer

model = SentenceTransformer("intfloat/multilingual-e5-small")

con = sqlite3.connect("vat_review.db")
cur = con.cursor()

# 저장해둔 판례 벡터를 숫자 묶음으로 되돌린다.
vector_rows = cur.execute(
    "SELECT source_id, vector FROM precedent_vectors ORDER BY source_id"
).fetchall()

if not vector_rows:
    raise RuntimeError("판례 벡터가 없습니다. 먼저 07_embed_precedents.py를 실행하세요.")

ids = [source_id for source_id, _ in vector_rows]
V = np.array([json.loads(vector) for _, vector in vector_rows], dtype="float32")

# 실행할 때 전표번호 또는 직접 검색문장을 적을 수 있다.
# 아무것도 적지 않으면 테스트 전표 18260102-1을 사용한다.
search_value = " ".join(sys.argv[1:]).strip() or "18260102-1"

voucher = cur.execute("""
    SELECT "계정과목", "품목이름", "적요", "1차판정", "핵심쟁점", "법령근거"
    FROM vat_screening_results
    WHERE "전표번호" = ?
""", (search_value,)).fetchone()

if voucher:
    account, item, description, decision, issue, legal_basis = voucher
    query = f"{account}. {item}. {description}"
    print("전표번호:", search_value)
    print("1차판정:", decision)
    print("핵심쟁점:", issue)
    print("법령근거:", legal_basis)
else:
    query = search_value

print("판례 검색문:", query)

# 질문도 똑같이 벡터로 바꾼다. e5 검색 질문에는 query: 를 붙인다.
q = model.encode([f"query: {query}"], normalize_embeddings=True)[0]

# V는 (판례 수, 384), q는 (384,)다. 곱하면 판례마다 점수 하나씩 나온다.
scores = V @ q

# 점수가 큰 판례 세 건을 가져온다.
top = scores.argsort()[::-1][:3]

for rank, i in enumerate(top, start=1):
    source_id = ids[i]
    row = cur.execute("""
        SELECT reference_no, title, matched_topics, source_url
        FROM legal_references
        WHERE source_id = ?
    """, (source_id,)).fetchone()

    reference_no, title, topics, source_url = row
    print(f"\n{rank}위  유사도 {scores[i]:.4f}")
    print("사건번호:", reference_no)
    print("판례명  :", title)
    print("쟁점    :", topics)
    print("출처    :", source_url)

# 검색 계산 자체가 얼마나 걸리는지도 확인한다.
started = time.time()
for _ in range(100):
    scores = V @ q
print(f"\n검색 한 번 {(time.time() - started) / 100 * 1000:.3f}ms")

con.close()
