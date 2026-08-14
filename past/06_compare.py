import numpy as np
from sentence_transformers import SentenceTransformer

model = SentenceTransformer("intfloat/multilingual-e5-small")

texts = [
    "query: 대표이사 업무용 2,000cc 승용차 주유비의 매입세액 공제 여부",
    "passage: 비영업용 소형승용자동차의 구입·임차·유지에 관한 매입세액은 공제하지 않는다.",
    "passage: 생산라인에 직접 투입되는 원재료 매입세액은 과세사업 관련 매입으로 공제할 수 있다.",
    "passage: 오늘 점심 메뉴를 무엇으로 정할지 고민하고 있다.",
]

# 목록을 통째로 넣으면 한 번에 다 바꿔준다. 하나씩 넣는 것보다 빠르다.
# normalize_embeddings=True 는 "모든 벡터의 길이를 1로 맞춰라" 는 뜻이다.
E = model.encode(texts, normalize_embeddings=True)

print("모양:", E.shape)      # (4, 384) = 문장 4개 x 숫자 384개

# 첫 문장을 기준으로 나머지와 하나씩 비교한다.
# 결과는 문장을 적은 순서대로 찍힌다. 점수 순이 아니다.
for i in range(1, len(texts)):
    score = E[0] @ E[i]
    print(f"  {score:.4f}  {texts[i]}")
