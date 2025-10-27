import logging
import os
from logging.handlers import RotatingFileHandler
from config import LOG_FILE_PATH, LOG_LEVEL_DEV, LOG_MAX_BYTES, LOG_BACKUP_COUNT, LOG_DIR
from datetime import datetime

# 2025-10-20 - 스마트 단어장 - 로깅 시스템 설정 모듈
# 파일 위치: utils/logger.py - v1

def setup_logger(log_level=LOG_LEVEL_DEV):
    """
    애플리케이션의 로거를 설정하고 반환합니다.
    (파일 핸들러와 콘솔 핸들러 포함)
    """
    # 1. 로그 디렉토리 생성 (없으면)
    os.makedirs(LOG_DIR, exist_ok=True)
    
    # 2. 로거 인스턴스 생성
    logger = logging.getLogger('SmartVocabLogger')
    logger.setLevel(log_level)
    
    # 중복 핸들러 방지
    if logger.handlers:
        return logger

    # 3. 로그 포맷 정의
    formatter = logging.Formatter(
        '[%(asctime)s] - %(levelname)s - %(filename)s:%(lineno)d - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # 4. 파일 핸들러 (로깅 파일 관리)
    file_handler = RotatingFileHandler(
        LOG_FILE_PATH,
        maxBytes=LOG_MAX_BYTES,  # 10MB
        backupCount=LOG_BACKUP_COUNT,  # 3개 백업
        encoding='utf-8'
    )
    file_handler.setFormatter(formatter)
    
    # 5. 콘솔 핸들러 (개발 중 실시간 확인)
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)

    # 6. 로거에 핸들러 추가
    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)
    
    logger.info(f"Logger initialized successfully. Log file: {LOG_FILE_PATH}")
    
    return logger

# 초기 테스트 용도로 모듈 임포트 시 로거를 바로 설정할 수 있습니다.
# LOGGER = setup_logger()