#!/usr/bin/env python3
# test_load_cell.py - Test HX711 load cell (older library)
import RPi.GPIO as GPIO
from hx711 import HX711
import time
import config

print("=" * 50)
print("HX711 LOAD CELL TEST")
print("=" * 50)

# Setup
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

try:
    # Initialize HX711 (positional args)
    hx = HX711(config.LOADCELL_DT, config.LOADCELL_SCK)
    
    print("\nInitializing load cell...")
    hx.reset()
    time.sleep(1)
    
    print("✓ Load cell ready")
    print("\nREMOVE all weight from load cell")
    input("Press Enter when ready to zero (tare)...")
    
    # Tare
    hx.tare()
    print("✓ Zeroed (tared)")
    
    print("\nNow place objects on load cell")
    print("Weight in grams will be displayed")
    print("\nPress Ctrl+C to exit\n")
    
    while True:
        # Get weight (manual averaging and scaling)
        readings = []
        for _ in range(5):
            readings.append(hx.get_weight())  # No argument
            time.sleep(0.1)
        raw_value = sum(readings) / len(readings)
        weight = raw_value / config.LOAD_SCALE  # Manual scaling
        
        print(f"Weight: {weight:.2f}g  ", end='')
        
        # Rough indication
        if abs(weight) < 0.1:
            print("[Empty]")
        elif abs(weight) < 1:
            print("[Light object]")
        elif abs(weight) < 5:
            print("[Medium object]")
        else:
            print("[Heavy object]")
        
        time.sleep(0.5)
        
except KeyboardInterrupt:
    print("\n\nTest stopped")
    
except Exception as e:
    print(f"\n\nError: {e}")
    print("\nTroubleshooting:")
    print("- Check HX711 VCC and GND connections")
    print("- Verify DT and SCK connections (GPIO5 and GPIO6)")
    print("- Ensure load cell is connected to HX711")
    print("- Check all 4 load cell wires (E+, E-, A+, A-)")
    print("- Library issue: Confirm methods (e.g., try hx.power_up() if reset fails)")
    
finally:
    GPIO.cleanup()
