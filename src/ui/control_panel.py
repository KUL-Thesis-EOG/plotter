from typing import Optional
from PyQt6 import QtWidgets, QtCore

from src.ui.serial_control import SerialControlPanel
from src.ui.participant_control import ParticipantControlPanel


class ControlPanel(QtWidgets.QWidget):
    """Widget containing all control panels"""

    portSelected = QtCore.pyqtSignal(str)
    participantRegistered = QtCore.pyqtSignal(int)
    sessionStartRequested = QtCore.pyqtSignal()
    sessionPauseRequested = QtCore.pyqtSignal()
    sessionResumeRequested = QtCore.pyqtSignal()
    sessionEndRequested = QtCore.pyqtSignal()

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)
        self.main_layout = QtWidgets.QVBoxLayout(self)

        # Create top control panels layout
        self.top_controls_layout = QtWidgets.QHBoxLayout()

        # Create serial control panel
        self.serial_panel = SerialControlPanel()

        # Create participant control panel
        self.participant_panel = ParticipantControlPanel()

        # Add top control panels to the layout
        self.top_controls_layout.addWidget(self.serial_panel)
        self.top_controls_layout.addWidget(self.participant_panel)

        # Add top controls to main layout
        self.main_layout.addLayout(self.top_controls_layout)

        # Connect serial panel signals
        self.serial_panel.portSelected.connect(self.portSelected)

        # Connect participant panel signals
        self.participant_panel.participantRegistered.connect(self.participantRegistered)
        self.participant_panel.sessionStartRequested.connect(self.sessionStartRequested)
        self.participant_panel.sessionPauseRequested.connect(self.sessionPauseRequested)
        self.participant_panel.sessionResumeRequested.connect(
            self.sessionResumeRequested
        )
        self.participant_panel.sessionEndRequested.connect(self.sessionEndRequested)

        # Set stretch factors to make top panels take minimal space
        self.main_layout.setStretch(0, 0)  # Top panels - minimal space
        self.main_layout.setStretch(1, 1)  # Channel panels - all remaining space
