"""
================================================================
COFFEE BEAN QUALITY SORTER — STEP 6: RASPBERRY PI DEPLOYMENT
Uganda Christian University | Group Trailblazers
S23B23/056 | S23B23/010 | S23B23/046

CHANGES FROM ORIGINAL:
  1. GPIO pins updated to match actual hardware
  2. HX711 removed (not connected)
  3. LED ring removed (not connected)
  4. DC motor removed (not connected yet)
  5. TCS3200 uses pulse counting (fixes Debian Trixie error)
  6. Conveyor delays added (1.5s/1.5s/1.0s)
  7. tflite_runtime replaced with tensorflow.lite
  8. Camera uses camera_module.py
  9. Colour rule added (R-G difference for TCS3200)
  10. Weight replaced with 0.30g default (no HX711)

CONVEYOR LAYOUT:
  IR Sensor → Colour Sensor → Camera → Servo Gate

HOW TO RUN:
  python3 scripts/06_sorter_main.py

STOP:
  Press Ctrl+C

GPIO PINS:
  Servo       : GPIO 18
  IR Sensor   : GPIO 16
  TCS3200 S0  : GPIO 17
  TCS3200 S1  : GPIO 27
  TCS3200 S2  : GPIO 22
  TCS3200 S3  : GPIO 23
  TCS3200 OUT : GPIO 24
================================================================
"""

import os
import sys
import csv
import json
import time
import logging
import warnings
import numpy as np
from datetime import datetime

sys.path.insert(0, 'scripts')
warnings.filterwarnings('ignore')

# ================================================================
# LOGGING SETUP
# ================================================================
os.makedirs("data", exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("data/sorter_log.txt"),
        logging.StreamHandler(sys.stdout)
    ]
)
log = logging.getLogger(__name__)

# ================================================================
# CONFIGURATION
# CHANGE 1: GPIO pins updated to match actual hardware
# CHANGE 2: HX711, LED, DC motor pins removed
# ================================================================
CONFIG = {
    # ── GPIO Pin Numbers (BCM numbering) ──────────────────────
    # CHANGE 1: Updated from wrong pins to actual hardware pins
    "S0"         : 17,      # TCS3200 (was 23)
    "S1"         : 27,      # TCS3200 (was 25)
    "S2"         : 22,      # TCS3200 (was 8)
    "S3"         : 23,      # TCS3200 (was 7)
    "OUT"        : 24,      # TCS3200 (unchanged)
    "IR_PIN"     : 16,      # IR sensor (new — was DC_MOTOR_EN)
    "SERVO_PIN"  : 18,      # Servo (was 12)

    # CHANGE 2: HX711 removed — not connected
    # "HX_DT"    : 5,       # REMOVED
    # "HX_SCK"   : 6,       # REMOVED

    # CHANGE 3: LED ring removed — not connected
    # "LED_PIN"  : 18,      # REMOVED

    # CHANGE 4: DC motor removed — not connected yet
    # "DC_MOTOR_IN1": 20,   # REMOVED
    # "DC_MOTOR_IN2": 21,   # REMOVED
    # "DC_MOTOR_EN" : 16,   # REMOVED (pin now used for IR sensor)

    # ── Servo Settings ────────────────────────────────────────
    "SERVO_PASS_ANGLE"  : 0,
    "SERVO_REJECT_ANGLE": 90,
    "SERVO_DELAY"       : 0.5,

    # ── Camera Settings ───────────────────────────────────────
    "IMG_SIZE"          : 224,

    # ── Conveyor Delays (seconds) ─────────────────────────────
    # CHANGE 6: Added conveyor delays for 1 bean per 5 seconds
    "DELAY_IR_TO_COLOUR" : 1.5,   # IR detection → colour sensor
    "DELAY_COLOUR_TO_CAM": 1.5,   # colour sensor → camera
    "DELAY_CAM_TO_SERVO" : 1.0,   # camera → servo gate
    "DELAY_SERVO_RESET"  : 0.3,   # after servo resets

    # ── ML Settings ───────────────────────────────────────────
    "DT_WEIGHT"         : 0.65,
    "CNN_WEIGHT"        : 0.35,
    "FUSION_THRESHOLD"  : 0.5,

    # ── Colour Rule ───────────────────────────────────────────
    # CHANGE 9: Added colour rule for TCS3200 decision
    # True  = use R-G difference rule (recommended until DT retrained)
    # False = use trained Decision Tree
    "USE_COLOUR_RULE"   : True,
    "COLOUR_RULE_DIFF"  : 50,     # R-G must exceed this to be GOOD

    # ── Default Weight (no HX711) ─────────────────────────────
    # CHANGE 10: Fixed weight used since HX711 is removed
    "DEFAULT_WEIGHT"    : 0.30,

    # ── File Paths ────────────────────────────────────────────
    "DT_MODEL_PATH"     : "models/decision_tree_model.pkl",
    "CNN_MODEL_PATH"    : "models/cnn_model.tflite",
    "SCALER_PATH"       : "models/scaler.pkl",
    "FUSION_CONFIG_PATH": "models/fusion_config.json",
    "LOG_CSV_PATH"      : "data/sorting_results.csv",
}


# ================================================================
# SECTION 1 — LOAD ML MODELS
# CHANGE 7: tflite_runtime replaced with tensorflow.lite
# ================================================================
def load_models():
    log.info("Loading ML models...")

    import joblib
    # CHANGE 7: was 'import tflite_runtime.interpreter as tflite'
    import tensorflow as tf

    dt_model = joblib.load(CONFIG["DT_MODEL_PATH"])
    scaler   = joblib.load(CONFIG["SCALER_PATH"])
    log.info("  Decision Tree loaded")

    with open(CONFIG["FUSION_CONFIG_PATH"]) as f:
        fusion_cfg = json.load(f)
    log.info("  Fusion config loaded")

    # CHANGE 7: was 'tflite.Interpreter(...)'
    interpreter = tf.lite.Interpreter(model_path=CONFIG["CNN_MODEL_PATH"])
    interpreter.allocate_tensors()
    input_details  = interpreter.get_input_details()
    output_details = interpreter.get_output_details()
    log.info("  CNN TFLite loaded")

    return dt_model, scaler, interpreter, input_details, output_details, fusion_cfg


# ================================================================
# SECTION 2 — HARDWARE INITIALISATION
# CHANGE 2,3,4,8: HX711/LED/DC motor removed, camera_module used
# ================================================================
def init_hardware():
    import RPi.GPIO as GPIO
    # CHANGE 8: was 'from picamera2 import Picamera2'
    from camera_module import CameraModule

    log.info("Initialising hardware...")
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)

    # TCS3200 colour sensor
    GPIO.setup([CONFIG["S0"], CONFIG["S1"],
                CONFIG["S2"], CONFIG["S3"],
                CONFIG["SERVO_PIN"]], GPIO.OUT)
    GPIO.setup([CONFIG["IR_PIN"], CONFIG["OUT"]], GPIO.IN)
    GPIO.output(CONFIG["S0"], GPIO.HIGH)
    GPIO.output(CONFIG["S1"], GPIO.LOW)
    log.info("  TCS3200 colour sensor initialised")

    # CHANGE 2: HX711 removed — was 'hx = HX711(...)'
    # CHANGE 3: LED ring removed — was 'GPIO.setup(LED_PIN...)'
    # CHANGE 4: DC motor removed — was 'motor_pwm = GPIO.PWM(...)'

    # Servo motor
    servo_pwm = GPIO.PWM(CONFIG["SERVO_PIN"], 50)
    servo_pwm.start(0)
    set_servo_angle(servo_pwm, CONFIG["SERVO_PASS_ANGLE"])
    log.info("  Servo motor initialised (gate open)")

    # CHANGE 8: Camera uses CameraModule instead of Picamera2 directly
    cam = CameraModule(resolution=(CONFIG["IMG_SIZE"], CONFIG["IMG_SIZE"]))
    log.info("  Camera Module 2 initialised")

    return GPIO, servo_pwm, cam


# ================================================================
# SECTION 3 — COLOUR SENSOR READING
# CHANGE 5: Replaced GPIO.wait_for_edge with pulse counting
# ================================================================
def read_colour_channel(GPIO, s2_val, s3_val):
    """
    Read one RGB channel using pulse counting.
    CHANGE 5: was 'GPIO.wait_for_edge()' which fails on Debian Trixie
    Now uses manual pulse counting which works on all OS versions.
    """
    GPIO.output(CONFIG["S2"], s2_val)
    GPIO.output(CONFIG["S3"], s3_val)
    time.sleep(0.1)
    count = 0
    start = time.time()
    last_state = GPIO.input(CONFIG["OUT"])
    while time.time() - start < 0.2:
        current_state = GPIO.input(CONFIG["OUT"])
        if last_state == GPIO.HIGH and current_state == GPIO.LOW:
            count += 1
        last_state = current_state
    return count

def read_all_sensors(GPIO):
    """
    Read RGB colour only (no weight — HX711 removed).
    CHANGE 2: Weight replaced with CONFIG['DEFAULT_WEIGHT']
    Returns: (weight_g, red, green, blue)
    """
    # CHANGE 3: LED ring removed — was 'GPIO.output(LED_PIN, HIGH)'

    rs, gs, bs = [], [], []
    for _ in range(3):
        rs.append(read_colour_channel(GPIO, GPIO.LOW,  GPIO.LOW))
        gs.append(read_colour_channel(GPIO, GPIO.HIGH, GPIO.HIGH))
        bs.append(read_colour_channel(GPIO, GPIO.LOW,  GPIO.HIGH))
        time.sleep(0.1)

    r = int(np.mean(rs))
    g = int(np.mean(gs))
    b = int(np.mean(bs))

    # CHANGE 2: Use default weight since HX711 is removed
    weight = CONFIG["DEFAULT_WEIGHT"]

    return weight, r, g, b


# ================================================================
# SECTION 4 — CAMERA CAPTURE
# CHANGE 8: Uses camera_module.py instead of Picamera2 directly
# ================================================================
def capture_bean_image(cam):
    """
    Capture image using CameraModule.
    CHANGE 8: was 'cam.capture_array()' with Picamera2 directly
    Now uses CameraModule.capture_image() for consistency.
    """
    from PIL import Image
    raw_image = cam.capture_image()
    img = Image.fromarray(raw_image)
    img = img.resize((CONFIG["IMG_SIZE"], CONFIG["IMG_SIZE"]),
                     Image.LANCZOS)
    return np.array(img) / 255.0


# ================================================================
# SECTION 5 — ML PREDICTION
# CHANGE 9: Colour rule added for TCS3200 decision
# CHANGE 10: Default weight used instead of HX711
# ================================================================
def predict_bean(sensor_data, image_array,
                 dt_model, scaler,
                 interpreter, input_details, output_details):
    """Run fusion prediction combining TCS3200 and CNN."""
    weight, r, g, b = sensor_data
    diff = r - g

    # CHANGE 9: Colour rule or Decision Tree for TCS3200 decision
    if CONFIG["USE_COLOUR_RULE"]:
        dt_prob = 1.0 if diff > CONFIG["COLOUR_RULE_DIFF"] else 0.0
    else:
        try:
            # CHANGE 10: Uses DEFAULT_WEIGHT since HX711 removed
            raw    = np.array([[weight, r, g, b]])
            scaled = scaler.transform(raw)
            dt_prob = float(dt_model.predict_proba(scaled)[0][1])
        except Exception as e:
            log.warning("DT error: " + str(e))
            dt_prob = 1.0 if diff > CONFIG["COLOUR_RULE_DIFF"] else 0.0

    # CNN prediction
    try:
        img_input = np.expand_dims(image_array, axis=0).astype(np.float32)
        interpreter.set_tensor(input_details[0]["index"], img_input)
        interpreter.invoke()
        cnn_prob = float(
            interpreter.get_tensor(output_details[0]["index"])[0][0]
        )
    except Exception as e:
        log.warning("CNN error: " + str(e))
        cnn_prob = dt_prob

    fusion_score = (CONFIG["DT_WEIGHT"]  * dt_prob +
                    CONFIG["CNN_WEIGHT"] * cnn_prob)
    decision = "GOOD" if fusion_score >= CONFIG["FUSION_THRESHOLD"] else "BAD"

    return decision, fusion_score, dt_prob, cnn_prob


# ================================================================
# SECTION 6 — SERVO CONTROL
# ================================================================
def set_servo_angle(servo_pwm, angle):
    duty = 2 + (angle / 18)
    servo_pwm.ChangeDutyCycle(duty)
    time.sleep(0.1)
    servo_pwm.ChangeDutyCycle(0)

def trigger_sort(servo_pwm, decision):
    if decision == "BAD":
        set_servo_angle(servo_pwm, CONFIG["SERVO_REJECT_ANGLE"])
        time.sleep(CONFIG["SERVO_DELAY"])
        set_servo_angle(servo_pwm, CONFIG["SERVO_PASS_ANGLE"])


# ================================================================
# SECTION 7 — CSV LOGGING
# ================================================================
def init_csv_log():
    file_exists = os.path.isfile(CONFIG["LOG_CSV_PATH"])
    with open(CONFIG["LOG_CSV_PATH"], "a", newline="") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow([
                "timestamp", "bean_id", "weight_g",
                "red", "green", "blue", "r_minus_g",
                "dt_prob", "cnn_prob", "fusion_score", "decision"
            ])

def log_result(bean_id, weight, r, g, b,
               dt_prob, cnn_prob, fusion_score, decision):
    with open(CONFIG["LOG_CSV_PATH"], "a", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            bean_id, weight, r, g, b, r - g,
            round(dt_prob, 4), round(cnn_prob, 4),
            round(fusion_score, 4), decision
        ])


# ================================================================
# SECTION 8 — STATISTICS DISPLAY
# ================================================================
def print_stats(total, good_count, bad_count, start_time):
    elapsed     = time.time() - start_time
    rate        = total / (elapsed / 60) if elapsed > 0 else 0
    pass_rate   = (good_count / total * 100) if total > 0 else 0
    reject_rate = (bad_count  / total * 100) if total > 0 else 0
    log.info("─"*45)
    log.info("LIVE STATISTICS — " + str(total) + " beans sorted")
    log.info("Good (passed)   : " + str(good_count) +
             "  (" + str(round(pass_rate,   1)) + "%)")
    log.info("Bad  (rejected) : " + str(bad_count) +
             "  (" + str(round(reject_rate, 1)) + "%)")
    log.info("Throughput      : " + str(round(rate, 1)) + " beans/min")
    log.info("Session time    : " + str(int(elapsed//60)) + "m " +
             str(int(elapsed%60)) + "s")
    log.info("─"*45)


# ================================================================
# SECTION 9 — MAIN SORTING LOOP
# CHANGE 6: Conveyor delays added between each stage
# ================================================================
def main():
    print("\n" + "="*55)
    print("  COFFEE BEAN QUALITY SORTER — CONVEYOR MODE")
    print("  Uganda Christian University | Group Trailblazers")
    print("="*55)

    # Load models
    try:
        dt_model, scaler, interpreter, \
        input_details, output_details, \
        fusion_cfg = load_models()
    except Exception as e:
        log.error("Failed to load models: " + str(e))
        sys.exit(1)

    # Initialise hardware
    try:
        # CHANGE 2,3,4: init_hardware now returns GPIO, servo, cam only
        GPIO, servo_pwm, cam = init_hardware()
    except Exception as e:
        log.error("Hardware init failed: " + str(e))
        sys.exit(1)

    init_csv_log()

    log.info("Conveyor timing:")
    log.info("  IR to colour  : " + str(CONFIG["DELAY_IR_TO_COLOUR"])  + "s")
    log.info("  Colour to cam : " + str(CONFIG["DELAY_COLOUR_TO_CAM"]) + "s")
    log.info("  Cam to servo  : " + str(CONFIG["DELAY_CAM_TO_SERVO"])  + "s")
    log.info("  Colour rule   : " + str(CONFIG["USE_COLOUR_RULE"]))

    print("\n  SYSTEM READY — Place beans on the conveyor")
    print("  Press Ctrl+C to stop\n")

    # CHANGE 4: DC motor removed — was 'start_belt(motor_pwm, GPIO)'
    # Belt must be started manually or added back when DC motor connected

    total_sorted = 0
    good_count   = 0
    bad_count    = 0
    start_time   = time.time()
    bean_id      = 1

    try:
        while True:
            try:
                bean_label = "bean_" + str(bean_id).zfill(5)

                # STAGE 1 — Wait for IR detection
                log.info("[" + bean_label + "] Waiting for bean...")
                while GPIO.input(CONFIG["IR_PIN"]) != GPIO.LOW:
                    time.sleep(0.01)
                log.info("[" + bean_label + "] Bean detected by IR!")

                # STAGE 2 — Wait for bean to reach colour sensor
                # CHANGE 6: Added conveyor delay
                log.info("[" + bean_label + "] Waiting " +
                         str(CONFIG["DELAY_IR_TO_COLOUR"]) +
                         "s for bean to reach colour sensor...")
                time.sleep(CONFIG["DELAY_IR_TO_COLOUR"])

                # STAGE 3 — Read colour
                weight, r, g, b = read_all_sensors(GPIO)
                log.info("[" + bean_label + "] Colour: R=" + str(r) +
                         " G=" + str(g) + " B=" + str(b) +
                         " (R-G=" + str(r-g) + ")")

                # STAGE 4 — Wait for bean to reach camera
                # CHANGE 6: Added conveyor delay
                log.info("[" + bean_label + "] Waiting " +
                         str(CONFIG["DELAY_COLOUR_TO_CAM"]) +
                         "s for bean to reach camera...")
                time.sleep(CONFIG["DELAY_COLOUR_TO_CAM"])

                # STAGE 5 — Capture image
                try:
                    image = capture_bean_image(cam)
                    log.info("[" + bean_label + "] Image captured")
                except Exception as e:
                    log.warning("[" + bean_label + "] Camera error: " + str(e))
                    image = np.zeros(
                        (CONFIG["IMG_SIZE"], CONFIG["IMG_SIZE"], 3),
                        dtype=np.float32
                    )

                # STAGE 6 — ML prediction
                decision, fusion_score, dt_prob, cnn_prob = predict_bean(
                    (weight, r, g, b), image,
                    dt_model, scaler,
                    interpreter, input_details, output_details
                )
                log.info("[" + bean_label + "] Decision: " + decision +
                         " (Colour=" + str(round(dt_prob, 2)) +
                         " CNN="     + str(round(cnn_prob, 2)) +
                         " Fusion="  + str(round(fusion_score, 2)) + ")")

                # STAGE 7 — Wait for bean to reach servo
                # CHANGE 6: Added conveyor delay
                log.info("[" + bean_label + "] Waiting " +
                         str(CONFIG["DELAY_CAM_TO_SERVO"]) +
                         "s for bean to reach servo gate...")
                time.sleep(CONFIG["DELAY_CAM_TO_SERVO"])

                # STAGE 8 — Trigger servo
                trigger_sort(servo_pwm, decision)

                # STAGE 9 — Log result
                log_result(bean_label, weight, r, g, b,
                           dt_prob, cnn_prob, fusion_score, decision)

                # STAGE 10 — Update counts
                total_sorted += 1
                if decision == "GOOD":
                    good_count += 1
                else:
                    bad_count += 1

                # Print stats every 10 beans
                if total_sorted % 10 == 0:
                    print_stats(total_sorted, good_count,
                                bad_count, start_time)

                bean_id += 1
                time.sleep(CONFIG["DELAY_SERVO_RESET"])

            except Exception as e:
                log.warning("Error on bean " + str(bean_id) + ": " + str(e))
                log.warning("Skipping and continuing...")
                time.sleep(0.5)
                continue

    except KeyboardInterrupt:
        print("\n\n  Stopping sorter (Ctrl+C)...")

    finally:
        try:
            set_servo_angle(servo_pwm, CONFIG["SERVO_PASS_ANGLE"])
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

        elapsed = time.time() - start_time
        rate    = total_sorted / (elapsed / 60) if elapsed > 0 else 0

        print("\n" + "="*55)
        print("  SESSION COMPLETE — FINAL SUMMARY")
        print("="*55)
        print("  Total sorted  : " + str(total_sorted))
        print("  Good (passed) : " + str(good_count) +
              "  (" + str(round(good_count/max(total_sorted,1)*100, 1)) + "%)")
        print("  Bad (rejected): " + str(bad_count) +
              "  (" + str(round(bad_count/max(total_sorted,1)*100, 1)) + "%)")
        print("  Throughput    : " + str(round(rate, 1)) + " beans/min")
        print("  Duration      : " + str(int(elapsed//60)) + "m " +
              str(int(elapsed%60)) + "s")
        print("  Results saved : " + CONFIG["LOG_CSV_PATH"])
        print("="*55)
        log.info("Sorter shutdown complete.")


# ================================================================
# SIMULATION MODE (for testing on laptop)
# ================================================================
def simulate_on_laptop():
    import joblib
    import tensorflow as tf

    print("\n" + "="*55)
    print("  SIMULATION MODE (Laptop — no hardware needed)")
    print("  Uganda Christian University | Group Trailblazers")
    print("="*55)

    dt_model = joblib.load("models/decision_tree_model.pkl")
    scaler   = joblib.load("models/scaler.pkl")
    interpreter = tf.lite.Interpreter(model_path="models/cnn_model.tflite")
    interpreter.allocate_tensors()
    input_details  = interpreter.get_input_details()
    output_details = interpreter.get_output_details()

    with open("models/fusion_config.json") as f:
        fusion_cfg = json.load(f)

    init_csv_log()
    np.random.seed(42)

    print("\n  Simulating 20 beans...\n")
    print("  Bean          Weight     R     G     B   Colour   CNN  Fusion  Decision")
    print("  " + "─"*72)

    total = good = bad = 0
    from PIL import Image, ImageDraw

    for i in range(20):
        is_good = i % 3 != 0
        if is_good:
            weight = round(np.random.normal(0.32, 0.02), 3)
            r = int(np.random.normal(273, 15))
            g = int(np.random.normal(164, 10))
            b = int(np.random.normal(197, 10))
        else:
            weight = round(np.random.normal(0.18, 0.02), 3)
            r = int(np.random.normal(207, 15))
            g = int(np.random.normal(195, 10))
            b = int(np.random.normal(195, 10))

        diff    = r - g
        dt_prob = 1.0 if diff > CONFIG["COLOUR_RULE_DIFF"] else 0.0

        img_pil   = Image.new("RGB", (224, 224), (20, 12, 6))
        draw      = ImageDraw.Draw(img_pil)
        draw.ellipse([57, 72, 167, 152], fill=(
            int(np.clip(r, 0, 255)),
            int(np.clip(g, 0, 255)),
            int(np.clip(b, 0, 255))
        ))
        img_array = np.array(img_pil).astype(np.float32) / 255.0

        img_input = np.expand_dims(img_array, axis=0).astype(np.float32)
        interpreter.set_tensor(input_details[0]["index"], img_input)
        interpreter.invoke()
        cnn_prob = float(
            interpreter.get_tensor(output_details[0]["index"])[0][0]
        )

        fusion_score = CONFIG["DT_WEIGHT"] * dt_prob + CONFIG["CNN_WEIGHT"] * cnn_prob
        decision     = "GOOD" if fusion_score >= CONFIG["FUSION_THRESHOLD"] else "BAD"
        bean_label   = "bean_" + str(i+1).zfill(5)

        log_result(bean_label, weight, r, g, b,
                   dt_prob, cnn_prob, fusion_score, decision)

        total += 1
        if decision == "GOOD":
            good += 1
        else:
            bad += 1

        icon = "✓" if decision == "GOOD" else "✗"
        print("  " + icon + " " + bean_label + "  " +
              str(weight) + "g" +
              "  " + str(r).rjust(4) +
              "  " + str(g).rjust(4) +
              "  " + str(b).rjust(4) +
              "  " + str(round(dt_prob, 2)).rjust(6) +
              "  " + str(round(cnn_prob, 2)).rjust(5) +
              "  " + str(round(fusion_score, 3)).rjust(6) +
              "  " + decision)
        time.sleep(0.05)

    print("  " + "─"*72)
    print("\n  SIMULATION COMPLETE")
    print("  Total=" + str(total) +
          "  Good=" + str(good) + " (" + str(round(good/total*100)) + "%)" +
          "  Bad="  + str(bad)  + " (" + str(round(bad/total*100))  + "%)")
    print("  Results saved to: " + CONFIG["LOG_CSV_PATH"])


# ================================================================
# ENTRY POINT
# ================================================================
if __name__ == "__main__":
    try:
        with open("/proc/cpuinfo") as f:
            cpu_info = f.read()
        is_raspberry_pi = "Raspberry Pi" in cpu_info or "BCM" in cpu_info
    except FileNotFoundError:
        is_raspberry_pi = False

    if is_raspberry_pi:
        print("\n  Raspberry Pi detected — starting hardware mode...")
        main()
    else:
        print("\n  Laptop detected — starting simulation mode...")
        simulate_on_laptop()