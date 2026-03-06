import RPi.GPIO as GPIO
import time
import os
import csv
import numpy as np
from datetime import datetime
from picamera2 import Picamera2
import joblib
import tensorflow as tf
from PIL import Image

# PINS
SERVO_PIN = 18
IR_PIN    = 16
S0  = 17
S1  = 27
S2  = 22
S3  = 23
OUT = 24

# SETTINGS
DT_WEIGHT          = 0.65
CNN_WEIGHT         = 0.35
THRESHOLD          = 0.5
IMG_SIZE           = 224
SERVO_PASS_ANGLE   = 0
SERVO_REJECT_ANGLE = 90

# GPIO SETUP
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)
GPIO.setup([S0, S1, S2, S3, SERVO_PIN], GPIO.OUT)
GPIO.setup([IR_PIN, OUT], GPIO.IN)
GPIO.output(S0, GPIO.HIGH)
GPIO.output(S1, GPIO.LOW)

# SERVO
pwm = GPIO.PWM(SERVO_PIN, 50)
pwm.start(0)

def set_servo(angle):
    pwm.ChangeDutyCycle(2 + (angle / 18))
    time.sleep(0.4)
    pwm.ChangeDutyCycle(0)

set_servo(SERVO_PASS_ANGLE)

# COLOUR SENSOR
def read_channel(s2_val, s3_val):
    GPIO.output(S2, s2_val)
    GPIO.output(S3, s3_val)
    time.sleep(0.05)
    count = 0
    start = time.time()
    last_state = GPIO.input(OUT)
    while time.time() - start < 0.1:
        current_state = GPIO.input(OUT)
        if last_state == GPIO.HIGH and current_state == GPIO.LOW:
            count += 1
        last_state = current_state
    return count

def read_rgb():
    r = read_channel(GPIO.LOW,  GPIO.LOW)
    g = read_channel(GPIO.HIGH, GPIO.HIGH)
    b = read_channel(GPIO.LOW,  GPIO.HIGH)
    return r, g, b

# LOAD ML MODELS
print("\n" + "="*50)
print("  BEAN PASS-THROUGH TEST")
print("  Uganda Christian University")
print("  Group Trailblazers")
print("="*50)
print("\n  Loading ML models...")

try:
    dt_model = joblib.load("models/decision_tree_model.pkl")
    scaler   = joblib.load("models/scaler.pkl")
    interpreter    = tf.lite.Interpreter(model_path="models/cnn_model.tflite")
    interpreter.allocate_tensors()
    input_details  = interpreter.get_input_details()
    output_details = interpreter.get_output_details()
    USE_ML = True
    print("  ML models loaded")
except Exception as e:
    print("  ML models not found: " + str(e))
    print("  Using colour-only decision")
    USE_ML = False

# CAMERA
print("  Initialising camera...")
cam = Picamera2()
cam.configure(cam.create_still_configuration(
    main={"size": (IMG_SIZE, IMG_SIZE)},
    controls={"ExposureTime": 50000, "AnalogueGain": 4.0}
))
cam.start()
time.sleep(2)
print("  Camera ready")

# CSV LOG
os.makedirs("data", exist_ok=True)
LOG_FILE = "data/passthrough_results.csv"
with open(LOG_FILE, "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["timestamp","bean_id","red","green","blue",
                     "dt_prob","cnn_prob","fusion_score","decision"])

# PREDICTION FUNCTION
def predict_bean(r, g, b, image_array):
    if not USE_ML:
        diff = r - g
        decision = "GOOD" if diff > 50 else "BAD"
        return decision, 0.0, 0.0, 0.0
    raw    = np.array([[0.30, r, g, b]])
    scaled = scaler.transform(raw)
    dt_prob = dt_model.predict_proba(scaled)[0][1]
    img_input = np.expand_dims(image_array, axis=0).astype(np.float32)
    interpreter.set_tensor(input_details[0]["index"], img_input)
    interpreter.invoke()
    cnn_prob = float(interpreter.get_tensor(output_details[0]["index"])[0][0])
    fusion_score = DT_WEIGHT * dt_prob + CNN_WEIGHT * cnn_prob
    decision = "GOOD" if fusion_score >= THRESHOLD else "BAD"
    return decision, fusion_score, dt_prob, cnn_prob

# MAIN LOOP
print("\n" + "="*50)
print("  READY - Drop beans one at a time")
print("  Press Ctrl+C to stop")
print("="*50 + "\n")

bean_id    = 1
good_count = 0
bad_count  = 0
start_time = time.time()

try:
    while True:
        print("  Waiting for bean " + str(bean_id) + "...")

        # Wait for IR detection
        while GPIO.input(IR_PIN) != GPIO.LOW:
            time.sleep(0.01)

        print("  Bean " + str(bean_id) + " detected!")
        time.sleep(0.1)

        # Read colour
        print("  Reading colour...", end=" ", flush=True)
        r, g, b = read_rgb()
        print("R=" + str(r) + " G=" + str(g) + " B=" + str(b))

        # Capture image
        print("  Capturing image...", end=" ", flush=True)
        img_path = "data/bean_" + str(bean_id).zfill(4) + ".jpg"
        cam.capture_file(img_path)
        img_array = np.array(
            Image.open(img_path).resize((IMG_SIZE, IMG_SIZE))
        ) / 255.0
        print("saved")

        # ML prediction
        print("  Running prediction...", end=" ", flush=True)
        decision, fusion_score, dt_prob, cnn_prob = predict_bean(r, g, b, img_array)
        print(decision)

        # Servo
        if decision == "BAD":
            print("  Servo: REJECTING")
            set_servo(SERVO_REJECT_ANGLE)
            time.sleep(0.5)
            set_servo(SERVO_PASS_ANGLE)
            bad_count += 1
        else:
            print("  Servo: PASSING")
            good_count += 1

        # Log
        with open(LOG_FILE, "a", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "bean_" + str(bean_id).zfill(4),
                r, g, b,
                round(dt_prob, 4),
                round(cnn_prob, 4),
                round(fusion_score, 4),
                decision
            ])

        elapsed = time.time() - start_time
        print("\n  Bean " + str(bean_id) + " -> " + decision)
        print("  Good: " + str(good_count) + "  Bad: " + str(bad_count))
        print("  Time: " + str(int(elapsed//60)) + "m " + str(int(elapsed%60)) + "s\n")

        bean_id += 1
        time.sleep(0.5)

except KeyboardInterrupt:
    print("\n  Stopping...")

finally:
    set_servo(SERVO_PASS_ANGLE)
    pwm.stop()
    cam.stop()
    GPIO.cleanup()
    total   = good_count + bad_count
    elapsed = time.time() - start_time
    print("\n" + "="*50)
    print("  FINAL SUMMARY")
    print("="*50)
    print("  Total beans : " + str(total))
    print("  Good        : " + str(good_count))
    print("  Bad         : " + str(bad_count))
    print("  Duration    : " + str(int(elapsed//60)) + "m " + str(int(elapsed%60)) + "s")
    print("  Results     : " + LOG_FILE)
    print("="*50)

