#!/usr/bin/env python3
"""
test_integrated.py
Test both sensors together (color + weight)
Usage: python3 test_integrated.py
"""

import RPi.GPIO as GPIO
import time
from hx711 import HX711
import config

def setup_tcs3200():
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(config.COLOR_S0, GPIO.OUT)
    GPIO.setup(config.COLOR_S1, GPIO.OUT)
    GPIO.setup(config.COLOR_S2, GPIO.OUT)
    GPIO.setup(config.COLOR_S3, GPIO.OUT)
    GPIO.setup(config.COLOR_OUT, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    
    GPIO.output(config.COLOR_S0, GPIO.HIGH)
    GPIO.output(config.COLOR_S1, GPIO.HIGH)

def read_color_frequency():
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
    print("Integrated Sensor Test (Color + Weight)")
    print("=" * 60)
    print("Setting up all sensors...")
    
    # Setup color sensor
    setup_tcs3200()
    
    # Setup load cell GPIO (fixes KeyboardInterrupt)
    GPIO.setup(config.LOADCELL_DT, GPIO.IN)
    GPIO.setup(config.LOADCELL_SCK, GPIO.OUT)
    GPIO.output(config.LOADCELL_SCK, GPIO.LOW)
    
    # Setup load cell
    hx = HX711(config.LOADCELL_DT, config.LOADCELL_SCK)
    hx.reset()
    print("Taring load cell...")
    hx.tare()
    try:
        hx.set_reference_unit(config.LOAD_SCALE)
    except AttributeError:
        print("Warning: LOAD_SCALE not in config.py. Using default 1.")
        hx.set_reference_unit(1)
    
    print("\nPlace coffee beans one at a time")
    print("Press Ctrl+C to stop\n")
    
    bean_count = 0
    
    try:
        while True:
            input(f"Bean #{bean_count + 1} - Press Enter to measure...")
            
            # Read color
            red, green, blue = read_rgb()
            
            # Read weight (manual averaging for older library)
            weight_readings = []
            for _ in range(10):
                weight_readings.append(hx.get_weight())
                time.sleep(0.1)
            weight = sum(weight_readings) / len(weight_readings)
            
            # Display results
            print(f"  Color  - R: {red:6.0f}, G: {green:6.0f}, B: {blue:6.0f}")
            print(f"  Weight - {weight:6.2f} g")
            print()
            
            bean_count += 1
            
    except KeyboardInterrupt:
        print(f"\nTest stopped. Measured {bean_count} beans")
        GPIO.cleanup()
        print("GPIO cleaned up")
