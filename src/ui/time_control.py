from typing import List, Optional
from PyQt6 import QtWidgets
from PyQt6.QtCore import pyqtSignal


class TimeControlPanel(QtWidgets.QGroupBox):
    """Panel for controlling the time range of the oscilloscope"""

    timeRangeChanged = pyqtSignal(int)
    viewAllRequested = pyqtSignal()

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__("Time Range (seconds)", parent)
        self.layout = QtWidgets.QHBoxLayout(self)

        # Add time range buttons (removed 1s and 2s options)
        self.time_ranges: List[int] = [2, 4, 10]
        for t_range in self.time_ranges:
            btn = QtWidgets.QPushButton(f"{t_range}s")
            btn.clicked.connect(lambda checked, r=t_range: self.set_time_range(r))
            self.layout.addWidget(btn)

        # Add view all button
        self.view_all_btn = QtWidgets.QPushButton("View All")
        self.view_all_btn.clicked.connect(self.request_view_all)
        self.layout.addWidget(self.view_all_btn)

    def set_time_range(self, seconds: int) -> None:
        """Change the time range and emit signal"""
        self.timeRangeChanged.emit(seconds)

    def request_view_all(self) -> None:
        """Request to view all collected data"""
        self.viewAllRequested.emit()
