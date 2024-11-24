# Camera Sensor Documentation

## Overview
This program implements a motion and light change detection system using a Raspberry Pi camera. It captures images continuously, analyzes them for significant changes, and triggers actions when motion or light changes are detected. The system includes LED feedback through NeoPixels and can save images locally and/or upload them to AWS S3.

## Features
- Motion and light change detection
- Configurable activation thresholds and cooldown periods
- LED status indication using NeoPixels
- Local image storage
- AWS S3 upload capability
- MQTT integration for external device control
- Day/Night mode operation
- Configurable resolution and sampling intervals

## Prerequisites

### Hardware Requirements
- Raspberry Pi (any model with camera support)
- Raspberry Pi Camera Module
- NeoPixel LED strip
- Appropriate power supply

### Software Requirements
```
opencv-python==4.8.1.78
numpy==1.26.2
RPi.GPIO>=0.7.1
board==1.0
adafruit-blinka==8.25.0
adafruit-circuitpython-neopixel>=6.3.9
paho-mqtt==1.6.1
boto3==1.33.6
botocore==1.33.6
```

## Installation

1. Update system packages:
```bash
sudo apt-get update
sudo apt-get install -y python3-dev python3.11-dev gcc build-essential libcap-dev libpython3.11-dev
```

2. Create and activate virtual environment:
```bash
python -m venv camera
source camera/bin/activate
```

3. Install required packages:
```bash
pip install -r requirements.txt
sudo apt install -y python3-picamera2
```

## Configuration

The system is configured through `config.py`. Here are the key configuration parameters:

### MQTT Configuration
```python
MQTT_BROKER = "mqtthost"
MQTT_PORT = 1883
MQTT_USERNAME = "mqtt username"
MQTT_PASSWORD = "mqtt password"
```

### Camera Configuration
```python
MAX_IMAGES = 100
ACTIVATION_THRESHOLD = 5000000
MIN_AREA = 20000
SAMPLE_INTERVAL = 0.05
ACTIVATION_COOLDOWN = 40
RESOLUTION = (320, 240)
```

### Time Configuration
```python
DISABLED_START_HOUR = 22  # 10 PM
DISABLED_END_HOUR = 6    # 6 AM
```

### Storage Configuration
```python
SAVE_LOCALLY = False
LOCAL_STORAGE_PATH = "activation_images"
UPLOAD_TO_S3 = False
```

## Core Components

### Motion Detection
The system uses OpenCV to detect motion by:
1. Converting images to grayscale
2. Applying Gaussian blur
3. Computing frame differences
4. Identifying significant contours

### Light Change Detection
Monitors overall brightness changes between frames using mean pixel values.

### LED Feedback
NeoPixel LEDs provide system status:
- GREEN: System ready for next activation
- RED: Motion detected, cooling down
- YELLOW: Cooldown progress indication
- OFF: System inactive (night mode)

### Storage Management
- Local storage with configurable maximum image count
- S3 upload with customizable path and bucket settings
- Temporary file cleanup for S3-only operation

## MQTT Integration

The system can trigger MQTT messages on activation. Configure messages in `config.py`:
```python
MQTT_CONFIGURATIONS = [
   {
       "topic": "your/topic",
        "payload": {
            "duration": 2,
            "direction": 1,
            "minpower": 15,
            "maxpower": 15
        }
    }
]
```

## Operation Modes

### Day Mode (6 AM - 10 PM)
- Full system operation
- Motion and light change detection active
- LED feedback enabled

### Night Mode (10 PM - 6 AM)
- System inactive
- LEDs turned off
- No image capture or motion detection

## Error Handling
- Camera connection issues
- MQTT connection failures
- S3 upload errors
- File system errors

## Logging
The system logs important events with timestamps:
- System start/stop
- Activations detected
- Image saves and uploads
- Error conditions
- State changes (day/night mode)

## Usage

1. Configure the system through `config.py`
2. Ensure hardware is properly connected
3. Run the program:
```bash
python camera-sensor.py
```

## Maintenance

### Regular Tasks
1. Monitor disk space when using local storage
2. Check S3 bucket usage if enabled
3. Review log files for errors
4. Update configuration as needed

### Troubleshooting
- Check camera connection if image capture fails
- Verify MQTT broker connectivity
- Confirm AWS credentials if S3 uploads fail
- Monitor system resources (CPU, memory)

## Best Practices
1. Set appropriate `MIN_AREA` for motion detection
2. Adjust `ACTIVATION_THRESHOLD` based on environment
3. Configure `SAMPLE_INTERVAL` based on CPU capacity
4. Use `VERBOSE` mode for debugging
5. Implement appropriate security measures for MQTT and AWS credentials
