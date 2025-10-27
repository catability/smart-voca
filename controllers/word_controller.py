from typing import List, Dict, Any, Optional
from controllers.base_controller import BaseController
from utils.logger import setup_logger
from models.word_model import WordModel

# 2025-10-20 - 스마트 단어장 - 단어 관리 컨트롤러
# 파일 위치: controllers/word_controller.py - v1
# 목적: 단어 CRUD 및 조회, 검색, 즐겨찾기 관리 비즈니스 로직 구현

LOGGER = setup_logger()

class WordController(BaseController):
    """
    단어장(words 테이블)의 모든 사용자 인터페이스 로직을 처리합니다.
    """

    def __init__(self):
        super().__init__()
        # self.word_model은 BaseController에서 이미 초기화됨
        
    # --- 1. 단어 추가/수정/삭제 ---

    def add_word(self, word_text: str, meaning_ko: str, category: str, memo: Optional[str] = None) -> Optional[int]:
        """
        새 단어를 데이터베이스에 추가합니다. (F4 단어 편집)
        - 중복 단어 확인 후 추가를 진행합니다.
        """
        word_text = word_text.strip()
        meaning_ko = meaning_ko.strip()

        if self.word_model.is_word_exist(word_text):
            LOGGER.warning(f"Failed to add word: '{word_text}' already exists.")
            # 0은 중복 오류 코드로 가정하거나, 명시적인 오류 처리 필요 (Controller는 View에 오류 메시지를 전달해야 함)
            return 0 # 0을 중복 오류 코드로 사용
        
        data = {
            "word_text": word_text,
            "meaning_ko": meaning_ko,
            "category": category,
            "memo": memo if memo else "",
        }
        
        word_id = self.word_model.insert(data)
        if word_id:
            LOGGER.info(f"Word added successfully. ID: {word_id}")
            return word_id
        
        return None

    def update_word(self, word_id: int, word_text: str, meaning_ko: str, category: str, memo: Optional[str] = None) -> bool:
        """
        기존 단어 정보를 업데이트합니다. (F4 단어 편집)
        - word_id를 제외한 다른 단어와의 중복을 확인합니다.
        """
        word_text = word_text.strip()
        meaning_ko = meaning_ko.strip()
        
        if self.word_model.is_word_exist(word_text, exclude_id=word_id):
            LOGGER.warning(f"Failed to update word ID {word_id}: '{word_text}' already exists in another record.")
            return False
            
        data = {
            "word_text": word_text,
            "meaning_ko": meaning_ko,
            "category": category,
            "memo": memo if memo else "",
        }
        
        success = self.word_model.update(word_id, data)
        if success:
            LOGGER.info(f"Word updated successfully. ID: {word_id}")
        return success
        
    def delete_word(self, word_id: int) -> bool:
        """
        단어를 논리적으로 삭제합니다 (is_deleted = 1). (F4 단어 편집)
        """
        success = self.word_model.delete(word_id, logical_delete=True)
        if success:
            LOGGER.info(f"Word logically deleted. ID: {word_id}")
        return success

    # --- 2. 단어 조회 및 검색 ---

    def get_all_active_words(self) -> List[Dict[str, Any]]:
        """
        삭제되지 않은 전체 단어 목록을 반환합니다. (F3 단어 목록 조회)
        """
        return self.word_model.select_active_words()
        
    def get_word_by_id(self, word_id: int) -> Optional[Dict[str, Any]]:
        """
        특정 ID의 단어 정보를 반환합니다.
        """
        return self.word_model.select_by_id(word_id)

    def search_words(self, keyword: str, search_by: str = 'all') -> List[Dict[str, Any]]:
        """
        키워드로 단어를 검색합니다. (F3 단어 목록 조회)
        """
        if not keyword.strip():
            return self.get_all_active_words() # 키워드가 없으면 전체 목록 반환
            
        return self.word_model.search_words(keyword, search_by)
        
    def get_words_by_category(self, category: str) -> List[Dict[str, Any]]:
        """
        특정 카테고리에 속한 단어 목록을 반환합니다.
        """
        return self.word_model.select_by_category(category)

    # --- 3. 즐겨찾기 및 상태 관리 ---

    def toggle_word_favorite(self, word_id: int, is_favorite: bool) -> bool:
        """
        단어의 즐겨찾기 상태를 변경합니다. (F16 즐겨찾기 기능)
        """
        success = self.word_model.toggle_favorite(word_id, is_favorite)
        if success:
            LOGGER.info(f"Word ID {word_id} favorite status toggled to {is_favorite}.")
        return success
        
    def get_favorite_words(self) -> List[Dict[str, Any]]:
        """
        즐겨찾기 된 단어 목록을 반환합니다.
        """
        return self.word_model.select_favorites()

    def get_all_categories(self) -> List[str]:
        """
        현재 DB에 저장된 모든 단어의 고유 카테고리 목록을 반환합니다. (F6 카테고리 관리)
        """
        sql = "SELECT DISTINCT category FROM words WHERE is_deleted = 0 ORDER BY category ASC"
        
        try:
            self.word_model.db.connect()
            rows = self.word_model.db.fetchall(sql)
            return [row['category'] for row in rows]
        except Exception as e:
            LOGGER.error(f"Failed to fetch all categories: {e}")
            return []
        finally:
            self.word_model.db.close()