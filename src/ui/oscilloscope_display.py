from typing import Optional, Dict, Tuple
import time
import numpy as np
import pyqtgraph as pg
from PyQt6 import QtWidgets
from PyQt6.QtCore import pyqtSignal, pyqtSlot, QTimer
from collections import deque


class OscilloscopeDisplay(QtWidgets.QWidget):
    """Base widget for displaying oscilloscope signals"""

    dataUpdated = pyqtSignal(
        np.ndarray, np.ndarray
    )  # Signal emitted with voltage and time data

    def __init__(
        self,
        title: str,
        pen_color: Tuple[int, int, int],
        signal_name: str,
        parent: Optional[QtWidgets.QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.layout = QtWidgets.QVBoxLayout(self)

        # Create oscilloscope plot
        self.plot_graph = pg.PlotWidget()
        self.layout.addWidget(self.plot_graph)
        self.plot_graph.setBackground("w")

        # Configure plot
        self.plot_graph.setTitle(title, color="b", size="20pt")
        styles: Dict[str, str] = {"color": "blue", "font-size": "16px"}
        self.plot_graph.setLabel("left", "Voltage (V)", **styles)
        self.plot_graph.setLabel("bottom", "Time (s)", **styles)
        self.plot_graph.addLegend()
        self.plot_graph.showGrid(x=True, y=True)

        # Initialize parameters
        self.time_range: int = 5  # default time range in seconds
        self.plot_graph.setXRange(0, self.time_range)
        self.plot_graph.setYRange(0, 5)

        # Calculate buffer size based on 30 seconds of data
        self.retention_time: float = 30.0  # Keep only the last 30 seconds of data
        self.samples_per_second: int = 1000  # Estimated sample rate
        self.buffer_size: int = int(self.retention_time * self.samples_per_second * 1.5)  # Buffer with 50% margin
        self.time_data: np.ndarray = np.zeros(self.buffer_size)
        self.voltage_data: np.ndarray = np.zeros(self.buffer_size)
        self.data_index: int = 0
        self.latest_time: float = 0.0  # Track the latest timestamp

        # Create the line plot
        pen = pg.mkPen(color=pen_color, width=2)
        self.signal_line = self.plot_graph.plot(
            self.time_data, self.voltage_data, name=signal_name, pen=pen, symbol=None
        )
        
        # Performance optimization variables
        self.last_update_time = time.time()
        self.update_interval = 0.01 
        self.pending_update = False
        self.data_changed = False
        
        # Moving average filter for display
        self.moving_avg_window_size = int(1.0 / self.update_interval)  # Window size based on refresh rate
        self.moving_avg_buffer = deque(maxlen=self.moving_avg_window_size)
        self.filtered_voltage_data = np.zeros(self.buffer_size)

    @pyqtSlot(int)
    def set_time_range(self, seconds: int) -> None:
        """Change the time range of the x-axis"""
        self.time_range = seconds

        if self.data_index > 0:
            # Update the view to show the most recent data
            current_time = self.time_data[self.data_index - 1]
            # Disable auto-range before setting explicit range
            self.plot_graph.disableAutoRange(axis="x")
            # Set the range to show the specified time window
            self.plot_graph.setXRange(
                max(0, current_time - self.time_range),
                current_time,
                padding=0,  # No padding
            )
            # Ensure the view is updated immediately
            self.plot_graph.update()

    @pyqtSlot()
    def view_all_data(self) -> None:
        """Adjust view to show all collected data"""
        if self.data_index > 0:
            # Get the actual min and max time values from the data
            min_time = self.time_data[0]
            max_time = self.time_data[self.data_index - 1]

            # Add a small padding (5%) for better visualization
            padding = (max_time - min_time) * 0.05

            # Force the auto range first to clear any previous manual ranges
            self.plot_graph.enableAutoRange(axis="x")

            # Then set the explicit range with padding
            self.plot_graph.setXRange(
                min_time,
                max_time + padding,
                padding=0,  # No additional padding (we already added our own)
            )

            # Ensure the view is updated immediately
            self.plot_graph.update()

    @pyqtSlot(float, float)
    def set_voltage_range(self, min_v: float, max_v: float) -> None:
        """Update the voltage range"""
        self.plot_graph.setYRange(min_v, max_v)

    def reset_plot(self) -> None:
        """Reset the oscilloscope plot data"""
        self.time_data = np.zeros(self.buffer_size)
        self.voltage_data = np.zeros(self.buffer_size)
        self.filtered_voltage_data = np.zeros(self.buffer_size)
        self.moving_avg_buffer.clear()
        self.data_index = 0
        self.latest_time = 0.0
        self.signal_line.setData(self.time_data[:1], self.voltage_data[:1])
        self.data_changed = False
        self.pending_update = False

    def add_data_point(self, time_point: float, voltage: float) -> None:
        """Add a new data point to the oscilloscope"""
        # Update latest time point
        self.latest_time = time_point
        
        # Check if we need to trim old data (older than retention_time)
        if self.data_index > 0 and self.data_index >= self.buffer_size * 0.75:  # Start checking when buffer is 75% full
            # Find data points that are older than retention_time seconds
            cutoff_time = self.latest_time - self.retention_time
            # Find the index of the first data point that's newer than the cutoff
            newer_indices = np.where(self.time_data[:self.data_index] >= cutoff_time)[0]
            
            if len(newer_indices) > 0 and newer_indices[0] > 0:
                # Keep only data within retention window
                keep_idx = newer_indices[0]
                keep_count = self.data_index - keep_idx
                
                # Shift data to start of buffer
                self.time_data[:keep_count] = self.time_data[keep_idx:self.data_index]
                self.voltage_data[:keep_count] = self.voltage_data[keep_idx:self.data_index]
                
                # Update data index
                self.data_index = keep_count
        
        # Add new data point
        if self.data_index < self.buffer_size:
            self.time_data[self.data_index] = time_point
            self.voltage_data[self.data_index] = voltage
            
            # Update moving average buffer and calculate filtered value
            self.moving_avg_buffer.append(voltage)
            if len(self.moving_avg_buffer) > 0:
                self.filtered_voltage_data[self.data_index] = sum(self.moving_avg_buffer) / len(self.moving_avg_buffer)
            else:
                self.filtered_voltage_data[self.data_index] = voltage
                
            self.data_index += 1
            self.data_changed = True  # Mark data as changed
            
            # Check if it's time to update the display
            current_time = time.time()
            time_since_update = current_time - self.last_update_time
            
            # Only update display if enough time has passed since last update
            if time_since_update >= self.update_interval:
                self._update_display(time_point)
                self.last_update_time = current_time
            elif not self.pending_update:
                # Schedule an update if one isn't already pending
                QTimer.singleShot(int(self.update_interval * 1000), self._delayed_update)
                self.pending_update = True
        else:
            # Buffer is completely full, shift data to make room
            # This should rarely happen due to our trimming logic above
            shift_amount = self.buffer_size // 4  # Shift by 25% of buffer
            self.time_data[:-shift_amount] = self.time_data[shift_amount:]
            self.voltage_data[:-shift_amount] = self.voltage_data[shift_amount:]
            self.data_index -= shift_amount
            
            # Continue with the new sample
            self.add_data_point(time_point, voltage)
            
    def _delayed_update(self) -> None:
        """Handle delayed display update"""
        self.pending_update = False
        if self.data_changed and self.data_index > 0:
            self._update_display(self.time_data[self.data_index - 1])
            self.last_update_time = time.time()
            
    def _update_display(self, current_time: float) -> None:
        """Update the display with current data"""
        if not self.data_changed or self.data_index == 0:
            return
            
        # Update plot with filtered data for display
        visible_filtered_data = self.filtered_voltage_data[: self.data_index]
        self.signal_line.setData(self.time_data[: self.data_index], visible_filtered_data)

        # Emit signal with original data (not filtered) for saving
        visible_data = self.voltage_data[: self.data_index]
        self.dataUpdated.emit(visible_data, self.time_data[: self.data_index])
        self.data_changed = False

        # Update view window to show the most recent data
        if self.data_index > 1:  # Only update if we have at least one point
            # Only update the view if we're not in "view all" mode
            # Check if the current view range is approximately what we'd expect for the time window
            view_range = self.plot_graph.viewRange()[0]  # Get current x-axis view range
            expected_min = max(0, current_time - self.time_range)

            # If the view is close to the expected window or the view's right edge is near current_time,
            # then update to follow the signal
            if abs(view_range[1] - current_time) < 0.5:  # If right edge is within 0.5s of current time
                self.plot_graph.setXRange(expected_min, current_time, padding=0)
                self.plot_graph.update()


class VerticalChannelDisplay(OscilloscopeDisplay):
    """Widget for displaying the vertical channel of the oscilloscope"""

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(
            title="Vertical Channel",
            pen_color=(255, 0, 0),  # Red
            signal_name="Vertical Signal",
            parent=parent,
        )

    @pyqtSlot(float, float, float)
    def add_sample(self, time_point: float, vertical_voltage: float, _: float) -> None:
        """Add a new sample to the vertical channel display"""
        self.add_data_point(time_point, vertical_voltage)


class HorizontalChannelDisplay(OscilloscopeDisplay):
    """Widget for displaying the horizontal channel of the oscilloscope"""

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(
            title="Horizontal Channel",
            pen_color=(0, 0, 255),  # Blue
            signal_name="Horizontal Signal",
            parent=parent,
        )

    @pyqtSlot(float, float, float)
    def add_sample(
        self, time_point: float, _: float, horizontal_voltage: float
    ) -> None:
        """Add a new sample to the horizontal channel display"""
        self.add_data_point(time_point, horizontal_voltage)
