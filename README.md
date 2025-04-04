# Arduino Serial Oscilloscope - Simplified

A PyQt6-based application that functions as a dual-channel oscilloscope for Arduino signals while recording experimental data.

## Overview

This application provides a real-time visualization and recording system for analog signals from an Arduino. It features dual-channel oscilloscope displays, basic control panels, participant management, and experimental data recording capabilities.

![Application](images/App.png)

## Features

- **Real-time dual-channel oscilloscope display**
  - Vertical and horizontal signal visualization
  - Fixed display window showing 5000 samples
  - Auto-scaling display

- **Arduino serial connection management**
  - Automatic port detection and connection
  - Connection status monitoring
  - Auto-reconnection on connection loss
  - Data watchdog to ensure continuous data flow

- **Experiment management**
  - Participant registration system
  - Session control (start, pause, resume, end)
  - Data recording with timestamps

- **Data management**
  - CSV-based data storage for maximum compatibility
  - Background data buffering for performance

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
   - Enter Participant ID in the Experiment Control panel
   - Click "Register"
   - Participant data will be saved to the experiment data files

3. **Start an Experiment Session:**
   - After registering a participant, click "Start Recording"
   - The recording status will change to indicate recording is active
   - Data from both channels will now be recorded

4. **Manage the Session:**
   - Pause/Resume recording using the session controls
   - Click "End Session" to complete the experiment

### Data Files

The application creates an `experiment_data` directory containing:

- `participants.csv`: Registry of all participants
- `sessions.csv`: Details of each experimental session
- Individual session CSV files with the raw measurement data

Data format:
- timestamp: Unix timestamp when the measurement was taken
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
int sensorPin1 = A0;  // input pin for the first potentiometer
int sensorPin2 = A1;  // input pin for the second potentiometer
int digitalValue1 = 0;  // variable to store the value from A0
int digitalValue2 = 0;  // variable to store the value from A1
unsigned long nextSampleTime = 0;  // time for the next sample
const unsigned long samplePeriod = 2000;  // 2000 microseconds = 2ms = 500Hz

void setup() {
  Serial.begin(115200);
  nextSampleTime = micros();  // Initialize next sample time
}

void loop() {
  unsigned long currentTime = micros();
  
  if ((long)(currentTime - nextSampleTime) >= 0) {
    digitalValue1 = analogRead(sensorPin1);
    digitalValue2 = analogRead(sensorPin2);
    
    Serial.print(digitalValue1);
    Serial.print(",");
    Serial.println(digitalValue2);
    
    nextSampleTime += samplePeriod;
  }
}
```

## Development

- Format code: `black .`
- Type check: `mypy .`
- Lint code: `pylint main.py` or `pylint src/`
- Run application: `python main.py`

## Architecture

The application follows a modular architecture with separation of concerns:

- **Core Components:**
  - `signal_generator.py`: Handles Arduino communication and signal processing
  - `data_recorder.py`: Manages data recording and storage

- **UI Components:**
  - `app.py`: Main application window and component orchestration
  - `oscilloscope_display.py`: Signal visualization widgets
  - `control_panel.py`: Container for all control panels
  - `serial_control.py`: Serial connection management
  - `participant_control.py`: Participant and session management

- **Communication:**
  - The application uses Qt's signal/slot mechanism for inter-component communication
  - Core components emit signals when data changes
  - UI components connect to these signals and update accordingly