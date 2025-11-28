#!/usr/bin/env python3
"""
coffee_sorter.py
Complete coffee bean sorter with ML classification and ThingSpeak integration
With HX711 timeout and skip option for testing
"""

import RPi.GPIO as GPIO
from hx711 import HX711  # Older library
import time
import config
import joblib  # For ML model
import requests  # For ThingSpeak
import signal  # For timeout

# Load ML model
model = joblib.load('decision_tree_model.pkl')

# ThingSpeak settings
THINGSPEAK_API_KEY = 'OBBTD99JSDQKY8F2'  # Replace with your ThingSpeak API key
THINGSPEAK_URL = 'https://api.thingspeak.com/update'

# Timeout handler for HX711 init
def timeout_handler(signum, frame):
    raise TimeoutError("HX711 init timeout")

# Color sensor functions
def count_pulses(duration=config.COLOR_PULSE_DURATION):
    start_time = time.time()
    pulses = 0
    while (time.time() - start_time) < duration:
        if GPIO.input(config.COLOR_OUT) == GPIO.LOW:
            pulses += 1
            while GPIO.input(config.COLOR_OUT) == GPIO.LOW:
                pass
    return int(pulses / duration)

def read_color():
    GPIO.output(config.COLOR_S2, GPIO.LOW)
    GPIO.output(config.COLOR_S3, GPIO.LOW)
    time.sleep(0.1)
    red = count_pulses()
    GPIO.output(config.COLOR_S2, GPIO.HIGH)
    GPIO.output(config.COLOR_S3, GPIO.HIGH)
    time.sleep(0.1)
    green = count_pulses()
    GPIO.output(config.COLOR_S2, GPIO.LOW)
    GPIO.output(config.COLOR_S3, GPIO.HIGH)
    time.sleep(0.1)
    blue = count_pulses()
    return red, green, blue

# ML classification function
def classify_bean(r, g, b, weight):
    prediction = model.predict([[r, g, b, weight]])
    return "GOOD" if prediction[0] == 1 else "BAD"

# Load cell functions
def get_weight(hx, samples=5):
    if hx is None:
        return 0.25  # Default weight for testing when HX711 is disabled
    readings = []
    for _ in range(samples):
        readings.append(hx.get_weight())
        time.sleep(0.1)
    raw = sum(readings) / len(readings)
    return raw / config.LOAD_SCALE  # Manual scaling

# Servo functions
def set_servo_angle(angle):
    duty = 2 + (angle / 18)
    pwm.ChangeDutyCycle(duty)
    time.sleep(config.SERVO_MOVE_DELAY)
    pwm.ChangeDutyCycle(0)

# LED functions
def set_leds(green=False, red=False):
    GPIO.output(config.LED_GREEN, GPIO.HIGH if green else GPIO.LOW)
    GPIO.output(config.LED_RED, GPIO.HIGH if red else GPIO.LOW)

# Setup GPIO
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

# Color sensor
GPIO.setup(config.COLOR_S0, GPIO.OUT)
GPIO.setup(config.COLOR_S1, GPIO.OUT)
GPIO.setup(config.COLOR_S2, GPIO.OUT)
GPIO.setup(config.COLOR_S3, GPIO.OUT)
GPIO.setup(config.COLOR_OUT, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.output(config.COLOR_S0, GPIO.HIGH)  # 100% scaling
GPIO.output(config.COLOR_S1, GPIO.LOW)

# Servo
GPIO.setup(config.SERVO_PIN, GPIO.OUT)
pwm = GPIO.PWM(config.SERVO_PIN, 50)
pwm.start(0)
set_servo_angle(config.SERVO_HOME)  # Start at home

# LEDs
GPIO.setup(config.LED_GREEN, GPIO.OUT)
GPIO.setup(config.LED_RED, GPIO.OUT)
set_leds()  # Off initially

# IR sensor
GPIO.setup(config.IR_SENSOR, GPIO.IN)

# Load cell GPIO setup
GPIO.setup(config.LOADCELL_DT, GPIO.IN)
GPIO.setup(config.LOADCELL_SCK, GPIO.OUT)
GPIO.output(config.LOADCELL_SCK, GPIO.LOW)

# Initialize load cell with timeout and skip option
signal.signal(signal.SIGALRM, timeout_handler)
signal.alarm(3)  # 3-second timeout

try:
    print("Initializing HX711...")
    hx = HX711(config.LOADCELL_DT, config.LOADCELL_SCK)
    hx.reset()
    time.sleep(0.5)
    hx.tare()
    print("HX711 ready!")
except (KeyboardInterrupt, TimeoutError):
    print("HX711 init failed. Running without load cell (weight = 0.25g default).")
    hx = None  # Skip load cell for testing
except Exception as e:
    print(f"HX711 error: {e}")
    hx = None

signal.alarm(0)  # Cancel alarm

# Counters for ThingSpeak (initialize here)
good_count = 0
bad_count = 0
total_weight = 0.0

print("=" * 70)
print("COFFEE BEAN SORTER WITH ML AND THINGSPEAK")
print("=" * 70)
print("Automatic mode: IR sensor detects beans.")
print("Manual mode: Press Enter to sort.")
print("Data sent to ThingSpeak every 10 beans.")
print("Press Ctrl+C to exit.\n")

try:
    while True:
        # Wait for bean detection
        print("Waiting for bean...")
        bean_detected = False
        while not bean_detected:
            if GPIO.input(config.IR_SENSOR) == GPIO.LOW:  # Active low
                bean_detected = True
                print("✓ Bean detected!")
                time.sleep(0.5)  # Debounce
            else:
                # Manual trigger
                try:
                    input("")  # Non-blocking check
                    bean_detected = True
                    print("✓ Manual trigger!")
                except:
                    pass
            time.sleep(0.1)

        # Read sensors
        weight = get_weight(hx)
        r, g, b = read_color()
        print(f"Weight: {weight:.2f}g | Color - R:{r} G:{g} B:{b}")

        # Classify with ML
        color_class = classify_bean(r, g, b, weight)
        weight_ok = 0.1 <= weight <= 0.5

        # Update counters
        total_weight += weight
        if color_class == "GOOD" and weight_ok:
            good_count += 1
            print("✓ ACCEPT: Good bean")
            set_leds(green=True, red=False)
            set_servo_angle(config.SERVO_GOOD)
        else:
            bad_count += 1
            print("✗ REJECT: Bad bean")
            set_leds(green=False, red=True)
            set_servo_angle(config.SERVO_BAD)

        time.sleep(1)
        set_servo_angle(config.SERVO_HOME)
        set_leds()  # Turn off LEDs

        # Send to ThingSpeak every 10 beans
        total_beans = good_count + bad_count
        if total_beans % 10 == 0 and total_beans > 0:
            avg_weight = total_weight / total_beans
            print(f"Sending to ThingSpeak: Good={good_count}, Bad={bad_count}, Avg Weight={avg_weight:.2f}")
            payload = {
                'api_key': THINGSPEAK_API_KEY,
                'field1': good_count,
                'field2': bad_count,
                'field3': avg_weight
            }
            try:
                response = requests.post(THINGSPEAK_URL, data=payload)
                print(f"Response: {response.status_code}")
            except Exception as e:
                print(f"ThingSpeak error: {e}")

        time.sleep(2)  # Wait before next bean

except KeyboardInterrupt:
    print("\nSorter stopped")

finally:
    pwm.stop()
    set_leds()
    GPIO.cleanup()
    print("Cleanup complete")
