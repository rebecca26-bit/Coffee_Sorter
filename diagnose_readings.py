#!/usr/bin/env python3
"""
Diagnostic Script - Shows Raw Sensor Values
Helps determine proper thresholds for classification
"""

import RPi.GPIO as GPIO
from hx711 import HX711
import time
import json
from pathlib import Path
import config

print("=" * 70)
print(" SENSOR DIAGNOSTIC - RAW VALUES")
print("=" * 70)

# Setup GPIO
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

# Setup color sensor
GPIO.setup(config.COLOR_S0, GPIO.OUT)
GPIO.setup(config.COLOR_S1, GPIO.OUT)
GPIO.setup(config.COLOR_S2, GPIO.OUT)
GPIO.setup(config.COLOR_S3, GPIO.OUT)
GPIO.setup(config.COLOR_OUT, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.output(config.COLOR_S0, GPIO.LOW)
GPIO.output(config.COLOR_S1, GPIO.HIGH)

# Setup load cell
#hx = HX711(dout_pin=config.LOADCELL_DT, pd_sck_pin=config.LOADCELL_SCK)
#hx.reset()
#time.sleep(0.5)
#hx.set_scale_ratio(config.LOADCELL_CALIBRATION_FACTOR)
#hx.tare()

def count_pulses(duration=0.5):
    """Count frequency pulses"""
    start_time = time.time()
    pulses = 0
    while (time.time() - start_time) < duration:
        if GPIO.input(config.COLOR_OUT) == GPIO.LOW:
            pulses += 1
            while GPIO.input(config.COLOR_OUT) == GPIO.LOW:
                pass
    return int(pulses / duration)

def read_color():
    """Read RGB values"""
    GPIO.output(config.COLOR_S2, GPIO.LOW)
    GPIO.output(config.COLOR_S3, GPIO.LOW)
    time.sleep(0.05)
    red = count_pulses(0.3)
    
    GPIO.output(config.COLOR_S2, GPIO.HIGH)
    GPIO.output(config.COLOR_S3, GPIO.HIGH)
    time.sleep(0.05)
    green = count_pulses(0.3)
    
    GPIO.output(config.COLOR_S2, GPIO.LOW)
    GPIO.output(config.COLOR_S3, GPIO.HIGH)
    time.sleep(0.05)
    blue = count_pulses(0.3)
    
    return red, green, blue

#def read_weight():
    """Read weight"""
 #   weight = hx.get_weight_mean(5)
  #  return weight if weight is not False else 0.0

# Load calibration if exists
cal_file = Path('../data/color_calibration.json')
if cal_file.exists():
    with open(cal_file, 'r') as f:
        calibration = json.load(f)
    
    good_avg = sum(calibration['good_beans']['mean'].values()) / 3
    bad_avg = sum(calibration['bad_beans']['mean'].values()) / 3
    threshold = (good_avg + bad_avg) / 2
    
    print(f"\n📊 Your Calibration Data:")
    print(f"  Good beans average RGB sum: {int(good_avg)}")
    print(f"  Bad beans average RGB sum:  {int(bad_avg)}")
    print(f"  Current threshold:          {int(threshold)}")
else:
    print("\n⚠️  No calibration file found")
    threshold = 500

print("\n" + "=" * 70)
print(" TESTING INSTRUCTIONS")
print("=" * 70)
print("\n1. Test several GOOD beans")
print("2. Test several BAD beans (dark, green, defects)")
print("3. Look at the RGB Sum values")
print("4. We'll suggest new thresholds based on results")
print("\nPress Ctrl+C when done\n")

samples = {
    'good': [],
    'bad': []
}

try:
    sample_num = 0
    
    while True:
        sample_num += 1
        
        # Get bean type
        print(f"\n{'=' * 70}")
        print(f"SAMPLE #{sample_num}")
        bean_type = input("Place bean and enter type (g=good, b=bad, s=skip): ").lower().strip()
        
        if bean_type == 's':
            continue
        
        if bean_type not in ['g', 'b']:
            print("Invalid input! Use 'g', 'b', or 's'")
            continue
        
        # Read sensors
        print("Reading...", end='', flush=True)
        red, green, blue = read_color()
   #     weight = read_weight()
        rgb_sum = red + green + blue
        print(" Done!")
        
        # Display results
        print(f"\n  Red:     {red:4d}")
        print(f"  Green:   {green:4d}")
        print(f"  Blue:    {blue:4d}")
        print(f"  RGB Sum: {rgb_sum:4d}  ", end='')
        
        # Compare to threshold
        if rgb_sum > threshold:
            print(f"[Would classify as GOOD]")
        else:
            print(f"[Would classify as BAD]")
        
    #    print(f"  Weight:  {weight:.3f}g")
        
        # Store sample
        category = 'good' if bean_type == 'g' else 'bad'
        samples[category].append({
            'red': red,
            'green': green,
            'blue': blue,
            'rgb_sum': rgb_sum,
     #       'weight': weight
        })
        
        # Show running statistics
        if samples['good']:
            good_avg_sum = sum(s['rgb_sum'] for s in samples['good']) / len(samples['good'])
            print(f"\n  📊 Good beans tested: {len(samples['good'])} (avg RGB: {good_avg_sum:.0f})")
        
        if samples['bad']:
            bad_avg_sum = sum(s['rgb_sum'] for s in samples['bad']) / len(samples['bad'])
            print(f"  📊 Bad beans tested:  {len(samples['bad'])} (avg RGB: {bad_avg_sum:.0f})")

except KeyboardInterrupt:
    print("\n\n" + "=" * 70)
    print(" ANALYSIS RESULTS")
    print("=" * 70)
    
    if not samples['good'] and not samples['bad']:
        print("\nNo samples collected!")
    else:
        # Analyze good beans
        if samples['good']:
            good_rgb_sums = [s['rgb_sum'] for s in samples['good']]
         #   good_weights = [s['weight'] for s in samples['good']]
            
            print(f"\n✅ GOOD BEANS ({len(samples['good'])} samples):")
            print(f"  RGB Sum - Min: {min(good_rgb_sums)}, Max: {max(good_rgb_sums)}, Avg: {sum(good_rgb_sums)/len(good_rgb_sums):.0f}")
          #  print(f"  Weight  - Min: {min(good_weights):.3f}g, Max: {max(good_weights):.3f}g, Avg: {sum(good_weights)/len(good_weights):.3f}g")
        
        # Analyze bad beans
        if samples['bad']:
            bad_rgb_sums = [s['rgb_sum'] for s in samples['bad']]
           # bad_weights = [s['weight'] for s in samples['bad']]
            
            print(f"\n❌ BAD BEANS ({len(samples['bad'])} samples):")
            print(f"  RGB Sum - Min: {min(bad_rgb_sums)}, Max: {max(bad_rgb_sums)}, Avg: {sum(bad_rgb_sums)/len(bad_rgb_sums):.0f}")
           # print(f"  Weight  - Min: {min(bad_weights):.3f}g, Max: {max(bad_weights):.3f}g, Avg: {sum(bad_weights)/len(bad_weights):.3f}g")
        
        # Calculate recommended thresholds
        if samples['good'] and samples['bad']:
            good_avg = sum(good_rgb_sums) / len(good_rgb_sums)
            bad_avg = sum(bad_rgb_sums) / len(bad_rgb_sums)
            
            print("\n" + "=" * 70)
            print(" RECOMMENDED THRESHOLDS")
            print("=" * 70)
            
            # Check if there's overlap
            if min(good_rgb_sums) <= max(bad_rgb_sums):
                print("\n⚠️  WARNING: Overlap detected!")
                print(f"  Some good beans have lower RGB than some bad beans")
                print(f"  Good min: {min(good_rgb_sums)}, Bad max: {max(bad_rgb_sums)}")
                print(f"  This will cause misclassification!")
                
                # Suggest stricter threshold
                new_threshold = (min(good_rgb_sums) + max(bad_rgb_sums)) / 2
                print(f"\n  Compromise threshold: {new_threshold:.0f}")
            else:
                # No overlap - calculate optimal threshold
                new_threshold = (good_avg + bad_avg) / 2
                print(f"\n✓ No overlap - clean separation possible!")
                print(f"  Recommended RGB threshold: {new_threshold:.0f}")
            
            print(f"\n  Current threshold:  {threshold:.0f}")
            print(f"  Suggested threshold: {new_threshold:.0f}")
            
            # Weight thresholds
           # if good_weights and bad_weights:
            #    good_weight_avg = sum(good_weights) / len(good_weights)
             #   bad_weight_avg = sum(bad_weights) / len(bad_weights)
                
              #  print(f"\n  Weight range:")
               # print(f"    Good: {min(good_weights):.3f}g - {max(good_weights):.3f}g")
               # print(f"    Bad:  {min(bad_weights):.3f}g - {max(bad_weights):.3f}g")
            
            # Generate fix code
            print("\n" + "=" * 70)
            print(" HOW TO FIX")
            print("=" * 70)
            print(f"\nEdit coffee_sorter_simple.py and update the classify_bean method:")
            print(f"\nChange this line:")
            print(f"  self.color_threshold = {threshold:.0f}")
            print(f"\nTo this:")
            print(f"  self.color_threshold = {new_threshold:.0f}")
            
            print(f"\nOR manually adjust in the code:")
            print(f"  nano coffee_sorter_simple.py")
            print(f"  Find: self.color_threshold = ")
            print(f"  Change to: self.color_threshold = {new_threshold:.0f}")

finally:
    GPIO.cleanup()
    print("\n✓ Diagnostic complete")
