from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QStackedWidget, 
    QLabel, QPushButton, QComboBox, QSpinBox, QGroupBox, 
    QFormLayout, QMessageBox, QSizePolicy, QLineEdit,
    QRadioButton, QButtonGroup, QGridLayout
)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer, QTime
from PyQt5.QtGui import QFont
from controllers.exam_controller import ExamController
from controllers.word_controller import WordController # 카테고리 로딩용
from typing import List, Dict, Any, Optional
from utils.logger import setup_logger
from datetime import datetime

# 2025-10-20 - 스마트 단어장 - 시험 관리 뷰
# 파일 위치: views/exam_view.py - v1
# 목적: 시험 설정, 진행, 결과 화면 및 채점 로직 구현 (화면 설계서 4.3)

LOGGER = setup_logger()

class ExamView(QWidget):
    """
    '시험' 탭의 내용을 구성하는 뷰입니다.
    시험 설정 -> 시험 진행 -> 시험 결과 화면을 관리합니다.
    """
    # MainWindow의 상태 바 업데이트를 위한 시그널
    exam_status_changed = pyqtSignal()

    def __init__(self, exam_controller: ExamController, word_controller: WordController):
        super().__init__()
        self.exam_controller = exam_controller
        self.word_controller = word_controller # 카테고리 로딩에 사용
        
        # 시험 진행 상태 변수
        self.exam_words: List[Dict[str, Any]] = [] # 출제될 단어 목록
        self.exam_questions: List[Dict[str, Any]] = [] # 문제와 사용자 답변 포함 목록
        self.current_question_index: int = 0
        self.exam_start_time: float = 0
        self.timer = QTimer(self)
        self.time_limit_sec: int = 0
        
        self._setup_ui()
        self._load_categories()
        
    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        
        # QStackedWidget: 설정 (0) <-> 진행 (1) <-> 결과 (2)
        self.stacked_widget = QStackedWidget()
        main_layout.addWidget(self.stacked_widget)
        
        # 1. 시험 설정 화면 (Page 0)
        self.setting_page = self._create_setting_page()
        self.stacked_widget.addWidget(self.setting_page)
        
        # 2. 시험 진행 화면 (Page 1)
        self.progress_page = self._create_progress_page()
        self.stacked_widget.addWidget(self.progress_page)
        
        # 3. 시험 결과 화면 (Page 2)
        self.result_page = self._create_result_page()
        self.stacked_widget.addWidget(self.result_page)
        
        # 초기 화면 설정
        self.stacked_widget.setCurrentIndex(0)

    # --- 1. 시험 설정 화면 UI ---
    
    def _create_setting_page(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        setting_group = QGroupBox("시험 옵션 설정")
        form_layout = QFormLayout()
        
        # 1. 출제 문항 수
        self.count_spin = QSpinBox()
        self.count_spin.setRange(10, 500)
        self.count_spin.setSingleStep(10)
        self.count_spin.setValue(30)
        form_layout.addRow(QLabel("출제 문항 수:"), self.count_spin)
        
        # 2. 출제 모드 (F13)
        self.mode_combo = QComboBox()
        self.mode_combo.addItem("랜덤 출제", "random")
        self.mode_combo.addItem("오답률 기반 개인화 출제", "wrong_note")
        form_layout.addRow(QLabel("출제 모드:"), self.mode_combo)

        # 3. 문항 유형 (F14)
        self.type_combo = QComboBox()
        self.type_combo.addItem("단답형 (의미 입력)", "short_answer")
        self.type_combo.addItem("객관식 (4지선다)", "multiple_choice")
        form_layout.addRow(QLabel("문항 유형:"), self.type_combo)

        # 4. 카테고리 필터
        self.category_combo = QComboBox()
        form_layout.addRow(QLabel("카테고리 필터:"), self.category_combo)
        
        # 5. 시간 제한 (F15)
        self.time_limit_spin = QSpinBox()
        self.time_limit_spin.setRange(0, 300) # 0분 ~ 300분
        self.time_limit_spin.setSuffix(" 분 (0은 제한 없음)")
        self.time_limit_spin.setValue(0)
        form_layout.addRow(QLabel("총 시간 제한:"), self.time_limit_spin)
        
        setting_group.setLayout(form_layout)
        layout.addWidget(setting_group)
        layout.addStretch(1)

        # 시험 시작 버튼
        self.start_btn = QPushButton("시험 시작")
        self.start_btn.setMinimumHeight(40)
        self.start_btn.clicked.connect(self._start_exam)
        layout.addWidget(self.start_btn)
        
        return widget

    def _load_categories(self):
        """ WordController를 통해 카테고리 목록을 불러와 콤보 박스에 채웁니다. """
        self.category_combo.clear()
        self.category_combo.addItem("전체 카테고리", None)
        categories = self.word_controller.get_all_categories()
        for cat in categories:
            self.category_combo.addItem(cat, cat)
            
    # --- 2. 시험 진행 화면 UI ---

    def _create_progress_page(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 상단 정보 (남은 시간 및 진행률)
        self.top_bar = QHBoxLayout()
        self.timer_label = QLabel("남은 시간: --:--")
        self.progress_label = QLabel("진행: 0 / 0")
        self.timer_label.setAlignment(Qt.AlignLeft)
        self.progress_label.setAlignment(Qt.AlignRight)
        self.top_bar.addWidget(self.timer_label)
        self.top_bar.addWidget(self.progress_label)
        layout.addLayout(self.top_bar)
        
        # 문제 영역
        self.question_label = QLabel("Q. 1. 다음 단어의 의미는?")
        self.question_label.setFont(QFont('Arial', 14))
        self.question_label.setWordWrap(True)
        layout.addWidget(self.question_label)

        # 카드 영역 (단어 표시)
        self.word_card = QLabel("WORD TEXT")
        self.word_card.setAlignment(Qt.AlignCenter)
        self.word_card.setFont(QFont('Arial', 32, QFont.Bold))
        self.word_card.setStyleSheet("border: 1px solid #ccc; padding: 40px; background-color: white; color: black;")
        self.word_card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        layout.addWidget(self.word_card)
        
        # 답변 입력/선택 영역 (Stacked Widget으로 동적 전환)
        self.answer_stack = QStackedWidget()
        
        #   1) 단답형 입력 (Index 0)
        self.short_answer_input = QLineEdit()
        self.short_answer_input.setPlaceholderText("답변을 입력하세요.")
        self.answer_stack.addWidget(self.short_answer_input)
        
        #   2) 객관식 버튼 (Index 1)
        self.multiple_choice_widget = QWidget()
        self.mc_layout = QGridLayout(self.multiple_choice_widget)
        self.mc_group = QButtonGroup(self) # 라디오 버튼 그룹
        self.mc_options = []
        for i in range(4): # 4지선다
            rb = QRadioButton(f"Option {i+1}")
            self.mc_group.addButton(rb, i)
            self.mc_options.append(rb)
            self.mc_layout.addWidget(rb, i // 2, i % 2) # 2x2 그리드
        self.answer_stack.addWidget(self.multiple_choice_widget)

        layout.addWidget(self.answer_stack)
        
        # 다음/제출 버튼
        self.next_btn = QPushButton("다음 문제")
        self.next_btn.setMinimumHeight(35)
        self.next_btn.clicked.connect(self._submit_answer_and_next)
        layout.addWidget(self.next_btn)
        
        return widget
        
    # --- 3. 시험 결과 화면 UI ---
    
    def _create_result_page(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 결과 요약
        self.score_label = QLabel("점수: 0점")
        self.score_label.setAlignment(Qt.AlignCenter)
        self.score_label.setFont(QFont('Arial', 48, QFont.Bold))
        layout.addWidget(self.score_label)
        
        self.summary_label = QLabel("총 0문제 중 0문제 정답 (0% 정답률)")
        self.summary_label.setAlignment(Qt.AlignCenter)
        self.summary_label.setFont(QFont('Arial', 18))
        layout.addWidget(self.summary_label)

        layout.addStretch(1)
        
        # 버튼
        button_layout = QHBoxLayout()
        self.review_btn = QPushButton("오답 노트 복습 시작")
        self.history_btn = QPushButton("시험 이력 확인")
        self.restart_btn = QPushButton("다시 시험 시작")
        
        self.review_btn.clicked.connect(lambda: QMessageBox.information(self, "기능 예정", "오답 노트 탭으로 이동"))
        self.history_btn.clicked.connect(lambda: QMessageBox.information(self, "기능 예정", "시험 이력 탭으로 이동"))
        self.restart_btn.clicked.connect(lambda: self.stacked_widget.setCurrentIndex(0))
        
        button_layout.addWidget(self.review_btn)
        button_layout.addWidget(self.history_btn)
        button_layout.addWidget(self.restart_btn)
        
        layout.addLayout(button_layout)
        
        return widget
        
    # --- 4. 시험 관리 로직 ---
    
    def _start_exam(self):
        """ 시험 옵션을 읽고 시험 단어를 생성하여 시험을 시작합니다. """
        
        # 옵션 읽기
        question_count = self.count_spin.value()
        mode = self.mode_combo.currentData()
        exam_type = self.type_combo.currentData()
        category = self.category_combo.currentData()
        self.time_limit_sec = self.time_limit_spin.value() * 60 # 분을 초로 변환
        
        # 1. 단어 목록 가져오기
        self.exam_words = self.exam_controller.generate_exam_words(question_count, mode, category)

        if not self.exam_words:
            QMessageBox.warning(self, "시험 시작 실패", "선택된 옵션에 해당하는 단어가 없거나 출제에 실패했습니다.")
            return

        # 2. 시험 상태 초기화
        self.exam_questions = []
        self.current_question_index = 0
        self.exam_start_time = datetime.now().timestamp()

        # 3. 시간 제한 설정 및 시작
        if self.time_limit_sec > 0:
            self.timer.timeout.connect(self._update_timer)
            self.timer.start(1000) # 1초마다 업데이트
            self.time_limit_end = QTime.currentTime().addSecs(self.time_limit_sec)
        else:
            self.timer_label.setText("시간 제한 없음")

        # 4. 화면 전환 및 첫 문제 표시
        self.stacked_widget.setCurrentIndex(1)
        self._show_question()
        LOGGER.info(f"Exam started: {len(self.exam_words)} questions, Type: {exam_type}")

    def _update_timer(self):
        """ 남은 시간을 계산하여 타이머 라벨을 업데이트합니다. """
        remaining_time = QTime.currentTime().secsTo(self.time_limit_end)
        
        if remaining_time <= 0:
            self.timer.stop()
            self.timer_label.setText("남은 시간: 00:00")
            QMessageBox.information(self, "시간 초과", "시험 제한 시간이 초과되었습니다. 자동 제출됩니다.")
            self._end_exam()
            return

        time_format = QTime(0, 0).addSecs(remaining_time).toString("mm:ss")
        self.timer_label.setText(f"남은 시간: {time_format}")

    def _show_question(self):
        """ 다음 문제를 화면에 표시합니다. """
        if self.current_question_index >= len(self.exam_words):
            self._end_exam()
            return

        q_idx = self.current_question_index
        word_data = self.exam_words[q_idx]
        exam_type = self.type_combo.currentData()
        
        self.progress_label.setText(f"진행: {q_idx + 1} / {len(self.exam_words)}")
        self.word_card.setText(word_data['word_text'])
        self.question_label.setText(f"Q. {q_idx + 1}. 다음 단어의 의미는?")
        
        # 입력 필드 및 버튼 초기화
        self.short_answer_input.clear()
        self.mc_group.setExclusive(False)
        for rb in self.mc_options:
            rb.setChecked(False)
        self.mc_group.setExclusive(True)

        # 문항 유형에 따라 답변 영역 설정
        if exam_type == 'short_answer':
            self.answer_stack.setCurrentIndex(0)
        else: # multiple_choice
            self.answer_stack.setCurrentIndex(1)
            # 객관식 보기 생성 (간단 구현)
            self._generate_multiple_choice(word_data)
            
        # 마지막 문제일 경우 버튼 텍스트 변경
        self.next_btn.setText("최종 제출" if q_idx == len(self.exam_words) - 1 else "다음 문제")

    def _generate_multiple_choice(self, correct_word: Dict[str, Any]):
        """ 객관식 보기를 생성합니다. (정답 + 오답 3개) """
        all_words = self.exam_words # 이미 출제될 단어들 중에서 오답을 선택
        correct_meaning = correct_word['meaning_ko']
        
        # 오답 목록 선정 (현재 단어 제외)
        distractors = [w['meaning_ko'] for w in all_words if w['word_id'] != correct_word['word_id']]
        
        # 중복 방지를 위해 set 사용 후 리스트 변환
        unique_distractors = list(set(distractors))
        
        # 오답이 부족할 경우 전체 단어 목록에서 가져올 수 있으나, 여기서는 출제 단어 내에서만 처리
        
        if len(unique_distractors) < 3:
            # 오답 수가 부족하면 중복을 허용하거나 (단순화), 더 많은 단어에서 가져와야 함.
            # 여기서는 출제 목록에서 랜덤하게 3개 선택 (오답 목록에 정답이 포함될 수 있음 - UI 로직 단순화)
            # 이 로직은 실제로는 DB에서 제외 로직을 통해 구현해야 함.
            random_distractors = random.sample(distractors, min(3, len(distractors)))
        else:
            random_distractors = random.sample(unique_distractors, 3)
            
        options = random_distractors + [correct_meaning]
        random.shuffle(options)
        
        # 라디오 버튼에 보기 할당
        for i, opt in enumerate(options):
            self.mc_options[i].setText(opt)
            # 버튼의 사용자 데이터에 정답 여부를 저장
            self.mc_options[i].setProperty("is_correct_answer", opt == correct_meaning)

    def _submit_answer_and_next(self):
        """ 현재 문제의 답변을 채점하고 다음 문제로 넘어갑니다. """
        q_idx = self.current_question_index
        word_data = self.exam_words[q_idx]
        exam_type = self.type_combo.currentData()
        
        user_answer = ""
        is_correct = 0
        
        if exam_type == 'short_answer':
            user_answer = self.short_answer_input.text().strip()
            # 단답형 채점: 대소문자 무시, 띄어쓰기 무시, 쉼표 등 부호 제거 후 비교
            correct_answer_clean = ''.join(c for c in word_data['meaning_ko'] if c.isalnum()).lower()
            user_answer_clean = ''.join(c for c in user_answer if c.isalnum()).lower()
            
            if correct_answer_clean == user_answer_clean and user_answer_clean:
                is_correct = 1
                
        else: # multiple_choice
            selected_rb = self.mc_group.checkedButton()
            if selected_rb:
                user_answer = selected_rb.text()
                if selected_rb.property("is_correct_answer"):
                    is_correct = 1
            else:
                QMessageBox.warning(self, "답변 오류", "답변을 선택하거나 입력해주세요.")
                return # 답변이 없으면 다음으로 넘어가지 않음

        # 문제 상세 기록 (ExamController로 전달할 데이터 구조)
        self.exam_questions.append({
            "word_id": word_data['word_id'],
            "word_text": word_data['word_text'],
            "correct_answer": word_data['meaning_ko'],
            "user_answer": user_answer,
            "question_type": exam_type,
            "is_correct": is_correct,
        })
        
        self.current_question_index += 1
        self._show_question()

    def _end_exam(self):
        """ 시험을 종료하고 결과를 처리합니다. """
        
        # 1. 타이머 정지
        self.timer.stop()
        
        # 2. 총 시험 시간 계산
        total_duration_sec = int(datetime.now().timestamp() - self.exam_start_time)
        
        # 3. 시험 결과 기록 및 오답 노트 업데이트 (트랜잭션)
        result_summary = self.exam_controller.submit_and_record_exam(
            exam_type=self.type_combo.currentData(),
            duration_sec=total_duration_sec,
            questions_data=self.exam_questions
        )

        if result_summary:
            # 4. 결과 화면 표시
            self.score_label.setText(f"점수: {result_summary['score']}점")
            self.summary_label.setText(
                f"총 {result_summary['total_questions']}문제 중 "
                f"{result_summary['correct_count']}문제 정답 "
                f"({result_summary['score']}% 정답률)"
            )
            
            # 5. 상태 바 업데이트 알림
            self.exam_status_changed.emit()

            self.stacked_widget.setCurrentIndex(2)
        else:
            QMessageBox.critical(self, "오류", "시험 결과 기록에 실패했습니다. 관리자에게 문의하세요.")
            self.stacked_widget.setCurrentIndex(0) # 초기 화면으로 복귀

    # --- 외부 호출용 ---
    def reset_view(self):
        """ 뷰를 초기화하고 설정 화면으로 복귀합니다. """
        self.stacked_widget.setCurrentIndex(0)