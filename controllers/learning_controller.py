import random
from typing import List, Dict, Any, Optional, Tuple
from controllers.base_controller import BaseController
from utils.logger import setup_logger
from datetime import datetime

# 2025-10-20 - 스마트 단어장 - 학습 관리 컨트롤러
# 파일 위치: controllers/learning_controller.py - v1
# 목적: 학습 세션 시작/종료, 단어 선정 로직, 학습 결과 기록 및 통계 업데이트 구현

LOGGER = setup_logger()

class LearningController(BaseController):
    """
    단어 학습(플래시카드) 및 SRS(간격 반복 학습) 통계를 관리하는 컨트롤러입니다.
    """

    def __init__(self):
        super().__init__()
        # self.word_model, self.learning_model, self.statistics_model, self.exam_model 사용 가능
        
    # --- 1. 단어 선정 로직 (F1 양방향 학습, F2 출력 방식) ---
    
    def get_words_for_session(self, mode: str, word_count: int, category: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        선택된 모드와 조건에 따라 학습할 단어 목록을 반환합니다.
        
        Args:
            mode (str): 'random', 'sequential', 'review_srs', 'wrong_note'
            word_count (int): 요청 단어 수
            category (str, optional): 필터링할 카테고리
            
        Returns:
            List[Dict[str, Any]]: 학습할 단어 목록 (word_id, word_text, meaning_ko 등 포함)
        """
        all_words: List[Dict[str, Any]] = []
        
        # 1. 단어 데이터 가져오기 (모드별)
        if mode == 'review_srs':
            # StatisticsModel에서 다음 복습일이 도래한 단어 가져오기
            all_words = self.statistics_model.select_review_words(word_count)
            LOGGER.info(f"Loaded {len(all_words)} words for SRS review.")
            
        elif mode == 'wrong_note':
            # ExamModel에서 오답률이 높은 단어 가져오기
            all_words = self.exam_model.select_wrong_words_for_review(word_count)
            LOGGER.info(f"Loaded {len(all_words)} words from wrong note.")

        else: # 'random' 또는 'sequential' 모드
            if category:
                # 카테고리 필터링
                all_words = self.word_model.select_by_category(category)
            else:
                # 전체 단어 (삭제되지 않은)
                all_words = self.word_model.select_active_words()
            
            # 2. 순서 결정 (Sequential vs Random)
            if mode == 'random':
                random.shuffle(all_words)
        
        # 3. 개수 제한 (Limit)
        # SRS/Wrong Note 모드는 이미 word_count로 제한되거나, 전체 단어가 적을 수 있음
        final_list = all_words[:word_count] if len(all_words) > word_count else all_words
        
        LOGGER.info(f"Final session word list size: {len(final_list)} for mode '{mode}'.")
        return final_list

    # --- 2. 세션 관리 ---

    def start_session(self, session_type: str, session_mode: str, word_list: List[Dict[str, Any]]) -> Optional[int]:
        """
        새 학습 세션을 시작하고, 세션 ID를 반환합니다.
        """
        total_words = len(word_list)
        if total_words == 0:
            LOGGER.warning("Attempted to start session with 0 words.")
            return None
            
        return self.learning_model.start_session(session_type, session_mode, total_words)

    def end_session(self, session_id: int, correct_count: int, wrong_count: int) -> bool:
        """
        학습 세션을 종료하고 결과를 기록합니다.
        """
        return self.learning_model.end_session(session_id, correct_count, wrong_count)

    # --- 3. 학습 결과 기록 및 통계 업데이트 (핵심 SRS 로직) ---

    def record_word_result(self, session_id: int, word_id: int, is_correct: bool, response_time: float) -> bool:
        """
        단어 학습 결과를 기록하고 통계를 업데이트합니다. (핵심)
        """
        success = True
        
        # 1. 학습 이력 기록 (Learning History)
        history_success = self.learning_model.add_history(session_id, word_id, is_correct, response_time) is not None
        if not history_success:
            LOGGER.error(f"Failed to record learning history for word ID: {word_id}")
            success = False
            
        # 2. 단어 통계 업데이트 (SRS 로직 실행)
        stats_success = self.statistics_model.update_statistics(word_id, is_correct)
        if not stats_success:
            LOGGER.error(f"Failed to update statistics (SRS) for word ID: {word_id}")
            success = False
            
        if success:
            LOGGER.debug(f"Word ID {word_id} result recorded. Correct: {is_correct}")
            
        return success

    # --- 4. 대시보드 통계 조회 (F11 학습 통계) ---
    
    def get_dashboard_summary(self) -> Dict[str, Any]:
        """
        대시보드에 표시할 주요 학습 통계 요약을 반환합니다.
        """
        # 1. 오늘의 학습 시간 (분)
        today_time = self.learning_model.get_total_learning_time_today()
        
        # 2. 숙련도 레벨별 분포
        mastery_distribution = self.statistics_model.get_mastery_distribution()
        
        # 3. 최근 7일간 정답률
        daily_correct_rate = self.learning_model.get_daily_correct_rate(days=7)
        
        # 4. 전체 단어 수
        total_words = len(self.word_model.select_active_words())
        
        # 5. 복습 필요 단어 수
        # 복습 단어는 next_review 필터링 (최대 1000개까지 조회하여 Count)
        review_words_count = len(self.statistics_model.select_review_words(1000)) 

        # 6. 오답 노트 단어 수
        wrong_words_count = len(self.exam_model.select_wrong_words_for_review(1000))
        
        return {
            "today_learning_time_min": today_time,
            "total_words_count": total_words,
            "review_words_count": review_words_count,
            "wrong_words_count": wrong_words_count,
            "mastery_distribution": mastery_distribution,
            "daily_correct_rate": daily_correct_rate,
        }

    def get_word_proficiency_distribution(self) -> Dict[int, int]:
        """
        단어 숙련도 레벨(mastery_level)별 단어 분포를 가져옵니다.
        예: {0: 10, 1: 20, 2: 5}
        """
        try:
            # StatisticsModel의 기능을 호출
            return self.statistics_model.get_proficiency_distribution()
        except Exception as e:
            LOGGER.error(f"Error fetching proficiency distribution: {e}")
            return {}


    def get_daily_correct_rate_trend(self, days: int) -> List[Dict[str, Any]]:
        """
        지난 'days' 동안의 일별 정답률 추이를 가져옵니다.
        예: [{'date': '2025-10-15', 'rate': 85.5}, ...]
        """
        try:
            # StatisticsModel의 기능을 호출
            return self.statistics_model.get_daily_correct_rate_trend(days)
        except Exception as e:
            LOGGER.error(f"Error fetching daily trend: {e}")
            return []