from pathlib import Path

# c:\jw_project2 (프로젝트 루트 경로)
BASE_DIR = Path(__file__).resolve().parent.parent

# CSV 파일 폴더 경로 (c:\jw_project2\data)
DATA_DIR = BASE_DIR / "data"

# SQLite DB 파일 경로 (c:\jw_project2\test.db)
DB_PATH = BASE_DIR / "test.db"