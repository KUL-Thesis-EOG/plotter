import os
import time
import csv
from typing import Optional, List, Tuple, Any, TextIO
from PyQt6.QtCore import QObject, pyqtSignal, QTimer


class DataRecorder(QObject):
    """Ultra-minimal data recorder using CSV files - Simplified for robustness"""

    statusChanged = pyqtSignal(bool, str)

    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)

        # Create data directory
        self.app_dir = os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )
        self.data_dir = os.path.join(self.app_dir, "experiment_data")
        os.makedirs(self.data_dir, exist_ok=True)

        # Metadata file paths
        self.participants_file = os.path.join(self.data_dir, "participants.csv")
        self.sessions_file = os.path.join(self.data_dir, "sessions.csv")

        # Initialize metadata files if they don't exist
        self._init_metadata_files()

        # State variables
        self.participant_id: Optional[int] = None
        self.session_id: Optional[int] = None
        self.experiment_running: bool = False
        self.data_file: Optional[str] = None
        self.data_file_handle: Optional[TextIO] = None
        self.csv_writer: Any = None

        # Buffer for measurements
        self.buffer: List[Tuple[float, float, float]] = []

        # Qt Timer for flushing data instead of using a separate thread
        self.flush_timer = QTimer(self)
        self.flush_timer.timeout.connect(self._check_and_flush_buffer)
        self.flush_timer.start(200)  # Check every 200ms

        self.statusChanged.emit(True, "Data recorder initialized")

    def _get_next_session_id(self) -> int:
        """Get the next available session ID"""
        if not os.path.exists(self.sessions_file):
            return 1

        try:
            with open(self.sessions_file, "r", newline="") as f:
                reader = csv.reader(f)
                next(reader)  # Skip header

                # Get the highest ID
                max_id = 0
                for row in reader:
                    if row and row[0].isdigit():
                        max_id = max(max_id, int(row[0]))

                return max_id + 1
        except:
            # If anything fails, start from 1
            return 1

    def _init_metadata_files(self) -> None:
        """Initialize metadata files if they don't exist"""
        # Create participants file if it doesn't exist
        if not os.path.exists(self.participants_file):
            with open(self.participants_file, "w", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(["participant_id", "created_at"])

        # Create sessions file if it doesn't exist
        if not os.path.exists(self.sessions_file):
            with open(self.sessions_file, "w", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(
                    ["session_id", "participant_id", "started_at", "data_file"]
                )
                
    def _check_and_flush_buffer(self) -> None:
        """Check if buffer needs flushing and do it"""
        buffer_threshold = 10
        
        if len(self.buffer) >= buffer_threshold or (self.buffer and not self.experiment_running):
            self._flush_buffer()
            
    def _flush_buffer(self) -> None:
        """Flush the current data buffer to file"""
        if not self.buffer or not self.data_file_handle:
            return

        # Get reference to buffer and clear it
        buffer_copy = self.buffer[:]
        self.buffer = []

        # Write data
        try:
            if self.csv_writer and self.data_file_handle:
                for timestamp, vert, horiz in buffer_copy:
                    # Write timestamp and raw voltage values
                    self.csv_writer.writerow([timestamp, vert, horiz])

                # Force flush to disk
                self.data_file_handle.flush()
                # Also force OS to write to disk for extra safety
                os.fsync(self.data_file_handle.fileno())
        except Exception as e:
            self.statusChanged.emit(False, f"Error writing data: {str(e)}")

    def register_participant(self, participant_id: int) -> bool:
        """Register a participant"""
        if participant_id <= 0:
            self.statusChanged.emit(False, "Invalid participant ID")
            return False

        try:
            # Check if participant already exists
            with open(self.participants_file, "r", newline="") as f:
                reader = csv.reader(f)
                next(reader)  # Skip header
                for row in reader:
                    if row and row[0] == str(participant_id):
                        # Participant exists
                        self.participant_id = participant_id
                        self.statusChanged.emit(
                            True, f"Participant {participant_id} registered"
                        )
                        return True

            # Add new participant
            with open(self.participants_file, "a", newline="") as f:
                writer = csv.writer(f)
                writer.writerow([participant_id, time.time()])

            self.participant_id = participant_id
            self.statusChanged.emit(True, f"Participant {participant_id} registered")
            return True
        except Exception as e:
            self.statusChanged.emit(False, f"Error registering participant: {str(e)}")
            return False

    def start_session(self) -> bool:
        """Start a new experiment session"""
        if not self.participant_id:
            self.statusChanged.emit(
                False, "Cannot start session: No participant registered"
            )
            return False

        if self.experiment_running:
            self.statusChanged.emit(False, "Session already running")
            return False

        try:
            # Get next session ID
            next_id = self._get_next_session_id()
            self.session_id = next_id

            # Create data file
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            self.data_file = os.path.join(
                self.data_dir,
                f"session_{next_id}_participant_{self.participant_id}_{timestamp}.csv",
            )

            # Open data file and write header
            self.data_file_handle = open(self.data_file, "w", newline="")
            self.csv_writer = csv.writer(self.data_file_handle)
            self.csv_writer.writerow(
                ["timestamp", "vertical_value", "horizontal_value"]
            )
            # Force immediate write of header
            self.data_file_handle.flush()
            os.fsync(self.data_file_handle.fileno())

            # Record session in sessions file
            with open(self.sessions_file, "a", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(
                    [
                        next_id,
                        self.participant_id,
                        time.time(),
                        os.path.basename(self.data_file),
                    ]
                )

            self.experiment_running = True
            self.statusChanged.emit(
                True, f"Session {next_id} started for participant {self.participant_id}"
            )
            return True
        except Exception as e:
            # Clean up on error
            if self.data_file_handle:
                self.data_file_handle.close()
                self.data_file_handle = None

            self.session_id = None
            self.data_file = None
            self.statusChanged.emit(False, f"Error starting session: {str(e)}")
            return False

    def store_measurement(
        self, time_point: float, vertical_value: float, horizontal_value: float
    ) -> bool:
        """Store a measurement in the buffer"""
        if not self.experiment_running or self.session_id is None:
            return False

        try:
            # Add to buffer - store timestamp and raw values
            self.buffer.append(
                (time.time(), vertical_value, horizontal_value)
            )
            return True
        except Exception as e:
            self.statusChanged.emit(False, f"Error storing measurement: {str(e)}")
            return False

    def pause_session(self) -> None:
        """Pause the current session"""
        if self.experiment_running:
            self.experiment_running = False
            # Immediately flush buffer on pause
            self._flush_buffer()
            self.statusChanged.emit(True, f"Session {self.session_id} paused")

    def resume_session(self) -> None:
        """Resume the current session"""
        if self.session_id and not self.experiment_running:
            self.experiment_running = True
            self.statusChanged.emit(True, f"Session {self.session_id} resumed")

    def end_session(self) -> None:
        """End the current session"""
        if not self.session_id:
            return

        # Stop recording and ensure all data is written
        self.experiment_running = False
        self._flush_buffer()

        # Close the data file
        if self.data_file_handle:
            try:
                self.data_file_handle.flush()
                os.fsync(self.data_file_handle.fileno())
                self.data_file_handle.close()
            except Exception as e:
                self.statusChanged.emit(False, f"Error closing file: {str(e)}")
            finally:
                self.data_file_handle = None

        self.statusChanged.emit(True, f"Session {self.session_id} ended")

        # Reset state
        self.session_id = None
        self.data_file = None
        self.csv_writer = None

    def cleanup(self) -> None:
        """Clean up resources"""
        # End any active session
        if self.experiment_running:
            self.end_session()

        # Stop the flush timer
        self.flush_timer.stop()
        
        # Flush any remaining data immediately
        self._flush_buffer()

        # Close file handle if somehow not closed yet
        if self.data_file_handle:
            try:
                self.data_file_handle.flush()
                os.fsync(self.data_file_handle.fileno())
                self.data_file_handle.close()
            except Exception:
                pass
            self.data_file_handle = None

        self.statusChanged.emit(False, "Data recorder shut down")
