from typing import Optional, Tuple, List
from PyQt6 import QtWidgets, QtCore

from src.ui.time_control import TimeControlPanel
from src.ui.voltage_control import VoltageControlPanel
from src.ui.statistics import StatisticsPanel
from src.ui.serial_control import SerialControlPanel
from src.ui.participant_control import ParticipantControlPanel


class ChannelControlPanel(QtWidgets.QGroupBox):
    """Controls for a specific channel"""

    def __init__(
        self, channel_name: str, parent: Optional[QtWidgets.QWidget] = None
    ) -> None:
        super().__init__(f"{channel_name} Controls", parent)
        self.layout = QtWidgets.QVBoxLayout(self)

        # Create sub-panels for this channel
        self.time_panel = TimeControlPanel()
        self.voltage_panel = VoltageControlPanel()
        self.stats_panel = StatisticsPanel(channel_name)

        # Add panels to layout
        self.layout.addWidget(self.time_panel)
        self.layout.addWidget(self.voltage_panel)
        self.layout.addWidget(self.stats_panel)


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

        # Create horizontal layout for channel controls
        self.channels_layout = QtWidgets.QHBoxLayout()

        # Create channel control panels
        self.vertical_channel_panel = ChannelControlPanel("Vertical Channel")
        self.horizontal_channel_panel = ChannelControlPanel("Horizontal Channel")

        # Add channel panels to layout
        self.channels_layout.addWidget(self.vertical_channel_panel)
        self.channels_layout.addWidget(self.horizontal_channel_panel)

        # Add channel layout to main layout
        self.main_layout.addLayout(self.channels_layout)

        # Set stretch factors to make top panels take minimal space
        self.main_layout.setStretch(0, 0)  # Top panels - minimal space
        self.main_layout.setStretch(1, 1)  # Channel panels - all remaining space
