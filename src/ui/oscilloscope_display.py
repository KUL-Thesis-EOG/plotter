from typing import Optional, Dict, Tuple, List
import time
import numpy as np
import pyqtgraph as pg
from PyQt6 import QtWidgets
from PyQt6.QtCore import pyqtSignal, pyqtSlot, QTimer
from collections import deque
from scipy import signal
import math


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
        
        # Anti-aliasing and downsampling for display
        self.filtered_voltage_data = np.zeros(self.buffer_size)
        
        # Downsampling parameters - will be adjusted based on time range
        self.max_points_displayed = 2000  # Maximum points to display for optimal performance
        self.downsampling_factor = 1      # Will be adjusted based on time range
        self.last_downsample_count = 0    # Track last number of points after downsampling
        
        # For low-pass filtering (anti-aliasing)
        self.filter_kernel_size = 8       # Base kernel size for anti-aliasing filter
        self.use_savgol = True            # Whether to use Savitzky-Golay filtering

    @pyqtSlot(int)
    def set_time_range(self, seconds: int) -> None:
        """Change the time range of the x-axis"""
        self.time_range = seconds
        
        # Adjust anti-aliasing and downsampling parameters based on time range
        if self.data_index > 0:
            # Calculate optimal downsampling based on time range
            # Estimate how many samples are in the current view
            data_time_span = self.time_data[self.data_index - 1] - self.time_data[0]
            if data_time_span > 0:
                # Estimate samples per second
                samples_per_second = self.data_index / data_time_span
                # Estimate samples in view
                samples_in_view = samples_per_second * seconds
                
                # Adjust downsampling factor to target max_points_displayed
                if samples_in_view > self.max_points_displayed:
                    self.downsampling_factor = max(1, int(samples_in_view / self.max_points_displayed))
                else:
                    self.downsampling_factor = 1
                
                # Adjust filter kernel size based on downsampling factor
                # Larger downsampling requires wider filter for anti-aliasing
                self.filter_kernel_size = min(51, max(5, self.downsampling_factor * 2 + 1))
                
                # Must be odd for Savitzky-Golay filter
                if self.filter_kernel_size % 2 == 0:
                    self.filter_kernel_size += 1
            
            # Get current view state
            view_range = self.plot_graph.viewRange()[0]
            current_time = self.time_data[self.data_index - 1]
            
            # Check if we're following the most recent data
            auto_scroll_active = abs(view_range[1] - current_time) < 0.5
            
            # Disable auto-range before setting explicit range
            self.plot_graph.disableAutoRange(axis="x")
            
            if auto_scroll_active:
                # If auto-scrolling, update to show most recent time window
                self.plot_graph.setXRange(
                    max(0, current_time - self.time_range),
                    current_time,
                    padding=0,  # No padding
                )
            else:
                # If manually positioned, keep the right edge of view at same position
                # but adjust the width of the window
                self.plot_graph.setXRange(
                    max(0, view_range[1] - self.time_range),
                    view_range[1],
                    padding=0,  # No padding
                )
                
            # Recalculate filtered data with new parameters
            self._recalculate_filtered_data()
                
            # Ensure the view is updated immediately
            self.plot_graph.update()

    @pyqtSlot()
    def view_all_data(self) -> None:
        """Adjust view to show all collected data"""
        if self.data_index > 0:
            # Get the actual min and max time values from the data
            min_time = self.time_data[0]
            max_time = self.time_data[self.data_index - 1]
            
            # If there's not enough data, use a minimum range of 1 second
            if max_time - min_time < 1.0:
                center = (max_time + min_time) / 2
                min_time = center - 0.5
                max_time = center + 0.5
            
            # Add a small padding (5%) for better visualization
            padding = (max_time - min_time) * 0.05
            
            # Disable auto range before setting explicit range
            self.plot_graph.disableAutoRange(axis="x")

            # Set the explicit range with padding
            self.plot_graph.setXRange(
                max(0, min_time - padding),  # Ensure we don't go below 0
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
        self.data_index = 0
        self.latest_time = 0.0
        self.signal_line.setData(self.time_data[:1], self.voltage_data[:1])
        self.data_changed = False
        self.pending_update = False
        self.last_downsample_count = 0
        
        # Reset downsampling parameters
        self.downsampling_factor = 1
        self.filter_kernel_size = 8

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
            
            # Just store the raw data - we'll apply filtering when displaying
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
            
    def _recalculate_filtered_data(self) -> None:
        """Process all data with anti-aliasing filter and downsample for display"""
        if self.data_index <= 0:
            return
            
        # Get the raw data to process
        raw_voltage = self.voltage_data[:self.data_index]
        raw_time = self.time_data[:self.data_index]
        
        # Set up downsampling and filtering
        filtered_data = raw_voltage.copy()  # Start with a copy of the raw data
        
        # Apply low-pass filter for anti-aliasing before downsampling
        if len(filtered_data) > self.filter_kernel_size:
            try:
                if self.use_savgol:
                    # Savitzky-Golay filter - better preserves peaks while smoothing
                    polyorder = min(3, self.filter_kernel_size - 2)  # Must be less than window_length
                    filtered_data = signal.savgol_filter(
                        filtered_data, 
                        window_length=self.filter_kernel_size,
                        polyorder=polyorder
                    )
                else:
                    # Compute a window with the Nyquist frequency of half the downsampling rate
                    b = signal.firwin(
                        self.filter_kernel_size, 
                        1.0/self.downsampling_factor, 
                        window='hamming'
                    )
                    filtered_data = signal.filtfilt(b, [1.0], filtered_data)
            except Exception:
                # Fallback to simpler mean if the filter fails
                filtered_data = np.array(raw_voltage)
        
        # Downsample the data
        if self.downsampling_factor > 1 and len(filtered_data) > self.downsampling_factor * 2:
            # Calculate indices to keep after downsampling
            # Using decimate would be ideal but might require more specific handling
            indices = np.arange(0, len(filtered_data), self.downsampling_factor)
            
            # If there's remaining data that doesn't divide evenly, include the last point
            if indices[-1] < len(filtered_data) - 1:
                indices = np.append(indices, len(filtered_data) - 1)
                
            # Get the downsampled data
            times = raw_time[indices]
            values = filtered_data[indices]
            
            self.last_downsample_count = len(indices)
        else:
            # No downsampling needed
            times = raw_time
            values = filtered_data
            self.last_downsample_count = len(values)
        
        # Update the plot with anti-aliased and downsampled data
        self.signal_line.setData(times, values)
        
    def _update_display(self, current_time: float) -> None:
        """Update the display with current data"""
        if not self.data_changed or self.data_index == 0:
            return
        
        # Check if we need to adjust downsampling based on data growth
        data_time_span = self.time_data[self.data_index - 1] - self.time_data[0]
        if data_time_span > 0:
            # Calculate estimated samples in the current time window
            samples_per_second = self.data_index / data_time_span
            samples_in_view = samples_per_second * self.time_range
            
            # Update downsampling factor if needed
            new_factor = max(1, int(samples_in_view / self.max_points_displayed))
            if new_factor != self.downsampling_factor:
                self.downsampling_factor = new_factor
                # Adjust filter kernel size based on new downsampling factor
                self.filter_kernel_size = min(51, max(5, self.downsampling_factor * 2 + 1))
                if self.filter_kernel_size % 2 == 0:
                    self.filter_kernel_size += 1
        
        # Apply anti-aliasing filter and downsample
        self._recalculate_filtered_data()
        
        # Emit signal with original data (not filtered) for statistics and recording
        visible_data = self.voltage_data[: self.data_index]
        self.dataUpdated.emit(visible_data, self.time_data[: self.data_index])
        self.data_changed = False

        # Store current view state to determine if auto-scrolling is active
        view_range = self.plot_graph.viewRange()[0]  # Get current x-axis view range
        expected_min = max(0, current_time - self.time_range)
        expected_max = current_time
        
        # Check if we're in auto-scrolling mode (right edge follows the data)
        auto_scroll_active = abs(view_range[1] - current_time) < 0.5  # Right edge is near current time
        
        # Update view window based on auto-scroll state
        if self.data_index > 1 and auto_scroll_active:  # Only update if we have at least one point
            # Update the view to follow the signal with a stable time window
            self.plot_graph.setXRange(expected_min, expected_max, padding=0)
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
