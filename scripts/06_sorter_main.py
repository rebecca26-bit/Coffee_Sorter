import os
import sys
import csv
import time
import json
import warnings
import numpy as np
from datetime import datetime

sys.path.insert(0, 'scripts')
warnings.filterwarnings('ignore')

import RPi.GPIO as GPIO
from camera_module2 import CameraModule

# TFLite
try:
    import tflite_runtime.interpreter as tflite
    CNN_AVAILABLE = True
except ImportError:
    try:
        import tensorflow as tf
        tflite = tf.lite
        CNN_AVAILABLE = True
    except ImportError:
        CNN_AVAILABLE = False

# ================================================================
# PIN CONFIGURATION (BCM)
# ================================================================
PIN_SERVO     = 18
PIN_IR        = 16
PIN_S0        = 17
PIN_S1        = 27
PIN_S2        = 22
PIN_S3        = 23
PIN_OUT       = 24
PIN_MOTOR_IN1 = 5    # L298N IN1  ← change to your wiring
PIN_MOTOR_IN2 = 6    # L298N IN2  ← change to your wiring
PIN_MOTOR_ENA = None   # L298N ENA  ← change to your wiring (must be PWM pin)

# ================================================================
# TIMING CONFIGURATION
# ================================================================
# Belt speed
BELT_SPEED           = 55   # PWM duty cycle 0-100 (low = slow belt)

# Travel times between stations (tune these to your belt length)
BELT_IR_TO_COLOUR    = 16.901  # seconds: IR sensor → colour sensor
BELT_COLOUR_TO_CAM   = 11.972  # seconds: colour sensor → camera
BELT_CAM_TO_SERVO    = 9.859  # seconds: camera → servo gate

# Pause times at each station (belt stopped)
COLOUR_READ_PAUSE    = 0.5  # seconds: pause while colour sensor reads
CAMERA_CAPTURE_PAUSE = 0.4  # seconds: pause for camera AE to settle
SERVO_HOLD_TIME      = 0.8  # seconds: keep servo in eject position

# Servo
SERVO_PASS_ANGLE     = 0    # degrees: gate open
SERVO_REJECT_ANGLE   = 90   # degrees: gate closed / eject
SERVO_MOVE_TIME      = 0.6  # seconds: wait for servo to reach angle

# IR debounce
IR_DEBOUNCE_SAMPLES  = 3    # consecutive LOW reads needed to confirm bean
IR_DEBOUNCE_DELAY    = 0.02 # seconds between confirmation reads
IR_COOLDOWN          = 0.5  # seconds: minimum time between detections

# Colour thresholds (from calibrate_colour.py output)
THRESHOLDS = {
    "good_red_min"  : 145,
    "good_rg_margin": 47,
    "good_rb_margin": 80,
    "black_max"     : 60,
    "foreign_min"   : 200,
}

# Paths
CAL_FILE       = "scripts/colour_calibration.json"
CNN_MODEL_PATH = "models/cnn_model.tflite"
LOG_CSV_PATH   = "data/sorting_log.csv"
IMAGES_DIR     = "data/sorted_images/"
IMG_SIZE       = 224

os.makedirs("data",     exist_ok=True)
os.makedirs(IMAGES_DIR, exist_ok=True)

# ================================================================
# SESSION STATS
# ================================================================
stats = {
    "total"  : 0,
    "good"   : 0,
    "bad"    : 0,
    "foreign": 0,
    "start"  : time.time()
}

# ================================================================
# STARTUP BANNER
# ================================================================
print("\n" + "="*55)
print("  AUTOMATED COFFEE BEAN SORTER")
print("  Uganda Christian University | Group Trailblazers")
print("="*55)

# ================================================================
# GPIO SETUP
# ================================================================
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

for pin in [PIN_S0, PIN_S1, PIN_S2, PIN_S3,
            PIN_SERVO, PIN_MOTOR_IN1, PIN_MOTOR_IN2]:
    GPIO.setup(pin, GPIO.OUT)
    GPIO.output(pin, GPIO.LOW)

GPIO.setup(PIN_IR,  GPIO.IN)
GPIO.setup(PIN_OUT, GPIO.IN)

# TCS3200: S0=HIGH, S1=LOW → 20% frequency scaling
GPIO.output(PIN_S0, GPIO.HIGH)
GPIO.output(PIN_S1, GPIO.LOW)

# ================================================================
# BELT (DC MOTOR via L298N)
# ================================================================
def belt_start():
    """Start conveyor belt moving forward."""
    GPIO.output(PIN_MOTOR_IN1, GPIO.HIGH)
    GPIO.output(PIN_MOTOR_IN2, GPIO.LOW)

def belt_stop():
    """Stop conveyor belt immediately."""
    GPIO.output(PIN_MOTOR_IN1, GPIO.LOW)
    GPIO.output(PIN_MOTOR_IN2, GPIO.LOW)

# ================================================================
# SERVO
# ================================================================
servo_pwm = GPIO.PWM(PIN_SERVO, 50)
servo_pwm.start(0)

def set_servo(angle: int):
    """Move servo to angle then kill PWM signal to stop jitter."""
    duty = 2.0 + (angle / 18.0)
    servo_pwm.ChangeDutyCycle(duty)
    time.sleep(SERVO_MOVE_TIME)
    servo_pwm.ChangeDutyCycle(0)

set_servo(SERVO_PASS_ANGLE)
print("  Servo                 : ready (gate open)")

# ================================================================
# IR SENSOR — DEBOUNCED
# ================================================================
_last_ir_time = 0.0

def ir_bean_detected() -> bool:
    """
    Non-blocking. Returns True only when a bean is confirmed
    present by multiple consecutive reads AND cooldown has passed.
    """
    global _last_ir_time
    if GPIO.input(PIN_IR) != GPIO.LOW:
        return False
    for _ in range(IR_DEBOUNCE_SAMPLES):
        time.sleep(IR_DEBOUNCE_DELAY)
        if GPIO.input(PIN_IR) != GPIO.LOW:
            return False
    now = time.time()
    if (now - _last_ir_time) < IR_COOLDOWN:
        return False
    _last_ir_time = now
    return True

# ================================================================
# COLOUR SENSOR (TCS3200)
# ================================================================
def _read_channel(s2: bool, s3: bool, window: float = 0.08) -> int:
    GPIO.output(PIN_S2, GPIO.HIGH if s2 else GPIO.LOW)
    GPIO.output(PIN_S3, GPIO.HIGH if s3 else GPIO.LOW)
    time.sleep(0.03)
    count = 0
    last  = GPIO.input(PIN_OUT)
    end   = time.time() + window
    while time.time() < end:
        val = GPIO.input(PIN_OUT)
        if val != last:
            count += 1
            last = val
    return count // 2

def read_raw_rgb(samples: int = 5) -> tuple:
    rs, gs, bs = [], [], []
    for _ in range(samples):
        rs.append(_read_channel(False, False))  # Red
        gs.append(_read_channel(True,  True ))  # Green
        bs.append(_read_channel(False, True ))  # Blue
    return int(np.mean(rs)), int(np.mean(gs)), int(np.mean(bs))

# Load calibration
cal_black = [0,   0,   0  ]
cal_white = [255, 255, 255]
if os.path.exists(CAL_FILE):
    with open(CAL_FILE) as f:
        cal = json.load(f)
    cal_black = cal.get("black", cal_black)
    cal_white = cal.get("white", cal_white)
    print("  Colour calibration    : loaded")
else:
    print("  Colour calibration    : ⚠ not found — run calibrate_colour.py first!")

def normalise_rgb(raw_r, raw_g, raw_b) -> list:
    out = []
    for v, b, w in zip([raw_r, raw_g, raw_b], cal_black, cal_white):
        span = (w - b) if (w - b) > 0 else 1
        out.append(int(min(255, max(0, (v - b) / span * 255))))
    return out

def classify_colour(r, g, b) -> str:
    t = THRESHOLDS
    if r > t["foreign_min"] and g > t["foreign_min"] and b > t["foreign_min"]:
        return "FOREIGN"
    if r < t["black_max"] and g < t["black_max"] and b < t["black_max"]:
        return "BAD_BLACK"
    if g > r and (g - r) > t["good_rg_margin"]:
        return "BAD_GREEN"
    if (r >= t["good_red_min"] and
            (r - g) >= t["good_rg_margin"] and
            (r - b) >= t["good_rb_margin"]):
        return "GOOD"
    return "BAD_UNKNOWN"

# ================================================================
# CAMERA + CNN
# ================================================================
print("  Opening camera        : ", end="", flush=True)
cam = None
try:
    cam = CameraModule()
    print("ready")
except Exception as e:
    print(f"FAILED ({e})")

cnn     = None
cnn_in  = None
cnn_out = None
if CNN_AVAILABLE and os.path.exists(CNN_MODEL_PATH):
    try:
        cnn = tflite.Interpreter(model_path=CNN_MODEL_PATH)
        cnn.allocate_tensors()
        cnn_in  = cnn.get_input_details()
        cnn_out = cnn.get_output_details()
        print("  CNN model             : loaded")
    except Exception as e:
        print(f"  CNN model             : FAILED ({e})")
else:
    print("  CNN model             : not available (colour-only mode)")

def cnn_predict(frame_rgb) -> tuple:
    """Returns (label, score). label = 'GOOD' or 'BAD'."""
    if cnn is None:
        return "UNKNOWN", 0.0
    try:
        from PIL import Image
        img   = Image.fromarray(frame_rgb).resize((IMG_SIZE, IMG_SIZE))
        arr   = np.expand_dims(
                    np.array(img, dtype=np.float32) / 255.0, axis=0)
        cnn.set_tensor(cnn_in[0]["index"], arr)
        cnn.invoke()
        score = float(cnn.get_tensor(cnn_out[0]["index"])[0][0])
        return ("GOOD" if score >= 0.5 else "BAD"), score
    except Exception as e:
        print(f"  [CNN] error: {e}")
        return "BAD", 0.0

# ================================================================
# CSV LOG
# ================================================================
file_exists = os.path.isfile(LOG_CSV_PATH)
log_file    = open(LOG_CSV_PATH, "a", newline="")
log_writer  = csv.writer(log_file)
if not file_exists:
    log_writer.writerow([
        "timestamp", "bean_id",
        "norm_r", "norm_g", "norm_b", "colour_result",
        "cnn_label", "cnn_score", "final_decision"
    ])

# ================================================================
# SORTING PIPELINE — ONE BEAN
# ================================================================
def sort_one_bean(bean_id: int) -> str:
    """
    Executes the full stop-at-each-station pipeline for one bean.

    Belt was already stopped by IR detection in main loop.
    """
    print(f"\n  {'─'*48}")
    print(f"  Bean #{bean_id:04d} │ IR triggered — belt stopped")

    # ── Station 1 → 2: Run belt to colour sensor ──────────────────────────────
    print(f"  ▶ Belt running: IR → Colour sensor ({BELT_IR_TO_COLOUR}s)")
    belt_start()
    time.sleep(BELT_IR_TO_COLOUR)
    belt_stop()

    # ── Station 2: Read colour sensor ─────────────────────────────────────────
    print(f"  ■ Belt stopped at colour sensor — reading colour...")
    time.sleep(COLOUR_READ_PAUSE)
    raw_r, raw_g, raw_b    = read_raw_rgb(samples=5)
    norm_r, norm_g, norm_b = normalise_rgb(raw_r, raw_g, raw_b)
    colour_result          = classify_colour(norm_r, norm_g, norm_b)
    print(f"    R={norm_r:3d}  G={norm_g:3d}  B={norm_b:3d}  → {colour_result}")

    # ── Station 2 → 3: Run belt to camera ────────────────────────────────────
    print(f"  ▶ Belt running: Colour → Camera ({BELT_COLOUR_TO_CAM}s)")
    belt_start()
    time.sleep(BELT_COLOUR_TO_CAM)
    belt_stop()

    # ── Station 3: Camera capture + CNN ──────────────────────────────────────
    print(f"  ■ Belt stopped at camera — capturing...")
    time.sleep(CAMERA_CAPTURE_PAUSE)

    cnn_label = "UNKNOWN"
    cnn_score = 0.0

    if cam is not None:
        try:
            img_path          = os.path.join(IMAGES_DIR, f"bean_{bean_id:04d}.jpg")
            frame             = cam.capture_bean(save_path=img_path)
            print(f"    Image saved: {img_path}")
            if cnn is not None:
                cnn_label, cnn_score = cnn_predict(frame)
                print(f"    CNN: {cnn_label}  (score={cnn_score:.3f})")
        except Exception as e:
            print(f"    Camera/CNN error: {e}")
    else:
        print("    Camera skipped (not available)")

    # ── Fusion decision ───────────────────────────────────────────────────────
    # Conservative: either sensor flagging BAD → reject
    is_foreign = (colour_result == "FOREIGN")
    if is_foreign:
        decision = "FOREIGN"
    elif colour_result != "GOOD":
        decision = "BAD"
    elif cnn_label == "BAD":
        decision = "BAD"
    else:
        decision = "GOOD"

    # ── Station 3 → 4: Run belt to servo gate ────────────────────────────────
    print(f"  ▶ Belt running: Camera → Servo gate ({BELT_CAM_TO_SERVO}s)")
    belt_start()
    time.sleep(BELT_CAM_TO_SERVO)
    belt_stop()

    # ── Station 4: Servo action ───────────────────────────────────────────────
    if decision == "GOOD":
        print(f"  ✓ GOOD — gate stays open, bean passes through")
        set_servo(SERVO_PASS_ANGLE)
        stats["good"] += 1
    else:
        print(f"  ✗ {decision} — ejecting bean")
        set_servo(SERVO_REJECT_ANGLE)
        time.sleep(SERVO_HOLD_TIME)
        set_servo(SERVO_PASS_ANGLE)   # reset gate for next bean
        if is_foreign:
            stats["foreign"] += 1
        else:
            stats["bad"] += 1

    # ── Resume belt for next bean ─────────────────────────────────────────────
    print(f"  ▶ Belt resuming — ready for next bean")
    belt_start()

    # ── Log ───────────────────────────────────────────────────────────────────
    log_writer.writerow([
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        f"bean_{bean_id:04d}",
        norm_r, norm_g, norm_b, colour_result,
        cnn_label, round(cnn_score, 4), decision
    ])
    log_file.flush()

    stats["total"] += 1
    return decision

# ================================================================
# SESSION SUMMARY
# ================================================================
def print_stats():
    t = stats["total"]
    if t == 0:
        return
    elapsed = int(time.time() - stats["start"])
    rate    = round(t / elapsed * 3600) if elapsed > 0 else 0
    print("\n" + "="*55)
    print("  SESSION SUMMARY")
    print("="*55)
    print(f"  Total sorted  : {t}")
    print(f"  Good          : {stats['good']}  ({stats['good']/t*100:.1f}%)")
    print(f"  Bad           : {stats['bad']}   ({stats['bad']/t*100:.1f}%)")
    print(f"  Foreign       : {stats['foreign']}")
    print(f"  Duration      : {elapsed//60}m {elapsed%60}s")
    print(f"  Throughput    : ~{rate} beans/hour")
    print(f"  Log saved     : {LOG_CSV_PATH}")
    print("="*55)

# ================================================================
# ENTRY POINT
# ================================================================
def main():
    print("\n" + "="*55)
    print("  READY — Starting belt. Feed beans into the chute.")
    print("  Press Ctrl+C to stop.")
    print("="*55 + "\n")

    bean_id = 1
    belt_start()

    try:
        while True:
            if ir_bean_detected():
                print("  ⚠ Bean detected at IR sensor — press Enter to start belt...")
                input()
                belt_stop()              # stop immediately at IR trigger
                sort_one_bean(bean_id)   # belt is restarted inside this function
                bean_id += 1
            else:
                time.sleep(0.005)        # avoid hammering CPU while polling

    except KeyboardInterrupt:
        print("\n\n  Stopping …")

    finally:
        belt_stop()
        set_servo(SERVO_PASS_ANGLE)
        servo_pwm.stop()
        if cam:
            cam.close()
        GPIO.cleanup()
        log_file.close()
        print_stats()
        print("  Shutdown complete.")


if __name__ == "__main__":
    main()
