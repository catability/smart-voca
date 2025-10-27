from models.settings_model import SettingsModel
from models.word_model import WordModel
from models.statistics_model import StatisticsModel
from models.learning_model import LearningModel
from models.exam_model import ExamModel
from utils.logger import setup_logger
from typing import Dict, Any, Optional

# 2025-10-20 - 스마트 단어장 - 모든 컨트롤러의 기반 클래스
# 파일 위치: controllers/base_controller.py - v1
# 목적: 모든 모델 인스턴스를 관리하고, 뷰와 모델 간의 연결을 담당

LOGGER = setup_logger()

class BaseController:
    """
    모든 컨트롤러 클래스가 상속받는 기반 클래스입니다.
    애플리케이션의 핵심 모델 인스턴스들을 초기화하고 접근할 수 있도록 제공합니다.
    """
    
    def __init__(self):
        # 핵심 모델 인스턴스 초기화
        # SettingsModel은 최초 실행 시 DB 초기화 로직을 포함하므로 먼저 초기화합니다.
        self.settings_model: SettingsModel = SettingsModel()
        self.word_model: WordModel = WordModel()
        self.statistics_model: StatisticsModel = StatisticsModel()
        self.learning_model: LearningModel = LearningModel()
        self.exam_model: ExamModel = ExamModel()
        
        LOGGER.info("BaseController initialized and all core models instantiated.")

    # --- 공통 유틸리티 기능 (모든 컨트롤러가 사용할 수 있는) ---

    def get_current_settings(self) -> Dict[str, Any]:
        """
        현재 애플리케이션의 모든 설정값을 딕셔너리 형태로 반환합니다.
        """
        try:
            return self.settings_model.get_all_settings()
        except Exception as e:
            LOGGER.error(f"Failed to fetch current settings: {e}")
            # 설정값 로드 실패 시, 안전을 위해 빈 딕셔너리 반환 (또는 config.py의 기본값)
            return {}

    def get_setting_value(self, key: str) -> Optional[Any]:
        """
        특정 설정 키의 값을 반환합니다.
        """
        try:
            return self.settings_model.get_setting(key)
        except Exception as e:
            LOGGER.error(f"Failed to fetch setting key '{key}': {e}")
            return None

    def update_app_setting(self, key: str, value: Any) -> bool:
        """
        사용자 설정값을 업데이트하고 성공 여부를 반환합니다.
        """
        try:
            success = self.settings_model.update_setting(key, value)
            if success:
                LOGGER.info(f"Setting '{key}' updated to '{value}'.")
            return success
        except Exception as e:
            LOGGER.error(f"Failed to update setting '{key}': {e}")
            return False

    def close_all_db_connections(self):
        """
        애플리케이션 종료 전 모든 모델이 공유하는 DB 연결을 닫습니다.
        """
        # BaseModel에 의해 DBConnection은 Singleton이므로, 한 번만 닫으면 됩니다.
        self.settings_model.db.close()
        LOGGER.info("All shared DB connections closed.")