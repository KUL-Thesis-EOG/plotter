from typing import Optional
from PyQt6 import QtWidgets
from PyQt6.QtCore import pyqtSignal


class VoltageControlPanel(QtWidgets.QGroupBox):
    """Panel for controlling the voltage range of the oscilloscope"""

    voltageRangeChanged = pyqtSignal(float, float)

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__("Voltage Range", parent)
        self.layout = QtWidgets.QGridLayout(self)

        self.min_label = QtWidgets.QLabel("Min (V):")
        self.min_spinner = QtWidgets.QDoubleSpinBox()
        self.min_spinner.setRange(0, 4.9)
        self.min_spinner.setValue(0)
        self.min_spinner.setSingleStep(0.1)
        self.min_spinner.valueChanged.connect(self.update_voltage_range)

        self.max_label = QtWidgets.QLabel("Max (V):")
        self.max_spinner = QtWidgets.QDoubleSpinBox()
        self.max_spinner.setRange(0.1, 5.0)
        self.max_spinner.setValue(5.0)
        self.max_spinner.setSingleStep(0.1)
        self.max_spinner.valueChanged.connect(self.update_voltage_range)

        self.layout.addWidget(self.min_label, 0, 0)
        self.layout.addWidget(self.min_spinner, 0, 1)
        self.layout.addWidget(self.max_label, 1, 0)
        self.layout.addWidget(self.max_spinner, 1, 1)

    def update_voltage_range(self) -> None:
        """Update the voltage range based on spinner values and emit signal"""
        min_v: float = self.min_spinner.value()
        max_v: float = self.max_spinner.value()

        # Ensure min is less than max
        if min_v >= max_v:
            if self.sender() == self.min_spinner:
                self.min_spinner.setValue(max_v - 0.1)
                min_v = max_v - 0.1
            else:
                self.max_spinner.setValue(min_v + 0.1)
                max_v = min_v + 0.1

        self.voltageRangeChanged.emit(min_v, max_v)
