from typing import List, Dict, Any, Optional, Tuple
from models.base_model import BaseModel
from utils.logger import setup_logger
from datetime import datetime

# 2025-10-20 - 스마트 단어장 - 단어 데이터 모델
# 파일 위치: models/word_model.py - v1
# 목적: words 테이블 CRUD 및 단어 검색 기능 구현

LOGGER = setup_logger()

class WordModel(BaseModel):
    """
    'words' 테이블에 대한 데이터 접근 및 비즈니스 로직을 담당합니다.
    """
    TABLE_NAME = "words"
    PRIMARY_KEY = "word_id"
    # 데이터 설계서(1.2) 기반 모든 필드 정의
    FIELDS = [
        "word_id", "word_text", "meaning_ko", "category", 
        "memo", "is_favorite", "created_date", 
        "modified_date", "is_deleted"
    ]

    def __init__(self):
        super().__init__()

    # --- 단어 특화 Read 기능 ---

    def select_active_words(self) -> List[Dict[str, Any]]:
        """
        논리적으로 삭제되지 않은(is_deleted=0) 모든 단어를 반환합니다.
        """
        # created_date 순으로 정렬하여 최신 단어가 뒤에 오도록 함
        return self.select_all(where_clause="is_deleted = 0 ORDER BY created_date ASC")

    def select_by_category(self, category: str) -> List[Dict[str, Any]]:
        """
        특정 카테고리에 속하며 삭제되지 않은 단어 목록을 반환합니다.
        """
        where = "is_deleted = 0 AND category = ?"
        return self.select_all(where_clause=where, params=(category,))

    def select_favorites(self) -> List[Dict[str, Any]]:
        """
        즐겨찾기 된 단어(is_favorite=1) 목록을 반환합니다.
        """
        where = "is_deleted = 0 AND is_favorite = 1"
        return self.select_all(where_clause=where)

    def search_words(self, keyword: str, search_by: str = 'all') -> List[Dict[str, Any]]:
        """
        키워드로 단어(word_text)나 의미(meaning_ko)를 검색합니다.
        search_by: 'word_text', 'meaning_ko', 'all' 중 하나.
        """
        keyword_like = f"%{keyword}%"
        
        if search_by == 'word_text':
            where = "is_deleted = 0 AND word_text LIKE ?"
            params = (keyword_like,)
        elif search_by == 'meaning_ko':
            where = "is_deleted = 0 AND meaning_ko LIKE ?"
            params = (keyword_like,)
        else: # 'all'
            where = "is_deleted = 0 AND (word_text LIKE ? OR meaning_ko LIKE ?)"
            params = (keyword_like, keyword_like)

        return self.select_all(where_clause=where, params=params)

    # --- 단어 특화 Update 기능 ---

    def toggle_favorite(self, word_id: int, is_favorite: bool) -> bool:
        """
        단어의 즐겨찾기 상태를 토글합니다.
        """
        data = {"is_favorite": 1 if is_favorite else 0}
        return self.update(word_id, data)

    def hard_delete(self, word_id: int) -> bool:
        """
        단어를 물리적으로 완전히 삭제합니다. (주의: 일반적인 삭제는 논리 삭제를 권장)
        """
        return self.delete(word_id, logical_delete=False)
    
    # --- 데이터 일관성 검증 (선택적) ---
    
    def is_word_exist(self, word_text: str, exclude_id: Optional[int] = None) -> bool:
        """
        이미 존재하는 단어인지 확인합니다 (중복 검사).
        exclude_id가 있으면 해당 ID의 단어는 검사에서 제외합니다 (수정 시 사용).
        """
        sql = f"SELECT {self.PRIMARY_KEY} FROM {self.TABLE_NAME} WHERE word_text = ? AND is_deleted = 0"
        params: List[Any] = [word_text]
        
        if exclude_id is not None:
            sql += f" AND {self.PRIMARY_KEY} != ?"
            params.append(exclude_id)
        
        try:
            self.db.connect()
            result = self.db.fetchone(sql, tuple(params))
            return result is not None
        except Exception as e:
            LOGGER.error(f"Error checking word existence: {e}")
            return True # 오류 발생 시 보수적으로 True 반환
        finally:
            self.db.close()

    def get_word_by_text(self, word_text: str) -> Optional[Dict[str, Any]]:
        """
        단어 텍스트(word_text)를 기준으로 단어 정보를 조회합니다. 
        CSV 임포트 시 중복 단어 확인에 사용됩니다.
        """
        sql = f"SELECT * FROM {self.TABLE_NAME} WHERE word_text = ? AND is_deleted = 0"
        
        try:
            self.db.connect()
            result = self.db.fetchone(sql, (word_text,))
            # fetchone은 딕셔너리를 반환한다고 가정
            return result
        except Exception as e:
            LOGGER.error(f"Error fetching word by text '{word_text}': {e}")
            return None
        finally:
            self.db.close()

    def update_word_by_text(self, word_text: str, data: Dict[str, Any]) -> bool:
        """
        단어 텍스트(word_text)를 기준으로 단어 정보를 업데이트합니다.
        CSV 임포트 시 기존 단어 정보를 갱신하는 데 사용됩니다.
        """
        # updated_data에서 word_text는 제외하고, modified_date를 갱신합니다.
        updated_data = {k: v for k, v in data.items() if k not in ['word_id', 'word_text', 'created_date']}
        updated_data['modified_date'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # SQL 쿼리 구성
        set_clause = ", ".join([f"{key} = ?" for key in updated_data.keys()])
        sql = f"UPDATE {self.TABLE_NAME} SET {set_clause} WHERE word_text = ? AND is_deleted = 0"
        
        params = tuple(updated_data.values()) + (word_text,)

        try:
            self.db.connect()
            cursor = self.db.execute(sql, params)
            if cursor and cursor.rowcount > 0:
                self.db.commit()
                return True
            return False
        except Exception as e:
            LOGGER.error(f"Error updating word by text '{word_text}': {e}")
            self.db.rollback()
            return False
        finally:
            self.db.close()

    def insert_word(self, data: Dict[str, Any]) -> Optional[int]:
        """
        새로운 단어를 words 테이블에 삽입하고, 성공 시 새 word_id를 반환합니다.
        CSV 임포트 및 단어 추가 다이얼로그에서 사용됩니다.
        """
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # 삽입할 데이터 딕셔너리 구성 및 기본값 처리
        insert_data = {
            'word_text': data.get('word_text', '').strip(),
            'meaning_ko': data.get('meaning_ko', '').strip(),
            'category': data.get('category', '미분류').strip(),
            'memo': data.get('memo', '').strip(),
            'is_favorite': int(data.get('is_favorite', 0)),
            'created_date': now,
            'modified_date': now,
            'is_deleted': 0
        }

        # SQL 쿼리 구성
        columns = ', '.join(insert_data.keys())
        placeholders = ', '.join(['?' for _ in insert_data.keys()])
        sql = f"INSERT INTO {self.TABLE_NAME} ({columns}) VALUES ({placeholders})"
        params = tuple(insert_data.values())

        try:
            self.db.connect()
            cursor = self.db.execute(sql, params)
            if cursor:
                self.db.commit()
                return cursor.lastrowid # 삽입된 행의 ID 반환
            return None
        except Exception as e:
            LOGGER.error(f"Error inserting word: {e}")
            self.db.rollback()
            return None
        finally:
            self.db.close()