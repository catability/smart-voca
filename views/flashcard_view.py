from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QStackedWidget, 
    QLabel, QPushButton, QComboBox, QSpinBox, QGroupBox, 
    QFormLayout, QMessageBox, QSizePolicy
)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer, QElapsedTimer
from PyQt5.QtGui import QFont
from controllers.learning_controller import LearningController
from controllers.word_controller import WordController
from typing import List, Dict, Any, Optional
from utils.logger import setup_logger

from datetime import datetime

# 2025-10-20 - 스마트 단어장 - 플래시카드 학습 뷰
# 파일 위치: views/flashcard_view.py - v1
# 목적: 학습 옵션 설정 화면 및 플래시카드 학습 화면 전환 구현 (화면 설계서 4.2)

LOGGER = setup_logger()

class FlashcardView(QWidget):
    """
    '플래시 카드' 탭의 내용을 구성하는 뷰입니다.
    학습 옵션 설정과 실제 카드 학습 화면을 관리합니다.
    """
    # MainWindow의 상태 바 업데이트를 위한 시그널
    learning_status_changed = pyqtSignal()

    def __init__(self, learning_controller: LearningController, word_controller: WordController):
        super().__init__()
        self.learning_controller = learning_controller
        self.word_controller = word_controller
        
        # 학습 관련 상태 변수
        self.current_session_id: Optional[int] = None
        self.current_word_list: List[Dict[str, Any]] = []
        self.current_word_index: int = 0
        self.is_answer_shown: bool = False
        self.correct_count: int = 0
        self.wrong_count: int = 0
        self.session_start_time: float = 0
        
        # 타이머 (응답 시간 기록용)
        # self.response_timer = QTimer(self)
        self.response_timer = QElapsedTimer()
        
        self._setup_ui()
        self._load_categories()

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        
        # QStackedWidget: 옵션 설정 화면 <-> 학습 화면 전환
        self.stacked_widget = QStackedWidget()
        main_layout.addWidget(self.stacked_widget)
        
        # 1. 옵션 설정 화면 (Page 0)
        self.option_page = self._create_option_page()
        self.stacked_widget.addWidget(self.option_page)
        
        # 2. 플래시카드 학습 화면 (Page 1)
        self.card_page = self._create_card_page()
        self.stacked_widget.addWidget(self.card_page)
        
        # 초기 화면 설정
        self.stacked_widget.setCurrentIndex(0)

    # --- 1. 옵션 설정 화면 UI ---
    
    def _create_option_page(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 학습 설정 그룹 박스
        setting_group = QGroupBox("학습 옵션 설정")
        form_layout = QFormLayout()
        
        # 1. 학습 모드 (출력 방식 F2)
        self.mode_combo = QComboBox()
        self.mode_combo.addItem("랜덤 순서", "random")
        self.mode_combo.addItem("순차 순서", "sequential")
        self.mode_combo.addItem("SRS 복습 (D-Day 단어)", "review_srs")
        self.mode_combo.addItem("오답 노트 복습", "wrong_note")
        form_layout.addRow(QLabel("출제 모드:"), self.mode_combo)
        
        # 2. 출제 단어 수
        self.count_spin = QSpinBox()
        self.count_spin.setRange(10, 500)
        self.count_spin.setSingleStep(10)
        self.count_spin.setValue(self.learning_controller.get_setting_value('daily_word_goal') or 50)
        form_layout.addRow(QLabel("학습 단어 수:"), self.count_spin)

        # 3. 카테고리 필터
        self.category_combo = QComboBox()
        form_layout.addRow(QLabel("카테고리 필터:"), self.category_combo)

        # 4. 양방향 학습 모드 (F1)
        self.direction_combo = QComboBox()
        self.direction_combo.addItem("영어 -> 한국어", "eng_to_kor")
        self.direction_combo.addItem("한국어 -> 영어", "kor_to_eng")
        form_layout.addRow(QLabel("학습 방향:"), self.direction_combo)
        
        setting_group.setLayout(form_layout)
        layout.addWidget(setting_group)
        layout.addStretch(1)

        # 학습 시작 버튼
        self.start_btn = QPushButton("학습 시작")
        self.start_btn.setMinimumHeight(40)
        self.start_btn.clicked.connect(self._start_session)
        layout.addWidget(self.start_btn)
        
        return widget

    def _load_categories(self):
        """ 카테고리 목록을 불러와 콤보 박스에 채웁니다. """
        self.category_combo.clear()
        self.category_combo.addItem("전체 카테고리", None)
        categories = self.word_controller.get_all_categories()
        for cat in categories:
            self.category_combo.addItem(cat, cat)
            
    # --- 2. 플래시카드 학습 화면 UI ---

    def _create_card_page(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 상단 정보 (남은 단어 수)
        self.progress_label = QLabel("0 / 0")
        self.progress_label.setAlignment(Qt.AlignCenter)
        self.progress_label.setFont(QFont('Arial', 12))
        layout.addWidget(self.progress_label)
        
        # 카드 표시 영역
        self.card_label = QLabel("여기에 단어가 표시됩니다.")
        self.card_label.setAlignment(Qt.AlignCenter)
        self.card_label.setFont(QFont('Arial', 36, QFont.Bold))
        self.card_label.setWordWrap(True)
        self.card_label.setStyleSheet("border: 1px solid gray; padding: 50px;")
        self.card_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        layout.addWidget(self.card_label)
        
        # 답변 표시 영역 (블라인드 처리)
        self.meaning_label = QLabel("의미 (답변)")
        self.meaning_label.setAlignment(Qt.AlignCenter)
        self.meaning_label.setFont(QFont('Arial', 18))
        self.meaning_label.setWordWrap(True)
        layout.addWidget(self.meaning_label)

        # --- 버튼 영역 ---
        self.show_answer_btn = QPushButton("답 확인")
        self.show_answer_btn.setMinimumHeight(35)
        self.show_answer_btn.clicked.connect(self._show_answer)
        layout.addWidget(self.show_answer_btn)
        
        # 정답/오답 선택 버튼 (답 확인 후 활성화)
        self.result_buttons = QHBoxLayout()
        self.wrong_btn = QPushButton("몰랐음 (X)")
        self.correct_btn = QPushButton("알고 있었음 (O)")
        
        self.wrong_btn.clicked.connect(lambda: self._record_result(is_correct=False))
        self.correct_btn.clicked.connect(lambda: self._record_result(is_correct=True))
        
        self.result_buttons.addWidget(self.wrong_btn)
        self.result_buttons.addWidget(self.correct_btn)
        layout.addLayout(self.result_buttons)

        # 공부 중단 버튼 추가
        self.stop_btn = QPushButton("공부 중단하기")
        self.stop_btn.setStyleSheet("background-color: #E57373; color: white; font-weight: bold;")
        self.stop_btn.setMinimumHeight(35)
        self.stop_btn.clicked.connect(self._confirm_end_session)
        layout.addWidget(self.stop_btn)
        
        self._set_card_state(state='initial') # 초기 상태 설정
        return widget

    # --- 3. 세션 및 학습 관리 로직 ---

    def _start_session(self):
        """ 학습 옵션을 읽고 세션을 시작하며 화면을 전환합니다. """
        mode = self.mode_combo.currentData()
        word_count = self.count_spin.value()
        category = self.category_combo.currentData()
        direction = self.direction_combo.currentData()

        # 1. 단어 목록 가져오기
        words = self.learning_controller.get_words_for_session(mode, word_count, category)

        if not words:
            QMessageBox.warning(self, "학습 시작 실패", "선택된 옵션에 해당하는 단어가 없습니다.")
            return

        self.current_word_list = words
        self.current_word_index = 0
        self.correct_count = 0
        self.wrong_count = 0
        self.session_start_time = datetime.now().timestamp()
        
        # 2. 세션 시작 기록
        self.current_session_id = self.learning_controller.start_session("Flashcard", mode, words)
        if self.current_session_id is None:
             QMessageBox.critical(self, "오류", "학습 세션 시작 기록에 실패했습니다.")
             return

        # 3. 화면 전환 및 첫 카드 표시
        self.stacked_widget.setCurrentIndex(1)
        self._show_next_card()
        
        LOGGER.info(f"Session started: {len(words)} words, Mode: {mode}, Direction: {direction}")

    def _show_next_card(self):
        """ 다음 단어를 표시합니다. """
        if self.current_word_index >= len(self.current_word_list):
            self._end_session()
            return

        word_data = self.current_word_list[self.current_word_index]
        direction = self.direction_combo.currentData()

        # 학습 방향에 따라 카드 내용 설정
        if direction == "eng_to_kor":
            card_text = word_data['word_text']
            meaning_text = word_data['meaning_ko']
        else: # kor_to_eng
            card_text = word_data['meaning_ko']
            meaning_text = word_data['word_text']

        self.progress_label.setText(f"{self.current_word_index + 1} / {len(self.current_word_list)}")
        self.card_label.setText(card_text)

        self._current_meaning_text = meaning_text
        self.meaning_label.setText("???")
        self.meaning_label.setStyleSheet('color: grey')
        
        self._set_card_state(state='word_only') # 답변 블라인드 처리
        
        # 응답 시간 측정 시작
        self.response_timer.start()
        
        self.current_word_index += 1

    def _show_answer(self):
        """ 답변을 표시하고 버튼 상태를 전환합니다. """
        self.meaning_label.setText(self._current_meaning_text)
        self.meaning_label.setStyleSheet('color: blue')

        self._set_card_state(state='answer_shown')
        self.is_answer_shown = True

    def _record_result(self, is_correct: bool):
        """ 학습 결과를 기록하고 다음 카드로 넘어갑니다. """
        if not self.is_answer_shown:
            QMessageBox.warning(self, "답변 확인", "먼저 [답 확인] 버튼을 눌러주세요.")
            return

        # 1. 응답 시간 계산 (ms)
        response_time_ms = self.response_timer.elapsed()
        # self.response_timer.stop()
        response_time_sec = response_time_ms / 1000.0

        # 2. 결과 카운트
        if is_correct:
            self.correct_count += 1
        else:
            self.wrong_count += 1

        # 3. DB 기록 및 SRS 업데이트
        # current_word_index는 이미 +1 되어 있으므로, 이전 인덱스를 사용
        word_idx = self.current_word_index - 1
        word_data = self.current_word_list[word_idx]
        
        self.learning_controller.record_word_result(
            session_id=self.current_session_id,
            word_id=word_data['word_id'],
            is_correct=is_correct,
            response_time=response_time_sec
        )

        # 4. 다음 카드로 전환
        self._show_next_card()
        self.is_answer_shown = False # 상태 리셋

    def _confirm_end_session(self):
        """ 사용자가 공부를 중단할 때 확인 후 세션 종료 """
        reply = QMessageBox.question(
            self,
            "공부 중단",
            "정말로 현재 학습을 중단하시겠습니까?",
            QMessageBox.Yes |QMessageBox.No,
            QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            # 세션 종료 (기존 종료 로직 재활용)
            try:
                self._end_session()
                LOGGER.info("User stopped the study session manually.")
            except Exception as e:
                QMessageBox.critical(self, "오류", f"세션 종료 중 오류 발생: {e}")

    def _end_session(self):
        """ 학습 세션을 종료하고 결과를 표시한 후 초기 화면으로 돌아갑니다. """
        
        # 1. 세션 종료 기록 (총 학습 시간, 정답/오답 수)
        total_duration_sec = datetime.now().timestamp() - self.session_start_time
        self.learning_controller.end_session(
            session_id=self.current_session_id,
            correct_count=self.correct_count,
            wrong_count=self.wrong_count
        )
        
        # 2. 상태 바 업데이트 알림
        self.learning_status_changed.emit()

        # 3. 결과 메시지 표시
        total = self.correct_count + self.wrong_count
        rate = round((self.correct_count / total) * 100, 1) if total > 0 else 0.0
        
        QMessageBox.information(
            self, "학습 완료",
            f"총 {total} 단어 학습 완료!\n"
            f"정답: {self.correct_count}개, 오답: {self.wrong_count}개\n"
            f"정답률: {rate}%"
        )
        
        # 4. 초기 화면으로 전환
        self.stacked_widget.setCurrentIndex(0)

    def _set_card_state(self, state: str):
        """ 카드 화면의 UI 요소를 상태에 따라 전환합니다. """
        if state == 'initial' or state == 'word_only':
            # 단어만 표시, 답변 블라인드, 결과 버튼 비활성화
            self.meaning_label.setStyleSheet("color: black;") # QSS로 블라인드 효과 적용 예정
            self.show_answer_btn.setEnabled(True)
            self.wrong_btn.setEnabled(False)
            self.correct_btn.setEnabled(False)
            
        elif state == 'answer_shown':
            # 답변 표시, 답 확인 버튼 비활성화, 결과 버튼 활성화
            self.meaning_label.setStyleSheet("color: blue;")
            self.show_answer_btn.setEnabled(False)
            self.wrong_btn.setEnabled(True)
            self.correct_btn.setEnabled(True)