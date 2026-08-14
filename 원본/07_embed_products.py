import sqlite3

import numpy as np
from sentence_transformers import SentenceTransformer

model = SentenceTransformer("intfloat/multilingual-e5-small")

con = sqlite3.connect("shop.db")
cur = con.cursor()

# 상품 200개를 통째로 꺼낸다
rows = cur.execute("SELECT product_id, name, description FROM products").fetchall()

# 이름과 설명을 붙여 한 덩어리로 만든다.
# 설명만 넣으면 「히알루론산」 같은 성분 이름이 이름 쪽에만 있을 때 빠진다.
# for 안의 _ 는 "이 값은 안 쓴다"는 표시다 (여기서는 product_id)
docs = [f"{name}. {desc}" for _, name, desc in rows]

# batch_size=32 는 "한 번에 32개씩 묶어서 계산해라" 는 뜻이다.
# 한꺼번에 200개를 올리면 메모리가 모자랄 수 있어 나눠서 처리한다
V = model.encode(docs, normalize_embeddings=True, batch_size=32)

print("모양:", V.shape)               # (200, 384) = 상품 200개 x 숫자 384개
print("한 상품의 숫자 개수:", len(V[0]))

import json

# 벡터를 담을 표를 만든다. IF NOT EXISTS 를 붙이면 이미 있을 때 그냥 넘어간다
cur.execute("""
CREATE TABLE IF NOT EXISTS product_vectors (
    product_id TEXT PRIMARY KEY,
    vector     TEXT          -- 숫자 384개를 글자로 눌러 담는다
)
""")

# 다시 만들 때를 대비해 기존 것을 비운다. DELETE 에 WHERE 를 안 쓰면 전부 지운다
cur.execute("DELETE FROM product_vectors")

# zip 은 두 목록을 짝지어 하나씩 꺼내준다.  rows[0]와 V[0], rows[1]과 V[1], ...
for (pid, _, _), vec in zip(rows, V):
    # tolist() 는 numpy 숫자 묶음을 파이썬 목록으로 바꾼다.
    # json.dumps 는 그 목록을 글자로 만든다 -> "[0.0623, -0.0149, ...]"
    cur.execute(
        "INSERT INTO product_vectors VALUES (?, ?)",
        (pid, json.dumps(vec.tolist())),
    )

con.commit()

# 잘 들어갔는지 확인한다
print("저장된 줄:", cur.execute("SELECT COUNT(*) FROM product_vectors").fetchone()[0])
raw = cur.execute("SELECT vector FROM product_vectors LIMIT 1").fetchone()[0]
print("한 줄 길이:", len(raw), "글자")

def load_vectors():
    """저장해둔 글자를 숫자 묶음으로 되돌린다."""
    rows = cur.execute("SELECT product_id, vector FROM product_vectors").fetchall()

    ids = [pid for pid, _ in rows]

    # json.loads 는 글자를 다시 목록으로 바꾼다 (dumps 의 반대)
    # np.array 는 그 목록을 numpy 숫자 묶음으로 만든다 — 계산이 빨라진다
    # dtype="float32" 는 "소수를 32비트 크기로 담아라" 는 뜻이다. 기본값(64비트)의 절반이라
    # 메모리를 아끼고, 이 정도 정밀도면 검색 결과가 달라지지 않는다
    V = np.array([json.loads(v) for _, v in rows], dtype="float32")

    return ids, V
