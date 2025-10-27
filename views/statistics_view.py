from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QGroupBox, 
    QGridLayout, QSizePolicy
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from controllers.learning_controller import LearningController
from typing import Dict, Any, List, Tuple
from utils.logger import setup_logger

# Matplotlib를 PyQt5 위젯에 통합하기 위한 모듈
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.pyplot as plt
import random

# 2025-10-20 - 스마트 단어장 - 통계 뷰
# 파일 위치: views/statistics_view.py - v1
# 목적: 대시보드 요약 및 matplotlib 차트 시각화 구현 (화면 설계서 4.4)

LOGGER = setup_logger()

# Matplotlib 차트 위젯을 위한 기본 클래스
class MplCanvas(FigureCanvas):
    """ Matplotlib Figure를 포함하고 PyQt5에서 사용할 수 있는 캔버스 위젯입니다. """
    def __init__(self, parent=None, width=5, height=4, dpi=100):
        # 차트 스타일 설정 (다크 모드 대비)
        plt.style.use('default') # 기본 스타일 사용
        self.fig = Figure(figsize=(width, height), dpi=dpi, facecolor='none')
        self.axes = self.fig.add_subplot(111)
        super().__init__(self.fig)
        self.setParent(parent)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.updateGeometry()

class StatisticsView(QWidget):
    """
    '통계' 탭의 내용을 구성하는 뷰입니다.
    학습 대시보드와 통계 차트를 표시합니다.
    """
    
    def __init__(self, controller: LearningController):
        super().__init__()
        self.controller = controller
        
        self._setup_ui()

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        
        # 1. 대시보드 요약 패널
        summary_panel = self._create_summary_panel()
        main_layout.addWidget(summary_panel)
        
        # 2. 차트 영역
        chart_group = QGroupBox("학습 통계 시각화")
        chart_layout = QGridLayout(chart_group)
        
        # 2-1. 숙련도 분포 차트 (파이 차트)
        self.proficiency_canvas = MplCanvas(self, width=5, height=4)
        chart_layout.addWidget(self.proficiency_canvas, 0, 0)
        
        # 2-2. 일간 정답률 추이 차트 (라인 차트)
        self.daily_trend_canvas = MplCanvas(self, width=5, height=4)
        chart_layout.addWidget(self.daily_trend_canvas, 0, 1)

        chart_group.setLayout(chart_layout)
        main_layout.addWidget(chart_group)
        main_layout.addStretch(1)

    def _create_summary_panel(self) -> QWidget:
        """ 핵심 학습 지표를 보여주는 대시보드 패널을 생성합니다. """
        group_box = QGroupBox("대시보드 요약")
        h_layout = QHBoxLayout(group_box)
        h_layout.setContentsMargins(10, 10, 10, 10)
        
        self.summary_labels: Dict[str, QLabel] = {}
        data_points = [
            ("total_words", "총 단어 수", "0개", "green"),
            ("today_words", "오늘 학습 단어", "0개", "blue"),
            ("today_time", "오늘 학습 시간", "0분", "orange"),
            ("due_review", "D-Day 복습 단어", "0개", "red"),
        ]

        for key, title, default_value, color in data_points:
            v_layout = QVBoxLayout()
            title_label = QLabel(title)
            title_label.setFont(QFont('Arial', 10))
            
            value_label = QLabel(default_value)
            value_label.setFont(QFont('Arial', 18, QFont.Bold))
            value_label.setAlignment(Qt.AlignCenter)
            value_label.setStyleSheet(f"color: {color};")
            
            v_layout.addWidget(title_label, alignment=Qt.AlignCenter)
            v_layout.addWidget(value_label, alignment=Qt.AlignCenter)
            v_layout.setSpacing(5)
            
            h_layout.addLayout(v_layout)
            h_layout.addStretch(1)
            
            self.summary_labels[key] = value_label
            
        return group_box

    # --- 데이터 로딩 및 차트 그리기 ---
    
    def showEvent(self, event):
        """ 뷰가 화면에 표시될 때마다 데이터를 로드하고 차트를 다시 그립니다. """
        super().showEvent(event)
        self._load_data_and_draw_charts()

    def _load_data_and_draw_charts(self):
        """ 컨트롤러에서 데이터를 가져와 대시보드와 차트를 업데이트합니다. """
        try:
            # 1. 대시보드 요약 업데이트
            summary_data = self.controller.get_dashboard_summary()
            # self.summary_labels['total_words'].setText(f"{summary_data.get('total_words', 0)}개")
            # self.summary_labels['today_words'].setText(f"{summary_data.get('today_words', 0)}개")
            # self.summary_labels['today_time'].setText(f"{summary_data.get('today_time', 0)}분")
            # self.summary_labels['due_review'].setText(f"{summary_data.get('due_review', 0)}개")

            self.summary_labels['total_words'].setText(f"{summary_data.get('total_words_count', 0)}개")
            self.summary_labels['today_words'].setText(f"{summary_data.get('today_words', 0)}개")
            self.summary_labels['today_time'].setText(f"{summary_data.get('today_learning_time_min', 0)}분")
            self.summary_labels['due_review'].setText(f"{summary_data.get('wrong_words_count', 0)}개")
            
            # 2. 차트 데이터 가져오기
            proficiency_data = self.controller.get_word_proficiency_distribution()
            daily_trend_data = self.controller.get_daily_correct_rate_trend(days=7)
            
            # 3. 차트 그리기
            self._draw_proficiency_chart(proficiency_data)
            self._draw_daily_trend_chart(daily_trend_data)
            
        except Exception as e:
            LOGGER.error(f"Failed to load statistics data: {e}")

    def _draw_proficiency_chart(self, data: Dict[str, int]):
        """ 숙련도 분포를 파이 차트로 그립니다. """
        canvas = self.proficiency_canvas
        canvas.axes.clear() # 기존 차트 지우기
        
        # 데이터 정제 (SRS 레벨별 단어 수 등)
        labels = list(data.keys())
        sizes = list(data.values())
        
        # 색상 및 라벨 설정
        colors = ['#4CAF50', '#FFC107', '#F44336'] # Green, Yellow, Red 계열
        explode = [0.05] * len(labels)
        
        if sum(sizes) == 0:
             canvas.axes.text(0.5, 0.5, '데이터 부족', transform=canvas.axes.transAxes, 
                              ha='center', va='center', fontsize=16, color='gray')
        else:
            canvas.axes.pie(sizes, labels=labels, autopct='%1.1f%%', 
                             startangle=90, colors=colors[:len(labels)], 
                             explode=explode[:len(labels)], shadow=True)
            
        canvas.axes.set_title("단어 숙련도 분포")
        canvas.draw()

    def _draw_daily_trend_chart(self, data: List[Tuple[str, float]]):
        """ 최근 학습일의 정답률 추이를 라인 차트로 그립니다. """
        canvas = self.daily_trend_canvas
        canvas.axes.clear() # 기존 차트 지우기

        # 데이터 정제
        dates = [item.get('date') for item in data]
        rates = [item.get('rate') for item in data]
        
        if not dates:
             canvas.axes.text(0.5, 0.5, '데이터 부족', transform=canvas.axes.transAxes, 
                              ha='center', va='center', fontsize=16, color='gray')
        else:
            canvas.axes.plot(dates, rates, marker='o', linestyle='-', color='#1976D2', label='정답률 (%)')
            canvas.axes.set_ylim(0, 100) # 정답률은 0%에서 100% 사이
            canvas.axes.set_title("최근 7일 학습 정답률 추이")
            canvas.axes.set_xlabel("날짜")
            canvas.axes.set_ylabel("정답률 (%)")
            canvas.axes.grid(True, linestyle='--', alpha=0.6)
            canvas.axes.tick_params(axis='x', rotation=45) # x축 라벨 기울임
            canvas.fig.tight_layout() # 레이아웃 조정
            
        canvas.draw()