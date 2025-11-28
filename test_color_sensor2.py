#!/usr/bin/env python3
"""
test_color_sensor2.py
Test the TCS3200 color sensor to verify RGB readings
Usage: python3 test_color_sensor.py
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
    
    # Add LED for illumination
    GPIO.setup(23, GPIO.OUT)  # LED pin (adjust if needed)
    GPIO.output(23, GPIO.HIGH)  # Turn on LED
    
    # Set frequency scaling to 100% (S0=HIGH, S1=HIGH)
    GPIO.output(config.COLOR_S0, GPIO.HIGH)
    GPIO.output(config.COLOR_S1, GPIO.HIGH)

def read_color_frequency():
    """Read frequency from OUT pin with polling"""
    start = time.time()
    pulses = 0
    duration = 0.5  # Longer duration for more pulses
    
    last_state = GPIO.input(config.COLOR_OUT)
    while (time.time() - start) < duration:
        current_state = GPIO.input(config.COLOR_OUT)
        if last_state == GPIO.HIGH and current_state == GPIO.LOW:
            pulses += 1
        last_state = current_state
        time.sleep(0.0001)  # Small delay
    
    frequency = pulses / duration
    return frequency


def read_rgb():
    """Read Red, Green, Blue values"""
    # Read Red
    GPIO.output(config.COLOR_S2, GPIO.LOW)
    GPIO.output(config.COLOR_S3, GPIO.LOW)
    time.sleep(0.1)
    red_freq = read_color_frequency()
    
    # Read Green
    GPIO.output(config.COLOR_S2, GPIO.HIGH)
    GPIO.output(config.COLOR_S3, GPIO.HIGH)
    time.sleep(0.1)
    green_freq = read_color_frequency()
    
    # Read Blue
    GPIO.output(config.COLOR_S2, GPIO.LOW)
    GPIO.output(config.COLOR_S3, GPIO.HIGH)
    time.sleep(0.1)
    blue_freq = read_color_frequency()
    
    return red_freq, green_freq, blue_freq

if __name__ == "__main__":
    print("=" * 60)
    print("TCS3200 Color Sensor Test")
    print("=" * 60)
    print("Setting up TCS3200...")
    setup_tcs3200()
    
    print("Reading color values (Press Ctrl+C to stop)...")
    print("Place different colored objects in front of the sensor\n")
    
    try:
        while True:
            red, green, blue = read_rgb()
            print(f"R: {red:7.0f} Hz | G: {green:7.0f} Hz | B: {blue:7.0f} Hz")
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("\n\nColor sensor test stopped")
        GPIO.cleanup()
        print("GPIO cleaned up")
