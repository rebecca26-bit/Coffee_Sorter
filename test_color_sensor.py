#!/usr/bin/env python3
"""
test_color_sensor.py
Tests TCS3200 color sensor using calibrated values
Classifies samples as good/bad coffee beans or unknown
"""

import RPi.GPIO as GPIO
import time
import config
import json

print("=" * 70)
print("TCS3200 COLOR SENSOR TEST")
print("=" * 70)

# Setup GPIO
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)
GPIO.setup(config.COLOR_S0, GPIO.OUT)
GPIO.setup(config.COLOR_S1, GPIO.OUT)
GPIO.setup(config.COLOR_S2, GPIO.OUT)
GPIO.setup(config.COLOR_S3, GPIO.OUT)
GPIO.setup(config.COLOR_OUT, GPIO.IN, pull_up_down=GPIO.PUD_UP)

# Set frequency scaling to 20% (matches calibration)
GPIO.output(config.COLOR_S0, GPIO.HIGH)
GPIO.output(config.COLOR_S1, GPIO.LOW)

def count_pulses(duration=0.5):
    """
    Count frequency pulses from color sensor
    
    Args:
        duration: How long to count (seconds)
    
    Returns:
        Frequency in Hz
    """
    start_time = time.time()
    pulses = 0
    
    while (time.time() - start_time) < duration:
        if GPIO.input(config.COLOR_OUT) == GPIO.LOW:
            pulses += 1
            # Wait for pulse to go high again
            while GPIO.input(config.COLOR_OUT) == GPIO.LOW:
                pass
    
    frequency = int(pulses / duration)
    return frequency

def read_color():
    """
    Read RGB frequencies once
    
    Returns:
        Tuple of (red, green, blue) frequencies
    """
    # Red filter
    GPIO.output(config.COLOR_S2, GPIO.LOW)
    GPIO.output(config.COLOR_S3, GPIO.LOW)
    time.sleep(0.1)
    red = count_pulses(0.5)
    
    # Green filter
    GPIO.output(config.COLOR_S2, GPIO.HIGH)
    GPIO.output(config.COLOR_S3, GPIO.HIGH)
    time.sleep(0.1)
    green = count_pulses(0.5)
    
    # Blue filter
    GPIO.output(config.COLOR_S2, GPIO.LOW)
    GPIO.output(config.COLOR_S3, GPIO.HIGH)
    time.sleep(0.1)
    blue = count_pulses(0.5)
    
    return red, green, blue

def classify_sample(r, g, b, threshold=30):
    """
    Classify sample based on calibrated thresholds with raw frequency fallback
    
    Args:
        r, g, b: RGB frequencies
        threshold: Distance threshold for classification
    
    Returns:
        Classification string
    """
    # Get calibrated values
    white = config.COLOR_CALIBRATION['white']
    black = config.COLOR_CALIBRATION['black']
    good_ref = config.COLOR_CALIBRATION['good_reference']
    bad_ref = config.COLOR_CALIBRATION['bad_reference']
    
    # Simple rule: If Green and Blue are high (based on bad bean calibration), classify as bad
    # Adjust these thresholds based on your bad_ref values (e.g., bad_ref['g'] + some margin)
    green_threshold = bad_ref['g'] * 0.8  # 80% of bad reference Green (tune as needed)
    blue_threshold = bad_ref['b'] * 0.8   # 80% of bad reference Blue
    if g > green_threshold and b > blue_threshold:
        return "BAD COFFEE BEAN"
    
    # Normalize readings (simple scaling to 0-100 based on white/black range)
    def normalize(value, min_val, max_val):
        if max_val - min_val == 0:
            return 0
        return max(0, min(100, (value - min_val) / (max_val - min_val) * 100))
    
    # Normalize current readings
    norm_r = normalize(r, black['r'], white['r'])
    norm_g = normalize(g, black['g'], white['g'])
    norm_b = normalize(b, black['b'], white['b'])
    
    # Normalize reference values for comparison
    norm_good_r = normalize(good_ref['r'], black['r'], white['r'])
    norm_good_g = normalize(good_ref['g'], black['g'], white['g'])
    norm_good_b = normalize(good_ref['b'], black['b'], white['b'])
    
    norm_bad_r = normalize(bad_ref['r'], black['r'], white['r'])
    norm_bad_g = normalize(bad_ref['g'], black['g'], white['g'])
    norm_bad_b = normalize(bad_ref['b'], black['b'], white['b'])
    
    # Calculate Euclidean distances to good and bad references
    dist_good = ((norm_r - norm_good_r)**2 + (norm_g - norm_good_g)**2 + (norm_b - norm_good_b)**2)**0.5
    dist_bad = ((norm_r - norm_bad_r)**2 + (norm_g - norm_bad_g)**2 + (norm_b - norm_bad_b)**2)**0.5
    
    if dist_good < threshold and dist_good < dist_bad:
        return "GOOD COFFEE BEAN"
    elif dist_bad < threshold and dist_bad < dist_good:
        return "BAD COFFEE BEAN"
    else:
        return "UNKNOWN SAMPLE"

                               

def display_reading(r, g, b, classification):
    """Display current reading and classification"""
    print(f"\nCurrent Reading:")
    print(f"  Red:   {r:5d} Hz")
    print(f"  Green: {g:5d} Hz")
    print(f"  Blue:  {b:5d} Hz")
    print(f"  Classification: {classification}")
    print("-" * 70)

# ============= TEST LOOP =============

print("\nTesting color sensor with calibrated values...")
print("Place samples under sensor and observe classifications.")
print("Press Ctrl+C to stop.\n")

try:
    while True:
        input("Place sample under sensor and press Enter to read...")  # Wait prompt
        r, g, b = read_color()
        classification = classify_sample(r, g, b)
        display_reading(r, g, b, classification)

except KeyboardInterrupt:
    print("\n\nTest stopped by user")

except Exception as e:
    print(f"\n\nError during test: {e}")
    import traceback
    traceback.print_exc()

finally:
    GPIO.cleanup()
