from typing import Dict, Any, Optional
from models.base_model import BaseModel
from utils.logger import setup_logger
from datetime import datetime
from config import DEFAULT_SETTINGS # config.py에서 기본 설정값 가져오기
import json

# 2025-10-20 - 스마트 단어장 - 사용자 설정 데이터 모델
# 파일 위치: models/settings_model.py - v1
# 목적: user_settings 테이블 CRUD 및 초기화 기능 구현

LOGGER = setup_logger()

class SettingsModel(BaseModel):
    """
    'user_settings' 테이블에 대한 데이터 접근 및 설정 관리를 담당합니다.
    """
    TABLE_NAME = "user_settings"
    PRIMARY_KEY = "setting_key"
    FIELDS = [
        "setting_key", "setting_value", "setting_type", 
        "description", "modified_date"
    ]

    def __init__(self):
        super().__init__()
        # 인스턴스 생성 시점에 DB를 확인하고 필요하면 초기화 스크립트를 실행합니다.
        self._initialize_settings()

    # --- 1. 초기화 기능 ---

    def _initialize_settings(self):
        """
        user_settings 테이블에 설정값이 없으면 config.py의 기본값으로 초기값을 삽입합니다.
        """
        try:
            current_settings = self.get_all_settings()
            
            # DB에 설정이 하나도 없거나 (최초 실행)
            # config.py의 기본 설정 중 DB에 누락된 항목이 있을 경우 초기화
            if not current_settings or len(current_settings) < len(DEFAULT_SETTINGS):
                LOGGER.info("User settings table empty or incomplete. Initializing default settings from config.py.")
                
                # config.py의 모든 기본값을 확인하며 누락된 값만 삽입
                for key, value in DEFAULT_SETTINGS.items():
                    if key not in current_settings:
                        # 2. user_settings 테이블에 삽입
                        data = {
                            "setting_key": key,
                            "setting_value": str(value), # 모든 값은 문자열로 저장
                            "setting_type": type(value).__name__,
                            "description": f"Default setting for {key}", # 초기 설명
                            "modified_date": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        }
                        # 트랜잭션 없이 BaseModel의 insert를 통해 개별 삽입
                        self.insert(data)
                        
                LOGGER.info("Default settings initialization complete.")

        except Exception as e:
            LOGGER.error(f"Failed to initialize default settings: {e}")
            # 이 시점에서 DB 연결이 불가능하면 애플리케이션 실행 불가

    # --- 2. 설정 읽기/쓰기 ---

    def get_setting(self, key: str) -> Optional[Any]:
        """
        특정 설정 키의 값을 반환합니다. 값은 저장된 타입으로 변환됩니다.
        """
        setting_data = self.select_by_id(key)
        if setting_data:
            value = setting_data['setting_value']
            # 저장된 setting_type에 따라 적절하게 타입 변환
            setting_type = setting_data.get('setting_type', 'string')
            
            if setting_type == 'integer':
                return int(value)
            elif setting_type == 'float':
                return float(value)
            elif setting_type == 'boolean':
                return value.lower() in ('true', '1')
            return value
        
        # DB에 없을 경우 config.py의 기본값을 확인하여 반환 (안정성 강화)
        default_value = DEFAULT_SETTINGS.get(key)
        if default_value is not None:
             LOGGER.warning(f"Setting key '{key}' not found in DB. Returning default value from config.py.")
             return default_value

        LOGGER.warning(f"Setting key '{key}' not found in DB or config.py defaults.")
        return None

    def get_all_settings(self) -> Dict[str, Any]:
        """
        모든 설정 키-값 쌍을 딕셔너리 형태로 반환합니다.
        """
        all_rows = self.select_all()
        settings = {}
        for row in all_rows:
            key = row['setting_key']
            value = self.get_setting(key) # 타입 변환된 값 사용
            if value is not None:
                settings[key] = value
        return settings

    def update_setting(self, key: str, value: Any) -> bool:
        """
        특정 설정 키의 값을 업데이트합니다.
        """
        data = {
            "setting_value": str(value),
            "setting_type": type(value).__name__,
            "modified_date": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        return self.update(key, data)

    def is_dark_mode(self) -> bool:
        """
        현재 테마 모드가 'dark'인지 확인하는 편의 함수.
        """
        return self.get_setting('theme_mode') == 'dark'