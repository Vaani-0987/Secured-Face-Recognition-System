DATASET_DIR = "data/dataset"
TRAINER_PATH = "data/trainer.yml"
LABELS_PATH = "data/labels.json"
LOG_PATH = "data/access_log.csv"
PINS_PATH = "data/pins.json"
STATUS_PATH = "data/status.json"

# LBPH face recognizer parameters / thresholds
# For LBPH in OpenCV, LOWER confidence values are better.
# You may adjust this based on your lighting and camera:
RECOGNITION_CONFIDENCE_THRESHOLD = 70.0

# Number of face images to capture during enrollment
IMAGES_PER_USER = 25

# How long (in seconds) the "Access Granted" status is considered active
ACCESS_GRANTED_DURATION = 5.0
