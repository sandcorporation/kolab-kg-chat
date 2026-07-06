"""테스트는 항상 결정적 mock source-db(4개 fixture)를 쓴다.

dev 서버가 real-source-db(628k)를 서빙하도록 SOURCE_DB_*를 바꿔도, 테스트는 여기서
mock으로 고정해 결정성을 지킨다(C: from_env가 컨테이너 env를 읽으므로 서버와 분리 필요).
"""
import os

os.environ["SOURCE_DB_HOST"] = "source-db"
os.environ["SOURCE_DB_PORT"] = "3306"
os.environ["SOURCE_DB_USER"] = "kolab"
os.environ["SOURCE_DB_PASSWORD"] = "kolab"
os.environ["SOURCE_DB_NAME"] = "kolabshop"
