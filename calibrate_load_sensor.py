#!/usr/bin/env python3
"""
calibrate_load_cell.py
Calibrates HX711 load cell using older library version
With input validation, fixed get_weight calls, and manual scaling
"""

import RPi.GPIO as GPIO
from hx711 import HX711  # Older library (e.g., python-hx711)
import time
import config

print("=" * 70)
print("HX711 LOAD CELL CALIBRATION (OLDER LIBRARY)")
print("=" * 70)

# Setup
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

try:
    # Initialize HX711 (positional args for older library)
    hx = HX711(config.LOADCELL_DT, config.LOADCELL_SCK)
    
    print("\nInitializing load cell...")
    hx.reset()
    time.sleep(1)
    
    print("✓ Load cell ready")
    print("\nREMOVE all weight from load cell")
    input("Press Enter when ready to zero (tare)...")
    
    # Tare (may be hx.zero() in some versions; adjust if needed)
    hx.tare()
    print("✓ Zeroed (tared)")
    
    # Get known weight with validation
    while True:
        try:
            weight_input = input("Enter known weight in grams (e.g., 100): ").strip()
            if not weight_input:
                print("Input cannot be empty. Please enter a number.")
                continue
            known_weight = float(weight_input)
            if known_weight <= 0:
                print("Weight must be positive. Try again.")
                continue
            break
        except ValueError:
            print("Invalid input. Please enter a valid number (e.g., 100).")
    
    print(f"Place {known_weight}g on the load cell.")
    input("Press Enter when ready...")
    
    # Read weight with known load (manual averaging for older libraries)
    readings = []
    for _ in range(20):
        readings.append(hx.get_weight())  # No argument
        time.sleep(0.1)
    measured_weight = sum(readings) / len(readings)
    scale = measured_weight / known_weight
    print(f"Scale factor: {scale:.2f}")
    
    # Test reading (apply scale manually)
    print("\n>>> TEST READING")
    print("Keep the known weight on the load cell.")
    input("Press Enter to test...")
    test_readings = []
    for _ in range(10):
        test_readings.append(hx.get_weight())
        time.sleep(0.1)
    test_raw = sum(test_readings) / len(test_readings)
    test_weight = test_raw / scale  # Manual scaling
    print(f"Test weight: {test_weight:.2f}g (should be ~{known_weight}g)")
    
    # Save to config
    print("\n" + "=" * 70)
    print("CALIBRATION COMPLETE!")
    print("=" * 70)
    print("\nAdd these to config.py:")
    print(f"LOAD_SCALE = {scale:.2f}")
    print("# Tare is handled by hx.tare() in code")
    print("# Scale is applied manually in readings: weight = raw / LOAD_SCALE")
    
    # Optional: Save to file
    with open("../data/load_calibration.txt", 'w') as f:
        f.write(f"scale={scale:.2f}\n")

except Exception as e:
    print(f"\n\nError: {e}")
    print("\nTroubleshooting:")
    print("- Check HX711 VCC and GND connections")
    print("- Verify DT and SCK connections")
    print("- Ensure load cell is connected")
    print("- Check library version: pip install python-hx711")
    print("- If methods differ (e.g., no tare), use hx.zero() or manual offset")

finally:
    GPIO.cleanup()
