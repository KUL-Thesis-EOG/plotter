from typing import Optional, Dict, Tuple
import time
import numpy as np
import pyqtgraph as pg
from PyQt6 import QtWidgets
from PyQt6.QtCore import pyqtSignal, pyqtSlot


class OscilloscopeDisplay(QtWidgets.QWidget):
    """Widget for displaying oscilloscope signals with fixed window"""

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
        self.plot_graph.setLabel("bottom", "Samples", **styles)
        self.plot_graph.addLegend()
        self.plot_graph.showGrid(x=True, y=True)

        # FIXED: Exactly 5000 samples displayed at once (about 5 seconds at 1000Hz)
        self.MAX_POINTS = 5000

        # Create data arrays of fixed size, filled with zeros initially
        self.voltage_data = np.zeros(self.MAX_POINTS)
        self.sample_indices = np.arange(self.MAX_POINTS)

        # Counter for positioning new data in the circular buffer
        self.current_index = 0
        self.sample_count = 0

        # Create the line plot
        pen = pg.mkPen(color=pen_color, width=2)
        self.signal_line = self.plot_graph.plot(
            self.sample_indices,
            self.voltage_data,
            name=signal_name,
            pen=pen,
            symbol=None,
        )

        # Fix the axis ranges permanently
        self.plot_graph.setXRange(0, self.MAX_POINTS, padding=0)
        self.plot_graph.setYRange(0, 5, padding=0)
        self.plot_graph.disableAutoRange()

        # Disable user interactions with the plot
        self.plot_graph.setMouseEnabled(x=False, y=False)
        self.plot_graph.setMenuEnabled(False)

        # Performance optimization
        self.last_update_time = time.time()
        self.update_interval = 0.05  # 50ms update interval
        self.data_changed = False

    def reset_plot(self) -> None:
        """Reset the oscilloscope plot data"""
        self.voltage_data = np.zeros(self.MAX_POINTS)
        self.current_index = 0
        self.sample_count = 0
        self.signal_line.setData(self.sample_indices, self.voltage_data)
        self.data_changed = False

    def add_data_point(self, timestamp: float, voltage: float) -> None:
        """Add a new data point using a circular buffer approach"""
        # Add data to fixed circular buffer
        self.voltage_data[self.current_index] = voltage

        # Update counters
        self.current_index = (self.current_index + 1) % self.MAX_POINTS
        self.sample_count += 1

        # Reset the buffer when we reach MAX_POINTS
        if self.sample_count >= self.MAX_POINTS:
            # Clear all old data
            self.reset_plot()

        self.data_changed = True

        # Check if it's time to update the display
        current_time = time.time()
        if (current_time - self.last_update_time) >= self.update_interval:
            self._update_display()
            self.last_update_time = current_time

    def _update_display(self) -> None:
        """Update the display with current data"""
        if not self.data_changed:
            return

        # Just plot the data directly, no need to rearrange since we're resetting at MAX_POINTS
        self.signal_line.setData(self.sample_indices, self.voltage_data)

        # Emit signal with data for statistics
        self.dataUpdated.emit(self.voltage_data, self.sample_indices)

        self.data_changed = False


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
