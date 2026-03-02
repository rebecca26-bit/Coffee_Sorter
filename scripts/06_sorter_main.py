"""
================================================================
COFFEE BEAN QUALITY SORTER — STEP 6: RASPBERRY PI DEPLOYMENT
Uganda Christian University | Group Trailblazers
S23B23/056 | S23B23/010 | S23B23/046

HOW TO INSTALL ON RASPBERRY PI:
  1. Copy the entire models/ folder to the Pi:
     From your laptop terminal:
     scp -r models/ pi@raspberrypi.local:/home/pi/coffee_sorter/

  2. Install required libraries on the Pi:
     pip install numpy pillow opencv-python tflite-runtime joblib
     pip install RPi.GPIO hx711-rpi-py picamera2

  3. Copy this script to the Pi:
     scp scripts/06_sorter_main.py pi@raspberrypi.local:/home/pi/coffee_sorter/

  4. Run on the Pi:
     python /home/pi/coffee_sorter/06_sorter_main.py

WHAT THIS SCRIPT DOES:
  - Initialises all hardware (camera, TCS3200, HX711, servo, LED)
  - Runs the main sorting loop continuously
  - For each bean: captures image + reads sensors simultaneously
  - Runs Decision Tree + CNN fusion to classify the bean
  - Triggers servo to divert defective beans
  - Logs all results to a CSV file for later analysis
  - Displays live statistics (total sorted, pass rate, etc.)
  - Handles errors gracefully so it never crashes mid-session
================================================================
"""

import os
import sys
import csv
import json
import time
import logging
import numpy as np
from datetime import datetime

# ================================================================
# LOGGING SETUP
# ================================================================
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
# CONFIGURATION — Edit these values to match your hardware setup
# ================================================================
CONFIG = {
    # ── GPIO Pin Numbers (BCM numbering) ──────────────────────
    "S0"         : 23,      # TCS3200 frequency scaling
    "S1"         : 25,      # TCS3200 frequency scaling
    "S2"         : 8,       # TCS3200 colour filter select
    "S3"         : 7,       # TCS3200 colour filter select
    "OUT"        : 24,      # TCS3200 digital output
    "HX_DT"      : 5,       # HX711 data pin
    "HX_SCK"     : 6,       # HX711 clock pin
    "SERVO_PIN"  : 12,      # Servo motor PWM pin
    "LED_PIN"    : 18,      # LED ring control pin
    "DC_MOTOR_IN1": 20,     # Conveyor belt motor IN1
    "DC_MOTOR_IN2": 21,     # Conveyor belt motor IN2
    "DC_MOTOR_EN" : 16,     # Conveyor belt motor enable (PWM)

    # ── Sensor Settings ───────────────────────────────────────
    "HX711_SCALE_RATIO" : 102,    # Calibration value — adjust for your load cell
    "WEIGHT_SAMPLES"    : 5,      # Number of weight readings to average
    "COLOR_SAMPLES"     : 30,     # Number of TCS3200 pulses to count

    # ── Servo Settings ────────────────────────────────────────
    "SERVO_PASS_ANGLE"  : 0,      # Degrees — gate open (bean passes)
    "SERVO_REJECT_ANGLE": 90,     # Degrees — gate closed (bean diverted)
    "SERVO_DELAY"       : 0.3,    # Seconds to hold position

    # ── Belt Settings ─────────────────────────────────────────
    "BELT_SPEED_PCT"    : 40,     # Belt speed 0-100% (lower = more time per bean)

    # ── Camera Settings ───────────────────────────────────────
    "IMG_SIZE"          : 224,    # Must match training size
    "CAMERA_WARMUP"     : 2,      # Seconds for camera to initialise

    # ── ML Model Settings ─────────────────────────────────────
    "DT_WEIGHT"         : 0.65,   # Decision Tree contribution to fusion
    "CNN_WEIGHT"        : 0.35,   # CNN contribution to fusion
    "FUSION_THRESHOLD"  : 0.5,    # Score >= this = GOOD bean

    # ── File Paths ────────────────────────────────────────────
    "DT_MODEL_PATH"     : "models/decision_tree_model.pkl",
    "CNN_MODEL_PATH"    : "models/cnn_model.tflite",
    "SCALER_PATH"       : "models/scaler.pkl",
    "FUSION_CONFIG_PATH": "models/fusion_config.json",
    "LOG_CSV_PATH"      : "data/sorting_results.csv",
}


# ================================================================
# SECTION 1 — LOAD ML MODELS
# ================================================================
def load_models():
    """Load all ML models and return them."""
    log.info("Loading ML models...")

    import joblib
    import tflite_runtime.interpreter as tflite

    # Load Decision Tree + scaler
    dt_model = joblib.load(CONFIG["DT_MODEL_PATH"])
    scaler   = joblib.load(CONFIG["SCALER_PATH"])
    log.info(f"  ✓ Decision Tree loaded (depth={dt_model.get_depth()})")

    # Load fusion config
    with open(CONFIG["FUSION_CONFIG_PATH"]) as f:
        fusion_cfg = json.load(f)
    log.info(f"  ✓ Fusion config loaded (strategy: {fusion_cfg['best_strategy']})")

    # Load CNN TFLite
    interpreter = tflite.Interpreter(model_path=CONFIG["CNN_MODEL_PATH"])
    interpreter.allocate_tensors()
    input_details  = interpreter.get_input_details()
    output_details = interpreter.get_output_details()
    log.info(f"  ✓ CNN TFLite loaded")

    return dt_model, scaler, interpreter, input_details, output_details, fusion_cfg


# ================================================================
# SECTION 2 — HARDWARE INITIALISATION
# ================================================================
def init_hardware():
    """Initialise all GPIO hardware and return handles."""
    import RPi.GPIO as GPIO
    from hx711 import HX711
    from picamera2 import Picamera2

    log.info("Initialising hardware...")
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)

    # TCS3200 colour sensor
    GPIO.setup([CONFIG["S0"], CONFIG["S1"],
                CONFIG["S2"], CONFIG["S3"],
                CONFIG["LED_PIN"]], GPIO.OUT)
    GPIO.setup(CONFIG["OUT"], GPIO.IN)
    GPIO.output(CONFIG["S0"], GPIO.HIGH)
    GPIO.output(CONFIG["S1"], GPIO.LOW)    # 20% frequency scaling
    GPIO.output(CONFIG["LED_PIN"], GPIO.LOW)
    log.info("  ✓ TCS3200 colour sensor initialised")

    # HX711 load cell
    hx = HX711(dout_pin=CONFIG["HX_DT"], pd_sck_pin=CONFIG["HX_SCK"])
    hx.set_scale_ratio(CONFIG["HX711_SCALE_RATIO"])
    hx.tare()
    log.info("  ✓ HX711 load cell initialised and tared")

    # Servo motor
    GPIO.setup(CONFIG["SERVO_PIN"], GPIO.OUT)
    servo_pwm = GPIO.PWM(CONFIG["SERVO_PIN"], 50)   # 50Hz PWM
    servo_pwm.start(0)
    set_servo_angle(servo_pwm, CONFIG["SERVO_PASS_ANGLE"])  # default = open
    log.info("  ✓ Servo motor initialised (gate open)")

    # DC motor (conveyor belt)
    GPIO.setup([CONFIG["DC_MOTOR_IN1"],
                CONFIG["DC_MOTOR_IN2"],
                CONFIG["DC_MOTOR_EN"]], GPIO.OUT)
    motor_pwm = GPIO.PWM(CONFIG["DC_MOTOR_EN"], 100)
    motor_pwm.start(0)
    log.info("  ✓ DC motor initialised")

    # Raspberry Pi Camera Module 3
    cam = Picamera2()
    cam.configure(cam.create_still_configuration(
        main={"size": (CONFIG["IMG_SIZE"], CONFIG["IMG_SIZE"])}
    ))
    cam.start()
    time.sleep(CONFIG["CAMERA_WARMUP"])
    log.info("  ✓ Camera Module 3 initialised")

    return GPIO, hx, servo_pwm, motor_pwm, cam


# ================================================================
# SECTION 3 — SENSOR READING FUNCTIONS
# ================================================================
def read_colour_channel(GPIO, s2_val, s3_val):
    """Read one RGB channel from TCS3200."""
    GPIO.output(CONFIG["S2"], s2_val)
    GPIO.output(CONFIG["S3"], s3_val)
    time.sleep(0.05)
    count = 0
    start = time.time()
    while count < CONFIG["COLOR_SAMPLES"]:
        GPIO.wait_for_edge(CONFIG["OUT"], GPIO.FALLING)
        count += 1
    elapsed = time.time() - start
    return int(count / elapsed)


def read_all_sensors(GPIO, hx):
    """
    Read weight + RGB colour simultaneously.
    Returns: (weight_g, red, green, blue)
    """
    # Turn on LED ring for consistent lighting
    GPIO.output(CONFIG["LED_PIN"], GPIO.HIGH)
    time.sleep(0.05)

    # Read colour channels
    r = read_colour_channel(GPIO, GPIO.LOW,  GPIO.LOW)    # Red
    g = read_colour_channel(GPIO, GPIO.HIGH, GPIO.HIGH)   # Green
    b = read_colour_channel(GPIO, GPIO.LOW,  GPIO.HIGH)   # Blue

    GPIO.output(CONFIG["LED_PIN"], GPIO.LOW)

    # Read weight (average of multiple readings for stability)
    readings = [hx.get_weight_mean(readings=CONFIG["WEIGHT_SAMPLES"])
                for _ in range(3)]
    weight = round(sum(readings) / len(readings), 3)

    return weight, r, g, b


# ================================================================
# SECTION 4 — CAMERA CAPTURE
# ================================================================
def capture_bean_image(cam):
    """
    Capture image of bean under LED ring lighting.
    Returns: numpy array shape (224, 224, 3) normalised 0.0-1.0
    """
    img_array = cam.capture_array()

    # Resize to 224x224 if needed
    from PIL import Image
    img = Image.fromarray(img_array)
    img = img.resize((CONFIG["IMG_SIZE"], CONFIG["IMG_SIZE"]),
                     Image.LANCZOS)

    # Normalise to 0.0-1.0
    return np.array(img) / 255.0


# ================================================================
# SECTION 5 — ML PREDICTION (FUSION)
# ================================================================
def predict_bean(sensor_data, image_array,
                 dt_model, scaler,
                 interpreter, input_details, output_details):
    """
    Run full fusion prediction on one bean.
    Returns: (decision, fusion_score, dt_prob, cnn_prob)
      decision     : 'GOOD' or 'BAD'
      fusion_score : 0.0-1.0 (higher = more likely good)
      dt_prob      : Decision Tree confidence (good)
      cnn_prob     : CNN confidence (good)
    """
    # ── Decision Tree prediction ──────────────────────────────
    weight, r, g, b = sensor_data
    raw    = np.array([[weight, r, g, b]])
    scaled = scaler.transform(raw)
    dt_prob = dt_model.predict_proba(scaled)[0][1]   # prob of good

    # ── CNN prediction ────────────────────────────────────────
    img_input = np.expand_dims(image_array, axis=0).astype(np.float32)
    interpreter.set_tensor(input_details[0]["index"], img_input)
    interpreter.invoke()
    cnn_prob = float(
        interpreter.get_tensor(output_details[0]["index"])[0][0]
    )

    # ── Weighted fusion ───────────────────────────────────────
    fusion_score = (CONFIG["DT_WEIGHT"]  * dt_prob +
                    CONFIG["CNN_WEIGHT"] * cnn_prob)
    decision = "GOOD" if fusion_score >= CONFIG["FUSION_THRESHOLD"] else "BAD"

    return decision, fusion_score, dt_prob, cnn_prob


# ================================================================
# SECTION 6 — SERVO CONTROL
# ================================================================
def set_servo_angle(servo_pwm, angle):
    """Move servo to specified angle (0-180 degrees)."""
    duty = 2 + (angle / 18)   # convert angle to duty cycle
    servo_pwm.ChangeDutyCycle(duty)
    time.sleep(0.1)
    servo_pwm.ChangeDutyCycle(0)  # stop signal (prevents jitter)


def trigger_sort(servo_pwm, decision):
    """
    Trigger servo based on sorting decision.
    GOOD  → gate stays open  (bean passes to good bin)
    BAD   → gate closes briefly (bean diverted to reject bin)
    """
    if decision == "BAD":
        set_servo_angle(servo_pwm, CONFIG["SERVO_REJECT_ANGLE"])
        time.sleep(CONFIG["SERVO_DELAY"])
        set_servo_angle(servo_pwm, CONFIG["SERVO_PASS_ANGLE"])
    # GOOD: do nothing, gate stays open


# ================================================================
# SECTION 7 — CSV LOGGING
# ================================================================
def init_csv_log():
    """Create CSV log file with headers if it doesn't exist."""
    os.makedirs("data", exist_ok=True)
    file_exists = os.path.isfile(CONFIG["LOG_CSV_PATH"])
    with open(CONFIG["LOG_CSV_PATH"], "a", newline="") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow([
                "timestamp", "bean_id", "weight_g",
                "red", "green", "blue",
                "dt_prob", "cnn_prob", "fusion_score", "decision"
            ])


def log_result(bean_id, weight, r, g, b,
               dt_prob, cnn_prob, fusion_score, decision):
    """Append one bean result to the CSV log."""
    with open(CONFIG["LOG_CSV_PATH"], "a", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            bean_id, weight, r, g, b,
            round(dt_prob, 4), round(cnn_prob, 4),
            round(fusion_score, 4), decision
        ])


# ================================================================
# SECTION 8 — DISPLAY STATISTICS
# ================================================================
def print_stats(total, good_count, bad_count, start_time):
    """Print live sorting statistics to terminal."""
    elapsed    = time.time() - start_time
    rate       = total / (elapsed / 60) if elapsed > 0 else 0
    pass_rate  = (good_count / total * 100) if total > 0 else 0
    reject_rate= (bad_count  / total * 100) if total > 0 else 0

    print(f"\n  {'─'*45}")
    print(f"  LIVE STATISTICS")
    print(f"  {'─'*45}")
    print(f"  Total sorted    : {total}")
    print(f"  Good (passed)   : {good_count}  ({pass_rate:.1f}%)")
    print(f"  Bad  (rejected) : {bad_count}  ({reject_rate:.1f}%)")
    print(f"  Throughput      : {rate:.0f} beans/minute")
    print(f"  Session time    : {int(elapsed//60)}m {int(elapsed%60)}s")
    print(f"  {'─'*45}\n")


# ================================================================
# SECTION 9 — CONVEYOR BELT CONTROL
# ================================================================
def start_belt(motor_pwm, GPIO):
    """Start the conveyor belt."""
    GPIO.output(CONFIG["DC_MOTOR_IN1"], GPIO.HIGH)
    GPIO.output(CONFIG["DC_MOTOR_IN2"], GPIO.LOW)
    motor_pwm.ChangeDutyCycle(CONFIG["BELT_SPEED_PCT"])
    log.info(f"  Belt started at {CONFIG['BELT_SPEED_PCT']}% speed")


def stop_belt(motor_pwm, GPIO):
    """Stop the conveyor belt."""
    motor_pwm.ChangeDutyCycle(0)
    GPIO.output(CONFIG["DC_MOTOR_IN1"], GPIO.LOW)
    GPIO.output(CONFIG["DC_MOTOR_IN2"], GPIO.LOW)
    log.info("  Belt stopped")


# ================================================================
# SECTION 10 — MAIN SORTING LOOP
# ================================================================
def main():
    """Main entry point — runs the full sorting system."""
    print("\n" + "="*55)
    print("  COFFEE BEAN QUALITY SORTER — STARTUP")
    print("  Uganda Christian University | Group Trailblazers")
    print("="*55)

    # ── Load models ───────────────────────────────────────────
    try:
        dt_model, scaler, interpreter, \
        input_details, output_details, \
        fusion_cfg = load_models()
    except Exception as e:
        log.error(f"Failed to load models: {e}")
        log.error("Make sure models/ folder is present on the Pi")
        sys.exit(1)

    # ── Initialise hardware ───────────────────────────────────
    try:
        GPIO, hx, servo_pwm, motor_pwm, cam = init_hardware()
    except Exception as e:
        log.error(f"Hardware initialisation failed: {e}")
        log.error("Check GPIO connections and run: gpio readall")
        sys.exit(1)

    # ── Prepare CSV log ───────────────────────────────────────
    init_csv_log()

    # ── Startup stats ─────────────────────────────────────────
    total_sorted  = 0
    good_count    = 0
    bad_count     = 0
    start_time    = time.time()
    bean_id       = 1

    print(f"\n  System ready! Starting conveyor belt...")
    print(f"  Press Ctrl+C to stop sorting session.\n")

    # ── Start conveyor belt ───────────────────────────────────
    start_belt(motor_pwm, GPIO)

    try:
        # ── MAIN SORTING LOOP ─────────────────────────────────
        while True:
            try:
                bean_label = f"bean_{bean_id:05d}"

                # Step 1: Read sensors
                weight, r, g, b = read_all_sensors(GPIO, hx)

                # Skip if no bean detected (weight too low)
                if weight < 0.05:
                    time.sleep(0.1)
                    continue

                # Step 2: Capture image
                image = capture_bean_image(cam)

                # Step 3: Run fusion prediction
                decision, fusion_score, dt_prob, cnn_prob = predict_bean(
                    (weight, r, g, b), image,
                    dt_model, scaler,
                    interpreter, input_details, output_details
                )

                # Step 4: Trigger servo
                trigger_sort(servo_pwm, decision)

                # Step 5: Log result
                log_result(bean_label, weight, r, g, b,
                           dt_prob, cnn_prob, fusion_score, decision)

                # Step 6: Update stats
                total_sorted += 1
                if decision == "GOOD":
                    good_count += 1
                else:
                    bad_count += 1

                # Step 7: Print result
                status_icon = "✓" if decision == "GOOD" else "✗"
                print(f"  {status_icon} {bean_label} | "
                      f"W:{weight:.2f}g R:{r} G:{g} B:{b} | "
                      f"DT:{dt_prob:.2f} CNN:{cnn_prob:.2f} | "
                      f"Score:{fusion_score:.2f} → {decision}")

                # Step 8: Print stats every 20 beans
                if total_sorted % 20 == 0:
                    print_stats(total_sorted, good_count,
                                bad_count, start_time)

                bean_id += 1

                # Small delay between beans
                time.sleep(0.2)

            except Exception as e:
                log.warning(f"Error processing bean {bean_id}: {e}")
                log.warning("Skipping bean and continuing...")
                time.sleep(0.5)
                continue

    except KeyboardInterrupt:
        # ── GRACEFUL SHUTDOWN ─────────────────────────────────
        print(f"\n\n  Stopping sorter (Ctrl+C pressed)...")

    finally:
        # Always clean up hardware on exit
        stop_belt(motor_pwm, GPIO)
        set_servo_angle(servo_pwm, CONFIG["SERVO_PASS_ANGLE"])
        servo_pwm.stop()
        motor_pwm.stop()
        cam.stop()
        GPIO.cleanup()

        # Print final session summary
        elapsed = time.time() - start_time
        print(f"\n" + "="*55)
        print(f"  SESSION COMPLETE — FINAL SUMMARY")
        print(f"="*55)
        print(f"""
  Total beans sorted  : {total_sorted}
  Good beans (passed) : {good_count}  ({good_count/max(total_sorted,1)*100:.1f}%)
  Bad beans (rejected): {bad_count}  ({bad_count/max(total_sorted,1)*100:.1f}%)
  Session duration    : {int(elapsed//60)}m {int(elapsed%60)}s
  Throughput          : {total_sorted/max(elapsed/60,1):.0f} beans/minute
  Results saved to    : {CONFIG['LOG_CSV_PATH']}
        """)
        print("="*55)
        log.info("Sorter shutdown complete.")


# ================================================================
# SECTION 11 — LAPTOP SIMULATION MODE
# ================================================================
def simulate_on_laptop():
    """
    Run a simulation of the sorting system on your laptop.
    Uses synthetic data instead of real hardware.
    Useful for testing the logic before deploying to the Pi.
    """
    import joblib
    import tensorflow as tf

    print("\n" + "="*55)
    print("  SIMULATION MODE (No Raspberry Pi hardware needed)")
    print("  Uganda Christian University | Group Trailblazers")
    print("="*55)

    # Load models
    dt_model = joblib.load("models/decision_tree_model.pkl")
    scaler   = joblib.load("models/scaler.pkl")

    interpreter = tf.lite.Interpreter(model_path="models/cnn_model.tflite")
    interpreter.allocate_tensors()
    input_details  = interpreter.get_input_details()
    output_details = interpreter.get_output_details()

    # Load fusion config
    with open("models/fusion_config.json") as f:
        fusion_cfg = json.load(f)

    init_csv_log()

    # Simulate 20 beans
    np.random.seed(42)
    print(f"\n  Simulating 20 beans through the sorting pipeline...\n")
    print(f"  {'Bean':<12} {'Weight':>8} {'R':>5} {'G':>5} {'B':>5} "
          f"{'DT':>6} {'CNN':>6} {'Score':>7} {'Decision':>10}")
    print(f"  {'─'*12} {'─'*8} {'─'*5} {'─'*5} {'─'*5} "
          f"{'─'*6} {'─'*6} {'─'*7} {'─'*10}")

    total = good = bad = 0
    from PIL import Image, ImageDraw, ImageFilter

    for i in range(20):
        # Generate synthetic bean (mix of good and bad)
        is_good = i % 3 != 0   # every 3rd bean is bad

        if is_good:
            weight = round(np.random.normal(0.32, 0.02), 3)
            r = int(np.random.normal(140, 10))
            g = int(np.random.normal(93,  8))
            b = int(np.random.normal(58,  6))
        else:
            defect = np.random.choice(["black", "immature", "foreign"])
            if defect == "black":
                weight = round(np.random.normal(0.30, 0.03), 3)
                r, g, b = int(np.random.normal(38,8)), int(np.random.normal(30,6)), int(np.random.normal(22,5))
            elif defect == "immature":
                weight = round(np.random.normal(0.13, 0.02), 3)
                r, g, b = int(np.random.normal(198,10)), int(np.random.normal(204,10)), int(np.random.normal(175,8))
            else:
                weight = round(np.random.uniform(0.8, 1.5), 3)
                r, g, b = int(np.random.normal(105,20)), int(np.random.normal(98,18)), int(np.random.normal(90,15))

        # Scale sensor data
        raw    = np.array([[weight, r, g, b]])
        scaled = scaler.transform(raw)

        # DT prediction
        dt_prob = dt_model.predict_proba(scaled)[0][1]

        # Generate synthetic image for CNN
        img_pil = Image.new("RGB", (224, 224), (20, 12, 6))
        draw    = ImageDraw.Draw(img_pil)
        r_c = int(np.clip(r, 0, 255))
        g_c = int(np.clip(g, 0, 255))
        b_c = int(np.clip(b, 0, 255))
        draw.ellipse([57, 72, 167, 152], fill=(r_c, g_c, b_c))
        img_array = np.array(img_pil.filter(ImageFilter.GaussianBlur(1))) / 255.0

        # CNN prediction
        img_input = np.expand_dims(img_array, axis=0).astype(np.float32)
        interpreter.set_tensor(input_details[0]["index"], img_input)
        interpreter.invoke()
        cnn_prob = float(interpreter.get_tensor(output_details[0]["index"])[0][0])

        # Fusion decision
        fusion_score = CONFIG["DT_WEIGHT"] * dt_prob + CONFIG["CNN_WEIGHT"] * cnn_prob
        decision     = "GOOD ✓" if fusion_score >= CONFIG["FUSION_THRESHOLD"] else "BAD  ✗"

        # Log result
        bean_label = f"bean_{i+1:05d}"
        log_result(bean_label, weight, r, g, b,
                   dt_prob, cnn_prob, fusion_score,
                   "GOOD" if fusion_score >= 0.5 else "BAD")

        total += 1
        if fusion_score >= 0.5: good += 1
        else: bad += 1

        print(f"  {bean_label:<12} {weight:>7.3f}g {r:>5} {g:>5} {b:>5} "
              f"{dt_prob:>5.2f} {cnn_prob:>5.2f} {fusion_score:>6.3f}  {decision}")

        time.sleep(0.05)

    print(f"\n  {'─'*70}")
    print(f"  SIMULATION COMPLETE")
    print(f"  Total: {total} | Good: {good} ({good/total*100:.0f}%) | "
          f"Bad: {bad} ({bad/total*100:.0f}%)")
    print(f"  Results logged to: {CONFIG['LOG_CSV_PATH']}")
    print(f"  {'─'*70}\n")


# ================================================================
# ENTRY POINT
# ================================================================
if __name__ == "__main__":
    # Detect if running on Raspberry Pi or laptop
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
        print("  (Deploy to Raspberry Pi for real hardware sorting)\n")
        simulate_on_laptop()