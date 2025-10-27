import sys
import os
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QTabWidget, QWidget, 
    QStatusBar, QMenuBar, QAction, QMessageBox, 
    QLabel, QSizePolicy
)
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import Qt, QSize
from controllers.base_controller import BaseController
from utils.logger import setup_logger
from utils.file_handler import FileHandler # DB 초기화 기능 사용
from config import BASE_DIR, DB_SCHEMA_PATH, DB_INIT_DATA_PATH # 경로 설정

# 2025-10-20 - 스마트 단어장 - 메인 윈도우 UI 구조
# 파일 위치: views/main_window.py - v1
# 목적: 메인 윈도우 (QMainWindow), 탭 위젯, 메뉴 바, 상태 바 구성 및 스타일 로드

LOGGER = setup_logger()

class MainWindow(QMainWindow):
    """
    애플리케이션의 메인 윈도우. 탭 기반 구조와 공통 UI 요소를 관리합니다.
    """
    
    def __init__(self):
        super().__init__()
        
        # 1. DB 초기화 (애플리케이션 실행 전 필수)
        if not self._initialize_db():
            QMessageBox.critical(self, "심각한 오류", "데이터베이스 초기화에 실패했습니다. 프로그램을 종료합니다.")
            sys.exit(1)
            
        # 2. 컨트롤러 초기화 (모든 모델 인스턴스 포함)
        self.controller: BaseController = BaseController()
        
        # 3. UI 구성
        self._setup_ui()
        self._load_styles() # QSS 스타일 로드 및 적용

    def _initialize_db(self) -> bool:
        """
        데이터베이스 파일과 스키마를 초기화합니다.
        """
        LOGGER.info("Starting database initialization...")
        file_handler = FileHandler()
        # file_handler.initialize_database 내부에서 DBConnection을 사용
        return file_handler.initialize_database(DB_SCHEMA_PATH, DB_INIT_DATA_PATH)

    def _setup_ui(self):
        """
        메인 윈도우의 기본 요소(크기, 제목, 메뉴바, 상태바, 중앙 위젯)를 설정합니다.
        """
        # 윈도우 기본 설정 (화면 설계서 1.1)
        self.setWindowTitle("Smart Vocab Builder")
        self.setWindowIcon(QIcon(os.path.join(BASE_DIR, 'resources', 'icons', 'app_icon.png'))) # 아이콘은 리소스에 있다고 가정
        self.setGeometry(100, 100, 1200, 800) # 초기 크기 설정

        # 중앙 위젯 및 탭 위젯 설정 (탭 기반 구조)
        self.tab_widget = QTabWidget()
        self.setCentralWidget(self.tab_widget)

        # 탭 페이지 임시 생성 (추후 다른 View 클래스로 대체 예정)
        # 단어 관리, 플래시 카드, 시험, 통계, 설정
        self.tab_widget.addTab(QWidget(), "단어 관리")
        self.tab_widget.addTab(QWidget(), "플래시 카드")
        self.tab_widget.addTab(QWidget(), "시험")
        self.tab_widget.addTab(QWidget(), "통계")
        self.tab_widget.addTab(QWidget(), "설정")
        
        # 메뉴 바 설정 (화면 설계서 4.1)
        self._create_menu_bar()

        # 상태 바 설정 (화면 설계서 4.2)
        self._create_status_bar()

    def _create_menu_bar(self):
        """
        메뉴 바를 구성하고 각 액션을 연결합니다.
        """
        menu_bar = QMenuBar(self)
        self.setMenuBar(menu_bar)
        
        # 1. 파일 메뉴
        file_menu = menu_bar.addMenu("파일(&F)")
        
        # CSV 임포트 (F5)
        import_action = QAction(QIcon(), "단어 가져오기 (CSV)", self)
        import_action.triggered.connect(self._handle_import_action)
        file_menu.addAction(import_action)
        
        # CSV 엑스포트 (F5)
        export_action = QAction(QIcon(), "단어 내보내기 (CSV)", self)
        export_action.triggered.connect(self._handle_export_action)
        file_menu.addAction(export_action)
        
        file_menu.addSeparator()

        # 종료
        exit_action = QAction(QIcon(), "종료(&X)", self)
        exit_action.setShortcut('Ctrl+Q')
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # 2. 보기 메뉴 (테마 토글 포함)
        view_menu = menu_bar.addMenu("보기(&V)")
        theme_action = QAction(QIcon(), "테마 토글 (다크/라이트)", self)
        theme_action.triggered.connect(self._toggle_theme)
        view_menu.addAction(theme_action)

        # 3. 도움말 메뉴
        help_menu = menu_bar.addMenu("도움말(&H)")
        about_action = QAction(QIcon(), "Smart Vocab Builder 정보", self)
        about_action.triggered.connect(self._show_about_dialog)
        help_menu.addAction(about_action)

    def _create_status_bar(self):
        """
        상태 바를 구성하고 학습 통계 정보를 표시합니다. (화면 설계서 4.2)
        """
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        
        # 초기 상태 표시 레이블
        self.total_words_label = QLabel("총 단어: 0개")
        self.today_learning_label = QLabel(" | 오늘 학습: 0개")
        self.learning_time_label = QLabel(" | 학습 시간: 0분")
        
        # QLabel의 사이즈 정책을 설정하여 상태 바 전체를 채우지 않도록 함
        self.total_words_label.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Preferred)
        self.today_learning_label.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Preferred)
        self.learning_time_label.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Preferred)
        
        self.status_bar.addWidget(self.total_words_label)
        self.status_bar.addWidget(self.today_learning_label)
        self.status_bar.addWidget(self.learning_time_label)
        
        self.update_status_bar() # 초기 값 로드

    # --- 공통 기능 핸들러 ---
    
    def _handle_import_action(self):
        # TODO: F5 단어 임포트 다이얼로그 호출 로직 (WordController 사용)
        QMessageBox.information(self, "기능 예정", "단어 가져오기 기능은 추후 구현됩니다.")

    def _handle_export_action(self):
        # TODO: F5 단어 엑스포트 다이얼로그 호출 로직 (WordController 사용)
        QMessageBox.information(self, "기능 예정", "단어 내보내기 기능은 추후 구현됩니다.")

    def _toggle_theme(self):
        """
        현재 테마를 토글하고 스타일을 다시 로드합니다.
        """
        current_theme = self.controller.get_setting_value('theme_mode')
        new_theme = 'light' if current_theme == 'dark' else 'dark'
        
        if self.controller.update_app_setting('theme_mode', new_theme):
            self._load_styles(new_theme)
            LOGGER.info(f"Theme changed to: {new_theme}")
        else:
            QMessageBox.critical(self, "오류", "테마 변경에 실패했습니다.")
    
    def _load_styles(self, theme_mode: Optional[str] = None):
        """
        QSS 파일을 로드하여 애플리케이션에 적용합니다.
        """
        if theme_mode is None:
            # 설정에서 현재 테마 모드를 가져옴
            theme_mode = self.controller.get_setting_value('theme_mode')
            if theme_mode is None:
                theme_mode = 'light' # 기본값
            
        style_path = os.path.join(BASE_DIR, 'resources', 'styles', f'{theme_mode}_theme.qss')
        
        try:
            with open(style_path, 'r', encoding='utf-8') as f:
                self.setStyleSheet(f.read())
            LOGGER.info(f"Loaded QSS style: {style_path}")
        except FileNotFoundError:
            LOGGER.error(f"Style file not found: {style_path}. Using default style.")
        except Exception as e:
            LOGGER.error(f"Error loading QSS: {e}")

    def _show_about_dialog(self):
        """
        정보 다이얼로그를 표시합니다.
        """
        QMessageBox.about(self, "Smart Vocab Builder 정보",
                          "Smart Vocab Builder v1.0\n\n"
                          "개발: AI Software Student Team\n"
                          "목적: 수험생 및 대학생을 위한 영어 단어 학습 도구\n"
                          "기술 스택: Python, PyQt5, SQLite3")

    def update_status_bar(self):
        """
        컨트롤러에서 현재 학습 통계 정보를 가져와 상태 바를 업데이트합니다.
        """
        try:
            # TODO: LearningController를 사용하여 통계 요약을 가져와야 함.
            # BaseController는 LearningModel 인스턴스를 가지고 있지만,
            # 통계 조회를 위한 복잡한 로직은 LearningController에 있으므로,
            # 실제 구현 시에는 LearningController 인스턴스를 사용해야 합니다.
            # 여기서는 BaseController가 가진 모델을 통해 직접 접근합니다.
            
            # **임시 통계 로직** (실제 통계는 LearningController에서 가져와야 함)
            total_words = len(self.controller.word_model.select_active_words())
            today_time = self.controller.learning_model.get_total_learning_time_today()
            # 오늘 학습한 단어 수는 현재 세션을 알 수 없으므로 임시로 0
            today_words = 0
            
            self.total_words_label.setText(f"총 단어: {total_words}개")
            self.today_learning_label.setText(f" | 오늘 학습: {today_words}개")
            self.learning_time_label.setText(f" | 학습 시간: {today_time}분")
            
        except Exception as e:
            LOGGER.error(f"Failed to update status bar: {e}")
            self.total_words_label.setText("총 단어: (오류)")
            self.today_learning_label.setText(" | 오늘 학습: (오류)")
            self.learning_time_label.setText(" | 학습 시간: (오류)")

    def closeEvent(self, event):
        """
        윈도우 종료 시 DB 연결을 안전하게 닫습니다.
        """
        LOGGER.info("Closing application. Shutting down DB connections.")
        self.controller.close_all_db_connections()
        event.accept()

# 애플리케이션 실행 메인 로직 (main.py에서 사용될 내용)
if __name__ == '__main__':
    # config.py와 리소스 경로가 설정되어 있다고 가정
    # 예시를 위한 임시 경로 설정
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    sys.path.append(os.path.join(BASE_DIR, '..'))

    # DBConnection 클래스가 FileHandler에서 사용할 수 있도록 config.py에 DB_PATH 설정이 필수
    # 이 부분은 main.py에서 최종적으로 실행될 예정

    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())