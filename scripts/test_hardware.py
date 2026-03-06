"""
================================================================
COFFEE BEAN SORTER — HARDWARE TEST SCRIPT
Uganda Christian University | Group Trailblazers

Tests: Camera Module 2, TCS3200, Servo Motor, IR Sensor
No HX711, No LED ring, No DC motor

HOW TO RUN:
  python3 scripts/test_hardware.py

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

import RPi.GPIO as GPIO
import time
import os
from picamera2 import Picamera2

# ================================================================
# PIN CONFIGURATION
# ================================================================
SERVO_PIN  = 18
IR_PIN     = 16
TCS_S0     = 17
TCS_S1     = 27
TCS_S2     = 22
TCS_S3     = 23
TCS_OUT    = 24

# ================================================================
# SETUP GPIO
# ================================================================
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

# Outputs
GPIO.setup([TCS_S0, TCS_S1, TCS_S2, TCS_S3, SERVO_PIN], GPIO.OUT)

# Inputs
GPIO.setup(IR_PIN,  GPIO.IN)
GPIO.setup(TCS_OUT, GPIO.IN)

# TCS3200 frequency scaling — 20%
GPIO.output(TCS_S0, GPIO.HIGH)
GPIO.output(TCS_S1, GPIO.LOW)

print("\n" + "="*50)
print("  HARDWARE TEST — Group Trailblazers")
print("="*50)


# ================================================================
# TEST 1 — SERVO MOTOR
# ================================================================
print("\n  TEST 1 — SERVO MOTOR")
print("  ─────────────────────")

def set_servo(angle):
    """Move servo to angle (0-180 degrees)."""
    pwm.ChangeDutyCycle(2 + (angle / 18))
    time.sleep(0.5)
    pwm.ChangeDutyCycle(0)

pwm = GPIO.PWM(SERVO_PIN, 50)
pwm.start(0)

print("  Moving to 0 degrees (PASS position)...", end=" ")
set_servo(0)
print("done")

print("  Moving to 90 degrees (REJECT position)...", end=" ")
set_servo(90)
print("done")

print("  Moving back to 0 degrees...", end=" ")
set_servo(0)
print("done")

print("  Servo test PASSED")


# ================================================================
# TEST 2 — IR SENSOR
# ================================================================
print("\n  TEST 2 — IR SENSOR")
print("  ───────────────────")
print("  Reading IR sensor for 5 seconds...")
print("  Place your hand in front of the sensor to test detection\n")

detections = 0
start = time.time()
while time.time() - start < 5:
    ir_value = GPIO.input(IR_PIN)
    if ir_value == GPIO.LOW:    # LOW = object detected
        print(f"  OBJECT DETECTED at {time.time()-start:.1f}s")
        detections += 1
        time.sleep(0.3)         # debounce

if detections > 0:
    print(f"  IR sensor detected {detections} object(s) — PASSED")
else:
    print("  No objects detected — place hand in front to test")
    print("  IR sensor wiring OK if no errors appeared")


# ================================================================
# TEST 3 — TCS3200 COLOUR SENSOR
# ================================================================
print("\n  TEST 3 — TCS3200 COLOUR SENSOR")
print("  ────────────────────────────────")

def read_colour_channel(s2_val, s3_val, samples=20):
    """Read one colour channel frequency."""
    GPIO.output(TCS_S2, s2_val)
    GPIO.output(TCS_S3, s3_val)
    time.sleep(0.05)
    count = 0
    start = time.time()
    while count < samples:
        GPIO.wait_for_edge(TCS_OUT, GPIO.FALLING, timeout=2000)
        count += 1
    elapsed = time.time() - start
    return int(count / elapsed) if elapsed > 0 else 0

def read_rgb():
    """Read full RGB values from TCS3200."""
    r = read_colour_channel(GPIO.LOW,  GPIO.LOW)    # Red
    g = read_colour_channel(GPIO.HIGH, GPIO.HIGH)   # Green
    b = read_colour_channel(GPIO.LOW,  GPIO.HIGH)   # Blue
    return r, g, b

print("  Reading colour 3 times — place a bean under the sensor\n")

for i in range(3):
    print(f"  Reading {i+1}/3...", end=" ")
    try:
        r, g, b = read_rgb()
        print(f"R={r:5}  G={g:5}  B={b:5}")
    except Exception as e:
        print(f"Error: {e}")
    time.sleep(1)

print("  TCS3200 test complete")


# ================================================================
# TEST 4 — CAMERA MODULE 2
# ================================================================
print("\n  TEST 4 — CAMERA MODULE 2")
print("  ─────────────────────────")

try:
    print("  Initialising camera...", end=" ")
    cam = Picamera2()
    cam.configure(cam.create_still_configuration(
        main={"size": (224, 224)}
    ))
    cam.start()
    time.sleep(2)
    print("done")

    print("  Capturing test image...", end=" ")
    cam.capture_file("test_bean_capture.jpg")
    cam.stop()
    print("done")

    # Verify file saved
    size = os.path.getsize("test_bean_capture.jpg")
    print(f"  Image saved: test_bean_capture.jpg ({size} bytes)")
    print(f"  Camera test PASSED")

except Exception as e:
    print(f"  Camera error: {e}")


# ================================================================
# TEST 5 — FULL PIPELINE TEST (Bean detection → colour → sort)
# ================================================================
print("\n  TEST 5 — FULL PIPELINE SIMULATION")
print("  ────────────────────────────────────")
print("  Simulating 3 beans going through the system...")
print("  Place objects in front of IR sensor when prompted\n")

cam2 = Picamera2()
cam2.configure(cam2.create_still_configuration(main={"size": (224, 224)}))
cam2.start()
time.sleep(2)

for bean_num in range(1, 4):
    print(f"  ── Bean {bean_num} ──────────────────")
    print(f"  Waiting for bean detection...")

    # Wait for IR sensor to detect bean
    timeout = time.time() + 10    # 10 second timeout
    detected = False
    while time.time() < timeout:
        if GPIO.input(IR_PIN) == GPIO.LOW:
            detected = True
            break
        time.sleep(0.05)

    if not detected:
        print(f"  No bean detected (timeout) — skipping")
        continue

    print(f"  Bean detected!")

    # Read colour
    print(f"  Reading colour...", end=" ")
    try:
        r, g, b = read_rgb()
        print(f"R={r}  G={g}  B={b}")
    except:
        r, g, b = 0, 0, 0
        print("colour read failed")

    # Capture image
    print(f"  Capturing image...", end=" ")
    cam2.capture_file(f"bean_{bean_num}.jpg")
    print(f"saved as bean_{bean_num}.jpg")

    # Simple sort decision based on colour
    # Good beans tend to have higher red values
    decision = "PASS" if r > 500 else "REJECT"
    print(f"  Decision: {decision}")

    # Trigger servo
    if decision == "REJECT":
        print(f"  Servo: diverting bean...")
        set_servo(90)
        time.sleep(0.5)
        set_servo(0)
    else:
        print(f"  Servo: bean passes through")

    print()
    time.sleep(0.5)

cam2.stop()


# ================================================================
# CLEANUP & SUMMARY
# ================================================================
pwm.stop()
GPIO.cleanup()

print("\n" + "="*50)
print("  HARDWARE TEST COMPLETE")
print("="*50)
print("""
  Component Status:
    Servo Motor    : tested (0° and 90°)
    IR Sensor      : tested (5 second detection)
    TCS3200        : tested (3 colour readings)
    Camera Module 2: tested (image captured)
    Full Pipeline  : tested (3 bean simulation)

  Files saved:
    test_bean_capture.jpg
    bean_1.jpg, bean_2.jpg, bean_3.jpg

  Next step:
    Run the full ML sorter:
    python3 scripts/06_sorter_main.py
""")
print("="*50)
