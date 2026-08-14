query = "건조한 피부에 순한 것"

# 질문도 똑같이 벡터로 바꾼다. 목록으로 넣었으니 결과도 목록이라 [0] 으로 첫 개를 꺼낸다
q = model.encode([query], normalize_embeddings=True)[0]

# V 는 (200, 384), q 는 (384,) 다. 곱하면 (200,) — 상품마다 점수 하나씩 나온다.
# 200번 반복문을 도는 대신 한 줄로 끝난다
scores = V @ q

# argsort 는 "정렬했을 때의 순서(번호)"를 돌려준다. 작은 것부터라서
# [::-1] 로 뒤집어 큰 것부터로 만들고, [:3] 으로 위에서 셋만 가져온다
top = scores.argsort()[::-1][:3]

for i in top:
    pid, name, _ = rows[i]
    print(f"  {scores[i]:.4f}  {pid} {name}")

import time

started = time.time()
for _ in range(100):
    scores = V @ q           # 200개를 전부 훑는다
print(f"검색 한 번 {(time.time() - started) / 100 * 1000:.3f}ms")
