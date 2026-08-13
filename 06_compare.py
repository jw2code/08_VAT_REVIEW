import numpy as np
from sentence_transformers import SentenceTransformer

model = SentenceTransformer("intfloat/multilingual-e5-small")

texts = [
    "건조한 피부에 순한 토너",
    "속당김 잡아주는 수분 화장수",     # 위와 겹치는 낱말이 하나도 없다
    "지성 피부용 산뜻한 클렌징폼",
    "오늘 점심 뭐 먹지",
]

# 목록을 통째로 넣으면 한 번에 다 바꿔준다. 하나씩 넣는 것보다 빠르다.
# normalize_embeddings=True 는 "모든 벡터의 길이를 1로 맞춰라" 는 뜻이다.
# 길이를 맞춰두면 두 벡터를 곱하는 것만으로 비슷한 정도가 나온다 (아래에서 씀)
E = model.encode(texts, normalize_embeddings=True)

print("모양:", E.shape)      # (4, 384) = 문장 4개 x 숫자 384개

# @ 는 파이썬의 "행렬 곱하기" 기호다. 길이를 1로 맞춰둔 벡터끼리 곱하면
# 결과가 -1 ~ 1 사이 값이 되고, 1에 가까울수록 뜻이 가깝다.
# 이걸 코사인 유사도라고 부른다
# 첫 문장(E[0])을 기준으로 나머지와 하나씩 비교한다.
# range(1, 4) 는 1, 2, 3 이다 — 0번(기준 문장)은 자기 자신이라 건너뛴다.
#
# 결과는 **문장을 적은 순서대로** 찍힌다. 점수 순이 아니다
for i in range(1, len(texts)):
    score = E[0] @ E[i]
    print(f"  {score:.4f}  {texts[i]}")
