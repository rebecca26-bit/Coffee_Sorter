#!/usr/bin/env python3
"""
calibrate_color_sensor.py
Calibrates TCS3200 color sensor for coffee bean sorting
Establishes baseline values for white, black, and coffee beans
"""

import RPi.GPIO as GPIO
import time
import config
import json
from datetime import datetime

print("=" * 70)
print("TCS3200 COLOR SENSOR CALIBRATION")
print("=" * 70)

# Setup GPIO
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)
GPIO.setup(config.COLOR_S0, GPIO.OUT)
GPIO.setup(config.COLOR_S1, GPIO.OUT)
GPIO.setup(config.COLOR_S2, GPIO.OUT)
GPIO.setup(config.COLOR_S3, GPIO.OUT)
GPIO.setup(config.COLOR_OUT, GPIO.IN, pull_up_down=GPIO.PUD_UP)

# Set frequency scaling to 20% (more stable readings)
GPIO.output(config.COLOR_S0, GPIO.HIGH)
GPIO.output(config.COLOR_S1, GPIO.LOW)

def count_pulses(duration=1.0):
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

def read_color_multiple(num_readings=5):
      red_readings = []
      green_readings = []
      blue_readings = []
      
      for i in range(num_readings):
          # Red filter
          GPIO.output(config.COLOR_S2, GPIO.LOW)
          GPIO.output(config.COLOR_S3, GPIO.LOW)
          time.sleep(0.1)
          red_readings.append(count_pulses(0.5))
          
          # Green filter
          GPIO.output(config.COLOR_S2, GPIO.HIGH)
          GPIO.output(config.COLOR_S3, GPIO.HIGH)
          time.sleep(0.1)
          green_readings.append(count_pulses(0.5))
          
          # Blue filter
          GPIO.output(config.COLOR_S2, GPIO.LOW)
          GPIO.output(config.COLOR_S3, GPIO.HIGH)
          time.sleep(0.1)
          blue_readings.append(count_pulses(0.5))
          
          print(f"  Reading {i+1}/{num_readings} complete...", end='\r')
      
      # Calculate averages (already present, no change needed)
      avg_red = int(sum(red_readings) / len(red_readings))
      avg_green = int(sum(green_readings) / len(green_readings))
      avg_blue = int(sum(blue_readings) / len(blue_readings))
      
      print()
      
      return avg_red, avg_green, avg_blue
  
            
   
                                                                                  
def display_color_values(label, r, g, b):
    """Display color values in formatted way"""
    print(f"\n{label}:")
    print(f"  Red:   {r:5d} Hz")
    print(f"  Green: {g:5d} Hz")
    print(f"  Blue:  {b:5d} Hz")
    
    # Show dominant color
    if r > g and r > b:
        print(f"  Dominant: RED")
    elif g > r and g > b:
        print(f"  Dominant: GREEN")
    elif b > r and b > g:
        print(f"  Dominant: BLUE")
    else:
        print(f"  Dominant: BALANCED")

# ============= CALIBRATION PROCEDURE =============

print("\nThis calibration will establish baseline values for:")
print("  1. White reference (maximum reflection)")
print("  2. Black reference (minimum reflection)")
print("  3. Good coffee bean (quality reference)")
print("  4. Defective coffee bean (defect reference)")
print("\nIMPORTANT:")
print("  • Keep lighting consistent throughout calibration")
print("  • Place sensor ~10mm above each sample")
print("  • Keep samples flat and stable")
print("  • Avoid shadows on samples")
print("\n" + "=" * 70)

calibration_data = {
    'timestamp': datetime.now().isoformat(),
    'frequency_scale': '20%',
    'readings': {}
}

try:
    # WHITE REFERENCE
    print("\n>>> STEP 1: WHITE REFERENCE")
    print("Place clean WHITE paper/cardboard under sensor")
    print("Position sensor about 10mm above the surface")
    input("Press Enter when ready...")
    
    print("Reading white reference (5 samples)...")
    white_r, white_g, white_b = read_color_multiple(5)
    display_color_values("White Reference", white_r, white_g, white_b)
    
    calibration_data['readings']['white'] = {
        'red': white_r,
        'green': white_g,
        'blue': white_b
    }
    
    # BLACK REFERENCE
    print("\n>>> STEP 2: BLACK REFERENCE")
    print("Place MATTE BLACK paper/cardboard under sensor")
    print("(Avoid glossy black - use flat black)")
    input("Press Enter when ready...")
    
    print("Reading black reference (5 samples)...")
    black_r, black_g, black_b = read_color_multiple(5)
    display_color_values("Black Reference", black_r, black_g, black_b)
    
    calibration_data['readings']['black'] = {
        'red': black_r,
        'green': black_g,
        'blue': black_b
    }
    
    # Calculate dynamic range
    print("\n" + "-" * 70)
    print("DYNAMIC RANGE ANALYSIS:")
    print(f"  Red range:   {white_r - black_r:5d} Hz  ({white_r} - {black_r})")
    print(f"  Green range: {white_g - black_g:5d} Hz  ({white_g} - {black_g})")
    print(f"  Blue range:  {white_b - black_b:5d} Hz  ({white_b} - {black_b})")
    print("-" * 70)
    
    # GOOD COFFEE BEAN
    print("\n>>> STEP 3: GOOD COFFEE BEAN")
    print("Place a GOOD QUALITY coffee bean under sensor")
    print("Characteristics: uniform color, no defects, proper size")
    input("Press Enter when ready...")
    
    print("Reading good bean (5 samples)...")
    good_r, good_g, good_b = read_color_multiple(5)
    display_color_values("Good Coffee Bean", good_r, good_g, good_b)
    
    calibration_data['readings']['good_bean'] = {
        'red': good_r,
        'green': good_g,
        'blue': good_b
    }
    
    # DEFECTIVE COFFEE BEAN
    print("\n>>> STEP 4: DEFECTIVE COFFEE BEAN")
    print("Place a DEFECTIVE coffee bean under sensor")
    print("Characteristics: discolored, broken, insect damage, mold")
    input("Press Enter when ready...")
    
    print("Reading defective bean (5 samples)...")
    bad_r, bad_g, bad_b = read_color_multiple(5)
    display_color_values("Defective Coffee Bean", bad_r, bad_g, bad_b)
    
    calibration_data['readings']['bad_bean'] = {
        'red': bad_r,
        'green': bad_g,
        'blue': bad_b
    }
    
    # ============= CALIBRATION SUMMARY =============
    
    print("\n" + "=" * 70)
    print("CALIBRATION COMPLETE!")
    print("=" * 70)
    
    print("\n>>> CALIBRATION SUMMARY:")
    print("\nReference Values:")
    print(f"  White:  R={white_r:5d}  G={white_g:5d}  B={white_b:5d}")
    print(f"  Black:  R={black_r:5d}  G={black_g:5d}  B={black_b:5d}")
    
    print("\nCoffee Bean Values:")
    print(f"  Good:   R={good_r:5d}  G={good_g:5d}  B={good_b:5d}")
    print(f"  Bad:    R={bad_r:5d}  G={bad_g:5d}  B={bad_b:5d}")
    
    print("\nColor Difference Analysis:")
    diff_r = abs(good_r - bad_r)
    diff_g = abs(good_g - bad_g)
    diff_b = abs(good_b - bad_b)
    
    print(f"  Red difference:   {diff_r:5d} Hz")
    print(f"  Green difference: {diff_g:5d} Hz")
    print(f"  Blue difference:  {diff_b:5d} Hz")
    
    # Calculate separability score
    total_diff = diff_r + diff_g + diff_b
    avg_range = (white_r - black_r + white_g - black_g + white_b - black_b) / 3
    separability = (total_diff / avg_range) * 100
    
    print(f"\nSeparability Score: {separability:.1f}%")
    if separability > 20:
        print("  ✓ EXCELLENT - Good and bad beans are easily distinguishable")
    elif separability > 10:
        print("  ✓ GOOD - Beans can be distinguished with ML")
    else:
        print("  ⚠ LOW - May need more distinct defect samples")
    
    # Save calibration data
    filename = f"../data/color_calibration_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(filename, 'w') as f:
        json.dump(calibration_data, f, indent=4)
    
    print(f"\n✓ Calibration data saved to: {filename}")
    
    # Update config file suggestion
    print("\n" + "=" * 70)
    print("RECOMMENDED CONFIG.PY UPDATE:")
    print("=" * 70)
    print("\nAdd these values to your config.py file:\n")
    print("COLOR_CALIBRATION = {")
    print(f"    'white': {{'r': {white_r}, 'g': {white_g}, 'b': {white_b}}},")
    print(f"    'black': {{'r': {black_r}, 'g': {black_g}, 'b': {black_b}}},")
    print(f"    'good_reference': {{'r': {good_r}, 'g': {good_g}, 'b': {good_b}}},")
    print(f"    'bad_reference': {{'r': {bad_r}, 'g': {bad_g}, 'b': {bad_b}}}")
    print("}")
    
    print("\n" + "=" * 70)
    print("Next step: Calibrate load cell with 'calibrate_load_cell.py'")
    print("=" * 70)

except KeyboardInterrupt:
    print("\n\nCalibration interrupted by user")

except Exception as e:
    print(f"\n\nError during calibration: {e}")
    import traceback
    traceback.print_exc()

finally:
    GPIO.cleanup()
