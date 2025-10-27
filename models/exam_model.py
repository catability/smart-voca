from typing import List, Dict, Any, Optional, Tuple
from models.base_model import BaseModel
from utils.logger import setup_logger
from datetime import datetime
import json # exam_questions의 user_answer 필드에 복잡한 데이터 구조 저장 시 활용 가능

# 2025-10-20 - 스마트 단어장 - 시험 및 오답 관리 데이터 모델
# 파일 위치: models/exam_model.py - v1
# 목적: 시험 이력, 상세 문제, 오답 노트 관리 기능 구현

LOGGER = setup_logger()

# 시험 이력 테이블
class ExamHistoryModel(BaseModel):
    TABLE_NAME = "exam_history"
    PRIMARY_KEY = "exam_id"
    FIELDS = [
        "exam_id", "exam_date", "exam_type", "total_questions", 
        "score", "duration_sec", "is_deleted"
    ]

    def __init__(self):
        super().__init__()

# 시험 문제 상세 테이블
class ExamQuestionModel(BaseModel):
    TABLE_NAME = "exam_questions"
    PRIMARY_KEY = "question_id"
    FIELDS = [
        "question_id", "exam_id", "word_id", "question_text", 
        "correct_answer", "user_answer", "is_correct"
    ]

    def __init__(self):
        super().__init__()

# 오답 노트 테이블
class WrongNoteModel(BaseModel):
    TABLE_NAME = "wrong_note"
    PRIMARY_KEY = "note_id"
    FIELDS = [
        "note_id", "word_id", "latest_exam_id", "wrong_count", 
        "last_wrong_date"
    ]

    def __init__(self):
        super().__init__()


# 통합 시험/오답 관리 모델 (Controller가 주로 사용할 기능 포함)
class ExamModel:
    """
    시험 및 오답 노트 관리를 통합하는 모델입니다.
    """
    def __init__(self):
        self.history_model = ExamHistoryModel()
        self.question_model = ExamQuestionModel()
        self.wrong_note_model = WrongNoteModel()
        self.db = self.history_model.db # DBConnection 인스턴스 공유

    # --- 1. 시험 결과 기록 (핵심 트랜잭션) ---

    def record_exam_result(self, 
                           exam_type: str, 
                           total_questions: int, 
                           score: float, 
                           duration_sec: int,
                           questions_detail: List[Dict[str, Any]]
                           ) -> Optional[int]:
        """
        시험 결과와 상세 문제를 한 번의 트랜잭션으로 기록하고, 오답 노트를 업데이트합니다.
        
        Args:
            questions_detail: 각 문제의 상세 정보 리스트. 
                              (word_id, question_text, correct_answer, user_answer, is_correct) 포함.
        Returns:
            삽입된 exam_id 또는 None
        """
        exam_id = None
        
        try:
            self.db.connect()
            self.db._conn.isolation_level = None # 트랜잭션 시작 (BEGIN)
            self.db.execute("BEGIN")

            # 1. 시험 이력 (exam_history) 기록
            history_data = {
                "exam_date": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                "exam_type": exam_type,
                "total_questions": total_questions,
                "score": score,
                "duration_sec": duration_sec,
            }
            # BaseModel의 insert는 DBConnection을 통해 트랜잭션 내에서 실행되도록 설계되어 있음
            # 하지만 안전을 위해, 명시적으로 커밋/롤백을 제어해야 하므로, DBConnection의 execute를 직접 사용
            
            # (A) Exam History 삽입
            columns = ', '.join(history_data.keys())
            placeholders = ', '.join(['?' for _ in history_data])
            values = tuple(history_data.values())
            history_sql = f"INSERT INTO {self.history_model.TABLE_NAME} ({columns}, is_deleted) VALUES ({placeholders}, 0)"
            cursor = self.db.execute(history_sql, values)
            exam_id = cursor.lastrowid

            if not exam_id:
                raise Exception("Failed to insert exam history.")

            # 2. 시험 문제 상세 (exam_questions) 기록 및 오답 노트 업데이트
            for q in questions_detail:
                q['exam_id'] = exam_id
                
                # (B) Exam Question 삽입
                q_columns = ', '.join(q.keys())
                q_placeholders = ', '.join(['?' for _ in q])
                q_values = tuple(q.values())
                q_sql = f"INSERT INTO {self.question_model.TABLE_NAME} ({q_columns}) VALUES ({q_placeholders})"
                self.db.execute(q_sql, q_values)

                # (C) 오답 노트 (wrong_note) 업데이트
                if q['is_correct'] == 0:
                    self._update_wrong_note(q['word_id'], exam_id)
            
            # 3. 트랜잭션 완료
            self.db.commit()
            LOGGER.info(f"Exam result recorded successfully. Exam ID: {exam_id}")
            return exam_id

        except Exception as e:
            LOGGER.error(f"Failed to record exam result. Transaction rolled back. Error: {e}")
            self.db.execute("ROLLBACK")
            return None
        finally:
            self.db.close()
            
    # --- 2. 오답 노트 관리 (내부 보조 함수) ---
    
    def _update_wrong_note(self, word_id: int, latest_exam_id: int) -> bool:
        """
        특정 단어가 오답이었을 때 오답 노트 테이블을 업데이트하거나 새로 삽입합니다.
        (이 함수는 record_exam_result 트랜잭션 내에서 실행됩니다.)
        """
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # 1. 기존 레코드 확인 (트랜잭션 내에서 db.execute 사용)
        select_sql = f"SELECT note_id, wrong_count FROM {self.wrong_note_model.TABLE_NAME} WHERE word_id = ?"
        row = self.db.fetchone(select_sql, (word_id,))
        
        if row:
            # 업데이트
            update_sql = f"""
                UPDATE {self.wrong_note_model.TABLE_NAME}
                SET wrong_count = wrong_count + 1, latest_exam_id = ?, last_wrong_date = ?
                WHERE note_id = ?
            """
            self.db.execute(update_sql, (latest_exam_id, now, row['note_id']))
        else:
            # 삽입
            insert_data = {
                "word_id": word_id,
                "latest_exam_id": latest_exam_id,
                "wrong_count": 1,
                "last_wrong_date": now,
            }
            columns = ', '.join(insert_data.keys())
            placeholders = ', '.join(['?' for _ in insert_data])
            insert_sql = f"INSERT INTO {self.wrong_note_model.TABLE_NAME} ({columns}) VALUES ({placeholders})"
            self.db.execute(insert_sql, tuple(insert_data.values()))
            
        return True # 트랜잭션이 커밋될 때 성공

    # --- 3. 오답 노트 목록 조회 ---
    
    def select_wrong_words_for_review(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        오답 노트에 있는 단어 목록을 오답 횟수 또는 마지막으로 틀린 날짜 기준으로 반환합니다.
        """
        sql = """
            SELECT W.word_id, W.word_text, W.meaning_ko, N.wrong_count, N.last_wrong_date
            FROM words W
            INNER JOIN wrong_note N ON W.word_id = N.word_id
            WHERE W.is_deleted = 0
            ORDER BY N.wrong_count DESC, N.last_wrong_date ASC
        """
        if limit is not None:
            sql += f" LIMIT {limit}"
            
        try:
            self.db.connect()
            cursor = self.db.execute(sql)
            if cursor:
                rows = cursor.fetchall()
                # sqlite3.Row 객체를 dict로 변환
                return [dict(row) for row in rows] 
            return []
        except Exception as e:
            LOGGER.error(f"Failed to select wrong words. Error: {e}")
            return []
        finally:
            self.db.close()