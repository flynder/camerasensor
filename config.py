# MQTT Configuration
MQTT_BROKER = "mqtthost"
MQTT_PORT = 1883
MQTT_USERNAME = "mqtt username"
MQTT_PASSWORD = "mqtt password"
MQTT_TOPIC = "mqtt-topic"

# Camera Configuration
MAX_IMAGES = 100
ACTIVATION_THRESHOLD = 5000000
MIN_AREA = 20000
SAMPLE_INTERVAL = 0.05
ACTIVATION_COOLDOWN = 40
DURATION = ACTIVATION_COOLDOWN / 2
COLOR_CHANGE_THRESHOLD = 50
RESOLUTION = (320, 240)
VERBOSE = False

# Time configuration
DISABLED_START_HOUR = 22  # 10 PM
DISABLED_END_HOUR = 6    # 6 AM

# NeoPixel configuration
PIXEL_PIN = "D18"  # Changed to string as it will be evaluated in main script
NUM_PIXELS = 16
PIXEL_BRIGHTNESS = 1.0

# Storage Configuration
SAVE_LOCALLY = False  # Set to False to disable local storage
LOCAL_STORAGE_PATH = "activation_images"  # Local storage directory

# AWS S3 Configuration
UPLOAD_TO_S3 = False  # Set to False to disable S3 uploads
AWS_ACCESS_KEY = "AWS_ACCESS_KEY"
AWS_SECRET_KEY = "AWS_SECRET_KEY"
AWS_BUCKET_NAME = "aws-bucket-name"
AWS_REGION = "eu-central-1"  # Change to your bucket's region
S3_FOLDER = "camera/"  # Optional: folder path in bucket


# MQTT_COMMANDS = [
#     {
#         "seconds": 20,
#         "direction": "1",
#         "minpower": 15,
#         "maxpower": 15
#     },
# ]


MQTT_CONFIGURATIONS = [
   {
       "topic": "sallingaarhus/command/hometrain/run",
        "payload": {
            "duration": 2,
            "direction": 1,
            "minpower": 15,
            "maxpower": 15
        }
    },
    {
        "topic": "sallingaarhus/command/hometrain/run",
        "payload": {
            "duration": 2,
            "direction": 0,
            "minpower": 15,
            "maxpower": 15
        }
    }
]