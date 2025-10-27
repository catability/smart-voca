from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, 
    QLineEdit, QPushButton, QComboBox, QHeaderView, 
    QAbstractItemView, QTableWidgetItem, QMessageBox, QLabel
)
from PyQt5.QtCore import Qt, pyqtSignal
from controllers.word_controller import WordController
from utils.logger import setup_logger
from typing import List, Dict, Any, Optional

# 2025-10-20 - 스마트 단어장 - 단어 관리 뷰
# 파일 위치: views/word_management_view.py - v1
# 목적: 단어 목록 조회, 검색, 추가/수정/삭제 UI 구현 (화면 설계서 3.1)

LOGGER = setup_logger()

class WordManagementView(QWidget):
    """
    '단어 관리' 탭의 내용을 구성하는 뷰입니다.
    단어 목록 표시, 검색, 필터링, CRUD 버튼을 제공하며,
    MainWindow의 상태 바 업데이트를 위해 시그널을 방출합니다.
    """
    
    # MainWindow에 단어 수가 변경되었음을 알리는 시그널
    word_count_changed = pyqtSignal()

    def __init__(self, controller: WordController):
        super().__init__()
        # WordController 인스턴스 (BaseController에서 상속받은 모델 접근 가능)
        self.controller = controller 
        self.current_words: List[Dict[str, Any]] = []
        self._setup_ui()
        self._load_categories()
        self._load_words()

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        
        # 1. 검색 및 필터링 영역 (Control Panel)
        control_panel = self._create_control_panel()
        main_layout.addWidget(control_panel)
        
        # 2. 단어 목록 테이블 영역 (QTableWidget)
        self.word_table = self._create_word_table()
        main_layout.addWidget(self.word_table)
        
        # 3. CRUD 버튼 영역
        crud_buttons = self._create_crud_buttons()
        main_layout.addLayout(crud_buttons)

    def _create_control_panel(self) -> QWidget:
        """ 검색 입력란, 카테고리 필터, CSV 버튼을 포함하는 위젯을 생성합니다. """
        control_widget = QWidget()
        h_layout = QHBoxLayout(control_widget)
        h_layout.setContentsMargins(0, 0, 0, 0)

        # 검색 영역
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("검색 (단어, 의미, 메모)")
        self.search_input.returnPressed.connect(self._search_words)
        h_layout.addWidget(self.search_input)
        
        self.search_button = QPushButton("검색")
        self.search_button.clicked.connect(self._search_words)
        h_layout.addWidget(self.search_button)
        
        # 카테고리 필터
        h_layout.addWidget(QLabel("카테고리:"))
        self.category_combo = QComboBox()
        self.category_combo.setMinimumWidth(120)
        self.category_combo.currentIndexChanged.connect(self._filter_by_category)
        h_layout.addWidget(self.category_combo)
        
        h_layout.addStretch(1) # 중앙 공백을 밀어냄
        
        return control_widget

    def _create_word_table(self) -> QTableWidget:
        """ 단어 목록을 표시할 QTableWidget을 생성 및 설정합니다. """
        table = QTableWidget()
        
        headers = ["ID", "단어", "의미", "카테고리", "메모", "즐겨찾기", "수정일"]
        table.setColumnCount(len(headers))
        table.setHorizontalHeaderLabels(headers)
        
        # QTableWidget 설정
        table.setEditTriggers(QAbstractItemView.NoEditTriggers) # 편집 불가능
        table.setSelectionBehavior(QAbstractItemView.SelectRows) # 행 단위 선택
        table.setSelectionMode(QAbstractItemView.SingleSelection) # 단일 행 선택
        
        # 컬럼 너비 조정
        header = table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents) 
        header.setSectionResizeMode(1, QHeaderView.Stretch) 
        header.setSectionResizeMode(2, QHeaderView.Stretch) 
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents) 
        header.setSectionResizeMode(4, QHeaderView.Stretch) 
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents) 
        header.setSectionResizeMode(6, QHeaderView.ResizeToContents) 

        # 테이블 더블 클릭 이벤트 연결 (단어 수정 다이얼로그 호출)
        table.doubleClicked.connect(self._handle_table_double_click)
        
        return table

    def _create_crud_buttons(self) -> QHBoxLayout:
        """ 단어 추가, 수정, 삭제 버튼을 포함하는 레이아웃을 생성합니다. """
        h_layout = QHBoxLayout()
        h_layout.addStretch(1) # 오른쪽 정렬
        
        self.add_btn = QPushButton("단어 추가")
        self.update_btn = QPushButton("단어 수정")
        self.delete_btn = QPushButton("단어 삭제")
        
        self.add_btn.clicked.connect(self._add_word_dialog)
        self.update_btn.clicked.connect(self._update_word_dialog)
        self.delete_btn.clicked.connect(self._delete_word)

        h_layout.addWidget(self.add_btn)
        h_layout.addWidget(self.update_btn)
        h_layout.addWidget(self.delete_btn)
        
        return h_layout

    # --- 데이터 및 로직 처리 ---

    def _load_categories(self):
        """ WordController를 통해 카테고리 목록을 불러와 콤보 박스에 채웁니다. """
        self.category_combo.blockSignals(True)
        self.category_combo.clear()
        self.category_combo.addItem("전체 카테고리")
        
        categories = self.controller.get_all_categories()
        for cat in categories:
            self.category_combo.addItem(cat)
            
        self.category_combo.blockSignals(False)

    def _load_words(self, word_list: Optional[List[Dict[str, Any]]] = None):
        """
        단어 목록을 불러와 테이블에 표시합니다.
        """
        if word_list is None:
            self.current_words = self.controller.get_all_active_words()
        else:
            self.current_words = word_list
            
        self.word_table.setRowCount(len(self.current_words))
        
        for row_idx, word in enumerate(self.current_words):
            self.word_table.setItem(row_idx, 0, QTableWidgetItem(str(word.get('word_id', ''))))
            self.word_table.setItem(row_idx, 1, QTableWidgetItem(word.get('word_text', '')))
            self.word_table.setItem(row_idx, 2, QTableWidgetItem(word.get('meaning_ko', '')))
            self.word_table.setItem(row_idx, 3, QTableWidgetItem(word.get('category', '')))
            self.word_table.setItem(row_idx, 4, QTableWidgetItem(word.get('memo', '')))
            fav_text = "★" if word.get('is_favorite', 0) == 1 else ""
            self.word_table.setItem(row_idx, 5, QTableWidgetItem(fav_text))
            self.word_table.setItem(row_idx, 6, QTableWidgetItem(word.get('modified_date', '')[:10]))

        # word_id 컬럼 숨김
        self.word_table.setColumnHidden(0, True)

        # 상태 바 업데이트 시그널 방출 (MainWindow에서 연결되어 상태바를 업데이트할 예정)
        self.word_count_changed.emit()
        LOGGER.info(f"Loaded {len(self.current_words)} words into the table.")

    def _get_selected_word_id(self) -> Optional[int]:
        """ 테이블에서 선택된 행의 word_id를 반환합니다. """
        selected_rows = self.word_table.selectedIndexes()
        if not selected_rows:
            QMessageBox.warning(self, "선택 오류", "먼저 목록에서 단어를 선택해주세요.")
            return None
            
        row = selected_rows[0].row()
        word_id_item = self.word_table.item(row, 0)
        
        try:
            return int(word_id_item.text())
        except Exception:
            return None

    def _search_words(self):
        """ 검색 입력 값으로 단어를 검색하고 테이블을 업데이트합니다. """
        keyword = self.search_input.text().strip()
        
        if keyword:
            search_results = self.controller.search_words(keyword, search_by='all')
            self._load_words(search_results)
        else:
            self._load_words() 
            
        # 검색 후 카테고리 필터를 '전체 카테고리'로 리셋
        self.category_combo.setCurrentIndex(0) 

    def _filter_by_category(self, index: int):
        """ 카테고리 콤보 박스 값 변경 시 단어 목록을 필터링합니다. """
        category = self.category_combo.currentText()
        self.search_input.clear()

        if category == "전체 카테고리":
            self._load_words()
        else:
            filtered_words = self.controller.get_words_by_category(category)
            self._load_words(filtered_words)

    # --- CRUD 버튼 액션 (다이얼로그 구현 전 임시) ---

    def _add_word_dialog(self):
        """ 단어 추가 다이얼로그를 열고 완료 후 목록을 새로고침합니다. """
        # TODO: WordEditDialog 구현 후 연동
        QMessageBox.information(self, "기능 예정", "단어 추가 다이얼로그가 곧 구현됩니다.")

    def _update_word_dialog(self):
        """ 선택된 단어의 수정 다이얼로그를 엽니다. """
        word_id = self._get_selected_word_id()
        if word_id is None:
            return
            
        # TODO: WordEditDialog 구현 후 연동
        QMessageBox.information(self, "기능 예정", f"단어 ID {word_id} 수정 다이얼로그가 곧 구현됩니다.")
            
    def _delete_word(self):
        """ 선택된 단어를 논리적으로 삭제합니다. """
        word_id = self._get_selected_word_id()
        if word_id is None:
            return

        reply = QMessageBox.question(self, '단어 삭제', 
                                     "선택한 단어를 정말로 삭제하시겠습니까? 이 작업은 되돌릴 수 없습니다.", 
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)

        if reply == QMessageBox.Yes:
            if self.controller.delete_word(word_id):
                QMessageBox.information(self, "삭제 완료", "단어가 성공적으로 삭제되었습니다.")
                self._load_words() # 목록 새로고침
                self._load_categories() # 카테고리 목록 새로고침
            else:
                QMessageBox.critical(self, "삭제 실패", "단어 삭제에 실패했습니다. 로그를 확인하세요.")

    def _handle_table_double_click(self):
        """ 테이블을 더블 클릭했을 때 수정 다이얼로그를 호출합니다. """
        self._update_word_dialog()