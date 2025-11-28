#!/usr/bin/env python3
"""
calibrate_color_sensor.py
Basic calibration for TCS3200 color sensor
Collects white and black reference readings
Usage: python3 calibrate_color_sensor.py
"""

import RPi.GPIO as GPIO
import time
import config

def setup_tcs3200():
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(config.COLOR_S0, GPIO.OUT)
    GPIO.setup(config.COLOR_S1, GPIO.OUT)
    GPIO.setup(config.COLOR_S2, GPIO.OUT)
    GPIO.setup(config.COLOR_S3, GPIO.OUT)
    GPIO.setup(config.COLOR_OUT, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    
    # Set frequency scaling to 100% (S0=HIGH, S1=HIGH)
    GPIO.output(config.COLOR_S0, GPIO.HIGH)
    GPIO.output(config.COLOR_S1, GPIO.HIGH)

def read_color_frequency():
    """Read frequency from OUT pin with polling"""
    start = time.time()
    pulses = 0
    duration = config.COLOR_PULSE_DURATION
    
    last_state = GPIO.input(config.COLOR_OUT)
    while (time.time() - start) < duration:
        current_state = GPIO.input(config.COLOR_OUT)
        if last_state == GPIO.HIGH and current_state == GPIO.LOW:
            pulses += 1
        last_state = current_state
        time.sleep(0.0001)
    
    frequency = pulses / duration
    return frequency

def read_rgb():
    # Red
    GPIO.output(config.COLOR_S2, GPIO.LOW)
    GPIO.output(config.COLOR_S3, GPIO.LOW)
    time.sleep(0.1)
    red_freq = read_color_frequency()
    
    # Green
    GPIO.output(config.COLOR_S2, GPIO.HIGH)
    GPIO.output(config.COLOR_S3, GPIO.HIGH)
    time.sleep(0.1)
    green_freq = read_color_frequency()
    
    # Blue
    GPIO.output(config.COLOR_S2, GPIO.LOW)
    GPIO.output(config.COLOR_S3, GPIO.HIGH)
    time.sleep(0.1)
    blue_freq = read_color_frequency()
    
    return red_freq, green_freq, blue_freq

if __name__ == "__main__":
    print("=" * 60)
    print("Color Sensor Calibration")
    print("=" * 60)
    print("Setting up TCS3200...")
    setup_tcs3200()
    
    print("\nPlace WHITE reference under sensor")
    input("Press Enter when ready...")
    white_r, white_g, white_b = read_rgb()
    print(f"White: R={white_r:.0f}, G={white_g:.0f}, B={white_b:.0f}")
    
    print("\nPlace BLACK reference under sensor")
    input("Press Enter when ready...")
    black_r, black_g, black_b = read_rgb()
    print(f"Black: R={black_r:.0f}, G={black_g:.0f}, B={black_b:.0f}")
    
    print("\n" + "=" * 60)
    print("CALIBRATION COMPLETE!")
    print("=" * 60)
    print("Add this to config.py:")
    print("COLOR_CALIBRATION = {")
    print(f"    'white': {{'r': {int(white_r)}, 'g': {int(white_g)}, 'b': {int(white_b)}}},")
    print(f"    'black': {{'r': {int(black_r)}, 'g': {int(black_g)}, 'b': {int(black_b)}}},")
    print("    'good_reference': {'r': 0, 'g': 0, 'b': 0},  # Update manually")
    print("    'bad_reference': {'r': 0, 'g': 0, 'b': 0}   # Update manually")
    print("}")
    print("=" * 60)
    
    GPIO.cleanup()
