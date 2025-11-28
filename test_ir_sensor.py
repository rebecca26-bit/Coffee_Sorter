#!/usr/bin/env python3
# test_ir_sensor.py - Test IR proximity sensor
import RPi.GPIO as GPIO
import time
import config

print("=" * 50)
print("IR PROXIMITY SENSOR TEST")
print("=" * 50)

# Setup
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)
GPIO.setup(config.IR_SENSOR, GPIO.IN)

print("\nIR sensor detects objects within 2-30cm")
print("Wave your hand or place coffee bean in front")
print("\nAdjust potentiometer on sensor if needed:")
print("  - Turn clockwise for shorter distance")
print("  - Turn counter-clockwise for longer distance")
print("\nPress Ctrl+C to exit\n")

detection_count = 0
previous_state = GPIO.HIGH

try:
    while True:
        current_state = GPIO.input(config.IR_SENSOR)
        
        # Most IR sensors are active LOW (detect = LOW)
        if current_state == GPIO.LOW and previous_state == GPIO.HIGH:
            detection_count += 1
            print(f"✓ OBJECT DETECTED! (Count: {detection_count})")
            
        elif current_state == GPIO.HIGH and previous_state == GPIO.LOW:
            print("  Object removed")
        
        previous_state = current_state
        time.sleep(0.1)
        
except KeyboardInterrupt:
    print(f"\n\nTest stopped")
    print(f"Total detections: {detection_count}")
    
finally:
    GPIO.cleanup()
