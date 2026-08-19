from pathlib import Path

# c:\jw_project2 (프로젝트 루트 경로)
BASE_DIR = Path(__file__).resolve().parent.parent

# ROOT경로에서 하위 data폴더 경로를 이어 붙여 csv  파일이 있는 절대 경로값 변수에 저장
DATA_DIR = ROOT / "data"

# 테이블이 저장될 DB파일명과 위치를 변수에 등록
# cosmetic.db란 이름으로 db파일을 루트 경로안쪾에 생성하고 문자열로 변환해서 변수 등록
# SQLite DB 파일 경로 (c:\jw_project2\test.db)
DB_PATH = str(ROOT / "comestic.db")


# 랭체인 설치
# python -m pip install langchain-text-splitters==1.1.2 transformers==5.14.1
# python -m pip install langchain-huggingface==1.2.2

# langchain-text-spitters : 글을 자르는 도구
# transformers : 토큰을 세는 도구
# langchain-huggingface : sectance-transformers, torch(PyTorch)같이 딸려옴

# torch(PyTorch)는 백터라이징에 필요한 행렬 계산을 해주는 엔진 : 해당 엔진위에서 임베딩, LLM모델이 구동
# sentance-transformer 기반으로 더 간단하게 청킹등의 작업을 처리해주는 편의기능

# langchain 개념
# AI 서비스 개발을 하기 위한, 청킨, 임베딩, LLM요청, 응답, 검증 등의 일괄적인 전체 프로세스를 표준화하기 위한 도구
# 만약 langchain이 없으면 로컬에서 허깅페이스 버전으로 만들었을 때 다른 사용 API버전으로 변경 시 모든 코드 구조를 일일이 변경해야 하는 번거로움 있음
# 이때 langchain을 쓰면 어떤 AI, 모델을 쓰더라도 표준 메서드명으로 통일해서 동작되는 표준규격 어댑터 제공