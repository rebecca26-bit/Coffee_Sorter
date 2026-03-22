"""
================================================================
DC MOTOR TEST — Group Trailblazers
Uganda Christian University

Tests the conveyor belt DC motor via L298N driver.
Pot on ENA controls speed (hardware).
Pi controls IN1/IN2 (direction/start/stop).

HOW TO RUN:
  cd ~/Projects/Coffee_Sorter
  python3 scripts/test_motor.py
================================================================
"""

import RPi.GPIO as GPIO
import time

# ── PIN CONFIG (BCM) ──────────────────────────────────────────
MOTOR_IN1 = 5   # L298N IN1
MOTOR_IN2 = 6   # L298N IN2
# ENA is controlled by pot — no GPIO pin needed

# ── SETUP ─────────────────────────────────────────────────────
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)
GPIO.setup(MOTOR_IN1, GPIO.OUT)
GPIO.setup(MOTOR_IN2, GPIO.OUT)
GPIO.output(MOTOR_IN1, GPIO.LOW)
GPIO.output(MOTOR_IN2, GPIO.LOW)

def motor_forward():
    GPIO.output(MOTOR_IN1, GPIO.HIGH)
    GPIO.output(MOTOR_IN2, GPIO.LOW)

def motor_stop():
    GPIO.output(MOTOR_IN1, GPIO.LOW)
    GPIO.output(MOTOR_IN2, GPIO.LOW)

# ── TEST SEQUENCE ─────────────────────────────────────────────
print("\n" + "="*50)
print("  DC MOTOR TEST — Group Trailblazers")
print("="*50)
print("  Make sure pot on ENA is turned UP before starting.")
print("  GPIO 5 → IN1 | GPIO 6 → IN2\n")

try:
    # Test 1: Short run
    print("  [Test 1] Running motor for 2 seconds...")
    motor_forward()
    time.sleep(2)
    motor_stop()
    print("  [Test 1] Motor stopped. ✓")
    time.sleep(1)

    # Test 2: Stop/start 3 times
    print("\n  [Test 2] Stop/start 3 times (1s on, 1s off)...")
    for i in range(1, 4):
        print(f"    Cycle {i}/3 — ON")
        motor_forward()
        time.sleep(1)
        print(f"    Cycle {i}/3 — OFF")
        motor_stop()
        time.sleep(1)
    print("  [Test 2] Done. ✓")
    time.sleep(1)

    # Test 3: Long run (belt travel simulation)
    print("\n  [Test 3] Running for 5 seconds (simulates belt travel)...")
    motor_forward()
    time.sleep(5)
    motor_stop()
    print("  [Test 3] Done. ✓")

    print("\n" + "="*50)
    print("  ALL TESTS PASSED")
    print("  If motor did not move, check:")
    print("  1. Pot on ENA — turn it up")
    print("  2. Power supply connected to L298N +12V")
    print("  3. GPIO 5 → IN1, GPIO 6 → IN2 wiring")
    print("="*50 + "\n")

except KeyboardInterrupt:
    print("\n  Test interrupted.")

finally:
    motor_stop()
    GPIO.cleanup()
    print("  GPIO cleaned up.")
