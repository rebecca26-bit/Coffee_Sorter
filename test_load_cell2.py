#!/usr/bin/env python3
"""
test_load_cell.py
Test the HX711 load cell amplifier to verify weight readings
Requires: pip3 install hx711 (older version: python-hx711)
Usage: python3 test_load_cell.py
"""

import RPi.GPIO as GPIO
import time
from hx711 import HX711
import config

if __name__ == "__main__":
    print("=" * 60)
    print("HX711 Load Cell Test")
    print("=" * 60)
    print("Setting up HX711 Load Cell...")
    
    # Use config pins (older library)
    hx = HX711(config.LOADCELL_DT, config.LOADCELL_SCK)
    
    # Reset and tare
    hx.reset()
    print("Resetting load cell...")
    time.sleep(1)
    
    # Tare (zero) the scale
    print("Taring... (Remove all weight from sensor)")
    time.sleep(2)
    hx.tare()
    print("Tare complete!\n")
    
    # Set reference unit (calibration factor from config if available)
    try:
        hx.set_reference_unit(config.LOAD_SCALE)
        print(f"Using calibrated scale: {config.LOAD_SCALE}")
    except AttributeError:
        print("Warning: LOAD_SCALE not found in config.py. Using default 1.")
        hx.set_reference_unit(1)
    
    print("Reading weight values (Press Ctrl+C to stop)...")
    print("Place objects on the load cell to test\n")
    
    try:
        while True:
            # Get weight reading (manual averaging for older library)
            readings = []
            for _ in range(5):
                readings.append(hx.get_weight())  # Use get_weight() instead of get_weight_mean()
                time.sleep(0.1)
            weight = sum(readings) / len(readings)
            print(f"Weight: {weight:8.2f} g")
            time.sleep(0.5)
            
    except KeyboardInterrupt:
        print("\n\nLoad cell test stopped")
        GPIO.cleanup()
        print("GPIO cleaned up")
