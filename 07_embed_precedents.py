import json
import re
import sqlite3

import numpy as np
from sentence_transformers import SentenceTransformer

model = SentenceTransformer("intfloat/multilingual-e5-small")

con = sqlite3.connect("vat_review.db")
cur = con.cursor()

# 정제된 판례 531건을 통째로 꺼낸다.
rows = cur.execute("""
    SELECT
        source_id,
        title,
        reference_no,
        issue_or_holding,
        summary_or_answer,
        facts_and_reasoning,
        related_law
    FROM legal_references
    ORDER BY source_id
""").fetchall()


def clean(value):
    """HTML 줄바꿈 표시와 불필요한 공백을 정리한다."""
    text = "" if value is None else str(value)
    text = re.sub(r"<br\s*/?>", " ", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).strip()


# 제목·쟁점·요지·사실관계·관련 법령을 붙여 판례 한 건의 검색 문서를 만든다.
# e5 모델의 문서에는 passage: 를 붙인다.
docs = []
for _, title, ref_no, issue, summary, reasoning, related_law in rows:
    doc = (
        f"passage: {clean(title)}. 사건번호 {clean(ref_no)}. "
        f"쟁점 {clean(issue)}. 판결요지 {clean(summary)}. "
        f"사실관계와 판단 {clean(reasoning)[:2500]}. "
        f"관련법령 {clean(related_law)}"
    )
    docs.append(doc)

# batch_size=16은 판례 문장이 상품 설명보다 길어서 조금 작게 잡았다.
V = model.encode(
    docs,
    normalize_embeddings=True,
    batch_size=16,
    show_progress_bar=True,
)

print("모양:", V.shape)               # (531, 384) 예상
print("한 판례의 숫자 개수:", len(V[0]))

# 벡터를 담을 표를 만든다. IF NOT EXISTS를 붙이면 이미 있을 때 그냥 넘어간다.
cur.execute("""
CREATE TABLE IF NOT EXISTS precedent_vectors (
    source_id INTEGER PRIMARY KEY,
    vector    TEXT
)
""")

# 판례 CSV를 새로 정제해 다시 실행할 때를 대비해 기존 벡터를 비운다.
cur.execute("DELETE FROM precedent_vectors")

# 판례ID와 벡터를 짝지어 저장한다.
for (source_id, *_), vec in zip(rows, V):
    cur.execute(
        "INSERT INTO precedent_vectors VALUES (?, ?)",
        (source_id, json.dumps(vec.tolist())),
    )

con.commit()

# 잘 들어갔는지 확인한다.
print("저장된 줄:", cur.execute("SELECT COUNT(*) FROM precedent_vectors").fetchone()[0])
raw = cur.execute("SELECT vector FROM precedent_vectors LIMIT 1").fetchone()[0]
print("한 줄 길이:", len(raw), "글자")


def load_vectors():
    """저장해둔 글자를 숫자 묶음으로 되돌린다."""
    vector_rows = cur.execute(
        "SELECT source_id, vector FROM precedent_vectors ORDER BY source_id"
    ).fetchall()

    ids = [source_id for source_id, _ in vector_rows]
    vectors = np.array([json.loads(v) for _, v in vector_rows], dtype="float32")
    return ids, vectors


ids, loaded_vectors = load_vectors()
print("다시 읽은 모양:", loaded_vectors.shape)

con.close()
