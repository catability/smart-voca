from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
    QLineEdit, QTextEdit, QPushButton, QComboBox, 
    QMessageBox, QFormLayout
)
from PyQt5.QtCore import Qt, pyqtSignal
from controllers.word_controller import WordController
from typing import Optional, Dict, Any
from utils.logger import setup_logger

# 2025-10-20 - 스마트 단어장 - 단어 추가/수정 다이얼로그
# 파일 위치: views/word_edit_dialog.py - v1
# 목적: 단어 CRUD의 입력 폼 및 유효성 검사 구현 (화면 설계서 4.1. 단어 추가 시나리오)

LOGGER = setup_logger()

class WordEditDialog(QDialog):
    """
    단어 추가 또는 수정을 위한 모달 다이얼로그입니다.
    """
    # 저장 완료 시 WordManagementView에 새로고침을 알리는 시그널
    word_saved = pyqtSignal()

    def __init__(self, controller: WordController, word_id: Optional[int] = None, parent=None):
        super().__init__(parent)
        self.controller = controller
        self.word_id = word_id
        self.is_edit_mode = word_id is not None
        
        self.setWindowTitle("단어 수정" if self.is_edit_mode else "새 단어 추가")
        self.setModal(True)
        self.setGeometry(200, 200, 450, 300)
        
        self._setup_ui()
        self._load_categories()
        
        if self.is_edit_mode:
            self._load_word_data()

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        form_layout = QFormLayout()
        
        # 1. 단어 입력 필드 (필수)
        self.word_input = QLineEdit()
        self.word_input.setPlaceholderText("단어를 입력하세요 (예: develop)")
        form_layout.addRow(QLabel("단어 (Word) *"), self.word_input)
        
        # 2. 의미 입력 필드 (필수)
        self.meaning_input = QLineEdit()
        self.meaning_input.setPlaceholderText("의미를 입력하세요 (예: 개발하다, 발전시키다)")
        form_layout.addRow(QLabel("의미 (Meaning) *"), self.meaning_input)

        # 3. 카테고리 선택 (필수)
        self.category_combo = QComboBox()
        self.category_combo.setEditable(True) # 새 카테고리 직접 입력 허용
        form_layout.addRow(QLabel("카테고리 (Category) *"), self.category_combo)

        # 4. 메모 입력 필드 (선택)
        self.memo_input = QTextEdit()
        self.memo_input.setPlaceholderText("추가 설명이나 예문 등을 입력하세요.")
        self.memo_input.setMaximumHeight(80)
        form_layout.addRow(QLabel("메모 (Memo)"), self.memo_input)

        main_layout.addLayout(form_layout)
        
        # 5. 버튼 영역
        button_layout = QHBoxLayout()
        self.save_btn = QPushButton("저장")
        self.cancel_btn = QPushButton("취소")
        
        self.save_btn.clicked.connect(self._save_word)
        self.cancel_btn.clicked.connect(self.reject) # QDialog의 reject 메서드는 QDialog.Rejected를 반환하며 창을 닫음

        button_layout.addStretch(1)
        button_layout.addWidget(self.save_btn)
        button_layout.addWidget(self.cancel_btn)
        
        main_layout.addLayout(button_layout)
        
    def _load_categories(self):
        """ 기존 카테고리 목록을 불러와 콤보 박스에 채웁니다. """
        self.category_combo.clear()
        self.category_combo.addItem("기타") # 기본 카테고리
        categories = self.controller.get_all_categories()
        for cat in categories:
            # 중복 방지 (기타는 이미 추가됨)
            if cat and cat not in ["기타"]:
                self.category_combo.addItem(cat)
                
    def _load_word_data(self):
        """ 수정 모드일 때 기존 단어 정보를 불러와 필드에 채웁니다. """
        word_data = self.controller.get_word_by_id(self.word_id)
        
        if word_data:
            self.word_input.setText(word_data.get('word_text', ''))
            self.meaning_input.setText(word_data.get('meaning_ko', ''))
            self.memo_input.setText(word_data.get('memo', ''))
            
            # 카테고리 설정
            category = word_data.get('category', '기타')
            index = self.category_combo.findText(category)
            if index != -1:
                self.category_combo.setCurrentIndex(index)
            else:
                # DB에는 있지만 콤보 박스에 없는 경우 (직접 입력한 경우)
                self.category_combo.setCurrentText(category)
        else:
            QMessageBox.critical(self, "오류", "단어 정보를 불러오는 데 실패했습니다.")
            self.reject()

    def _validate_inputs(self) -> Optional[Dict[str, Any]]:
        """ 입력값의 유효성을 검사하고, 유효하면 데이터를 딕셔너리로 반환합니다. """
        word_text = self.word_input.text().strip()
        meaning_ko = self.meaning_input.text().strip()
        category = self.category_combo.currentText().strip()
        memo = self.memo_input.toPlainText().strip()
        
        if not word_text:
            QMessageBox.warning(self, "입력 오류", "단어(Word)를 반드시 입력해야 합니다.")
            self.word_input.setFocus()
            return None
            
        if not meaning_ko:
            QMessageBox.warning(self, "입력 오류", "의미(Meaning)를 반드시 입력해야 합니다.")
            self.meaning_input.setFocus()
            return None

        if not category:
            QMessageBox.warning(self, "입력 오류", "카테고리를 반드시 입력하거나 선택해야 합니다.")
            self.category_combo.setFocus()
            return None

        return {
            "word_text": word_text,
            "meaning_ko": meaning_ko,
            "category": category,
            "memo": memo,
        }

    def _save_word(self):
        """ 유효성 검사를 통과한 데이터를 저장(추가/수정)합니다. """
        word_data = self._validate_inputs()
        if word_data is None:
            return

        success = False
        
        if self.is_edit_mode:
            # 1. 수정 모드
            success = self.controller.update_word(self.word_id, **word_data)
            message = "단어 정보가 성공적으로 수정되었습니다."
            error_message = "단어 수정에 실패했습니다."
        else:
            # 2. 추가 모드
            result = self.controller.add_word(**word_data)
            if result is not None:
                if result == 0:
                    QMessageBox.warning(self, "추가 실패", f"'{word_data['word_text']}' 단어가 이미 존재합니다. 다른 단어를 입력해주세요.")
                    return
                else:
                    success = True
                    message = "새 단어가 성공적으로 추가되었습니다."
            error_message = "단어 추가에 실패했습니다."


        if success:
            QMessageBox.information(self, "저장 완료", message)
            self.word_saved.emit() # WordManagementView에 새로고침 알림
            self.accept() # QDialog의 accept 메서드는 QDialog.Accepted를 반환하며 창을 닫음
        else:
            QMessageBox.critical(self, "저장 실패", error_message + " 로그를 확인해주세요.")

# if __name__를 통한 독립 실행 테스트 코드는 생략