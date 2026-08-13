# sentence_transformers 안의 SentenceTransformer 를 꺼내 쓴다.
# 파일 이름은 밑줄(sentence_transformers), 설치 이름은 하이픈(sentence-transformers)이다.
# 헷갈리기 쉬운데 파이썬 세계의 흔한 규칙이다
from sentence_transformers import SentenceTransformer

# 괄호 안이 모델 이름이다. 인터넷에 공개된 모델의 주소라고 보면 된다.
#   intfloat              만든 곳
#   multilingual-e5-small 여러 나라 말을 다루는, e5 계열의 작은 모델
#
# 처음 실행하면 이 줄에서 모델을 받아온다 (약 470MB · 몇 분).
# 두 번째부터는 컴퓨터에 저장된 것을 쓰므로 몇 초면 된다
model = SentenceTransformer("intfloat/multilingual-e5-small")

# 이 모델이 문장 하나를 숫자 몇 개로 바꾸는지 물어본다
print("차원:", model.get_sentence_embedding_dimension())
