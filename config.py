import os
from logging import DEBUG, INFO, WARNING, ERROR

# 2025-10-20 - 스마트 단어장 - 전역 설정 및 상수 정의
# 파일 위치: config.py - v1

# 프로젝트 루트 디렉토리를 기준으로 경로를 설정합니다.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# === 1. 경로 설정 (Path Settings) ===

# 데이터베이스 파일 경로 (database/smart_vocab.db)
DB_DIR = os.path.join(BASE_DIR, 'database')
DB_NAME = 'smart_vocab.db'
DATABASE_PATH = os.path.join(DB_DIR, DB_NAME)

# 로그 파일 경로 (logs/app.log)
LOG_DIR = os.path.join(BASE_DIR, 'logs')
LOG_FILE_NAME = 'app.log'
LOG_FILE_PATH = os.path.join(LOG_DIR, LOG_FILE_NAME)


# === 2. 로깅 설정 (Logging Settings) ===

# 로그 레벨: 개발 단계는 DEBUG, 배포 시는 INFO를 기본으로 합니다.
LOG_LEVEL_DEV = DEBUG
LOG_LEVEL_PROD = INFO
LOG_MAX_BYTES = 10 * 1024 * 1024  # 10MB
LOG_BACKUP_COUNT = 3              # 최대 3개 백업 파일 유지


# === 3. 기본 설정값 (Default App Settings) ===
# SettingsModel에서 초기 데이터로 사용됩니다.
DEFAULT_SETTINGS = {
    'theme_mode': 'light',        # 'light' 또는 'dark'
    'default_quiz_count': 10,     # 기본 퀴즈 문항 수
    'review_interval_days': 3,    # 기본 복습 주기
    'max_memo_length': 200,       # 메모 최대 길이
    'language_pair': 'en-ko',     # 'en-ko' 또는 'ko-en'
}

# === 4. UI 및 테마 상수 (UI and Theme Constants) ===

# UI 스타일 관리를 위한 테마 색상 정의 (QSS 적용 시 활용 가능)
THEME_COLORS = {
    'light': {
        'background': '#F0F0F0',
        'text': '#333333',
        'primary': '#007BFF',   # 주 색상: 파란색
        'success': '#28A745',   # 성공 색상: 녹색
    },
    'dark': {
        'background': '#333333',
        'text': '#F0F0F0',
        'primary': '#1E90FF',   # 주 색상: 다저 블루
        'success': '#3CB371',   # 성공 색상: 중간 바다 녹색
    }
}

DEFAULT_FONT_FAMILY = 'Arial'
DEFAULT_FONT_SIZE = 10