#!/usr/bin/env python3
"""
collect_training_data.py
Collect labeled data for machine learning training
Saves data to CSV file for model training
Usage: python3 collect_training_data.py
"""

import RPi.GPIO as GPIO
import time
from hx711 import HX711
import csv
from datetime import datetime
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
    print("Training Data Collection")
    print("=" * 60)
    print("Setting up sensors...")
    
    # Setup sensors
    setup_tcs3200()
    hx = HX711(config.LOADCELL_DT, config.LOADCELL_SCK)
    hx.reset()
    print("Taring load cell...")
    hx.tare()
    try:
        hx.set_reference_unit(config.LOAD_SCALE)
    except AttributeError:
        print("Warning: LOAD_SCALE not in config.py. Using default 1.")
        hx.set_reference_unit(1)
    
    # Create CSV file with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"coffee_training_data_{timestamp}.csv"
    
    print(f"\nData will be saved to: {filename}")
    print("For each bean, enter quality: 'good' or 'bad'")
    print("Press Ctrl+C when done\n")
    
    with open(filename, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['Red', 'Green', 'Blue', 'Weight', 'Quality'])
        
        bean_count = 0
        
        try:
            while True:
                input(f"Bean #{bean_count + 1} - Place bean and press Enter...")
                
                # Read sensors
                red, green, blue = read_rgb()
                
                # Read weight (manual averaging)
                weight_readings = []
                for _ in range(10):
                    weight_readings.append(hx.get_weight())
                    time.sleep(0.1)
                weight = sum(weight_readings) / len(weight_readings)
                
                print(f"  Color  - R: {red:6.0f}, G: {green:6.0f}, B: {blue:6.0f}")
                print(f"  Weight - {weight:6.2f} g")
                
                # Get label
                quality = input("  Quality (good/bad): ").strip().lower()
                
                while quality not in ['good', 'bad']:
                    quality = input("  Please enter 'good' or 'bad': ").strip().lower()
                
                # Save to CSV
                writer.writerow([red, green, blue, weight, quality])
                csvfile.flush()  # Save immediately
                
                bean_count += 1
                print(f"  ✓ Saved! Total beans: {bean_count}\n")
                
        except KeyboardInterrupt:
            print(f"\n\n" + "=" * 60)
            print("DATA COLLECTION COMPLETE!")
            print("=" * 60)
            print(f"Total samples collected: {bean_count}")
            print(f"Data saved to: {filename}")
            print("=" * 60)
            GPIO.cleanup()
            print("GPIO cleaned up")
