from typing import List, Tuple, Optional
from PyQt6 import QtWidgets, QtCore, QtGui


class SerialControlPanel(QtWidgets.QGroupBox):
    """Control panel for serial port connection"""

    portSelected = QtCore.pyqtSignal(str)
    disconnectRequested = QtCore.pyqtSignal()

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__("Serial Connection", parent)

        # Set up layout
        self.layout = QtWidgets.QHBoxLayout(self)

        # Create port selection components
        self.port_label = QtWidgets.QLabel("Port:")
        self.port_combo = QtWidgets.QComboBox()
        self.port_combo.setMinimumWidth(200)

        # Create refresh button
        self.refresh_button = QtWidgets.QPushButton("Refresh")
        self.refresh_button.clicked.connect(self.refresh_requested)

        # Create connect button
        self.connect_button = QtWidgets.QPushButton("Connect")
        self.connect_button.clicked.connect(self.connect_requested)
        self.connect_button.setEnabled(False)  # Disable until a port is selected

        # Create status display
        self.status_label = QtWidgets.QLabel("Status: Not connected")
        self.status_label.setMinimumWidth(250)

        # Add components to layout
        self.layout.addWidget(self.port_label)
        self.layout.addWidget(self.port_combo)
        self.layout.addWidget(self.refresh_button)
        self.layout.addWidget(self.connect_button)
        self.layout.addWidget(self.status_label)
        self.layout.addStretch(1)  # Push everything to the left

        # Connect signals
        self.port_combo.currentIndexChanged.connect(self._port_selection_changed)

    def _port_selection_changed(self, index: int) -> None:
        """Enable or disable connect button based on port selection"""
        self.connect_button.setEnabled(
            index >= 0 and self.port_combo.currentData() is not None
        )

    def connect_requested(self) -> None:
        """Toggle between connect and disconnect when button is clicked"""
        # If button text is "Connect", then connect to port
        if self.connect_button.text() == "Connect":
            if self.port_combo.currentIndex() >= 0:
                port_name = self.port_combo.currentData()
                if port_name:
                    self.portSelected.emit(port_name)
        # If button text is "Disconnect", then disconnect
        else:
            self.disconnectRequested.emit()

    def refresh_requested(self) -> None:
        """Called when user requests port refresh"""
        # This is a placeholder - the app will connect this to the actual refresh method
        pass

    @QtCore.pyqtSlot(list)
    def update_port_list(self, ports: List[Tuple[str, str]]) -> None:
        """Update the list of available ports"""
        current_port = (
            self.port_combo.currentData()
            if self.port_combo.currentIndex() >= 0
            else None
        )

        self.port_combo.clear()

        if not ports:
            self.port_combo.addItem("No ports available", None)
            self.connect_button.setEnabled(False)
            return

        # Add all available ports to the combo box
        selected_index = -1
        for i, (port_name, description) in enumerate(ports):
            display_text = f"{port_name} - {description}"
            self.port_combo.addItem(display_text, port_name)

            # If this is the currently selected port, remember its index
            if current_port == port_name:
                selected_index = i

        # Restore the previous selection if possible
        if selected_index >= 0:
            self.port_combo.setCurrentIndex(selected_index)

        # Enable connect button if we have ports
        self.connect_button.setEnabled(
            self.port_combo.count() > 0 and self.port_combo.currentData() is not None
        )

    @QtCore.pyqtSlot(bool, str)
    def update_connection_status(self, connected: bool, message: str) -> None:
        """Update the connection status display"""
        if connected:
            # Connected - show green status
            self.status_label.setText(f"Status: {message}")
            self.status_label.setStyleSheet(
                "color: green; font-weight: bold; background-color: #e0ffe0; padding: 3px; border-radius: 3px;"
            )

            # Update button
            self.connect_button.setText("Disconnect")
            self.connect_button.setStyleSheet("")
            self.port_combo.setEnabled(False)
            self.refresh_button.setEnabled(False)
        else:
            # Disconnected or error - show red status and different styling based on message
            self.status_label.setText(f"Status: {message}")

            if message == "Disconnected":
                # Normal disconnection
                self.status_label.setStyleSheet(
                    "color: #666666; background-color: #f0f0f0; padding: 3px; border-radius: 3px;"
                )
            else:
                # Error or abnormal disconnection
                self.status_label.setStyleSheet(
                    "color: red; font-weight: bold; background-color: #fff0f0; padding: 3px; border-radius: 3px;"
                )

            # Update button
            self.connect_button.setText("Connect")
            self.connect_button.setStyleSheet("")
            self.port_combo.setEnabled(True)
            self.refresh_button.setEnabled(True)
