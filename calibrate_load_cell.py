#!/usr/bin/env python3
"""
calibrate_load_cell.py
Calibrate the load cell with a known weight
This determines the reference unit for accurate readings
Usage: python3 calibrate_load_cell.py
"""

import RPi.GPIO as GPIO
import time
from hx711 import HX711
import config

if __name__ == "__main__":
    print("=" * 60)
    print("Load Cell Calibration")
    print("=" * 60)
    print("This will calibrate your load cell for accurate weight readings\n")
    
    # Setup GPIO for load cell pins (fixes KeyboardInterrupt)
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(config.LOADCELL_DT, GPIO.IN)
    GPIO.setup(config.LOADCELL_SCK, GPIO.OUT)
    GPIO.output(config.LOADCELL_SCK, GPIO.LOW)
    
    # Use config pins
    hx = HX711(config.LOADCELL_DT, config.LOADCELL_SCK)
    hx.reset()
    
    input("Remove all weight from sensor, then press Enter...")
    print("Taring...")
    hx.tare()
    print("Tare complete!\n")
    
    known_weight = float(input("Enter known weight in grams (e.g., 100): "))
    input(f"Place the {known_weight}g weight on sensor, then press Enter...")
    
    print("Reading... (this may take a few seconds)")
    # Manual averaging for older library
    readings = []
    for _ in range(20):
        readings.append(hx.get_weight())
        time.sleep(0.1)
    raw_value = sum(readings) / len(readings)
    
    reference_unit = raw_value / known_weight
    
    print("\n" + "=" * 60)
    print("CALIBRATION COMPLETE!")
    print("=" * 60)
    print(f"Reference Unit: {reference_unit:.2f}")
    print(f"\nIMPORTANT: Add this to config.py:")
    print(f"LOAD_SCALE = {reference_unit:.2f}")
    print("=" * 60 + "\n")
    
    # Test calibrated readings
    hx.set_reference_unit(reference_unit)
    print("Testing calibrated readings (10 samples)...\n")
    
    for i in range(10):
        # Manual averaging
        test_readings = []
        for _ in range(5):
            test_readings.append(hx.get_weight())
            time.sleep(0.1)
        weight = sum(test_readings) / len(test_readings)
        print(f"Reading {i+1}: {weight:6.2f} g")
        time.sleep(0.5)
    
    print("\nCalibration test complete!")
    GPIO.cleanup()
