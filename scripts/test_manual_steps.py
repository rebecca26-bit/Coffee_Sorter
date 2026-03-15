"""
================================================================
COFFEE BEAN SORTER - MANUAL STEP-BY-STEP TEST
Uganda Christian University | Group Trailblazers
S23B23/056 | S23B23/010 | S23B23/046

Uses camera_module.py for camera control.
You control each step with Enter key.

HOW TO RUN:
  python3 scripts/test_manual_steps.py

SEQUENCE PER BEAN:
  1. Place bean on IR sensor -> detected automatically
  2. Move bean to colour sensor -> press Enter to read
  3. Move bean to camera -> press Enter to capture
  4. Press Enter to run ML prediction
  5. Press Enter to trigger servo
  6. Press Enter to test next bean
================================================================
"""

import sys
import os
import csv
import time
import warnings
import numpy as np
from datetime import datetime

# Add scripts folder to path for camera_module import
sys.path.insert(0, 'scripts')

import RPi.GPIO as GPIO
from camera_module import CameraModule
import joblib
import tensorflow as tf
warnings.filterwarnings('ignore')

# ================================================================
# PIN CONFIGURATION
# ================================================================
SERVO_PIN = 18
IR_PIN    = 16
S0        = 17
S1        = 27
S2        = 22
S3        = 23
OUT       = 24

# ================================================================
# SETTINGS
# ================================================================
DT_WEIGHT          = 0.65
CNN_WEIGHT         = 0.35
THRESHOLD          = 0.5
IMG_SIZE           = 224
SERVO_PASS_ANGLE   = 0
SERVO_REJECT_ANGLE = 90

# ================================================================
# GPIO SETUP
# ================================================================
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)
GPIO.setup([S0, S1, S2, S3, SERVO_PIN], GPIO.OUT)
GPIO.setup([IR_PIN, OUT], GPIO.IN)
GPIO.output(S0, GPIO.HIGH)
GPIO.output(S1, GPIO.LOW)

# ================================================================
# SERVO
# ================================================================
pwm = GPIO.PWM(SERVO_PIN, 50)
pwm.start(0)

def set_servo(angle):
    pwm.ChangeDutyCycle(2 + (angle / 18))
    time.sleep(0.4)
    pwm.ChangeDutyCycle(0)

set_servo(SERVO_PASS_ANGLE)

# ================================================================
# COLOUR SENSOR
# ================================================================
def read_channel(s2_val, s3_val):
    GPIO.output(S2, s2_val)
    GPIO.output(S3, s3_val)
    time.sleep(0.1)
    count = 0
    start = time.time()
    last_state = GPIO.input(OUT)
    while time.time() - start < 0.2:
        current_state = GPIO.input(OUT)
        if last_state == GPIO.HIGH and current_state == GPIO.LOW:
            count += 1
        last_state = current_state
    return count

def read_rgb_average(samples=3):
    rs, gs, bs = [], [], []
    for _ in range(samples):
        r = read_channel(GPIO.LOW,  GPIO.LOW)
        g = read_channel(GPIO.HIGH, GPIO.HIGH)
        b = read_channel(GPIO.LOW,  GPIO.HIGH)
        rs.append(r)
        gs.append(g)
        bs.append(b)
        time.sleep(0.1)
    return int(np.mean(rs)), int(np.mean(gs)), int(np.mean(bs))

# ================================================================
# STARTUP
# ================================================================
print("\n" + "="*50)
print("  MANUAL STEP-BY-STEP TEST")
print("  Uganda Christian University")
print("  Group Trailblazers")
print("="*50)

# ================================================================
# LOAD ML MODELS
# ================================================================
print("\n  Loading ML models...")
USE_ML = False
try:
    dt_model       = joblib.load("models/decision_tree_model.pkl")
    scaler         = joblib.load("models/scaler.pkl")
    interpreter    = tf.lite.Interpreter(model_path="models/cnn_model.tflite")
    interpreter.allocate_tensors()
    input_details  = interpreter.get_input_details()
    output_details = interpreter.get_output_details()
    USE_ML = True
    print("  Decision Tree  : loaded")
    print("  CNN TFLite     : loaded")
except Exception as e:
    print("  ML models failed: " + str(e))
    print("  Using colour-only rule instead")

# ================================================================
# INITIALISE CAMERA
# ================================================================
print("\n  Initialising camera...")
try:
    cam = CameraModule(resolution=(IMG_SIZE, IMG_SIZE))
    print("  Camera         : ready")
except Exception as e:
    print("  Camera failed  : " + str(e))
    cam = None

# ================================================================
# CSV LOG
# ================================================================
os.makedirs("data", exist_ok=True)
LOG_FILE = "data/manual_test_results.csv"
with open(LOG_FILE, "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["timestamp", "bean_id", "red", "green", "blue",
                     "dt_prob", "cnn_prob", "fusion_score", "decision"])
print("  Log file       : " + LOG_FILE)

# ================================================================
# ML PREDICTION FUNCTION
# ================================================================
def predict_bean(r, g, b, image_array):
    """Run fusion prediction on sensor + image data."""
    if not USE_ML:
        diff = r - g
        decision = "GOOD" if diff > 50 else "BAD"
        return decision, 0.0, 0.0, 0.0

    # Decision Tree
    try:
        raw     = np.array([[0.30, r, g, b]], dtype=np.float64)
        scaled  = scaler.transform(raw)
        dt_prob = float(dt_model.predict_proba(scaled)[0][1])
    except Exception as e:
        print("  DT error: " + str(e))
        dt_prob = 1.0 if (r - g) > 50 else 0.0

    # CNN
    try:
        img_input = np.expand_dims(image_array, axis=0).astype(np.float32)
        interpreter.set_tensor(input_details[0]["index"], img_input)
        interpreter.invoke()
        cnn_prob = float(
            interpreter.get_tensor(output_details[0]["index"])[0][0]
        )
    except Exception as e:
        print("  CNN error: " + str(e))
        cnn_prob = dt_prob

    fusion_score = DT_WEIGHT * dt_prob + CNN_WEIGHT * cnn_prob
    decision     = "GOOD" if fusion_score >= THRESHOLD else "BAD"
    return decision, fusion_score, dt_prob, cnn_prob

# ================================================================
# MAIN LOOP
# ================================================================
print("\n" + "="*50)
print("  READY")
print("  You control each step with Enter")
print("  Press Ctrl+C anytime to stop")
print("="*50 + "\n")

bean_id    = 1
good_count = 0
bad_count  = 0
start_time = time.time()

try:
    while True:
        print("\n" + "="*50)
        print("  BEAN " + str(bean_id))
        print("="*50)

        # ── STEP 1: IR Detection ──────────────────────────────
        print("\n  STEP 1 — IR SENSOR")
        print("  Place bean in front of IR sensor")
        print("  Waiting for detection...")

        while GPIO.input(IR_PIN) != GPIO.LOW:
            time.sleep(0.01)

        print("  Bean detected!")

        # ── STEP 2: Colour Reading ────────────────────────────
        input("\n  Move bean under COLOUR SENSOR then press Enter...")
        print("\n  STEP 2 — COLOUR SENSOR")
        print("  Reading colour (3 samples averaged)...", end=" ", flush=True)
        r, g, b = read_rgb_average(samples=3)
        print("done")
        print("  R=" + str(r) + "  G=" + str(g) + "  B=" + str(b))
        diff = r - g
        print("  R-G difference = " + str(diff) +
              " (>50 suggests good bean)")

        # ── STEP 3: Camera Capture ────────────────────────────
        input("\n  Move bean under CAMERA then press Enter...")
        print("\n  STEP 3 — CAMERA")

        if cam is not None:
            print("  Capturing image...", end=" ", flush=True)
            img_path  = "data/bean_" + str(bean_id).zfill(4) + ".jpg"
            raw_image = cam.capture_image(img_path)

            # Resize and normalise for ML
            from PIL import Image as PILImage
            img_array = np.array(
                PILImage.fromarray(raw_image).resize((IMG_SIZE, IMG_SIZE))
            ).astype(np.float32) / 255.0
            print("saved as " + img_path)
        else:
            print("  Camera not available - using blank image")
            img_array = np.zeros((IMG_SIZE, IMG_SIZE, 3), dtype=np.float32)

        # ── STEP 4: ML Prediction ─────────────────────────────
        input("\n  Press Enter to run ML PREDICTION...")
        print("\n  STEP 4 — ML PREDICTION")
        decision, fusion_score, dt_prob, cnn_prob = predict_bean(
            r, g, b, img_array
        )
        print("  Decision Tree  : " + str(round(dt_prob,    3)))
        print("  CNN            : " + str(round(cnn_prob,   3)))
        print("  Fusion Score   : " + str(round(fusion_score, 3)))
        print("  DECISION       : " + decision)

        # ── STEP 5: Servo ─────────────────────────────────────
        input("\n  Press Enter to trigger SERVO...")
        print("\n  STEP 5 — SERVO")
        if decision == "BAD":
            print("  Rejecting bean (90 degrees)...")
            set_servo(SERVO_REJECT_ANGLE)
            time.sleep(0.5)
            set_servo(SERVO_PASS_ANGLE)
            bad_count += 1
        else:
            print("  Bean passes through (gate stays open)")
            good_count += 1

        # ── LOG RESULT ────────────────────────────────────────
        with open(LOG_FILE, "a", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "bean_" + str(bean_id).zfill(4),
                r, g, b,
                round(dt_prob,       4),
                round(cnn_prob,      4),
                round(fusion_score,  4),
                decision
            ])

        # ── RUNNING SUMMARY ───────────────────────────────────
        elapsed = time.time() - start_time
        print("\n  RUNNING TOTAL:")
        print("  Good : " + str(good_count))
        print("  Bad  : " + str(bad_count))
        print("  Time : " + str(int(elapsed//60)) + "m " +
              str(int(elapsed%60)) + "s")

        bean_id += 1
        input("\n  Press Enter to test NEXT BEAN...")

except KeyboardInterrupt:
    print("\n\n  Stopping...")

finally:
    # Cleanup all hardware
    try:
        set_servo(SERVO_PASS_ANGLE)
        pwm.stop()
    except:
        pass
    try:
        if cam is not None:
            cam.stop()
    except:
        pass
    GPIO.cleanup()

    total   = good_count + bad_count
    elapsed = time.time() - start_time

    print("\n" + "="*50)
    print("  FINAL SUMMARY")
    print("="*50)
    print("  Total beans  : " + str(total))
    print("  Good         : " + str(good_count))
    print("  Bad          : " + str(bad_count))
    if total > 0:
        print("  Pass rate    : " + str(round(good_count/total*100, 1)) + "%")
    print("  Duration     : " + str(int(elapsed//60)) + "m " +
          str(int(elapsed%60)) + "s")
    print("  Results      : " + LOG_FILE)
    print("="*50)
