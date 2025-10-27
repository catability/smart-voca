from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QGroupBox, 
    QFormLayout, QSpinBox, QComboBox, QPushButton, 
    QMessageBox, QFileDialog
)
from PyQt5.QtCore import Qt, pyqtSignal
from controllers.base_controller import BaseController
from utils.file_handler import FileHandler
from utils.logger import setup_logger
import os
from datetime import datetime

# 2025-10-20 - 스마트 단어장 - 설정 뷰
# 파일 위치: views/settings_view.py - v1
# 목적: 애플리케이션 일반 설정 및 데이터 관리 기능 구현 (화면 설계서 4.5)

LOGGER = setup_logger()

class SettingsView(QWidget):
    """
    '설정' 탭의 내용을 구성하는 뷰입니다.
    애플리케이션 설정 변경 및 데이터 관리 기능을 제공합니다.
    """
    # 테마 변경 시 MainWindow에 알림 (QSS 재로드를 위함)
    theme_changed = pyqtSignal()
    # CSV 임포트/엑스포트 시 WordManagementView에 알림 (목록 새로고침 위함)
    data_changed = pyqtSignal()

    def __init__(self, controller: BaseController):
        super().__init__()
        self.controller = controller
        self.file_handler = FileHandler() # 파일 입출력 및 DB 백업/복구 로직
        
        self._setup_ui()
        self._load_current_settings()

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        
        # 1. 일반 설정 그룹
        general_group = self._create_general_settings_group()
        main_layout.addWidget(general_group)
        
        # 2. 데이터 관리 그룹
        data_group = self._create_data_management_group()
        main_layout.addWidget(data_group)
        
        main_layout.addStretch(1) # 하단 공백

    # --- 1. 일반 설정 그룹 UI ---
    
    def _create_general_settings_group(self) -> QGroupBox:
        group_box = QGroupBox("일반 설정")
        form_layout = QFormLayout(group_box)
        
        # 1. 일일 학습 단어 목표
        self.goal_word_spin = QSpinBox()
        self.goal_word_spin.setRange(10, 500)
        self.goal_word_spin.setSingleStep(10)
        self.goal_word_spin.valueChanged.connect(self._save_setting_words)
        form_layout.addRow(QLabel("일일 학습 목표 (단어 수):"), self.goal_word_spin)
        
        # 2. 일일 학습 시간 목표 (분)
        self.goal_time_spin = QSpinBox()
        self.goal_time_spin.setRange(10, 180)
        self.goal_time_spin.setSingleStep(10)
        self.goal_time_spin.valueChanged.connect(self._save_setting_time)
        form_layout.addRow(QLabel("일일 학습 목표 (시간, 분):"), self.goal_time_spin)

        # 3. 테마 모드 (F18)
        self.theme_combo = QComboBox()
        self.theme_combo.addItem("라이트 모드", "light")
        self.theme_combo.addItem("다크 모드", "dark")
        self.theme_combo.currentIndexChanged.connect(self._save_setting_theme)
        form_layout.addRow(QLabel("테마 설정:"), self.theme_combo)

        # 4. 자동 백업 주기 (추후 확장)
        self.backup_combo = QComboBox()
        self.backup_combo.addItem("백업 안 함", 0)
        self.backup_combo.addItem("1일 1회", 1)
        self.backup_combo.addItem("1주 1회", 7)
        self.backup_combo.setEnabled(False) # 현재 비활성화
        form_layout.addRow(QLabel("자동 백업 주기:"), self.backup_combo)
        
        return group_box

    # --- 2. 데이터 관리 그룹 UI ---

    def _create_data_management_group(self) -> QGroupBox:
        group_box = QGroupBox("데이터 관리")
        v_layout = QVBoxLayout(group_box)
        
        # 1. CSV 임포트/엑스포트 버튼 (F5)
        csv_layout = QHBoxLayout()
        self.import_btn = QPushButton("단어 가져오기 (CSV 임포트)")
        self.export_btn = QPushButton("단어 내보내기 (CSV 엑스포트)")
        self.import_btn.clicked.connect(self._handle_csv_import)
        self.export_btn.clicked.connect(self._handle_csv_export)
        csv_layout.addWidget(self.import_btn)
        csv_layout.addWidget(self.export_btn)
        v_layout.addLayout(csv_layout)
        
        v_layout.addWidget(QLabel("--- 데이터베이스 관리 ---"))

        # 2. DB 백업/복구 버튼
        db_layout = QHBoxLayout()
        self.backup_btn = QPushButton("DB 수동 백업")
        self.restore_btn = QPushButton("DB 복원 (백업 파일)")
        self.backup_btn.clicked.connect(self._handle_db_backup)
        self.restore_btn.clicked.connect(self._handle_db_restore)
        db_layout.addWidget(self.backup_btn)
        db_layout.addWidget(self.restore_btn)
        v_layout.addLayout(db_layout)

        # 3. DB 초기화 버튼
        self.reset_btn = QPushButton("경고: 모든 데이터 초기화 (공장 초기화)")
        self.reset_btn.setStyleSheet("background-color: #F44336; color: white;")
        self.reset_btn.clicked.connect(self._handle_db_reset)
        v_layout.addWidget(self.reset_btn)
        
        return group_box

    # --- 3. 설정 값 로드 및 저장 ---

    def _load_current_settings(self):
        """ DB에서 현재 설정값을 불러와 UI에 적용합니다. """
        
        # 1. 목표 설정
        word_goal = self.controller.get_setting_value('daily_word_goal')
        if word_goal is not None:
            self.goal_word_spin.setValue(int(word_goal))
            
        time_goal = self.controller.get_setting_value('daily_time_goal')
        if time_goal is not None:
            self.goal_time_spin.setValue(int(time_goal))
            
        # 2. 테마 설정 (시그널 차단 후 값 적용)
        self.theme_combo.blockSignals(True)
        theme = self.controller.get_setting_value('theme_mode')
        index = self.theme_combo.findData(theme or 'light')
        if index != -1:
            self.theme_combo.setCurrentIndex(index)
        self.theme_combo.blockSignals(False)
        
        # TODO: 자동 백업 주기 로드 (구현 예정)

    # 설정 변경 시 DB 저장 로직 (이름을 달리하여 시그널 충돌 방지)
    
    def _save_setting_words(self, value: int):
        self.controller.update_app_setting('daily_word_goal', str(value))
        LOGGER.info(f"Setting updated: daily_word_goal = {value}")

    def _save_setting_time(self, value: int):
        self.controller.update_app_setting('daily_time_goal', str(value))
        LOGGER.info(f"Setting updated: daily_time_goal = {value}")

    def _save_setting_theme(self, index: int):
        theme = self.theme_combo.itemData(index)
        if self.controller.update_app_setting('theme_mode', theme):
            self.theme_changed.emit() # MainWindow에 테마 변경 알림
            LOGGER.info(f"Setting updated: theme_mode = {theme}. Signal emitted.")
        else:
            QMessageBox.critical(self, "오류", "테마 설정 저장에 실패했습니다.")

    # --- 4. 데이터 관리 기능 핸들러 ---
    
    def _handle_csv_import(self):
        """ CSV 파일을 선택하여 단어를 DB에 가져옵니다. """
        file_path, _ = QFileDialog.getOpenFileName(self, "CSV 파일 선택", "", "CSV Files (*.csv);;All Files (*)")
        if not file_path:
            return

        try:
            # FileHandler를 통해 CSV를 파싱하고 WordController를 통해 DB에 저장
            result = self.file_handler.import_words_from_csv(file_path, self.controller.word_model)
            if result:
                QMessageBox.information(self, "가져오기 완료", 
                                        f"총 {result['total']}개 단어 처리.\n"
                                        f"추가: {result['added']}개, 업데이트: {result['updated']}개, 건너뜀: {result['skipped']}개")
                self.data_changed.emit() # 단어 목록 뷰 갱신 요청
            else:
                QMessageBox.critical(self, "가져오기 실패", "CSV 파일 처리 중 오류가 발생했습니다.")
        except Exception as e:
            LOGGER.error(f"CSV import failed: {e}")
            QMessageBox.critical(self, "오류", f"CSV 가져오기 중 오류가 발생했습니다: {str(e)}")

    def _handle_csv_export(self):
        """ 현재 DB의 모든 단어를 CSV 파일로 내보냅니다. """
        default_name = f"smart_vocab_export_{datetime.now().strftime('%Y%m%d')}.csv"
        file_path, _ = QFileDialog.getSaveFileName(self, "CSV 파일로 저장", default_name, "CSV Files (*.csv)")
        if not file_path:
            return
            
        try:
            # WordController를 통해 모든 단어를 가져와 FileHandler로 CSV 생성
            all_words = self.controller.word_model.select_all_words(include_deleted=False)
            if self.file_handler.export_words_to_csv(file_path, all_words):
                QMessageBox.information(self, "내보내기 완료", f"총 {len(all_words)}개의 단어를\n{file_path}에 저장했습니다.")
            else:
                QMessageBox.critical(self, "내보내기 실패", "파일 저장 중 오류가 발생했습니다.")
        except Exception as e:
            LOGGER.error(f"CSV export failed: {e}")
            QMessageBox.critical(self, "오류", f"CSV 내보내기 중 오류가 발생했습니다: {str(e)}")

    def _handle_db_backup(self):
        """ 현재 DB 파일을 백업합니다. """
        try:
            backup_path = self.file_handler.backup_database()
            if backup_path:
                QMessageBox.information(self, "백업 완료", f"데이터베이스 백업이 성공적으로 완료되었습니다.\n경로: {backup_path}")
            else:
                QMessageBox.critical(self, "백업 실패", "데이터베이스 백업에 실패했습니다.")
        except Exception as e:
            LOGGER.error(f"DB backup failed: {e}")
            QMessageBox.critical(self, "오류", f"DB 백업 중 오류가 발생했습니다: {str(e)}")

    def _handle_db_restore(self):
        """ 백업 파일을 선택하여 DB를 복원합니다. """
        reply = QMessageBox.question(self, 'DB 복원', 
                                     "경고: 현재 데이터는 모두 사라지고 선택한 파일로 복구됩니다. 계속하시겠습니까?", 
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.No:
            return

        file_path, _ = QFileDialog.getOpenFileName(self, "백업 DB 파일 선택", "", "SQLite DB Files (*.db *.sqlite3);;All Files (*)")
        if not file_path:
            return

        try:
            if self.file_handler.restore_database(file_path):
                QMessageBox.information(self, "복원 완료", "데이터베이스 복원이 완료되었습니다. 애플리케이션을 다시 시작해주세요.")
                # 앱 종료를 유도하거나 메인 윈도우 재시작 시그널 발생 (여기서는 종료 유도)
            else:
                QMessageBox.critical(self, "복원 실패", "데이터베이스 복원에 실패했습니다. 파일이 유효한지 확인하세요.")
        except Exception as e:
            LOGGER.error(f"DB restore failed: {e}")
            QMessageBox.critical(self, "오류", f"DB 복원 중 오류가 발생했습니다: {str(e)}")

    def _handle_db_reset(self):
        """ DB를 완전히 초기화하고 초기 데이터를 삽입합니다. """
        reply = QMessageBox.question(self, '데이터 초기화', 
                                     "경고: 모든 단어, 학습 기록, 시험 이력이 영구적으로 삭제됩니다. 계속하시겠습니까?", 
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            try:
                # FileHandler.initialize_database를 통해 DB 초기화 (스키마 재생성 및 초기 데이터 삽입)
                if self.file_handler.reset_all_data():
                    QMessageBox.information(self, "초기화 완료", "모든 데이터가 성공적으로 초기화되었습니다. 애플리케이션을 다시 시작해주세요.")
                    # 앱 종료 유도
                else:
                    QMessageBox.critical(self, "초기화 실패", "데이터 초기화에 실패했습니다.")
            except Exception as e:
                LOGGER.error(f"DB reset failed: {e}")
                QMessageBox.critical(self, "오류", f"데이터 초기화 중 오류가 발생했습니다: {str(e)}")