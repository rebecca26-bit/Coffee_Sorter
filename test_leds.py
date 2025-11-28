#!/usr/bin/env python3
# test_leds.py - Test status LEDs
import RPi.GPIO as GPIO
import time
import config

print("=" * 50)
print("LED TEST")
print("=" * 50)

# Setup
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)
GPIO.setup(config.LED_GREEN, GPIO.OUT)
GPIO.setup(config.LED_RED, GPIO.OUT)

print("\nTesting LEDs...")
print("Watch the LEDs on your breadboard")
print("Press Ctrl+C to exit\n")

try:
    cycle = 0
    while True:
        cycle += 1
        print(f"Cycle {cycle}:")
        
        # Both OFF
        GPIO.output(config.LED_GREEN, GPIO.LOW)
        GPIO.output(config.LED_RED, GPIO.LOW)
        print("  Both OFF")
        time.sleep(1)
        
        # Green ON
        GPIO.output(config.LED_GREEN, GPIO.HIGH)
        GPIO.output(config.LED_RED, GPIO.LOW)
        print("  GREEN ON")
        time.sleep(1)
        
        # Red ON
        GPIO.output(config.LED_GREEN, GPIO.LOW)
        GPIO.output(config.LED_RED, GPIO.HIGH)
        print("  RED ON")
        time.sleep(1)
        
        # Both ON
        GPIO.output(config.LED_GREEN, GPIO.HIGH)
        GPIO.output(config.LED_RED, GPIO.HIGH)
        print("  BOTH ON")
        time.sleep(1)
        
except KeyboardInterrupt:
    print("\n\nTest stopped")
    
finally:
    GPIO.output(config.LED_GREEN, GPIO.LOW)
    GPIO.output(config.LED_RED, GPIO.LOW)
    GPIO.cleanup()
    print("LEDs turned off")
