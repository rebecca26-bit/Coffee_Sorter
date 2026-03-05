"""
Coffee Sorter with Camera Integration
====================================
Complete implementation combining:
- Raspberry Pi Camera for visual detection
- TCS3200 Color Sensor for color detection
- IR Sensor for bean detection
- Servo motor for sorting

Author: Coffee Sorter Team
Version: 2.0.0
"""

import RPi.GPIO as GPIO
import time
import logging
import sys
import pickle
import numpy as np
from pathlib import Path

# Import our modules
from camera_module import CameraModule, CameraError
from config import (
    # Color sensor pins
    COLOR_S0, COLOR_S1, COLOR_S2, COLOR_S3, COLOR_OUT,
    COLOR_FREQUENCY_SCALE, COLOR_PULSE_DURATION,
    COLOR_THRESHOLDS,
    # Servo settings
    SERVO_PIN, SERVO_HOME, SERVO_GREEN, SERVO_RED,
    SERVO_MOVE_DELAY, SERVO_FREQUENCY,
    # LED settings
    LED_GREEN, LED_RED, LED_BLINK_DURATION,
    # IR sensor
    IR_SENSOR, IR_DEBOUNCE_MS,
    # Timing
    MAIN_LOOP_DELAY, BEAN_PROCESS_TIME,
    LOG_LEVEL, LOG_FILE,
    # Detection mode
    DETECTION_MODE
)


# ============= LOGGING SETUP =============
def setup_logging():
    """Configure logging for the application"""
    logger = logging.getLogger('CoffeeSorterWithCamera')
    logger.setLevel(getattr(logging, LOG_LEVEL))
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG)
    console_format = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    console_handler.setFormatter(console_format)
    
    # File handler
    try:
        file_handler = logging.FileHandler(LOG_FILE)
        file_handler.setLevel(logging.DEBUG)
        file_format = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
        )
        file_handler.setFormatter(file_format)
    except Exception as e:
        print(f"Warning: Could not create log file: {e}")
        file_handler = None
    
    logger.addHandler(console_handler)
    if file_handler:
        logger.addHandler(file_handler)
    
    return logger


# ============= GLOBAL VARIABLES =============
logger = None
servo = None
camera = None
model = None
ir_sensor_state = {
    'last_trigger_time': 0,
    'last_state': None,
    'stable_count': 0,
    'last_reading_time': 0
}


# ============= GPIO SETUP =============
def setup_gpio():
    """Initialize all GPIO pins"""
    global servo
    
    logger.info("Setting up GPIO pins...")
    
    GPIO.setwarnings(False)
    GPIO.setmode(GPIO.BCM)
    
    # IR Sensor
    GPIO.setup(IR_SENSOR, GPIO.IN)
    logger.debug(f"IR_SENSOR configured on GPIO {IR_SENSOR}")
    
    # LEDs
    GPIO.setup(LED_GREEN, GPIO.OUT)
    GPIO.setup(LED_RED, GPIO.OUT)
    GPIO.output(LED_GREEN, False)
    GPIO.output(LED_RED, False)
    logger.debug(f"LEDs configured: GREEN={LED_GREEN}, RED={LED_RED}")
    
    # Servo
    GPIO.setup(SERVO_PIN, GPIO.OUT)
    servo = GPIO.PWM(SERVO_PIN, SERVO_FREQUENCY)
    servo.start(SERVO_HOME)
    time.sleep(1)
    logger.debug(f"Servo configured on GPIO {SERVO_PIN}")
    
    # TCS3200 Color Sensor
    GPIO.setup(COLOR_S0, GPIO.OUT)
    GPIO.setup(COLOR_S1, GPIO.OUT)
    GPIO.setup(COLOR_S2, GPIO.OUT)
    GPIO.setup(COLOR_S3, GPIO.OUT)
    GPIO.setup(COLOR_OUT, GPIO.IN)
    
    # Set frequency scaling
    if COLOR_FREQUENCY_SCALE == "100%":
        GPIO.output(COLOR_S0, True)
        GPIO.output(COLOR_S1, False)
    
    logger.info("GPIO setup complete")


def cleanup_gpio():
    """Clean up GPIO resources"""
    logger.info("Cleaning up GPIO...")
    try:
        if servo:
            servo.stop()
        GPIO.cleanup()
        logger.info("GPIO cleanup complete")
    except Exception as e:
        logger.error(f"Error during GPIO cleanup: {e}")


# ============= MODEL LOADING =============
def load_model(model_path="decision_tree_model.pkl"):
    """Load the ML model for camera-based detection"""
    global model
    
    model_file = Path(model_path)
    if model_file.exists():
        try:
            with open(model_path, 'rb') as f:
                model = pickle.load(f)
            logger.info(f"Model loaded from {model_path}")
            return True
        except Exception as e:
            logger.warning(f"Could not load model: {e}")
            return False
    else:
        logger.warning(f"Model file not found: {model_path}")
        return False


# ============= SERVO FUNCTIONS =============
def set_servo_angle(angle):
    """Move servo to specified angle"""
    try:
        duty = 2 + (angle / 18)
        logger.debug(f"Moving servo to {angle}°")
        servo.ChangeDutyCycle(duty)
        time.sleep(SERVO_MOVE_DELAY)
        servo.ChangeDutyCycle(0)
    except Exception as e:
        logger.error(f"Error moving servo: {e}")
        raise


def move_to_bin(bin_type):
    """Move servo to the appropriate bin"""
    try:
        if bin_type == "green":
            set_servo_angle(SERVO_GREEN)
            logger.info(f"Moved to GREEN bin")
        elif bin_type == "red":
            set_servo_angle(SERVO_RED)
            logger.info(f"Moved to RED bin")
        else:
            set_servo_angle(SERVO_HOME)
            logger.info(f"Moved to CENTER")
    except Exception as e:
        logger.error(f"Error moving to bin: {e}")


# ============= LED FUNCTIONS =============
def set_leds(green_on=False, red_on=False, blink=False):
    """Control LED states"""
    try:
        if blink:
            for _ in range(3):
                GPIO.output(LED_GREEN, green_on)
                GPIO.output(LED_RED, red_on)
                time.sleep(LED_BLINK_DURATION)
                GPIO.output(LED_GREEN, False)
                GPIO.output(LED_RED, False)
                time.sleep(LED_BLINK_DURATION)
        else:
            GPIO.output(LED_GREEN, green_on)
            GPIO.output(LED_RED, red_on)
    except Exception as e:
        logger.error(f"Error controlling LEDs: {e}")


# ============= COLOR SENSOR FUNCTIONS =============
def measure_pulse(duration=COLOR_PULSE_DURATION):
    """Measure pulses from TCS3200"""
    start_time = time.time()
    count = 0
    try:
        while time.time() - start_time < duration:
            if GPIO.input(COLOR_OUT) == 0:
                count += 1
                while GPIO.input(COLOR_OUT) == 0:
                    pass
    except Exception as e:
        logger.error(f"Error measuring pulse: {e}")
    return count


def read_color_sensor():
    """Read color from TCS3200 sensor"""
    try:
        # Red filter
        GPIO.output(COLOR_S2, False)
        GPIO.output(COLOR_S3, False)
        time.sleep(0.01)
        red = measure_pulse()
        
        # Green filter
        GPIO.output(COLOR_S2, True)
        GPIO.output(COLOR_S3, True)
        time.sleep(0.01)
        green = measure_pulse()
        
        logger.debug(f"Color sensor - Red: {red}, Green: {green}")
        
        min_diff = COLOR_THRESHOLDS['min_difference']
        
        if abs(red - green) < min_diff:
            return "unknown"
        
        if red < green:
            ratio = green / red if red > 0 else 0
            if ratio > COLOR_THRESHOLDS['green_ratio_min']:
                return "green"
        else:
            ratio = red / green if green > 0 else 0
            if ratio > COLOR_THRESHOLDS['red_ratio_min']:
                return "red"
        
        return "unknown"
        
    except Exception as e:
        logger.error(f"Error reading color: {e}")
        return "unknown"


# ============= CAMERA DETECTION =============
def detect_bean_color_from_image(image):
    """
    Detect bean color from camera image using ML model.
    
    Args:
        image: RGB image array from camera
    
    Returns:
        str: 'green', 'red', or 'unknown'
    """
    if model is None:
        logger.warning("No model loaded, cannot perform camera detection")
        return "unknown"
    
    try:
        # Preprocess image - extract color features
        # Calculate average color in the center region
        h, w = image.shape[:2]
        center_region = image[h//4:3*h//4, w//4:3*w//4]
        
        # Calculate mean color values
        avg_r = np.mean(center_region[:, :, 0])
        avg_g = np.mean(center_region[:, :, 1])
        avg_b = np.mean(center_region[:, :, 2])
        
        # Create feature vector
        features = np.array([[avg_r, avg_g, avg_b]])
        
        # Make prediction
        prediction = model.predict(features)[0]
        
        logger.debug(f"Camera detection - R:{avg_r:.1f}, G:{avg_g:.1f}, B:{avg_b:.1f} -> {prediction}")
        
        return prediction
        
    except Exception as e:
        logger.error(f"Error in camera detection: {e}")
        return "unknown"


# ============= IR SENSOR DEBOUNCING =============
def read_ir_sensor_debounced():
    """Read IR sensor with debouncing"""
    global ir_sensor_state
    
    current_time = time.time() * 1000
    current_state = GPIO.input(IR_SENSOR)
    
    if current_state != ir_sensor_state['last_state']:
        ir_sensor_state['last_reading_time'] = current_time
        ir_sensor_state['last_state'] = current_state
        ir_sensor_state['stable_count'] = 0
        return False
    
    time_since_change = current_time - ir_sensor_state['last_reading_time']
    if time_since_change >= IR_DEBOUNCE_MS:
        if ir_sensor_state['stable_count'] < 2:
            ir_sensor_state['stable_count'] += 1
        
        if ir_sensor_state['stable_count'] >= 1:
            return current_state == 0
    
    return False


# ============= MAIN SORTING LOGIC =============
def process_bean():
    """Process a single bean with both sensors"""
    logger.info("=== Bean Detected ===")
    
    color_result = {
        'color_sensor': None,
        'camera': None,
        'final': None
    }
    
    try:
        # Read from color sensor
        if DETECTION_MODE in ['color_sensor', 'both']:
            color_result['color_sensor'] = read_color_sensor()
            logger.info(f"Color sensor result: {color_result['color_sensor']}")
        
        # Read from camera
        if DETECTION_MODE in ['camera', 'both'] and camera:
            try:
                image = camera.capture_image()
                color_result['camera'] = detect_bean_color_from_image(image)
                logger.info(f"Camera detection result: {color_result['camera']}")
            except CameraError as e:
                logger.error(f"Camera error: {e}")
                color_result['camera'] = None
        
        # Combine results based on detection mode
        if DETECTION_MODE == 'camera':
            final_color = color_result['camera']
        elif DETECTION_MODE == 'color_sensor':
            final_color = color_result['color_sensor']
        else:  # 'both' - use sensor as primary, camera as secondary
            if color_result['color_sensor'] and color_result['color_sensor'] != 'unknown':
                final_color = color_result['color_sensor']
            else:
                final_color = color_result['camera']
        
        color_result['final'] = final_color or 'unknown'
        
        # Take action based on final color
        if final_color == "green":
            logger.info("Sorting to GREEN bin")
            set_leds(green_on=True)
            move_to_bin("green")
        elif final_color == "red":
            logger.info("Sorting to RED bin")
            set_leds(red_on=True)
            move_to_bin("red")
        else:
            logger.warning("Unknown color, sending to center")
            set_leds(green_on=True, red_on=True)
            move_to_bin("unknown")
        
        # Wait for bean to fall
        time.sleep(BEAN_PROCESS_TIME)
        
        # Return to home
        set_servo_angle(SERVO_HOME)
        set_leds()
        
        logger.info("=== Bean Processing Complete ===")
        
    except Exception as e:
        logger.error(f"Error processing bean: {e}")
        try:
            set_servo_angle(SERVO_HOME)
            set_leds(blink=True)
        except:
            pass


# ============= MAIN LOOP =============
def run():
    """Main application loop"""
    global logger, camera
    
    # Setup
    logger = setup_logging()
    logger.info("=" * 50)
    logger.info("Coffee Sorter v2.0.0 with Camera Starting...")
    logger.info(f"Detection mode: {DETECTION_MODE}")
    logger.info("=" * 50)
    
    try:
        # Setup GPIO
        setup_gpio()
        
        # Try to load ML model
        load_model()
        
        # Initialize camera if needed
        if DETECTION_MODE in ['camera', 'both']:
            try:
                camera = CameraModule(resolution=(640, 480))
                logger.info("Camera initialized successfully")
            except CameraError as e:
                logger.error(f"Camera initialization failed: {e}")
                camera = None
                if DETECTION_MODE == 'camera':
                    logger.error("Camera required but not available, exiting")
                    return
        
        # Move servo to home
        set_servo_angle(SERVO_HOME)
        
        logger.info("Coffee Sorter Running... Press Ctrl+C to stop.")
        
        # Main loop
        while True:
            try:
                if read_ir_sensor_debounced():
                    process_bean()
                
                time.sleep(MAIN_LOOP_DELAY)
                
            except Exception as e:
                logger.error(f"Error in main loop: {e}")
                time.sleep(1)
                
    except KeyboardInterrupt:
        logger.info("Shutdown requested by user")
    except Exception as e:
        logger.critical(f"Fatal error: {e}")
        raise
    finally:
        if camera:
            try:
                camera.stop()
            except:
                pass
        cleanup_gpio()
        logger.info("Coffee Sorter Stopped")


# ============= ENTRY POINT =============
if __name__ == "__main__":
    run()
