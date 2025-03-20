import time
from typing import Optional, List, Tuple
from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot, QTimer, QIODevice, QByteArray
from PyQt6.QtSerialPort import QSerialPort, QSerialPortInfo


class SerialSignalGenerator(QObject):
    """Class for generating signal data from Arduino serial connection"""

    newSample = pyqtSignal(
        float, float, float
    )  # time, vertical voltage, horizontal voltage
    connectionStatusChanged = pyqtSignal(bool, str)  # connected status, message
    portsChanged = pyqtSignal(list)  # list of available ports

    def __init__(
        self, baud_rate: int = 115200, parent: Optional[QObject] = None
    ) -> None:
        super().__init__(parent)
        self.baud_rate: int = baud_rate
        self.serial_port = QSerialPort(self)
        self.elapsed_time: float = 0.0
        self.last_timestamp: float = time.time()
        self.last_data_received: float = 0.0
        self.buffer: str = ""
        self.data_received: bool = False

        # Connect serial port signals
        self.serial_port.readyRead.connect(self._read_data)
        self.serial_port.errorOccurred.connect(self._handle_error)

        # Setup timer for port scanning
        self.port_scan_timer = QTimer(self)
        self.port_scan_timer.timeout.connect(self.scan_ports)
        self.port_scan_timer.start(2000)  # Check ports every 2 seconds

        # Setup data watchdog timer to detect if data stops coming
        self.data_watchdog = QTimer(self)
        self.data_watchdog.timeout.connect(self._check_data_flow)

        # Initial port scan
        self.scan_ports()

    def scan_ports(self) -> None:
        """Scan for available serial ports and emit signal with the results"""
        ports = self.get_available_ports()
        self.portsChanged.emit(ports)

    def get_available_ports(self) -> List[Tuple[str, str]]:
        """Get a list of available serial ports with descriptions"""
        return [
            (port.portName(), port.description())
            for port in QSerialPortInfo.availablePorts()
        ]

    @pyqtSlot(str)
    def connect_to_port(self, port_name: str) -> None:
        """Connect to the specified serial port"""
        # First disconnect if already connected
        if self.serial_port.isOpen():
            self.disconnect()

        try:
            # Configure serial port
            self.serial_port.setPortName(port_name)
            self.serial_port.setBaudRate(self.baud_rate)
            self.serial_port.setDataBits(QSerialPort.DataBits.Data8)
            self.serial_port.setParity(QSerialPort.Parity.NoParity)
            self.serial_port.setStopBits(QSerialPort.StopBits.OneStop)
            self.serial_port.setFlowControl(QSerialPort.FlowControl.NoFlowControl)

            # Open the port
            if not self.serial_port.open(QIODevice.OpenModeFlag.ReadOnly):
                error = self.serial_port.error()
                self.connectionStatusChanged.emit(
                    False, f"Failed to open port: {error}"
                )
                return

            # Reset time tracking and flags
            self.elapsed_time = 0.0
            self.last_timestamp = time.time()
            self.last_data_received = time.time()
            self.buffer = ""
            self.data_received = False

            # Signal success initially
            self.connectionStatusChanged.emit(True, f"Connected to {port_name}")

            # Start watchdog timer to check for incoming data
            # First check after 2 seconds if any data arrived at all
            self.data_watchdog.start(2000)

        except Exception as e:
            self.connectionStatusChanged.emit(False, f"Connection error: {str(e)}")

    def disconnect(self) -> None:
        """Disconnect from the serial port"""
        # Stop the data watchdog timer
        self.data_watchdog.stop()

        if self.serial_port.isOpen():
            self.serial_port.close()
            self.connectionStatusChanged.emit(False, "Disconnected")

    def _handle_error(self, error: QSerialPort.SerialPortError) -> None:
        """Handle serial port errors"""
        if error != QSerialPort.SerialPortError.NoError:
            error_msg = self._get_error_message(error)

            # ResourceError typically means the device was unplugged
            if error == QSerialPort.SerialPortError.ResourceError:
                self.connectionStatusChanged.emit(
                    False, f"Device disconnected: {error_msg}"
                )
            else:
                self.connectionStatusChanged.emit(False, f"Serial error: {error_msg}")

            # Try to close and reopen if there's a recoverable error
            if error in [
                QSerialPort.SerialPortError.ResourceError,
                QSerialPort.SerialPortError.TimeoutError,
                QSerialPort.SerialPortError.ReadError,
            ]:
                port_name = self.serial_port.portName()
                self.disconnect()
                # Schedule a reconnection attempt
                QTimer.singleShot(
                    3000, lambda port=port_name: self.connect_to_port(port)
                )

    def _get_error_message(self, error: QSerialPort.SerialPortError) -> str:
        """Convert QSerialPort error enum to a human-readable message"""
        error_messages = {
            QSerialPort.SerialPortError.NoError: "No error",
            QSerialPort.SerialPortError.DeviceNotFoundError: "Device not found",
            QSerialPort.SerialPortError.PermissionError: "Permission denied",
            QSerialPort.SerialPortError.OpenError: "Failed to open port",
            QSerialPort.SerialPortError.NotOpenError: "Port not open",
            QSerialPort.SerialPortError.WriteError: "Write error",
            QSerialPort.SerialPortError.ReadError: "Read error",
            QSerialPort.SerialPortError.ResourceError: "Resource error (device disconnected)",
            QSerialPort.SerialPortError.UnsupportedOperationError: "Unsupported operation",
            QSerialPort.SerialPortError.TimeoutError: "Operation timed out",
            QSerialPort.SerialPortError.UnknownError: "Unknown error",
        }
        return error_messages.get(error, f"Error code: {error}")

    def _read_data(self) -> None:
        """Read available data from serial port"""
        if self.serial_port.isOpen() and self.serial_port.bytesAvailable() > 0:
            data = self.serial_port.readAll()
            self.buffer += bytes(data).decode("utf-8", errors="replace")

            # Update data receipt tracking
            self.last_data_received = time.time()
            self.data_received = True

            # If it's the first data after connection, adjust the watchdog timer
            # to check every second after the first data arrives
            if self.data_watchdog.interval() == 2000:
                self.data_watchdog.stop()
                self.data_watchdog.start(1000)  # Check every second after initial data

            self._process_buffer()

    def _process_buffer(self) -> None:
        """Process the buffer for complete lines of data"""
        while "\n" in self.buffer:
            line, self.buffer = self.buffer.split("\n", 1)
            line = line.strip()
            if line:  # Skip empty lines
                self._process_line(line)

    def _process_line(self, line: str) -> None:
        """Process a complete line of data from Arduino"""
        try:
            # Parse data (expected format: vertical_val,horizontal_val)
            values = line.split(",")
            if len(values) == 2:
                vertical_raw = int(values[0].strip())
                horizontal_raw = int(values[1].strip())

                # Validate values are in expected range (0-1023 for Arduino ADC)
                if not (0 <= vertical_raw <= 1023 and 0 <= horizontal_raw <= 1023):
                    return

                # Convert raw values (0-1023) to voltage (0-5V)
                conversion_factor = 5.0 / 1023.0
                vertical_voltage = vertical_raw * conversion_factor
                horizontal_voltage = horizontal_raw * conversion_factor

                # Calculate timestamp
                current_time = time.time()
                time_delta = current_time - self.last_timestamp
                
                # Prevent time jumps that could be caused by system time changes
                if 0 < time_delta < 1.0:  # Normal range for data rate
                    self.elapsed_time += time_delta
                    
                self.last_timestamp = current_time

                # Emit the new sample with both channel values
                self.newSample.emit(
                    self.elapsed_time, vertical_voltage, horizontal_voltage
                )

        except (ValueError, IndexError) as e:
            # Skip malformed data
            pass

    def _check_data_flow(self) -> None:
        """Check if data is flowing from the Arduino"""
        current_time = time.time()

        # If no data has been received at all after the initial connection (2 seconds)
        if not self.data_received and self.data_watchdog.interval() == 2000:
            self.disconnect()
            self.connectionStatusChanged.emit(
                False,
                "No data received from Arduino. Check if device is sending data properly.",
            )
            return

        # If data flow has stopped (no data for more than 1 second)
        if self.data_received and (current_time - self.last_data_received) > 1.0:
            self.disconnect()
            self.connectionStatusChanged.emit(
                False,
                "Data flow stopped. Arduino connection lost or data transmission interrupted.",
            )
            return

    def reset(self) -> None:
        """Reset the signal generator time"""
        self.elapsed_time = 0.0
        self.last_timestamp = time.time()
