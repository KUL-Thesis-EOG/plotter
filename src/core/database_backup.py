import os
import sqlite3
import csv
import time
import threading
import logging
from typing import Dict, List, Set, Tuple, Optional, Any
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileCreatedEvent, FileModifiedEvent
from PyQt6.QtCore import QObject, pyqtSignal


class DatabaseBackup(QObject):
    """Backs up experiment data CSV files to SQLite database"""

    statusChanged = pyqtSignal(bool, str)

    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)

        # Get data directory
        self.app_dir = os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )
        self.data_dir = os.path.join(self.app_dir, "experiment_data")
        self.db_path = os.path.join(self.data_dir, "experiment_backup.db")

        # Initialize database
        self._init_database()

        # Keep track of processed files to avoid duplicates
        self.processed_files: Dict[str, float] = {}
        self.processed_lock = threading.Lock()
        
        # Load existing processed files to avoid reprocessing on startup
        self.load_processed_files_cache()
        
        # Set up file watcher with a longer delay to reduce processing frequency
        self.observer = Observer()
        self.event_handler = CSVFileHandler(self)
        self.observer.schedule(self.event_handler, self.data_dir, recursive=False)
        
        # Start observer
        self.observer.start()
        
        self.statusChanged.emit(True, "Database backup system initialized")

    def _init_database(self) -> None:
        """Initialize SQLite database with required tables"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Create participants table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS participants (
                    participant_id INTEGER PRIMARY KEY,
                    created_at REAL
                )
            ''')
            
            # Create sessions table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id INTEGER PRIMARY KEY,
                    participant_id INTEGER,
                    started_at REAL,
                    data_file TEXT,
                    FOREIGN KEY (participant_id) REFERENCES participants (participant_id)
                )
            ''')
            
            # Create measurements table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS measurements (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id INTEGER,
                    timestamp REAL,
                    elapsed_time REAL,
                    vertical_value REAL,
                    horizontal_value REAL,
                    FOREIGN KEY (session_id) REFERENCES sessions (session_id)
                )
            ''')
            
            # Create table to track processed files
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS processed_files (
                    file_path TEXT PRIMARY KEY,
                    last_modified REAL,
                    last_processed REAL,
                    rows_processed INTEGER
                )
            ''')
            
            conn.commit()
            conn.close()
        except Exception as e:
            self.statusChanged.emit(False, f"Error initializing database: {str(e)}")

    def backup_participants_file(self) -> None:
        """Backup participants data from CSV to SQLite"""
        participants_file = os.path.join(self.data_dir, "participants.csv")
        if not os.path.exists(participants_file):
            return
            
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Read existing participant IDs from database
            cursor.execute("SELECT participant_id FROM participants")
            existing_ids = {row[0] for row in cursor.fetchall()}
            
            # Read and insert new participants
            with open(participants_file, 'r', newline='') as f:
                reader = csv.reader(f)
                next(reader)  # Skip header
                
                # Prepare batch insert
                new_participants = []
                for row in reader:
                    if not row or not row[0].isdigit():
                        continue
                        
                    participant_id = int(row[0])
                    created_at = float(row[1]) if len(row) > 1 and row[1] else time.time()
                    
                    if participant_id not in existing_ids:
                        new_participants.append((participant_id, created_at))
                
                # Insert all new participants in one batch
                if new_participants:
                    cursor.executemany(
                        "INSERT OR IGNORE INTO participants (participant_id, created_at) VALUES (?, ?)",
                        new_participants
                    )
                    
            conn.commit()
            conn.close()
            self.statusChanged.emit(True, f"Backed up participants data: {len(new_participants)} new entries")
        except Exception as e:
            self.statusChanged.emit(False, f"Error backing up participants: {str(e)}")

    def backup_sessions_file(self) -> None:
        """Backup sessions data from CSV to SQLite"""
        sessions_file = os.path.join(self.data_dir, "sessions.csv")
        if not os.path.exists(sessions_file):
            return
            
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Read existing session IDs from database
            cursor.execute("SELECT session_id FROM sessions")
            existing_ids = {row[0] for row in cursor.fetchall()}
            
            # Read and insert new sessions
            with open(sessions_file, 'r', newline='') as f:
                reader = csv.reader(f)
                next(reader)  # Skip header
                
                # Prepare batch insert
                new_sessions = []
                for row in reader:
                    if not row or len(row) < 4 or not row[0].isdigit():
                        continue
                        
                    session_id = int(row[0])
                    participant_id = int(row[1]) if row[1].isdigit() else None
                    started_at = float(row[2]) if row[2] else time.time()
                    data_file = row[3] if row[3] else None
                    
                    if session_id not in existing_ids:
                        new_sessions.append((session_id, participant_id, started_at, data_file))
                
                # Insert all new sessions in one batch
                if new_sessions:
                    cursor.executemany(
                        "INSERT OR IGNORE INTO sessions (session_id, participant_id, started_at, data_file) VALUES (?, ?, ?, ?)",
                        new_sessions
                    )
                    
            conn.commit()
            conn.close()
            self.statusChanged.emit(True, f"Backed up sessions data: {len(new_sessions)} new entries")
        except Exception as e:
            self.statusChanged.emit(False, f"Error backing up sessions: {str(e)}")

    def backup_measurements_file(self, file_path: str) -> None:
        """Backup experiment measurements from CSV to SQLite"""
        # Skip metadata files
        if os.path.basename(file_path) in ("participants.csv", "sessions.csv"):
            return
            
        # Skip non-CSV files
        if not file_path.endswith('.csv'):
            return
            
        # Check if file exists
        if not os.path.exists(file_path):
            return
            
        try:
            # Get file modification time
            mod_time = os.path.getmtime(file_path)
            
            # Check if already processed this version of the file
            with self.processed_lock:
                if file_path in self.processed_files and self.processed_files[file_path] >= mod_time:
                    return  # Already processed this version
            
            # Try to extract session ID from filename
            # Format: session_{id}_participant_{id}_{timestamp}.csv
            try:
                filename = os.path.basename(file_path)
                parts = filename.split('_')
                if len(parts) >= 2 and parts[0] == "session" and parts[1].isdigit():
                    session_id = int(parts[1])
                else:
                    # If can't parse, skip file
                    self.statusChanged.emit(False, f"Cannot determine session ID for file: {filename}")
                    return
            except Exception:
                # If can't parse, skip file
                self.statusChanged.emit(False, f"Cannot parse filename: {os.path.basename(file_path)}")
                return
                
            conn = sqlite3.connect(self.db_path)
            
            # Enable WAL mode for better performance
            conn.execute("PRAGMA journal_mode = WAL")
            # Larger page size for better performance with large data
            conn.execute("PRAGMA page_size = 4096")
            # Increase cache size for better performance
            conn.execute("PRAGMA cache_size = 10000")
            
            cursor = conn.cursor()
            
            # Check if this file has been processed before
            cursor.execute(
                "SELECT rows_processed FROM processed_files WHERE file_path = ?", 
                (file_path,)
            )
            result = cursor.fetchone()
            rows_already_processed = result[0] if result else 0
            
            # Read and process measurements from file in chunks to avoid loading entire file
            batch_size = 5000  # Process up to 5000 rows at a time
            new_rows_count = 0
            
            with open(file_path, 'r', newline='') as f:
                reader = csv.reader(f)
                next(reader)  # Skip header
                
                # Skip already processed rows
                for _ in range(rows_already_processed):
                    try:
                        next(reader)
                    except StopIteration:
                        # Reached end of file prematurely
                        break
                
                # Process remaining rows in batches
                current_batch = []
                row_count = rows_already_processed
                
                try:
                    # Begin transaction for better performance
                    conn.execute("BEGIN TRANSACTION")
                    
                    for row in reader:
                        if not row or len(row) < 4:
                            continue
                            
                        try:
                            timestamp = float(row[0]) if row[0] else time.time()
                            elapsed_time = float(row[1]) if row[1] else 0.0
                            vertical_value = float(row[2]) if row[2] else 0.0
                            horizontal_value = float(row[3]) if row[3] else 0.0
                            
                            current_batch.append((session_id, timestamp, elapsed_time, vertical_value, horizontal_value))
                            row_count += 1
                            new_rows_count += 1
                            
                            # Insert batch if we've reached batch size
                            if len(current_batch) >= batch_size:
                                cursor.executemany(
                                    """INSERT INTO measurements 
                                       (session_id, timestamp, elapsed_time, vertical_value, horizontal_value) 
                                       VALUES (?, ?, ?, ?, ?)""",
                                    current_batch
                                )
                                current_batch = []
                        except (ValueError, IndexError):
                            # Skip malformed rows
                            continue
                    
                    # Insert any remaining rows
                    if current_batch:
                        cursor.executemany(
                            """INSERT INTO measurements 
                               (session_id, timestamp, elapsed_time, vertical_value, horizontal_value) 
                               VALUES (?, ?, ?, ?, ?)""",
                            current_batch
                        )
                    
                    # Update processed files record only after successful processing
                    cursor.execute(
                        """INSERT OR REPLACE INTO processed_files 
                           (file_path, last_modified, last_processed, rows_processed) 
                           VALUES (?, ?, ?, ?)""",
                        (file_path, mod_time, time.time(), row_count)
                    )
                    
                    # Commit the transaction
                    conn.commit()
                except Exception as e:
                    # Rollback on error
                    conn.rollback()
                    raise e
                    
            conn.close()
            
            # Update in-memory processed files
            with self.processed_lock:
                self.processed_files[file_path] = mod_time
                
            if new_rows_count > 0:
                self.statusChanged.emit(True, f"Backed up measurements from {os.path.basename(file_path)}: {new_rows_count} new rows")
        except Exception as e:
            self.statusChanged.emit(False, f"Error backing up measurements file {os.path.basename(file_path)}: {str(e)}")

    def backup_all_files(self) -> None:
        """Backup all CSV files in the data directory"""
        try:
            # First, backup metadata files
            self.backup_participants_file()
            self.backup_sessions_file()
            
            # Then, backup all measurement files
            for filename in os.listdir(self.data_dir):
                if filename.endswith('.csv') and filename not in ('participants.csv', 'sessions.csv'):
                    file_path = os.path.join(self.data_dir, filename)
                    self.backup_measurements_file(file_path)
        except Exception as e:
            self.statusChanged.emit(False, f"Error in backup_all_files: {str(e)}")

    def load_processed_files_cache(self) -> None:
        """Load cache of processed files from database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("SELECT file_path, last_modified FROM processed_files")
            rows = cursor.fetchall()
            
            with self.processed_lock:
                self.processed_files = {row[0]: row[1] for row in rows}
                
            conn.close()
        except Exception as e:
            self.statusChanged.emit(False, f"Error loading processed files cache: {str(e)}")

    def cleanup(self) -> None:
        """Clean up resources"""
        try:
            # Stop observer
            if self.observer.is_alive():
                self.observer.stop()
                self.observer.join(2.0)
                
            self.statusChanged.emit(True, "Database backup system shut down")
        except Exception as e:
            self.statusChanged.emit(False, f"Error in database backup cleanup: {str(e)}")


class CSVFileHandler(FileSystemEventHandler):
    """Watchdog handler for CSV file changes"""
    
    def __init__(self, backup_manager: DatabaseBackup):
        self.backup_manager = backup_manager
        self.last_processed: Dict[str, float] = {}
        self.pending_files: Set[str] = set()
        self.processing_timer: Optional[threading.Timer] = None
        self.processing_lock = threading.Lock()
        
    def on_created(self, event: FileCreatedEvent) -> None:
        """Handle file creation event"""
        if not event.is_directory and event.src_path.endswith('.csv'):
            # Add to pending files and schedule processing
            self._schedule_processing(event.src_path)
            
    def on_modified(self, event: FileModifiedEvent) -> None:
        """Handle file modification event"""
        if not event.is_directory and event.src_path.endswith('.csv'):
            # Add debouncing to avoid processing the same file multiple times
            now = time.time()
            
            # Check if we processed this file recently (within 5 seconds)
            if event.src_path in self.last_processed and now - self.last_processed[event.src_path] < 5:
                return
                
            self.last_processed[event.src_path] = now
            self._schedule_processing(event.src_path)
    
    def _schedule_processing(self, file_path: str) -> None:
        """Schedule processing of file with batching"""
        with self.processing_lock:
            # Add file to pending set
            self.pending_files.add(file_path)
            
            # If there's already a timer running, let it handle this file too
            if self.processing_timer is not None and self.processing_timer.is_alive():
                return
                
            # Otherwise, start a new timer to process all pending files
            self.processing_timer = threading.Timer(3.0, self._process_pending_files)
            self.processing_timer.daemon = True
            self.processing_timer.start()
    
    def _process_pending_files(self) -> None:
        """Process all pending files in batch"""
        with self.processing_lock:
            pending = list(self.pending_files)
            self.pending_files.clear()
            
        # Process metadata files first
        measurements_files = []
        
        for file_path in pending:
            basename = os.path.basename(file_path)
            try:
                if basename == "participants.csv":
                    self.backup_manager.backup_participants_file()
                elif basename == "sessions.csv":
                    self.backup_manager.backup_sessions_file()
                else:
                    # Collect measurement files for batch processing
                    measurements_files.append(file_path)
            except Exception as e:
                self.backup_manager.statusChanged.emit(
                    False, f"Error processing file {basename}: {str(e)}"
                )
                
        # Process measurement files if there are any
        if measurements_files:
            try:
                # Process one by one but in a batch context
                for file_path in measurements_files:
                    self.backup_manager.backup_measurements_file(file_path)
            except Exception as e:
                self.backup_manager.statusChanged.emit(
                    False, f"Error in batch processing: {str(e)}"
                )