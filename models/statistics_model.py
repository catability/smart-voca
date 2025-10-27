from typing import Dict, Any, Optional, Tuple, List
from models.base_model import BaseModel
from utils.logger import setup_logger
from datetime import datetime, timedelta

# 2025-10-20 - 스마트 단어장 - 단어 통계 데이터 모델
# 파일 위치: models/statistics_model.py - v1
# 목적: word_statistics 테이블 CRUD 및 학습 통계/SRS 로직 구현

LOGGER = setup_logger()

# === 간격 반복 학습 (Spaced Repetition System, SRS) 설정 ===
# Mastery Level (숙련도 레벨)에 따른 다음 복습 간격 (일)
# 레벨 0: 학습 시작 전
# 레벨 1: 1일 후
# 레벨 2: 3일 후
# 레벨 3: 7일 후
# 레벨 4: 14일 후
# 레벨 5: 30일 후 (마스터)
SRS_INTERVALS = {
    0: 1,
    1: 3,
    2: 7,
    3: 14,
    4: 30,
    5: 365, # 마스터 레벨은 1년 후 재확인
}
MAX_MASTERY_LEVEL = 5

class StatisticsModel(BaseModel):
    """
    'word_statistics' 테이블에 대한 데이터 접근 및 통계 업데이트를 담당합니다.
    """
    TABLE_NAME = "word_statistics"
    PRIMARY_KEY = "stats_id"
    FIELDS = [
        "stats_id", "word_id", "total_attempts", "correct_count", 
        "last_review", "next_review", "mastery_level"
    ]

    def __init__(self):
        super().__init__()

    # --- 내부 SRS 로직 ---

    def _calculate_next_review(self, current_level: int, is_correct: bool) -> Tuple[int, str]:
        """
        정답/오답 여부에 따라 숙련도 레벨을 업데이트하고 다음 복습일을 계산합니다.
        """
        # 1. 숙련도 레벨 변경
        if is_correct:
            # 정답: 레벨 1 증가 (최대 MAX_MASTERY_LEVEL)
            new_level = min(current_level + 1, MAX_MASTERY_LEVEL)
        else:
            # 오답: 레벨 0으로 초기화
            new_level = 0
            
        # 2. 다음 복습 간격 계산
        interval = SRS_INTERVALS.get(new_level, 1) # 레벨 0을 기본으로
        
        # 3. 다음 복습일 계산
        next_review_date = (datetime.now() + timedelta(days=interval)).strftime('%Y-%m-%d 00:00:00')
        
        return new_level, next_review_date

    # --- 외부 호출 기능 ---

    def update_statistics(self, word_id: int, is_correct: bool) -> bool:
        """
        단어의 학습 결과를 반영하여 통계를 업데이트합니다.
        통계 레코드가 없으면 새로 생성합니다.
        """
        current_stats = self.select_all(where_clause="word_id = ?", params=(word_id,))
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        if not current_stats:
            # 1. 통계 레코드가 없을 경우 (최초 학습)
            current_level = 0
            
            # 최초 학습의 정답 여부로 다음 레벨 및 복습일 계산
            new_level, next_review_date = self._calculate_next_review(current_level, is_correct)
            
            insert_data = {
                "word_id": word_id,
                "total_attempts": 1,
                "correct_count": 1 if is_correct else 0,
                "last_review": now,
                "next_review": next_review_date,
                "mastery_level": new_level
            }
            # BaseModel의 insert 메서드는 stats_id (PK)를 반환
            return self.insert(insert_data) is not None
        else:
            # 2. 통계 레코드가 있을 경우 (업데이트)
            stats = current_stats[0] # word_id는 UNIQUE 제약 조건으로 인해 1개만 존재
            stats_id = stats['stats_id']
            current_level = stats['mastery_level']
            
            new_level, next_review_date = self._calculate_next_review(current_level, is_correct)
            
            update_data = {
                "total_attempts": stats['total_attempts'] + 1,
                "correct_count": stats['correct_count'] + (1 if is_correct else 0),
                "last_review": now,
                "next_review": next_review_date,
                "mastery_level": new_level
            }
            return self.update(stats_id, update_data)

    def select_review_words(self, limit: int) -> List[Dict[str, Any]]:
        """
        오늘 날짜를 기준으로 복습이 필요한 단어 목록을 'next_review'가 빠른 순으로 반환합니다.
        """
        today = datetime.now().strftime('%Y-%m-%d 23:59:59')
        
        # 오늘까지 복습이 필요한 단어를 복습일이 가장 오래된 순서로 정렬 (ASC)
        sql = f"""
            SELECT W.word_id, W.word_text, W.meaning_ko, S.mastery_level, S.next_review
            FROM words W
            INNER JOIN {self.TABLE_NAME} S ON W.word_id = S.word_id
            WHERE W.is_deleted = 0 
              AND S.next_review <= ?
            ORDER BY S.next_review ASC
            LIMIT ?
        """
        
        try:
            self.db.connect()
            cursor = self.db.execute(sql, (today, limit))
            if cursor:
                rows = cursor.fetchall()
                # sqlite3.Row 객체를 dict로 변환
                return [dict(row) for row in rows] 
            return []
        except Exception as e:
            LOGGER.error(f"Failed to select review words. Error: {e}")
            return []
        finally:
            self.db.close()
            
    def get_mastery_distribution(self) -> Dict[int, int]:
        """
        숙련도 레벨별 단어 수를 반환합니다. (통계 대시보드용)
        """
        sql = f"""
            SELECT mastery_level, COUNT(word_id) as count
            FROM {self.TABLE_NAME}
            GROUP BY mastery_level
            ORDER BY mastery_level ASC
        """
        
        try:
            self.db.connect()
            rows = self.db.fetchall(sql)
            distribution = {row['mastery_level']: row['count'] for row in rows}
            
            # 레벨 0부터 MAX_MASTERY_LEVEL까지의 모든 레벨 포함 (데이터가 없는 레벨은 0으로)
            full_distribution = {level: distribution.get(level, 0) for level in range(MAX_MASTERY_LEVEL + 1)}
            return full_distribution
        except Exception as e:
            LOGGER.error(f"Failed to get mastery distribution. Error: {e}")
            return {}
        finally:
            self.db.close()

    def get_proficiency_distribution(self) -> Dict[int, int]:
        """
        단어 숙련도 레벨(mastery_level)별 단어 분포를 가져옵니다.
        """
        sql = """
            SELECT 
                ws.mastery_level,
                COUNT(ws.word_id) as word_count
            FROM 
                word_statistics ws
            JOIN
                words w ON ws.word_id = w.word_id
            WHERE
                w.is_deleted = 0
            GROUP BY 
                ws.mastery_level
            ORDER BY
                ws.mastery_level;
        """
        try:
            self.db.connect()
            results = self.db.fetchall(sql)
            # {0: 10, 1: 20, ...} 형태의 딕셔너리로 변환
            return {row['mastery_level']: row['word_count'] for row in results if row}
        except Exception as e:
            LOGGER.error(f"Error fetching proficiency distribution: {e}")
            return {}
        finally:
            self.db.close()

    def get_daily_correct_rate_trend(self, days: int) -> List[Dict[str, Any]]:
        """
        지난 'days' 동안의 일별 정답률 추이를 가져옵니다.
        """
        # SQLite는 1-based 인덱싱이 아닌 0-based 인덱싱을 지원하므로, DATETIME 함수 사용.
        # N일 전 날짜를 계산하여 해당 날짜 이후의 기록만 가져옵니다.
        sql = f"""
            SELECT
                STRFTIME('%Y-%m-%d', learning_date) AS learning_day,
                SUM(CASE WHEN is_correct = 1 THEN 1 ELSE 0 END) AS correct_count,
                COUNT(history_id) AS total_count
            FROM
                learning_history
            WHERE
                learning_date >= STRFTIME('%Y-%m-%d', DATE('now', '-{days} days'))
            GROUP BY
                learning_day
            ORDER BY
                learning_day ASC;
        """
        
        trend_data = []
        try:
            self.db.connect()
            results = self.db.fetchall(sql)
            
            for row in results:
                total = row['total_count']
                correct = row['correct_count']
                rate = round((correct / total) * 100, 1) if total > 0 else 0
                
                trend_data.append({
                    'date': row['learning_day'],
                    'rate': rate,
                    'total': total # 차트 툴팁 등을 위해 total도 함께 반환
                })
            
            return trend_data
        
        except Exception as e:
            LOGGER.error(f"Error fetching daily correct rate trend: {e}")
            return []
        finally:
            self.db.close()