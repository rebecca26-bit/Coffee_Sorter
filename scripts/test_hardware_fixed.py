"""
COFFEE BEAN SORTER — FIXED HARDWARE TEST
Uganda Christian University | Group Trailblazers
"""

import RPi.GPIO as GPIO
import time
import os
from picamera2 import Picamera2

# PIN CONFIGURATION
SERVO_PIN = 18
IR_PIN    = 16
TCS_S0    = 17
TCS_S1    = 27
TCS_S2    = 22
TCS_S3    = 23
TCS_OUT   = 24

# GPIO SETUP
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)
GPIO.setup([TCS_S0, TCS_S1, TCS_S2, TCS_S3, SERVO_PIN], GPIO.OUT)
GPIO.setup([IR_PIN, TCS_OUT], GPIO.IN)
GPIO.output(TCS_S0, GPIO.HIGH)
GPIO.output(TCS_S1, GPIO.LOW)

print("\n" + "="*50)
print("  FIXED HARDWARE TEST — Group Trailblazers")
print("="*50)

# SERVO TEST
print("\n  TEST 1 — SERVO MOTOR")
print("  ─────────────────────")
pwm = GPIO.PWM(SERVO_PIN, 50)
pwm.start(0)

def set_servo(angle):
    pwm.ChangeDutyCycle(2 + (angle / 18))
    time.sleep(0.5)
    pwm.ChangeDutyCycle(0)

print("  Moving to 0 degrees...", end=" ")
set_servo(0)
print("done")
print("  Moving to 90 degrees...", end=" ")
set_servo(90)
print("done")
print("  Moving back to 0...", end=" ")
set_servo(0)
print("done")
print("  Servo PASSED")

# IR SENSOR TEST
print("\n  TEST 2 — IR SENSOR")
print("  ───────────────────")
print("  Reading for 5 seconds — wave hand in front...")
detections = 0
start = time.time()
while time.time() - start < 5:
    if GPIO.input(IR_PIN) == GPIO.LOW:
        print(f"  DETECTED at {time.time()-start:.1f}s")
        detections += 1
        time.sleep(0.3)
print(f"  IR detections: {detections}")

# TCS3200 TEST
print("\n  TEST 3 — TCS3200 COLOUR SENSOR")
print("  ────────────────────────────────")

def read_channel(s2, s3, samples=20):
    GPIO.output(TCS_S2, s2)
    GPIO.output(TCS_S3, s3)
    time.sleep(0.1)
    count = 0
    for _ in range(samples):
        result = GPIO.wait_for_edge(TCS_OUT, GPIO.FALLING, timeout=3000)
        if result is None:
            return 0
        count += 1
    return count

def read_rgb():
    r = read_channel(GPIO.LOW,  GPIO.LOW)
    g = read_channel(GPIO.HIGH, GPIO.HIGH)
    b = read_channel(GPIO.LOW,  GPIO.HIGH)
    return r, g, b

print("  Place a bean under the sensor...")
for i in range(3):
    print(f"  Reading {i+1}/3...", end=" ")
    r, g, b = read_rgb()
    if r == 0 and g == 0 and b == 0:
        print("No signal — check VCC, GND and LED wiring")
    else:
        print(f"R={r}  G={g}  B={b}")
    time.sleep(1)

# CAMERA TEST — single instance only
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

    print("  Capturing image...", end=" ")
    cam.capture_file("test_bean_capture.jpg")
    print("done")

    size = os.path.getsize("test_bean_capture.jpg")
    print(f"  Saved: test_bean_capture.jpg ({size} bytes)")
    print(f"  Camera PASSED")

except Exception as e:
    print(f"  Camera error: {e}")

finally:
    try:
        cam.stop()
    except:
        pass

# FULL PIPELINE TEST
print("\n  TEST 5 — FULL PIPELINE")
print("  ────────────────────────")
print("  Reopening camera for pipeline test...")

try:
    cam2 = Picamera2()
    cam2.configure(cam2.create_still_configuration(
        main={"size": (224, 224)}
    ))
    cam2.start()
    time.sleep(2)

    print("  Drop 3 beans in front of IR sensor when prompted\n")

    for bean_num in range(1, 4):
        print(f"  Waiting for bean {bean_num}...")
        timeout = time.time() + 15
        detected = False
        while time.time() < timeout:
            if GPIO.input(IR_PIN) == GPIO.LOW:
                detected = True
                break
            time.sleep(0.05)

        if not detected:
            print(f"  No bean detected — skipping")
            continue

        print(f"  Bean {bean_num} detected!")

        # Read colour
        r, g, b = read_rgb()
        print(f"  Colour: R={r}  G={g}  B={b}")

        # Capture image
        img_file = f"bean_{bean_num}.jpg"
        cam2.capture_file(img_file)
        print(f"  Image saved: {img_file}")

        # Simple decision
        decision = "PASS" if r > 500 else "REJECT"
        print(f"  Decision: {decision}")

        # Servo action
        if decision == "REJECT":
            set_servo(90)
            time.sleep(0.5)
            set_servo(0)

        print()
        time.sleep(0.5)

    cam2.stop()

except Exception as e:
    print(f"  Pipeline error: {e}")
    try:
        cam2.stop()
    except:
        pass

# CLEANUP
pwm.stop()
GPIO.cleanup()

print("\n" + "="*50)
print("  ALL TESTS COMPLETE")
print("="*50)
