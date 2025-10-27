import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QTabWidget, QStatusBar, QMessageBox, QLabel
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import Qt, QSize

# 프로젝트 모듈 임포트
# Config, Logger, FileHandler
from config import DATABASE_PATH, LOG_FILE_PATH#, QSS_LIGHT_PATH, QSS_DARK_PATH
from utils.logger import setup_logger
from utils.file_handler import FileHandler

# Models
from models.base_model import BaseModel
from models.word_model import WordModel
from models.learning_model import LearningModel
from models.statistics_model import StatisticsModel
from models.exam_model import ExamModel

# Controllers
from controllers.base_controller import BaseController
from controllers.word_controller import WordController
from controllers.learning_controller import LearningController
from controllers.exam_controller import ExamController

# Views
from views.word_management_view import WordManagementView
from views.flashcard_view import FlashcardView
from views.exam_view import ExamView
from views.statistics_view import StatisticsView
from views.settings_view import SettingsView

# 2025-10-20 - 스마트 단어장 - 메인 실행 파일
# 파일 위치: main.py - v1
# 목적: 모든 모듈 통합, 초기화 및 애플리케이션 실행

LOGGER = setup_logger()

# --- 1. MainWindow 클래스 정의 (QTabWidget 통합) ---

class MainWindow(QMainWindow):
    """
    애플리케이션의 메인 윈도우. 탭 위젯과 상태 바를 관리합니다.
    """
    def __init__(self, controller: BaseController):
        super().__init__()
        self.base_controller = controller
        self.setWindowTitle("Smart Vocab Builder")
        self.setGeometry(100, 100, 1200, 800) # 초기 크기 설정 (화면 설계서 1.1)
        
        # QSS 스타일 로드
        self.current_theme = self.base_controller.get_setting_value('theme_mode') or 'light'
        self._load_styles()
        
        self._setup_controllers_and_views()
        self._setup_tab_widget()
        self._setup_menubar()
        self._setup_status_bar()
        self._connect_signals()

    def _setup_menubar(self):
        """ 메뉴바를 구성합니다. (F1-F4 단축키 연결은 생략하고 구조만 구현) """
        menu_bar = self.menuBar()
        
        # 파일 메뉴 (F)
        file_menu = menu_bar.addMenu("&파일(F)")
        file_menu.addAction("DB 백업 (Ctrl+B)", self._handle_db_backup)
        file_menu.addAction("CSV 임포트", self.settings_view._handle_csv_import)
        file_menu.addAction("종료 (Ctrl+Q)", self.close)

        # 도구 메뉴 (T)
        tool_menu = menu_bar.addMenu("&도구(T)")
        tool_menu.addAction("학습 시작 (F6)", lambda: self.tab_widget.setCurrentIndex(1))
        tool_menu.addAction("시험 시작 (F7)", lambda: self.tab_widget.setCurrentIndex(2))
        tool_menu.addAction("테마 변경", self._toggle_theme)

    def _setup_status_bar(self):
        """ 상태 바를 구성하고 초기 단어 정보를 표시합니다. (화면 설계서 4.2) """
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        
        self.total_words_label = QLabel("총 단어: 0개 |")
        self.learned_words_label = QLabel("오늘 학습: 0개 |")
        self.due_review_label = QLabel("복습 대기: 0개")

        self.status_bar.addWidget(self.total_words_label)
        self.status_bar.addWidget(self.learned_words_label)
        self.status_bar.addWidget(self.due_review_label)
        
        self._update_status_bar() # 초기 데이터 로드

    def _setup_controllers_and_views(self):
        """ 모든 컨트롤러와 뷰 인스턴스를 생성하고 연결합니다. """
        
        # # 1. Models (모두 BaseModel에 의존)
        # self.word_model = WordModel(self.base_controller.db_conn)
        # self.learning_model = LearningModel(self.base_controller.db_conn)
        # self.statistics_model = StatisticsModel(self.base_controller.db_conn)
        # self.exam_model = ExamModel(self.base_controller.db_conn)
        
        self.word_model = WordModel()
        self.learning_model = LearningModel()
        self.statistics_model = StatisticsModel()
        self.exam_model = ExamModel()

        # 2. Controllers
        # self.word_controller = WordController(self.base_controller.db_conn, self.word_model)
        # self.learning_controller = LearningController(self.base_controller.db_conn, self.word_model, self.learning_model, self.statistics_model)
        # self.exam_controller = ExamController(self.base_controller.db_conn, self.word_model, self.exam_model, self.learning_model)

        self.word_controller = WordController()
        self.learning_controller = LearningController()
        self.exam_controller = ExamController()

        # 3. Views
        self.word_management_view = WordManagementView(self.word_controller)
        self.flashcard_view = FlashcardView(self.learning_controller, self.word_controller)
        self.exam_view = ExamView(self.exam_controller, self.word_controller)
        self.statistics_view = StatisticsView(self.learning_controller)
        self.settings_view = SettingsView(self.base_controller)

    def _setup_tab_widget(self):
        """ 탭 위젯을 생성하고 뷰를 탭으로 추가합니다. (화면 설계서 1.1) """
        self.tab_widget = QTabWidget()
        self.tab_widget.addTab(self.word_management_view, "단어 관리")
        self.tab_widget.addTab(self.flashcard_view, "플래시 카드")
        self.tab_widget.addTab(self.exam_view, "시험")
        self.tab_widget.addTab(self.statistics_view, "통계")
        self.tab_widget.addTab(self.settings_view, "설정")
        
        self.setCentralWidget(self.tab_widget)
        
        # 탭 변경 시 시그널 연결 (통계 뷰 갱신 등)
        self.tab_widget.currentChanged.connect(self._handle_tab_change)

    def _connect_signals(self):
        """ 뷰 간의 통신 시그널을 연결합니다. """
        
        # 1. 단어 목록 변경 시 상태바 갱신 및 통계 갱신
        self.word_management_view.word_count_changed.connect(self._update_status_bar)
        
        # 2. 설정 변경 (테마, 데이터 변경)
        self.settings_view.theme_changed.connect(self._load_styles)
        self.settings_view.data_changed.connect(self.word_management_view._load_words) # 단어 관리 목록 새로고침

        # 3. 학습 및 시험 완료 시 상태바 갱신
        self.flashcard_view.learning_status_changed.connect(self._update_status_bar)
        self.exam_view.exam_status_changed.connect(self._update_status_bar)

    # --- UI 갱신 및 핸들러 메서드 ---

    def _update_status_bar(self):
        """ DB에서 최신 정보를 가져와 상태 바를 업데이트합니다. """
        try:
            summary = self.learning_controller.get_dashboard_summary()
            
            self.total_words_label.setText(f"총 단어: {summary.get('total_words', 0)}개 |")
            self.learned_words_label.setText(f"오늘 학습: {summary.get('today_words', 0)}개 |")
            self.due_review_label.setText(f"복습 대기: {summary.get('due_review', 0)}개")
            
        except Exception as e:
            LOGGER.error(f"Failed to update status bar: {e}")

    def _handle_db_backup(self):
        """ 메뉴바에서 DB 수동 백업 호출 """
        self.settings_view._handle_db_backup()
    
    def _toggle_theme(self):
        """ 메뉴바에서 테마 변경 호출 """
        new_theme = 'dark' if self.current_theme == 'light' else 'light'
        # settings_view의 로직을 통해 DB 저장 및 시그널 발생 유도
        index = self.settings_view.theme_combo.findData(new_theme)
        if index != -1:
             self.settings_view.theme_combo.setCurrentIndex(index)

    def _load_styles(self):
        """ 현재 설정된 테마 모드에 따라 QSS 파일을 로드합니다. """
        self.current_theme = self.base_controller.get_setting_value('theme_mode') or 'light'
        
        # if self.current_theme == 'dark':
        #     qss_path = QSS_DARK_PATH
        # else:
        #     qss_path = QSS_LIGHT_PATH
            
        # try:
        #     with open(qss_path, 'r', encoding='utf-8') as f:
        #         self.setStyleSheet(f.read())
        #     LOGGER.info(f"Loaded {self.current_theme} theme style.")
        # except FileNotFoundError:
        #     LOGGER.warning(f"QSS file not found at {qss_path}. Using default style.")

    def _handle_tab_change(self, index: int):
        """ 탭이 변경될 때 호출됩니다. """
        # 통계 탭(Index 3)으로 이동 시 데이터 새로고침
        if index == 3:
            self.statistics_view._load_data_and_draw_charts()
            
    def closeEvent(self, event):
        """ 윈도우가 닫힐 때 DB 연결을 종료합니다. """
        self.base_controller.close_all_db_connections()
        LOGGER.info("Application closed and DB connection terminated.")
        super().closeEvent(event)

# --- 2. 메인 실행 함수 ---

def main():
    """ 애플리케이션의 진입점입니다. """
    
    # 1. 파일 시스템 초기화 (DB 및 로그 파일 경로 확인)
    FileHandler().initialize_database('database/schema.sql', 'database/init_data.sql') 

    # 2. QApplication 인스턴스 생성
    app = QApplication(sys.argv)
    
    # 3. BaseController 및 DB 초기화
    try:
        # 기존
        # base_controller = BaseController(DATABASE_PATH)
        # 초기화: DB 파일이 없거나 테이블이 없는 경우 테이블 생성 및 초기 설정값 삽입
        # base_controller.initialize_database_if_needed()
        
        # 수정
        base_controller = BaseController()
        
    except Exception as e:
        QMessageBox.critical(None, "Fatal Error", f"데이터베이스 연결/초기화에 실패했습니다. 프로그램을 종료합니다.\n{e}")
        LOGGER.critical(f"DB initialization failed: {e}")
        sys.exit(1)

    # 4. MainWindow 생성 및 실행
    main_window = MainWindow(base_controller)
    main_window.show()
    
    # 5. 애플리케이션 이벤트 루프 시작
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()