#!/usr/bin/env python3
# test_s2_s3_pins.py - Test S2 and S3 control pins
import RPi.GPIO as GPIO
import time
import config

print("Testing S2 and S3 GPIO pins...")
print("=" * 50)

GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)
GPIO.setup(config.COLOR_S2, GPIO.OUT)
GPIO.setup(config.COLOR_S3, GPIO.OUT)

print(f"\nS2 is connected to GPIO{config.COLOR_S2} (should be GPIO22)")
print(f"S3 is connected to GPIO{config.COLOR_S3} (should be GPIO23)")

print("\nToggling S2 and S3 pins...")
print("Use multimeter or LED to verify pins are changing")
print("Press Ctrl+C to exit\n")

try:
    cycle = 0
    while True:
        cycle += 1
        print(f"\nCycle {cycle}:")
        
        # All combinations
        print("  S2=LOW,  S3=LOW  (RED filter)")
        GPIO.output(config.COLOR_S2, GPIO.LOW)
        GPIO.output(config.COLOR_S3, GPIO.LOW)
        time.sleep(2)
        
        print("  S2=HIGH, S3=HIGH (GREEN filter)")
        GPIO.output(config.COLOR_S2, GPIO.HIGH)
        GPIO.output(config.COLOR_S3, GPIO.HIGH)
        time.sleep(2)
        
        print("  S2=LOW,  S3=HIGH (BLUE filter)")
        GPIO.output(config.COLOR_S2, GPIO.LOW)
        GPIO.output(config.COLOR_S3, GPIO.HIGH)
        time.sleep(2)
        
        print("  S2=HIGH, S3=LOW  (CLEAR - no filter)")
        GPIO.output(config.COLOR_S2, GPIO.HIGH)
        GPIO.output(config.COLOR_S3, GPIO.LOW)
        time.sleep(2)
        
except KeyboardInterrupt:
    print("\n\nTest stopped")
    GPIO.cleanup()
