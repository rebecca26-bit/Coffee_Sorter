import time
import joblib
import threading
import pandas as pd
from flask import Flask, jsonify

import RPi.GPIO as GPIO


# =======================================================
#  TCS3200 COLOR SENSOR SETUP
# =======================================================

TCS_OUT = 17
S2 = 22
S3 = 27
S0 = 24
S1 = 25

GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

GPIO.setup(TCS_OUT, GPIO.IN)
GPIO.setup(S2, GPIO.OUT)
GPIO.setup(S3, GPIO.OUT)
GPIO.setup(S0, GPIO.OUT)
GPIO.setup(S1, GPIO.OUT)

GPIO.output(S0, GPIO.HIGH)
GPIO.output(S1, GPIO.LOW)

def set_filter(color):
    if color == 'R':
        GPIO.output(S2, GPIO.LOW)
        GPIO.output(S3, GPIO.LOW)
    elif color == 'G':
        GPIO.output(S2, GPIO.HIGH)
        GPIO.output(S3, GPIO.HIGH)
    elif color == 'B':
        GPIO.output(S2, GPIO.LOW)
        GPIO.output(S3, GPIO.HIGH)

def read_freq(duration=0.1):
    """Count rising edges on TCS_OUT."""
    count = 0
    start = time.time()
    last = GPIO.input(TCS_OUT)

    while time.time() - start < duration:
        now = GPIO.input(TCS_OUT)
        if last == 0 and now == 1:
            count += 1
        last = now
        time.sleep(0.00005)

    return count / duration


# =======================================================
#  NORMALIZATION USING YOUR CALIBRATION VALUES
# =======================================================

WHITE = {'R': 2400.0, 'G': 2350.0, 'B': 2750.0}
BLACK = {'R': 1437.5, 'G': 1362.5, 'B': 1725.0}

def normalize(raw):
    norm = {}
    for c in ['R', 'G', 'B']:
        norm[c] = (raw[c] - BLACK[c]) / (WHITE[c] - BLACK[c])
        norm[c] = max(0, min(1, norm[c]))
    return norm


# =======================================================
#  SERVO SETUP (HARDWARE PWM — NO JITTER)
# =======================================================

SERVO_PIN = 18  # MUST move servo wire here (GPIO 18 supports hardware PWM)

GPIO.setup(SERVO_PIN, GPIO.OUT)

# SG90 uses 50Hz PWM
pwm = GPIO.PWM(SERVO_PIN, 50)
pwm.start(0)

def angle_to_duty(angle):
    """
    SG90 pulse widths:
    - 0°   = 0.5 ms  →  2.5% duty
    - 90°  = 1.5 ms  →  7.5% duty
    - 180° = 2.5 ms  → 12.5% duty
    """
    return 2.5 + (angle / 180.0) * 10.0

def move_servo_smooth(target_angle, step=3, delay=0.02):
    """
    Smoothly move SG90 servo to target angle using hardware PWM.
    """
    current = getattr(move_servo_smooth, "last", 90)

    if current < target_angle:
        seq = range(current, target_angle + 1, step)
    else:
        seq = range(current, target_angle - 1, -step)

    for angle in seq:
        pwm.ChangeDutyCycle(angle_to_duty(angle))
        time.sleep(delay)

    move_servo_smooth.last = target_angle


# =======================================================
#  LOAD MODEL
# =======================================================

model_data = joblib.load("dt_model.joblib")
model = model_data["model"]

latest_result = {
    "raw": {"R": 0.0, "G": 0.0, "B": 0.0},
    "normalized": {"R": 0.0, "G": 0.0, "B": 0.0},
    "prediction": "WAITING",
    "timestamp": time.time(),
}


# =======================================================
#  SORTING LOOP
# =======================================================

def sorting_loop():
    print("\nSorter running. Place beans...\n")

    while True:
        time.sleep(0.6)  # Time to place bean

        # --- Read RGB ---
        raw = {}
        for c in ['R', 'G', 'B']:
            set_filter(c)
            time.sleep(0.05)
            raw[c] = read_freq()

        # Normalize
        norm = normalize(raw)

        # ML prediction
        X = pd.DataFrame([[norm['R'], norm['G'], norm['B']]],
                         columns=['r', 'g', 'b'])
        pred = model.predict(X)[0]

        # Update dashboard data
        latest_result.update({
            "raw": raw,
            "normalized": norm,
            "prediction": pred,
            "timestamp": time.time()
        })

        # --- Servo movement ---
        if pred == "BAD":
            move_servo_smooth(0)      # Move to left bin
        else:
            move_servo_smooth(180)    # Move to right bin

        time.sleep(0.6)
        move_servo_smooth(90)         # Return to center


# =======================================================
#  FLASK SERVER FOR DASHBOARD
# =======================================================

app = Flask(__name__)

@app.route("/status")
def status():
    return jsonify(latest_result)


# =======================================================
#  START THREADS
# =======================================================

t = threading.Thread(target=sorting_loop)
t.daemon = True
t.start()

if __name__ == "__main__":
    try:
        app.run(host="0.0.0.0", port=5000)
    finally:
        pwm.stop()
        GPIO.cleanup()
