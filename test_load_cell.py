#!/usr/bin/env python3
# test_load_cell.py - Test HX711 load cell
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
    # Initialize HX711
    hx = HX711(dout_pin=config.LOADCELL_DT, pd_sck_pin=config.LOADCELL_SCK)
    
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
    print("Raw values will be displayed")
    print("(Calibration needed for actual grams)")
    print("\nPress Ctrl+C to exit\n")
    
    while True:
        # Get raw value
        raw_value = hx.get_raw_data_mean(5)
        
        if raw_value is not False:
            print(f"Raw weight: {raw_value:8d}  ", end='')
            
            # Rough indication
            if abs(raw_value) < 100:
                print("[Empty]")
            elif abs(raw_value) < 1000:
                print("[Light object]")
            elif abs(raw_value) < 5000:
                print("[Medium object]")
            else:
                print("[Heavy object]")
        else:
            print("Error reading sensor")
        
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
    
finally:
    GPIO.cleanup()
