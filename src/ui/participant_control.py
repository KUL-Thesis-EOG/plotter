from typing import Optional
from PyQt6 import QtWidgets, QtCore, QtGui


class ParticipantControlPanel(QtWidgets.QGroupBox):
    """Control panel for participant registration and experiment session management"""

    participantRegistered = QtCore.pyqtSignal(int)
    sessionStartRequested = QtCore.pyqtSignal()
    sessionPauseRequested = QtCore.pyqtSignal()
    sessionResumeRequested = QtCore.pyqtSignal()
    sessionEndRequested = QtCore.pyqtSignal()

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__("Experiment Control", parent)

        # Set up layout
        self.layout = QtWidgets.QVBoxLayout(self)

        # Create participant ID entry components
        self.participant_layout = QtWidgets.QHBoxLayout()
        self.participant_label = QtWidgets.QLabel("Participant ID:")
        self.participant_input = QtWidgets.QSpinBox()
        self.participant_input.setMinimum(1)
        self.participant_input.setMaximum(9999)
        self.participant_input.setSingleStep(1)
        self.participant_input.setFixedWidth(100)
        self.register_button = QtWidgets.QPushButton("Register")
        self.register_button.clicked.connect(self._register_participant)

        self.participant_layout.addWidget(self.participant_label)
        self.participant_layout.addWidget(self.participant_input)
        self.participant_layout.addWidget(self.register_button)
        self.participant_layout.addStretch(1)

        # Create session control components
        self.session_layout = QtWidgets.QHBoxLayout()
        self.start_button = QtWidgets.QPushButton("Start Recording")
        self.start_button.clicked.connect(self._toggle_session)
        self.start_button.setEnabled(False)
        self.start_button.setStyleSheet("font-weight: bold;")

        self.pause_button = QtWidgets.QPushButton("Pause")
        self.pause_button.clicked.connect(self._toggle_pause)
        self.pause_button.setEnabled(False)

        self.end_button = QtWidgets.QPushButton("End Session")
        self.end_button.clicked.connect(self._end_session)
        self.end_button.setEnabled(False)
        self.end_button.setStyleSheet("")

        self.session_layout.addWidget(self.start_button)
        self.session_layout.addWidget(self.pause_button)
        self.session_layout.addWidget(self.end_button)
        self.session_layout.addStretch(1)

        # Create status display
        self.status_label = QtWidgets.QLabel("Status: No participant registered")
        self.status_label.setStyleSheet(
            "color: #666666; background-color: #f0f0f0; padding: 3px; border-radius: 3px;"
        )

        # Add components to main layout
        self.layout.addLayout(self.participant_layout)
        self.layout.addLayout(self.session_layout)
        self.layout.addWidget(self.status_label)

        # Initialize state
        self.participant_id = None
        self.session_active = False
        self.session_paused = False

    def _register_participant(self) -> None:
        """Register a participant and enable session controls"""
        participant_id = self.participant_input.value()
        if participant_id > 0:
            self.participant_id = participant_id
            self.participantRegistered.emit(participant_id)

            # Update UI state
            self.participant_input.setEnabled(False)
            self.register_button.setEnabled(False)
            self.start_button.setEnabled(True)

            # Update status
            self.status_label.setText(
                f"Status: Participant {participant_id} registered"
            )
            self.status_label.setStyleSheet(
                "color: green; font-weight: bold; background-color: #e0ffe0; padding: 3px; border-radius: 3px;"
            )

    def _toggle_session(self) -> None:
        """Start or end the recording session"""
        if not self.session_active:
            # Start session
            self.session_active = True
            self.sessionStartRequested.emit()

            # Update UI state
            self.start_button.setText("Stop Recording")
            self.start_button.setStyleSheet(
                "font-weight: bold;"
            )
            self.pause_button.setEnabled(True)
            self.end_button.setEnabled(True)

            # Update status
            self.status_label.setText(
                f"Status: Recording data for participant {self.participant_id}"
            )
            self.status_label.setStyleSheet(
                "color: green; font-weight: bold; background-color: #e0ffe0; padding: 3px; border-radius: 3px;"
            )
        else:
            # Stop recording
            self._end_session()

    def _toggle_pause(self) -> None:
        """Pause or resume the recording session"""
        if not self.session_paused:
            # Pause session
            self.session_paused = True
            self.sessionPauseRequested.emit()

            # Update UI state
            self.pause_button.setText("Resume")

            # Update status
            self.status_label.setText(
                f"Status: Recording PAUSED for participant {self.participant_id}"
            )
            self.status_label.setStyleSheet(
                "color: orange; font-weight: bold; background-color: #fff0e0; padding: 3px; border-radius: 3px;"
            )
        else:
            # Resume session
            self.session_paused = False
            self.sessionResumeRequested.emit()

            # Update UI state
            self.pause_button.setText("Pause")

            # Update status
            self.status_label.setText(
                f"Status: Recording data for participant {self.participant_id}"
            )
            self.status_label.setStyleSheet(
                "color: green; font-weight: bold; background-color: #e0ffe0; padding: 3px; border-radius: 3px;"
            )

    def _end_session(self) -> None:
        """End the current recording session"""
        self.session_active = False
        self.session_paused = False
        self.sessionEndRequested.emit()

        # Update UI state
        self.start_button.setText("Start Recording")
        self.start_button.setStyleSheet("font-weight: bold;")
        self.pause_button.setText("Pause")
        self.pause_button.setEnabled(False)
        self.end_button.setEnabled(False)

        # Enable new participant registration
        self.participant_input.setEnabled(True)
        self.register_button.setEnabled(True)

        # Update status
        self.status_label.setText("Status: Session ended")
        self.status_label.setStyleSheet(
            "color: #666666; background-color: #f0f0f0; padding: 3px; border-radius: 3px;"
        )

    def update_database_status(self, connected: bool, message: str) -> None:
        """Update the status display with database status information"""
        if not self.session_active:
            # Only update status if we're not in an active session
            self.status_label.setText(f"Status: {message}")

            if connected:
                self.status_label.setStyleSheet(
                    "color: green; background-color: #e0ffe0; padding: 3px; border-radius: 3px;"
                )
            else:
                self.status_label.setStyleSheet(
                    "color: red; background-color: #fff0f0; padding: 3px; border-radius: 3px;"
                )
