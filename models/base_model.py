from typing import List, Dict, Any, Optional, Tuple
from database.db_connection import DBConnection
from utils.logger import setup_logger
from datetime import datetime

# 2025-10-20 - 스마트 단어장 - 모든 모델의 기반 클래스
# 파일 위치: models/base_model.py - v1
# 목적: 공통 CRUD 기능 및 DB 연결 추상화

LOGGER = setup_logger()

class BaseModel:
    """
    모든 데이터 모델 클래스가 상속받는 기반 클래스입니다.
    데이터베이스 연결 관리 및 기본적인 CRUD 메서드를 제공합니다.
    """
    
    # 상속받는 클래스에서 반드시 재정의해야 하는 클래스 변수
    TABLE_NAME: str = ""
    PRIMARY_KEY: str = ""
    FIELDS: List[str] = []

    def __init__(self):
        # 모든 모델은 Singleton DBConnection 인스턴스를 사용합니다.
        self.db = DBConnection()
        if not self.TABLE_NAME or not self.PRIMARY_KEY:
             LOGGER.error(f"BaseModel initialization error: TABLE_NAME or PRIMARY_KEY not set in {self.__class__.__name__}")
             # 이 오류는 개발 단계에서 바로 잡아야 하므로 raise
             raise NotImplementedError("TABLE_NAME and PRIMARY_KEY must be defined in the derived class.")
        
        # 필드 목록에서 PK를 제외한 나머지 필드
        self.NON_PK_FIELDS = [f for f in self.FIELDS if f != self.PRIMARY_KEY]

    # --- 1. CRUD - Create ---
    def insert(self, data: Dict[str, Any]) -> Optional[int]:
        """
        새 레코드를 삽입하고 삽입된 레코드의 PRIMARY KEY(rowid)를 반환합니다.
        """
        # 생성 및 수정 날짜 자동 삽입
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        if 'created_date' in self.FIELDS and 'created_date' not in data:
            data['created_date'] = now
        if 'modified_date' in self.FIELDS and 'modified_date' not in data:
            data['modified_date'] = now
            
        columns = ', '.join(data.keys())
        placeholders = ', '.join(['?' for _ in data])
        values = tuple(data.values())
        
        sql = f"INSERT INTO {self.TABLE_NAME} ({columns}) VALUES ({placeholders})"
        
        try:
            self.db.connect()
            cursor = self.db.execute(sql, values)
            
            if cursor:
                # SQLite3는 rowid 또는 lastrowid를 통해 마지막 삽입된 ID를 반환
                last_id = cursor.lastrowid
                self.db.commit()
                LOGGER.info(f"Inserted into {self.TABLE_NAME}. ID: {last_id}")
                return last_id
        except Exception as e:
            LOGGER.error(f"Failed to insert into {self.TABLE_NAME}. Error: {e}")
            self.db.close() # 실패 시 연결 닫기
            return None
        finally:
            self.db.close()
        return None

    # --- 2. CRUD - Read ---
    def select_all(self, where_clause: str = "1=1", params: Tuple[Any, ...] = ()) -> List[Dict[str, Any]]:
        """
        WHERE 절 조건에 맞는 모든 레코드를 리스트(딕셔너리 형태)로 반환합니다.
        """
        sql = f"SELECT * FROM {self.TABLE_NAME} WHERE {where_clause}"
        
        try:
            self.db.connect()
            rows = self.db.fetchall(sql, params)
            # sqlite3.Row 객체를 dict로 변환
            result = [dict(row) for row in rows] 
            return result
        except Exception as e:
            LOGGER.error(f"Failed to select all from {self.TABLE_NAME}. Error: {e}")
            return []
        finally:
            self.db.close()

    def select_by_id(self, pk_value: Any) -> Optional[Dict[str, Any]]:
        """
        PRIMARY KEY 값으로 하나의 레코드를 딕셔너리 형태로 반환합니다.
        """
        sql = f"SELECT * FROM {self.TABLE_NAME} WHERE {self.PRIMARY_KEY} = ?"
        
        try:
            self.db.connect()
            row = self.db.fetchone(sql, (pk_value,))
            if row:
                return dict(row)
            return None
        except Exception as e:
            LOGGER.error(f"Failed to select by PK from {self.TABLE_NAME}. Error: {e}")
            return None
        finally:
            self.db.close()


    # --- 3. CRUD - Update ---
    def update(self, pk_value: Any, data: Dict[str, Any]) -> bool:
        """
        PRIMARY KEY 값으로 레코드를 찾아 업데이트합니다.
        업데이트 성공 여부를 반환합니다.
        """
        if not data:
            return False

        # 수정 날짜 자동 업데이트
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        if 'modified_date' in self.FIELDS and 'modified_date' not in data:
            data['modified_date'] = now
            
        set_clauses = [f"{col} = ?" for col in data.keys()]
        set_sql = ', '.join(set_clauses)
        
        values = tuple(data.values()) + (pk_value,)
        
        sql = f"UPDATE {self.TABLE_NAME} SET {set_sql} WHERE {self.PRIMARY_KEY} = ?"
        
        try:
            self.db.connect()
            cursor = self.db.execute(sql, values)
            
            if cursor and cursor.rowcount > 0:
                self.db.commit()
                LOGGER.info(f"Updated {self.TABLE_NAME} ID: {pk_value}. Rows affected: {cursor.rowcount}")
                return True
            else:
                LOGGER.warning(f"Update on {self.TABLE_NAME} ID: {pk_value} failed or no rows affected.")
                return False
        except Exception as e:
            LOGGER.error(f"Failed to update {self.TABLE_NAME} ID: {pk_value}. Error: {e}")
            self.db.close()
            return False
        finally:
            self.db.close()


    # --- 4. CRUD - Delete (논리 삭제 지원) ---
    def delete(self, pk_value: Any, logical_delete: bool = True) -> bool:
        """
        PRIMARY KEY 값으로 레코드를 삭제합니다.
        logical_delete=True이면 is_deleted=1로 업데이트(논리 삭제), False이면 실제 삭제(물리 삭제).
        """
        try:
            self.db.connect()
            if logical_delete and 'is_deleted' in self.FIELDS:
                # 논리 삭제
                sql = f"UPDATE {self.TABLE_NAME} SET is_deleted = 1, modified_date = ? WHERE {self.PRIMARY_KEY} = ?"
                values = (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), pk_value)
                delete_type = "Logical Delete"
            else:
                # 물리 삭제
                sql = f"DELETE FROM {self.TABLE_NAME} WHERE {self.PRIMARY_KEY} = ?"
                values = (pk_value,)
                delete_type = "Physical Delete"

            cursor = self.db.execute(sql, values)

            if cursor and cursor.rowcount > 0:
                self.db.commit()
                LOGGER.info(f"{delete_type} on {self.TABLE_NAME} ID: {pk_value} successful.")
                return True
            else:
                LOGGER.warning(f"{delete_type} on {self.TABLE_NAME} ID: {pk_value} failed or no rows affected.")
                return False
        except Exception as e:
            LOGGER.error(f"Failed to delete {self.TABLE_NAME} ID: {pk_value}. Error: {e}")
            self.db.close()
            return False
        finally:
            self.db.close()