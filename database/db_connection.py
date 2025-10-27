import sqlite3
import os
import threading
from typing import List, Tuple, Any, Optional

# 2025-10-20 - 스마트 단어장 - 데이터베이스 연결 모듈
# 파일 위치: database/db_connection.py - v1
# 목적: SQLite3 연결 관리 및 Singleton 패턴 적용

from config import DATABASE_PATH, DB_DIR
from utils.logger import setup_logger

LOGGER = setup_logger()

class DBConnection:
    """
    SQLite3 데이터베이스 연결을 관리하는 Singleton 클래스입니다.
    데이터베이스 초기화(파일 및 디렉토리 생성) 기능을 포함합니다.
    """
    _instance: Optional['DBConnection'] = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        """
        Singleton 패턴 구현: 인스턴스가 없으면 새로 생성하고, 있으면 기존 인스턴스를 반환합니다.
        """
        if cls._instance is None:
            with cls._lock:
                # 락을 잡고 다시 한번 확인 (멀티스레딩 환경 대비)
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False # 초기화 플래그
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self._conn: Optional[sqlite3.Connection] = None
        self._cursor: Optional[sqlite3.Cursor] = None
        self._initialized = True
        
        # DB 디렉토리가 없으면 생성
        if not os.path.exists(DB_DIR):
            os.makedirs(DB_DIR)
            LOGGER.info(f"Database directory created: {DB_DIR}")

    def connect(self):
        """
        데이터베이스에 연결하고 커서를 설정합니다.
        """
        if self._conn is None:
            try:
                self._conn = sqlite3.connect(DATABASE_PATH)
                self._conn.row_factory = sqlite3.Row  # 컬럼 이름으로 결과에 접근 가능하도록 설정
                self._cursor = self._conn.cursor()
                LOGGER.info(f"Database connected successfully to {DATABASE_PATH}")
            except sqlite3.Error as e:
                LOGGER.error(f"Database connection error: {e}")
                # 연결 실패 시 None으로 유지
                self._conn = None
                self._cursor = None
                raise e

    def close(self):
        """
        데이터베이스 연결을 닫습니다.
        """
        if self._conn:
            self._conn.close()
            self._conn = None
            self._cursor = None
            LOGGER.info("Database connection closed.")

    def commit(self):
        """
        현재 트랜잭션을 커밋합니다.
        """
        if self._conn:
            self._conn.commit()
        else:
            LOGGER.warning("Attempted to commit, but no active database connection.")

    def execute(self, sql: str, params: Tuple[Any, ...] = ()) -> Optional[sqlite3.Cursor]:
        """
        SQL 쿼리를 실행합니다.
        """
        if not self._conn:
            LOGGER.error("Execute failed: No active database connection.")
            return None
            
        try:
            self._cursor.execute(sql, params)
            return self._cursor
        except sqlite3.Error as e:
            LOGGER.error(f"SQL execution error on query: '{sql}' with params {params}. Error: {e}")
            # DML (INSERT, UPDATE, DELETE) 오류 시 롤백
            if self._conn:
                self._conn.rollback() 
            return None

    # 새로 추가된 메서드 (다중 구문용)
    def executescripts(self, sql_script: str) -> bool:
        """
        세미콜론으로 구분된 여러 SQL 구문이 포함된 스크립트를 실행합니다. (스키마 초기화용)
        """
        if not self._conn:
            LOGGER.error("ExecuteScripts failed: No active database connection.")
            return False
        
        try:
            # Connection 객체의 executescript 메서드 사용 (커서 아님)
            self._conn.executescript(sql_script) 
            self._conn.commit()
            return True
        except sqlite3.Error as e:
            LOGGER.error(f"SQL script execution error. Error: {e}")
            self._conn.rollback()
            return False

    def fetchall(self, sql: str, params: Tuple[Any, ...] = ()) -> List[sqlite3.Row]:
        """
        SELECT 쿼리를 실행하고 모든 결과를 반환합니다.
        """
        cursor = self.execute(sql, params)
        if cursor:
            return cursor.fetchall()
        return []

    def fetchone(self, sql: str, params: Tuple[Any, ...] = ()) -> Optional[sqlite3.Row]:
        """
        SELECT 쿼리를 실행하고 하나의 결과만 반환합니다.
        """
        cursor = self.execute(sql, params)
        if cursor:
            return cursor.fetchone()
        return None

# # 사용 예시 (테스트 용도)
# if __name__ == '__main__':
#     db = DBConnection()
#     try:
#         db.connect()
#         # 테이블 생성 예시 (실제 구현은 다음 단계에서)
#         db.execute("CREATE TABLE IF NOT EXISTS test_table (id INTEGER PRIMARY KEY, name TEXT)")
#         db.commit()
#         LOGGER.info("Test table checked/created.")
#     except Exception as e:
#         LOGGER.error(f"Initial test failed: {e}")
#     finally:
#         db.close()