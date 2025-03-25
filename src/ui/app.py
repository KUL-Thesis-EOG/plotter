from PyQt6 import QtWidgets, QtCore, QtGui

# Import core components
from src.core.signal_generator import SerialSignalGenerator
from src.core.data_recorder import DataRecorder
from src.core.database_backup import DatabaseBackup
from src.ui.control_panel import ControlPanel
from src.ui.oscilloscope_display import VerticalChannelDisplay, HorizontalChannelDisplay


class OscilloscopeApp(QtWidgets.QMainWindow):
    """Main oscilloscope application with dual channel display"""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Arduino Serial Oscilloscope - Experiment Recorder")
        self.resize(1200, 800)

        # Create main layout
        self.central_widget = QtWidgets.QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QtWidgets.QVBoxLayout(self.central_widget)

        # Create components
        self.control_panel = ControlPanel()
        self.signal_generator = SerialSignalGenerator()
        self.data_recorder = DataRecorder()
        self.database_backup = DatabaseBackup()

        # Create display layout for both oscilloscopes
        self.display_layout = QtWidgets.QHBoxLayout()
        self.vertical_channel = VerticalChannelDisplay()
        self.horizontal_channel = HorizontalChannelDisplay()

        # Add displays to display layout
        self.display_layout.addWidget(self.vertical_channel)
        self.display_layout.addWidget(self.horizontal_channel)

        # Add components to main layout
        self.main_layout.addWidget(self.control_panel)
        self.main_layout.addLayout(self.display_layout)

        # Connect signals and slots
        self.connect_signals()

        # Setup status message box
        self.status_message_box = QtWidgets.QMessageBox(self)
        self.status_message_box.setIcon(QtWidgets.QMessageBox.Icon.Warning)
        self.status_message_box.setWindowTitle("Status Alert")
        self.status_message_box.setStandardButtons(
            QtWidgets.QMessageBox.StandardButton.Ok
        )

        # Experiment recording state
        self.experiment_active = False

    def connect_signals(self) -> None:
        """Connect all signals and slots between components"""
        # Connect serial selection and status
        self.control_panel.portSelected.connect(self.signal_generator.connect_to_port)
        self.control_panel.serial_panel.disconnectRequested.connect(
            self.signal_generator.disconnect
        )
        self.signal_generator.portsChanged.connect(
            self.control_panel.serial_panel.update_port_list
        )
        self.signal_generator.connectionStatusChanged.connect(
            self.control_panel.serial_panel.update_connection_status
        )
        self.signal_generator.connectionStatusChanged.connect(
            self.handle_connection_status
        )

        # Connect serial panel refresh button
        self.control_panel.serial_panel.refresh_button.clicked.connect(
            self.signal_generator.scan_ports
        )

        # Connect participant and experiment control
        self.control_panel.participantRegistered.connect(self.register_participant)
        self.control_panel.sessionStartRequested.connect(self.start_experiment)
        self.control_panel.sessionPauseRequested.connect(self.pause_experiment)
        self.control_panel.sessionResumeRequested.connect(self.resume_experiment)
        self.control_panel.sessionEndRequested.connect(self.end_experiment)

        # Connect data recorder status to participant panel
        self.data_recorder.statusChanged.connect(
            self.control_panel.participant_panel.update_database_status
        )
        
        # Connect database backup status to participant panel
        self.database_backup.statusChanged.connect(
            self.control_panel.participant_panel.update_database_status
        )

        # Connect vertical channel controls
        self.control_panel.vertical_channel_panel.time_panel.timeRangeChanged.connect(
            self.vertical_channel.set_time_range
        )
        self.control_panel.vertical_channel_panel.time_panel.viewAllRequested.connect(
            self.vertical_channel.view_all_data
        )
        self.control_panel.vertical_channel_panel.voltage_panel.voltageRangeChanged.connect(
            self.vertical_channel.set_voltage_range
        )

        # Connect horizontal channel controls
        self.control_panel.horizontal_channel_panel.time_panel.timeRangeChanged.connect(
            self.horizontal_channel.set_time_range
        )
        self.control_panel.horizontal_channel_panel.time_panel.viewAllRequested.connect(
            self.horizontal_channel.view_all_data
        )
        self.control_panel.horizontal_channel_panel.voltage_panel.voltageRangeChanged.connect(
            self.horizontal_channel.set_voltage_range
        )

        # Connect signal generator to both oscilloscope displays and data recording
        self.signal_generator.newSample.connect(self.vertical_channel.add_sample)
        self.signal_generator.newSample.connect(self.horizontal_channel.add_sample)
        self.signal_generator.newSample.connect(self.record_data_sample)

        # Connect oscilloscope data updates to statistics panels
        self.vertical_channel.dataUpdated.connect(
            self.control_panel.vertical_channel_panel.stats_panel.update_statistics
        )
        self.horizontal_channel.dataUpdated.connect(
            self.control_panel.horizontal_channel_panel.stats_panel.update_statistics
        )

    def handle_connection_status(self, connected: bool, message: str) -> None:
        """Handle connection status changes with potential alerts"""
        # Show message box for any disconnection except manual "Disconnected" action
        if not connected:
            # Reset oscilloscope displays and clear buffers when device is disconnected
            self.vertical_channel.reset_plot()
            self.horizontal_channel.reset_plot()
            
            # Show alert message for unexpected disconnections
            if message != "Disconnected":
                self.status_message_box.setText(message)
                self.status_message_box.show()

    def register_participant(self, participant_id: int) -> None:
        """Register a participant in the data recorder"""
        success = self.data_recorder.register_participant(participant_id)
        if success:
            # Backup participants data after registration
            self.database_backup.backup_participants_file()
        else:
            self.status_message_box.setText("Failed to register participant.")
            self.status_message_box.show()

    def start_experiment(self) -> None:
        """Start recording experiment data"""
        # Start a new session in the data recorder
        success = self.data_recorder.start_session()
        if success:
            self.experiment_active = True
            # Backup sessions data after starting a new session
            self.database_backup.backup_sessions_file()
        else:
            self.status_message_box.setText(
                "Failed to start experiment session. Please register a participant first."
            )
            self.status_message_box.show()

    def pause_experiment(self) -> None:
        """Pause the experiment recording"""
        self.data_recorder.pause_session()

    def resume_experiment(self) -> None:
        """Resume the experiment recording"""
        self.data_recorder.resume_session()

    def end_experiment(self) -> None:
        """End the current experiment session"""
        self.experiment_active = False
        self.data_recorder.end_session()
        
        # Trigger a backup of the experiment data file that was just completed
        if self.data_recorder.data_file:
            self.database_backup.backup_measurements_file(self.data_recorder.data_file)

    @QtCore.pyqtSlot(float, float, float)
    def record_data_sample(
        self, elapsed_time: float, vertical_voltage: float, horizontal_voltage: float
    ) -> None:
        """Record a data sample if experiment is active"""
        if self.experiment_active:
            self.data_recorder.store_measurement(
                elapsed_time, vertical_voltage, horizontal_voltage
            )

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:
        """Clean up resources when closing the application"""
        # End any active experiment
        if self.experiment_active:
            self.end_experiment()

        # Clean up data recorder resources
        self.data_recorder.cleanup()
        
        # Clean up database backup resources
        self.database_backup.cleanup()

        # Disconnect from serial port when closing
        self.signal_generator.disconnect()

        super().closeEvent(event)
