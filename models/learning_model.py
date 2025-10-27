from typing import List, Dict, Any, Optional, Tuple
from models.base_model import BaseModel
from utils.logger import setup_logger
from datetime import datetime, timedelta

# 2025-10-20 - 스마트 단어장 - 학습 이력 데이터 모델
# 파일 위치: models/learning_model.py - v1
# 목적: learning_sessions 및 learning_history 테이블 CRUD 및 통계 조회 기능 구현

LOGGER = setup_logger()

# 학습 세션 테이블
class LearningSessionModel(BaseModel):
    TABLE_NAME = "learning_sessions"
    PRIMARY_KEY = "session_id"
    FIELDS = [
        "session_id", "session_type", "session_mode", "start_time", 
        "end_time", "total_words", "correct_count", 
        "wrong_count", "is_completed"
    ]

    def __init__(self):
        super().__init__()

# 학습 이력 테이블
class LearningHistoryModel(BaseModel):
    TABLE_NAME = "learning_history"
    PRIMARY_KEY = "history_id"
    FIELDS = [
        "history_id", "session_id", "word_id", "is_correct", 
        "response_time", "learning_date"
    ]

    def __init__(self):
        super().__init__()

# 통합 학습 모델 (Controller가 주로 사용할 기능 포함)
class LearningModel:
    """
    학습 세션과 이력 두 테이블을 통합 관리하고 학습 관련 통계를 제공하는 모델입니다.
    """
    def __init__(self):
        self.session_model = LearningSessionModel()
        self.history_model = LearningHistoryModel()
        self.db = self.session_model.db  # BaseModel에서 연결을 가져와 사용

    # --- 1. 세션 관리 ---

    def start_session(self, session_type: str, session_mode: str, total_words: int) -> Optional[int]:
        """
        새로운 학습 세션을 시작하고, 생성된 session_id를 반환합니다.
        """
        data = {
            "session_type": session_type,
            "session_mode": session_mode,
            "start_time": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "total_words": total_words,
            "is_completed": 0 # 시작 시 미완료 상태
        }
        # LearningSessionModel의 insert 메서드를 사용하여 세션 생성
        return self.session_model.insert(data)

    def end_session(self, session_id: int, correct_count: int, wrong_count: int) -> bool:
        """
        학습 세션을 종료하고 결과 및 종료 시간을 업데이트합니다.
        """
        data = {
            "end_time": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "correct_count": correct_count,
            "wrong_count": wrong_count,
            "is_completed": 1 # 완료 상태
        }
        return self.session_model.update(session_id, data)

    # --- 2. 이력 관리 ---

    def add_history(self, session_id: int, word_id: int, is_correct: bool, response_time: float) -> Optional[int]:
        """
        단어 하나에 대한 학습 이력을 기록합니다.
        """
        data = {
            "session_id": session_id,
            "word_id": word_id,
            "is_correct": 1 if is_correct else 0,
            "response_time": response_time,
            "learning_date": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        # LearningHistoryModel의 insert 메서드를 사용하여 이력 기록
        return self.history_model.insert(data)

    # --- 3. 통계 조회 ---
    
    def get_total_learning_time_today(self) -> float:
        """
        오늘 완료된 세션들의 총 학습 시간(분)을 반환합니다.
        """
        today_start = datetime.now().strftime('%Y-%m-%d 00:00:00')
        
        sql = """
            SELECT SUM(JULIANDAY(end_time) - JULIANDAY(start_time)) * 24 * 60 AS total_minutes
            FROM learning_sessions
            WHERE is_completed = 1 AND start_time >= ?
        """
        
        try:
            self.db.connect()
            row = self.db.fetchone(sql, (today_start,))
            if row and row['total_minutes'] is not None:
                return round(row['total_minutes'], 1)
            return 0.0
        except Exception as e:
            LOGGER.error(f"Failed to calculate total learning time today. Error: {e}")
            return 0.0
        finally:
            self.db.close()
            
    def get_daily_correct_rate(self, days: int = 7) -> List[Dict[str, Any]]:
        """
        최근 days일간의 일별 정답률을 계산하여 반환합니다. (통계 차트용)
        """
        start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d 00:00:00')
        
        sql = """
            SELECT 
                strftime('%Y-%m-%d', start_time) as learning_day,
                SUM(correct_count) AS total_correct,
                SUM(wrong_count) AS total_wrong
            FROM learning_sessions
            WHERE is_completed = 1 AND start_time >= ?
            GROUP BY learning_day
            ORDER BY learning_day ASC
        """
        
        try:
            self.db.connect()
            rows = self.db.fetchall(sql, (start_date,))
            result = []
            
            for row in rows:
                total_attempts = row['total_correct'] + row['total_wrong']
                correct_rate = 0.0
                if total_attempts > 0:
                    correct_rate = round((row['total_correct'] / total_attempts) * 100, 1)
                    
                result.append({
                    'date': row['learning_day'],
                    'correct_rate': correct_rate,
                    'total_attempts': total_attempts
                })
            return result
        except Exception as e:
            LOGGER.error(f"Failed to get daily correct rate. Error: {e}")
            return []
        finally:
            self.db.close()