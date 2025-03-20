from typing import Optional
import numpy as np
from PyQt6 import QtWidgets
from PyQt6.QtCore import pyqtSlot, QTime


class StatisticsPanel(QtWidgets.QGroupBox):
    """Panel for displaying signal statistics based on the last 10 seconds of data"""

    def __init__(
        self, channel_name: str = "Signal", parent: Optional[QtWidgets.QWidget] = None
    ) -> None:
        super().__init__(f"{channel_name} Statistics (Last 10s)", parent)
        self.layout = QtWidgets.QGridLayout(self)

        # Create labels for statistics
        self.mean_label = QtWidgets.QLabel("Average (V):")
        self.mean_value = QtWidgets.QLabel("0.00")
        self.max_label = QtWidgets.QLabel("Peak (V):")
        self.max_value = QtWidgets.QLabel("0.00")
        self.samples_label = QtWidgets.QLabel("Samples/sec:")
        self.samples_value = QtWidgets.QLabel("0")

        # Add statistics to layout
        self.layout.addWidget(self.mean_label, 0, 0)
        self.layout.addWidget(self.mean_value, 0, 1)
        self.layout.addWidget(self.max_label, 1, 0)
        self.layout.addWidget(self.max_value, 1, 1)
        self.layout.addWidget(self.samples_label, 2, 0)
        self.layout.addWidget(self.samples_value, 2, 1)

        # Initialize tracking for samples per second calculation
        self.last_sample_count = 0
        self.last_update_time = QTime.currentTime()
        self.samples_in_window = 0

    @pyqtSlot(np.ndarray, np.ndarray)
    def update_statistics(
        self, voltage_data: np.ndarray, time_data: np.ndarray
    ) -> None:
        """Update statistics based on the last 10 seconds of data"""
        if len(voltage_data) > 0 and len(time_data) > 0:
            # Get the current time (last sample time)
            current_time = time_data[-1]

            # Filter to only include data from the last 10 seconds
            time_window = 10.0  # seconds
            start_time = max(0, current_time - time_window)

            # Find indices of samples within the last 10 seconds
            recent_indices = np.where(time_data >= start_time)[0]

            if len(recent_indices) > 0:
                # Get the voltage data for these samples
                recent_voltage_data = voltage_data[recent_indices]

                # Calculate statistics on recent data
                mean_val: float = np.mean(recent_voltage_data)
                max_val: float = np.max(recent_voltage_data)

                # Update display for voltage statistics
                self.mean_value.setText(f"{mean_val:.2f}")
                self.max_value.setText(f"{max_val:.2f}")

                # Calculate samples per second
                current_qtime = QTime.currentTime()
                elapsed_msec = self.last_update_time.msecsTo(current_qtime)

                # Only update sample rate every second or if it's the first update
                if elapsed_msec >= 1000 or self.last_sample_count == 0:
                    # Calculate samples since last update
                    samples_received = len(voltage_data) - self.last_sample_count
                    self.samples_in_window = samples_received

                    # Calculate samples per second
                    if elapsed_msec > 0:
                        samples_per_sec = int(samples_received * 1000 / elapsed_msec)
                        self.samples_value.setText(f"{samples_per_sec}")

                    # Reset for next calculation
                    self.last_sample_count = len(voltage_data)
                    self.last_update_time = current_qtime
