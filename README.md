# Arduino Serial Oscilloscope - Experiment Recorder

A PyQt6-based application that functions as a dual-channel oscilloscope for Arduino signals while recording experimental data.

## Overview

This application provides a real-time visualization and recording system for analog signals from an Arduino. It features dual-channel oscilloscope displays, comprehensive control panels, participant management, and experimental data recording capabilities.

## Features

- **Real-time dual-channel oscilloscope display**
  - Vertical and horizontal signal visualization
  - Adjustable time and voltage ranges
  - Auto-scrolling display with "View All" option
  - Real-time signal statistics (average, peak, samples/second)

- **Arduino serial connection management**
  - Automatic port detection and connection
  - Connection status monitoring
  - Auto-reconnection on connection loss
  - Data watchdog to ensure continuous data flow

- **Experiment management**
  - Participant registration system
  - Session control (start, pause, resume, end)
  - Comprehensive data recording with timestamps

- **Data management**
  - CSV-based data storage for maximum compatibility
  - Background data buffering for performance
  - Automatic backup system
  - Session and participant tracking

## Hardware Requirements

- Arduino board with at least 2 analog inputs
- USB connection to computer
- Analog sensors or signal sources

## Software Requirements

- Python 3.10+
- Required Python packages (see requirements.txt):
  - PyQt6
  - pyqtgraph
  - numpy

## Installation

1. Clone the repository:
   ```
   git clone [repository-url]
   cd plotter
   ```

2. Install the required dependencies:
   ```
   pip install -r requirements.txt
   ```

## Usage

### Running the Application

```
python main.py
```

### Application Workflow

1. **Connect to Arduino:**
   - Select Arduino port from the dropdown in the Serial Control panel
   - Click "Connect"
   - Status will update to "Connected" when successful

2. **Register a Participant:**
   - Enter Participant ID in the Participant Control panel
   - Click "Register"
   - Participant data will be saved to the experiment database

3. **Start an Experiment Session:**
   - After registering a participant, click "Start Session"
   - The recording status will change to "Recording"
   - Data from both channels will now be recorded

4. **Control the Display:**
   - Adjust time range (5s, 10s, 20s) using Time Control panel
   - Set voltage ranges using Voltage Control panel
   - Use "View All" to see the entire dataset

5. **Manage the Session:**
   - Pause/Resume recording using the session controls
   - Click "End Session" to complete the experiment
   - Data is automatically backed up when a session ends

### Data Files

The application creates an `experiment_data` directory containing:

- `participants.csv`: Registry of all participants
- `sessions.csv`: Details of each experimental session
- Individual session CSV files with the raw measurement data

Data format:
- timestamp: Unix timestamp when the measurement was taken
- elapsed_time: Time in seconds from the start of the recording
- vertical_value: Voltage reading from the vertical channel (0-5V)
- horizontal_value: Voltage reading from the horizontal channel (0-5V)

## Arduino Setup

Your Arduino should be programmed to continuously send analog readings in the following format:
```
vertical_value,horizontal_value\n
```

Where:
- `vertical_value` is an integer from 0-1023 (10-bit ADC value)
- `horizontal_value` is an integer from 0-1023 (10-bit ADC value)
- Values are separated by a comma
- Each reading ends with a newline character

Example Arduino sketch:
```cpp
void setup() {
  Serial.begin(115200);
}

void loop() {
  int vertical = analogRead(A0);
  int horizontal = analogRead(A1);
  
  Serial.print(vertical);
  Serial.print(",");
  Serial.println(horizontal);
  
  delay(10); // 100Hz sample rate
}
```

## Development

- Format code: `black .`
- Type check: `mypy .`
- Lint code: `pylint main.py`

## Architecture

The application follows a modular architecture with separation of concerns:

- **Core Components:**
  - `signal_generator.py`: Handles Arduino communication and signal processing
  - `data_recorder.py`: Manages data recording and storage
  - `database_backup.py`: Handles data backup operations

- **UI Components:**
  - `app.py`: Main application window and component orchestration
  - `oscilloscope_display.py`: Signal visualization widgets
  - `control_panel.py`: Container for all control panels
  - Sub-panels: Individual control components for specific functions

- **Communication:**
  - The application uses Qt's signal/slot mechanism for inter-component communication
  - Core components emit signals when data changes
  - UI components connect to these signals and update accordingly