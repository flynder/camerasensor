import cv2
import numpy as np
import subprocess
import time
import os
from collections import deque
from datetime import datetime
import board
import neopixel
import paho.mqtt.client as mqtt
import json
import boto3
from botocore.exceptions import ClientError
import config

# Initialize S3 client if enabled
s3_client = None
if config.UPLOAD_TO_S3:
    try:
        s3_client = boto3.client(
            's3',
            aws_access_key_id=config.AWS_ACCESS_KEY,
            aws_secret_access_key=config.AWS_SECRET_KEY,
            region_name=config.AWS_REGION
        )
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        print(f"{timestamp} - Successfully connected to S3")
    except Exception as e:
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        print(f"{timestamp} - Error connecting to S3: {e}")

# MQTT Configuration
CLIENT_ID = f"fast_kamera_{int(time.time())}"

# NeoPixel configuration
PIXEL_PIN = getattr(board, config.PIXEL_PIN)
pixels = neopixel.NeoPixel(PIXEL_PIN, config.NUM_PIXELS, brightness=config.PIXEL_BRIGHTNESS, auto_write=False)

# Colors
RED = (255, 0, 0)
YELLOW = (255, 255, 0)
GREEN = (0, 255, 0)
OFF = (0, 0, 0)

def upload_to_s3(file_path, activation_count):
    """Upload a file to S3 bucket"""
    if not s3_client:
        return None
        
    try:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        file_name = os.path.basename(file_path)
        s3_path = f"{config.S3_FOLDER}activation_{activation_count}_{timestamp}.jpg"
        
        s3_client.upload_file(file_path, config.AWS_BUCKET_NAME, s3_path)
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        print(f"{timestamp} - Successfully uploaded {file_name} to S3")
        return f"s3://{config.AWS_BUCKET_NAME}/{s3_path}"
    except ClientError as e:
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        print(f"{timestamp} - Error uploading to S3: {e}")
        return None

def is_active_hours():
    current_hour = datetime.now().hour
    if config.DISABLED_START_HOUR <= current_hour or current_hour < config.DISABLED_END_HOUR:
        return False
    return True

def on_connect(client, userdata, flags, rc):
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"{timestamp} - Connected to MQTT Broker with result code: {rc}")

def on_publish(client, userdata, mid):
    if config.VERBOSE:
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        print(f"{timestamp} - Message published with ID: {mid}")

def setup_mqtt():
    client = mqtt.Client(client_id=CLIENT_ID)
    client.username_pw_set(config.MQTT_USERNAME, config.MQTT_PASSWORD)
    client.on_connect = on_connect
    client.on_publish = on_publish
    
    try:
        client.connect(config.MQTT_BROKER, config.MQTT_PORT, 60)
        client.loop_start()
        return client
    except Exception as e:
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        print(f"{timestamp} - Error connecting to MQTT broker: {e}")
        return None

def capture_image():
    subprocess.run(["libcamera-still", "-o", "temp.jpg", "-n", "--immediate",
                    f"--width", str(config.RESOLUTION[0]), 
                    f"--height", str(config.RESOLUTION[1])],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return cv2.imread("temp.jpg")

def save_image(frame, activation_count):
    """
    Save image based on configuration settings.
    Returns a tuple of (local_path, save_success)
    If local saving is disabled, local_path will be a temporary file
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    if config.SAVE_LOCALLY:
        # Ensure directory exists if we're saving locally
        if not os.path.exists(config.LOCAL_STORAGE_PATH):
            os.makedirs(config.LOCAL_STORAGE_PATH)
        filename = f"{config.LOCAL_STORAGE_PATH}/activation_{activation_count}_{timestamp}.jpg"
    else:
        # Use temp directory if we're only uploading to S3
        filename = f"/tmp/activation_{activation_count}_{timestamp}.jpg"
    
    try:
        cv2.imwrite(filename, frame)
        return filename, True
    except Exception as e:
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        print(f"{current_time} - Error saving image: {e}")
        return None, False

def cleanup_temp_file(filepath):
    """Remove temporary file if it exists and we're not saving locally"""
    if not config.SAVE_LOCALLY and filepath and os.path.exists(filepath):
        try:
            os.remove(filepath)
        except Exception as e:
            current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            print(f"{current_time} - Error removing temporary file: {e}")

def set_all_pixels(color):
    pixels.fill(color)
    pixels.show()

def update_pixels_countdown(elapsed_time):
    if not is_active_hours():
        set_all_pixels(OFF)
        return
        
    if elapsed_time >= config.ACTIVATION_COOLDOWN:
        set_all_pixels(GREEN)
    else:
        pixels_to_yellow = int((elapsed_time / config.ACTIVATION_COOLDOWN) * config.NUM_PIXELS)
        for i in range(config.NUM_PIXELS):
            if i < pixels_to_yellow:
                pixels[i] = YELLOW
            else:
                pixels[i] = RED
        pixels.show()

def detect_significant_change(current_frame, previous_frame, min_area):
    frame_delta = cv2.absdiff(previous_frame, current_frame)
    thresh = cv2.threshold(frame_delta, 25, 255, cv2.THRESH_BINARY)[1]
    thresh = cv2.dilate(thresh, None, iterations=2)
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    significant_contours = [cnt for cnt in contours if cv2.contourArea(cnt) > min_area]
    return len(significant_contours) > 0, np.sum(thresh)

def detect_light_change(current_frame, previous_frame, threshold):
    current_brightness = np.mean(current_frame)
    previous_brightness = np.mean(previous_frame)
    return abs(current_brightness - previous_brightness) > threshold

def detect_activation():
    mqtt_client = setup_mqtt()
    if mqtt_client is None:
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        print(f"{timestamp} - MQTT not available - continuing without MQTT")
    
    previous_frame = None
    activation_count = 0
    saved_images = deque(maxlen=config.MAX_IMAGES) if config.SAVE_LOCALLY else None
    last_activation_time = time.time() - config.ACTIVATION_COOLDOWN
    last_active_state = None
    
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"{timestamp} - Detection system started")
    if not config.SAVE_LOCALLY and not config.UPLOAD_TO_S3:
        print(f"{timestamp} - Warning: Both local saving and S3 upload are disabled. No images will be stored!")
    
    # Set initial state
    current_active = is_active_hours()
    if current_active:
        print(f"{timestamp} - System starting in active state")
        set_all_pixels(GREEN)
    else:
        print(f"{timestamp} - System starting in inactive state")
        set_all_pixels(OFF)
    last_active_state = current_active

    while True:
        start_time = time.time()
        
        # Check for state changes
        current_active = is_active_hours()
        if current_active != last_active_state:
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            if current_active:
                print(f"{timestamp} - Entering active hours (06:00-22:00)")
                set_all_pixels(GREEN)
            else:
                print(f"{timestamp} - Entering inactive hours (22:00-06:00)")
                set_all_pixels(OFF)
            last_active_state = current_active

        # Skip processing during disabled hours
        if not current_active:
            time.sleep(config.SAMPLE_INTERVAL)
            continue

        frame = capture_image()
        if frame is None:
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            print(f"{timestamp} - Error capturing image. Make sure the camera is properly connected.")
            time.sleep(config.SAMPLE_INTERVAL)
            continue

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (21, 21), 0)

        if previous_frame is None:
            previous_frame = gray
            continue

        significant_motion, motion_value = detect_significant_change(gray, previous_frame, config.MIN_AREA)
        light_change = detect_light_change(gray, previous_frame, config.COLOR_CHANGE_THRESHOLD)

        current_time = time.time()
        elapsed_time = current_time - last_activation_time

        if config.VERBOSE:
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            print(f"{timestamp} - Motion value: {motion_value}, Significant motion: {significant_motion}, Light change: {light_change}")

        if (significant_motion or light_change) and elapsed_time > config.ACTIVATION_COOLDOWN:
            activation_count += 1
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            print(f"\n{timestamp} - Activation detected! (#{activation_count})")
            print(f"{timestamp} - Motion value: {motion_value}")

            # Save image and get file path
            filename, save_success = save_image(frame, activation_count)
            
            if save_success:
                if config.SAVE_LOCALLY:
                    saved_images.append(filename)
                    print(f"{timestamp} - Image saved locally as: {filename}")
                    print(f"{timestamp} - Number of saved images: {len(saved_images)}")

                # Upload to S3 if enabled
                if config.UPLOAD_TO_S3:
                    s3_path = upload_to_s3(filename, activation_count)
                    if s3_path:
                        print(f"{timestamp} - Image uploaded to: {s3_path}")
                
                # Clean up temp file if not saving locally
                if not config.SAVE_LOCALLY:
                    cleanup_temp_file(filename)

            if mqtt_client:
                # Get the next configuration in rotation
                current_config = config.MQTT_CONFIGURATIONS[activation_count % len(config.MQTT_CONFIGURATIONS)]
    
                try:
                    # Get topic and payload from the current configuration
                    topic = current_config["topic"]
                    payload = current_config["payload"]
        
                    # Publish the message
                    mqtt_client.publish(topic, json.dumps(payload), qos=1)
                    print(f"{timestamp} - MQTT message sent to topic '{topic}': {payload}")
                except Exception as e:
                    print(f"{timestamp} - Error publishing MQTT message: {e}")


            last_activation_time = current_time
            set_all_pixels(RED)
            print(f"{timestamp} - Waiting {config.ACTIVATION_COOLDOWN} seconds before next possible activation...")

        update_pixels_countdown(elapsed_time)

        previous_frame = gray

        if config.VERBOSE:
            processing_time = time.time() - start_time
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            print(f"{timestamp} - Processing time: {processing_time:.3f} seconds")

        sleep_time = max(0, config.SAMPLE_INTERVAL - (time.time() - start_time))
        time.sleep(sleep_time)

if __name__ == "__main__":
    try:
        detect_activation()
    finally:
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        print(f"{timestamp} - Shutting down detection system")
        set_all_pixels(OFF)
        if 'mqtt_client' in locals() and mqtt_client is not None:
            mqtt_client.loop_stop()
            mqtt_client.disconnect()
