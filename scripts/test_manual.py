import os
import sys
import csv
import time
import warnings
import numpy as np
from datetime import datetime

sys.path.insert(0, 'scripts')
warnings.filterwarnings('ignore')

import RPi.GPIO as GPIO
from camera_module import CameraModule
import joblib
import tensorflow as tf
import json

# ================================================================
# CONFIGURATION
# ================================================================
CONFIG = {
    # GPIO Pins
    "SERVO_PIN"         : 18,
    "IR_PIN"            : 16,
    "S0"                : 17,
    "S1"                : 27,
    "S2"                : 22,
    "S3"                : 23,
    "OUT"               : 24,

    # Servo
    "SERVO_PASS_ANGLE"  : 0,
    "SERVO_REJECT_ANGLE": 90,
    "SERVO_HOLD"        : 0.8,   # FIX: increased from 0.5 so servo finishes moving

    # Camera
    "IMG_SIZE"          : 224,
    "USE_ROI"           : True,

    # ML
    "DT_WEIGHT"         : 0.65,
    "CNN_WEIGHT"        : 0.35,
    "FUSION_THRESHOLD"  : 0.5,

    # Colour rule
    "USE_COLOUR_RULE"   : True,
    "COLOUR_RULE_DIFF"  : 50,

    # Default weight (no HX711)
    "DEFAULT_WEIGHT"    : 0.30,

    # Paths
    "DT_MODEL_PATH"     : "models/decision_tree_model.pkl",
    "CNN_MODEL_PATH"    : "models/cnn_model.tflite",
    "SCALER_PATH"       : "models/scaler.pkl",
    "FUSION_CONFIG_PATH": "models/fusion_config.json",
    "LOG_CSV_PATH"      : "data/manual_test_results.csv",
    "IMAGES_DIR"        : "data/",

    # FIX: Force every object to BAD — set False when you have good beans to test
    "FORCE_REJECT_ALL"  : True,
}

os.makedirs("data", exist_ok=True)

# ================================================================
# STARTUP BANNER
# ================================================================
print("\n" + "="*55)
print("  COFFEE BEAN SORTER - MANUAL STEP TEST")
print("  Uganda Christian University | Group Trailblazers")
print("="*55)

if CONFIG["FORCE_REJECT_ALL"]:
    print("""
  WARNING: FORCE_REJECT_ALL = True
  Every object will be sent to the BAD bin.
  Set FORCE_REJECT_ALL = False when testing real beans.
""")

print("""
  You will move each bean by hand between sensors.
  Press Enter at each stage to advance.
  Type 'q' when prompted to quit.

  Stages:
    1 - Place bean at IR sensor
    2 - Move bean to colour sensor
    3 - Move bean under camera
    4 - Move bean to servo gate
""")

# ================================================================
# LOAD ML MODELS
# ================================================================
print("  Loading ML models...")
try:
    dt_model = joblib.load(CONFIG["DT_MODEL_PATH"])
    scaler   = joblib.load(CONFIG["SCALER_PATH"])
    print("  Decision Tree  : loaded")
except Exception as e:
    print("  Decision Tree  : FAILED - " + str(e))
    dt_model = None
    scaler   = None

try:
    interpreter    = tf.lite.Interpreter(model_path=CONFIG["CNN_MODEL_PATH"])
    interpreter.allocate_tensors()
    input_details  = interpreter.get_input_details()
    output_details = interpreter.get_output_details()
    print("  CNN TFLite     : loaded")
except Exception as e:
    print("  CNN TFLite     : FAILED - " + str(e))
    interpreter = None

# ================================================================
# INITIALISE HARDWARE
# ================================================================
print("\n  Initialising hardware...")

GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)
GPIO.setup([CONFIG["S0"], CONFIG["S1"],
            CONFIG["S2"], CONFIG["S3"],
            CONFIG["SERVO_PIN"]], GPIO.OUT)
GPIO.setup([CONFIG["IR_PIN"], CONFIG["OUT"]], GPIO.IN)
GPIO.output(CONFIG["S0"], GPIO.HIGH)
GPIO.output(CONFIG["S1"], GPIO.LOW)
print("  TCS3200 colour sensor : ready")

servo_pwm = GPIO.PWM(CONFIG["SERVO_PIN"], 50)
servo_pwm.start(0)

def set_servo_angle(angle):
    """
    FIX: Increased sleep to 0.6s so the servo physically
    completes its movement before the PWM signal stops.
    Original 0.1s was too short.
    """
    duty = 2 + (angle / 18)
    servo_pwm.ChangeDutyCycle(duty)
    time.sleep(0.6)              # FIX: was 0.1 — too fast, servo didn't move
    servo_pwm.ChangeDutyCycle(0) # stop signal to prevent jitter
    time.sleep(0.1)

# FIX: Test servo on startup so you can confirm it's working
# before any beans are tested
print("  Servo motor           : testing startup sweep...")
set_servo_angle(CONFIG["SERVO_REJECT_ANGLE"])
time.sleep(0.3)
set_servo_angle(CONFIG["SERVO_PASS_ANGLE"])
print("  Servo motor           : ready (gate open)")

try:
    cam = CameraModule(resolution=(640, 480))
    print("  Camera Module 2       : ready")
    print("  " + cam.get_roi_info())
except Exception as e:
    print("  Camera                : FAILED - " + str(e))
    cam = None

# ================================================================
# CSV LOG SETUP
# ================================================================
file_exists = os.path.isfile(CONFIG["LOG_CSV_PATH"])
csv_file    = open(CONFIG["LOG_CSV_PATH"], "a", newline="")
csv_writer  = csv.writer(csv_file)
if not file_exists:
    csv_writer.writerow([
        "timestamp", "bean_id", "weight_g",
        "red", "green", "blue", "r_minus_g",
        "dt_prob", "cnn_prob", "fusion_score", "decision"
    ])

# ================================================================
# HELPER FUNCTIONS
# ================================================================
def read_colour_channel(s2_val, s3_val):
    GPIO.output(CONFIG["S2"], s2_val)
    GPIO.output(CONFIG["S3"], s3_val)
    time.sleep(0.1)
    count      = 0
    start      = time.time()
    last_state = GPIO.input(CONFIG["OUT"])
    while time.time() - start < 0.2:
        current_state = GPIO.input(CONFIG["OUT"])
        if last_state == GPIO.HIGH and current_state == GPIO.LOW:
            count += 1
        last_state = current_state
    return count

def read_rgb(samples=3):
    rs, gs, bs = [], [], []
    for _ in range(samples):
        rs.append(read_colour_channel(GPIO.LOW,  GPIO.LOW))
        gs.append(read_colour_channel(GPIO.HIGH, GPIO.HIGH))
        bs.append(read_colour_channel(GPIO.LOW,  GPIO.HIGH))
        time.sleep(0.1)
    return int(np.mean(rs)), int(np.mean(gs)), int(np.mean(bs))

def predict_bean(r, g, b, image_array):
    diff = r - g

    if CONFIG["USE_COLOUR_RULE"] or dt_model is None:
        dt_prob = 1.0 if diff > CONFIG["COLOUR_RULE_DIFF"] else 0.0
    else:
        try:
            raw     = np.array([[CONFIG["DEFAULT_WEIGHT"], r, g, b]], dtype=np.float64)
            scaled  = scaler.transform(raw)
            dt_prob = float(dt_model.predict_proba(scaled)[0][1])
        except Exception as e:
            print("  DT error: " + str(e))
            dt_prob = 1.0 if diff > CONFIG["COLOUR_RULE_DIFF"] else 0.0

    if interpreter is not None:
        try:
            img_input = np.expand_dims(image_array, axis=0).astype(np.float32)
            interpreter.set_tensor(input_details[0]["index"], img_input)
            interpreter.invoke()
            cnn_prob = float(interpreter.get_tensor(output_details[0]["index"])[0][0])
        except Exception as e:
            print("  CNN error: " + str(e))
            cnn_prob = dt_prob
    else:
        cnn_prob = dt_prob

    fusion_score = (CONFIG["DT_WEIGHT"] * dt_prob +
                    CONFIG["CNN_WEIGHT"] * cnn_prob)
    decision     = "GOOD" if fusion_score >= CONFIG["FUSION_THRESHOLD"] else "BAD"
    return decision, fusion_score, dt_prob, cnn_prob

# ================================================================
# MAIN TEST LOOP
# ================================================================
print("\n" + "="*55)
print("  READY - Starting manual test")
print("="*55)

bean_id    = 1
good_count = 0
bad_count  = 0
start_time = time.time()

try:
    while True:

        print("\n")
        cont = input("  Press Enter to test bean " + str(bean_id) +
                     "  (or type 'q' to quit): ").strip().lower()
        if cont == 'q':
            break

        bean_label = "bean_" + str(bean_id).zfill(4)
        print("\n" + "-"*45)
        print("  BEAN " + str(bean_id) + "  (" + bean_label + ")")
        print("-"*45)

        # STAGE 1 - IR sensor
        input("\n  STAGE 1 - Place bean in front of IR sensor"
              "\n  Press Enter when bean is in position...")

        ir_state = GPIO.input(CONFIG["IR_PIN"])
        if ir_state == GPIO.LOW:
            print("  IR sensor : TRIGGERED (bean detected)")
        else:
            print("  IR sensor : not triggered (bean may be too far)")

        # STAGE 2 - Colour sensor
        input("\n  STAGE 2 - Move bean to colour sensor"
              "\n  Press Enter when bean is under colour sensor...")

        print("  Reading colour...", end=" ", flush=True)
        r, g, b = read_rgb(samples=3)
        diff    = r - g
        print("done")
        print("  R=" + str(r) +
              "  G=" + str(g) +
              "  B=" + str(b) +
              "  (R-G=" + str(diff) + ")")

        if CONFIG["USE_COLOUR_RULE"]:
            colour_verdict = "GOOD" if diff > CONFIG["COLOUR_RULE_DIFF"] else "BAD"
            print("  Colour rule : R-G=" + str(diff) +
                  " vs threshold " + str(CONFIG["COLOUR_RULE_DIFF"]) +
                  " -> " + colour_verdict)

        # STAGE 3 - Camera
        input("\n  STAGE 3 - Move bean under the camera"
              "\n  Press Enter when bean is under camera...")

        print("  Capturing image...", end=" ", flush=True)
        if cam is not None:
            try:
                img_path          = CONFIG["IMAGES_DIR"] + bean_label + ".jpg"
                ml_array = cam.capture_image(filename=img_path)
                cropped = ml_array
                print("done")
                print("  Saved       : " + img_path)
                print("  ML shape    : " + str(ml_array.shape))
                print("  Pixel range : " +
                      str(round(ml_array.min(), 2)) +
                      " to " +
                      str(round(ml_array.max(), 2)))
            except Exception as e:
                print("FAILED - " + str(e))
                ml_array = np.zeros(
                    (CONFIG["IMG_SIZE"], CONFIG["IMG_SIZE"], 3),
                    dtype=np.float32)
        else:
            print("SKIPPED (camera not available)")
            ml_array = np.zeros(
                (CONFIG["IMG_SIZE"], CONFIG["IMG_SIZE"], 3),
                dtype=np.float32)

        # ML prediction
        print("\n  Running ML prediction...", end=" ", flush=True)
        decision, fusion_score, dt_prob, cnn_prob = predict_bean(r, g, b, ml_array)
        print("done")

        # FIX: Force reject override — bypasses ML result
        if CONFIG["FORCE_REJECT_ALL"]:
            decision = "BAD"
            print("  WARNING: FORCE_REJECT_ALL active — overriding to BAD")

        # STAGE 4 - Servo
        input("\n  STAGE 4 - Move bean to servo gate"
              "\n  Press Enter to trigger servo...")

        if decision == "BAD":
            print("  Servo : REJECTING (moving to " +
                  str(CONFIG["SERVO_REJECT_ANGLE"]) + " degrees)")
            set_servo_angle(CONFIG["SERVO_REJECT_ANGLE"])
            time.sleep(CONFIG["SERVO_HOLD"])
            set_servo_angle(CONFIG["SERVO_PASS_ANGLE"])
            print("  Servo : reset to 0 degrees")
        else:
            print("  Servo : PASSING (gate stays open)")

        # Result summary
        print("\n  " + "="*35)
        if decision == "GOOD":
            print("  RESULT : GOOD BEAN  PASSED")
            good_count += 1
        else:
            print("  RESULT : BAD BEAN   REJECTED")
            bad_count  += 1

        print("  Colour score : " + str(round(dt_prob,      2)))
        print("  CNN    score : " + str(round(cnn_prob,     2)))
        print("  Fusion score : " + str(round(fusion_score, 2)))
        print("  R=" + str(r) +
              " G=" + str(g) +
              " B=" + str(b) +
              " (R-G=" + str(diff) + ")")
        print("  " + "="*35)

        # Log to CSV
        csv_writer.writerow([
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            bean_label,
            CONFIG["DEFAULT_WEIGHT"],
            r, g, b, diff,
            round(dt_prob,      4),
            round(cnn_prob,     4),
            round(fusion_score, 4),
            decision
        ])
        csv_file.flush()

        total = good_count + bad_count
        print("\n  Running totals : " +
              str(total)      + " total  |  " +
              str(good_count) + " good   |  " +
              str(bad_count)  + " bad")

        bean_id += 1

except KeyboardInterrupt:
    print("\n\n  Stopped by user")

# ================================================================
# CLEANUP
# ================================================================
print("\n  Cleaning up...")
try:
    set_servo_angle(CONFIG["SERVO_PASS_ANGLE"])
    servo_pwm.stop()
except:
    pass
try:
    cam.stop()
except:
    pass
try:
    GPIO.cleanup()
except:
    pass
try:
    csv_file.close()
except:
    pass

# ================================================================
# FINAL SUMMARY
# ================================================================
total   = good_count + bad_count
elapsed = time.time() - start_time

print("\n" + "="*55)
print("  MANUAL TEST COMPLETE - FINAL SUMMARY")
print("="*55)
print("  Total tested  : " + str(total))
print("  Good (passed) : " + str(good_count) +
      "  (" + str(round(good_count / max(total, 1) * 100, 1)) + "%)")
print("  Bad (rejected): " + str(bad_count) +
      "  (" + str(round(bad_count  / max(total, 1) * 100, 1)) + "%)")
print("  Duration      : " + str(int(elapsed // 60)) + "m " +
      str(int(elapsed % 60)) + "s")
print("  Results saved : " + CONFIG["LOG_CSV_PATH"])
print("="*55)
