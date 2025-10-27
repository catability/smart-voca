import random
from typing import List, Dict, Any, Optional, Tuple
from controllers.base_controller import BaseController
from utils.logger import setup_logger
from datetime import datetime

# 2025-10-20 - 스마트 단어장 - 시험 관리 컨트롤러
# 파일 위치: controllers/exam_controller.py - v1
# 목적: 시험 출제, 채점, 결과 기록 및 오답 노트 관리 로직 구현

LOGGER = setup_logger()

class ExamController(BaseController):
    """
    단어 시험의 출제, 진행, 결과 기록 및 오답 노트 관련 비즈니스 로직을 담당합니다.
    """

    def __init__(self):
        super().__init__()
        # self.word_model, self.exam_model 사용 가능

    # --- 1. 시험 출제 단어 선정 ---

    def _get_candidate_words(self, category: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        시험 출제를 위한 단어 후보 목록을 카테고리 필터링을 거쳐 가져옵니다.
        """
        if category:
            return self.word_model.select_by_category(category)
        else:
            return self.word_model.select_active_words()

    def generate_exam_words(self, question_count: int, mode: str, category: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        시험 출제 모드(랜덤, 오답률)와 문항 수에 따라 시험 단어를 선정합니다.
        """
        
        if mode == 'wrong_note':
            # 오답률 기반 개인화 출제 (F17)
            # 오답 노트에 있는 단어를 우선적으로 가져옴 (오답 횟수 내림차순 정렬)
            candidate_words = self.exam_model.select_wrong_words_for_review(question_count)
            # 오답 노트 단어가 부족할 경우, 일반 단어에서 무작위로 채움 (필요하다면)
            if len(candidate_words) < question_count:
                remaining_count = question_count - len(candidate_words)
                # 오답 노트에 없는 단어 목록을 추가로 가져와 무작위로 선택할 수 있으나,
                # 여기서는 구현 단순화를 위해 오답 단어만 반환하고, 부족하면 있는 만큼만 출제
                LOGGER.info(f"Wrong note words count ({len(candidate_words)}) is less than requested ({question_count}).")
            
            # 오답률 기반 단어는 이미 정렬되어 있으므로 그대로 사용
            return candidate_words

        else: # 'random' 또는 기타 모드
            # 일반 단어 목록 가져오기
            all_words = self._get_candidate_words(category)
            if len(all_words) < question_count:
                question_count = len(all_words) # 단어 수가 부족하면 전체 출제
                LOGGER.warning(f"Requested questions ({question_count}) exceed available words. Adjusting count.")
            
            # 무작위로 단어 선택
            random.shuffle(all_words)
            return all_words[:question_count]

    # --- 2. 시험 채점 및 결과 기록 (핵심 트랜잭션) ---

    def submit_and_record_exam(self, 
                              exam_type: str, 
                              duration_sec: int,
                              questions_data: List[Dict[str, Any]]
                              ) -> Optional[Dict[str, Any]]:
        """
        사용자의 답변을 채점하고, 시험 이력 및 오답 노트를 트랜잭션으로 기록합니다.
        
        Args:
            questions_data: 사용자의 답변이 포함된 문제 데이터 리스트.
        
        Returns:
            Dict[str, Any]: 시험 결과 요약 (score, correct_count, wrong_count, exam_id)
        """
        
        if not questions_data:
            return None
            
        correct_count = 0
        wrong_count = 0
        total_questions = len(questions_data)

        # 1. 최종 채점
        # Note: 'questions_data'에는 이미 채점 결과(is_correct)가 포함되어 있다고 가정하거나, 
        # 혹은 여기서 채점을 수행해야 합니다. (여기서는 채점은 뷰에서 사용자 답변을 검증하여 is_correct를 채운 후 전달한다고 가정)
        
        for q in questions_data:
            if q['is_correct'] == 1:
                correct_count += 1
            else:
                wrong_count += 1

        score = (correct_count / total_questions) * 100 if total_questions > 0 else 0.0
        score = round(score, 1) # 소수점 첫째 자리까지 반올림

        # 2. 시험 결과 기록 (ExamModel의 트랜잭션 기능 호출)
        exam_id = self.exam_model.record_exam_result(
            exam_type=exam_type,
            total_questions=total_questions,
            score=score,
            duration_sec=duration_sec,
            questions_detail=questions_data
        )

        if exam_id is not None:
            LOGGER.info(f"Exam ID {exam_id} recorded. Score: {score}, Correct: {correct_count}")
            return {
                "exam_id": exam_id,
                "score": score,
                "correct_count": correct_count,
                "wrong_count": wrong_count,
                "total_questions": total_questions,
            }
        
        return None

    # --- 3. 오답 관리 및 조회 ---

    def get_wrong_note_words(self) -> List[Dict[str, Any]]:
        """
        현재 오답 노트에 기록된 단어 목록을 반환합니다. (F14 오답 노트 화면)
        """
        return self.exam_model.select_wrong_words_for_review()
        
    def get_exam_history(self) -> List[Dict[str, Any]]:
        """
        과거 시험 이력 목록을 최신순으로 반환합니다.
        """
        # ExamHistoryModel의 select_all을 사용하여 목록 조회
        return self.exam_model.history_model.select_all(where_clause="is_deleted = 0 ORDER BY exam_date DESC")
        
    def get_exam_detail(self, exam_id: int) -> Optional[Dict[str, Any]]:
        """
        특정 시험 ID의 상세 이력과 문제 목록을 함께 반환합니다.
        """
        history = self.exam_model.history_model.select_by_id(exam_id)
        if not history:
            return None
            
        questions = self.exam_model.question_model.select_all(where_clause="exam_id = ?", params=(exam_id,))
        
        history['questions'] = questions
        return history