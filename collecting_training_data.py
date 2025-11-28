#!/usr/bin/env python3
"""
collect_training_data.py
Collect training data for ML model
"""

import RPi.GPIO as GPIO
from hx711 import HX711
import time
import config
import csv

# Color sensor functions (same as sorter)
def count_pulses(duration=0.05):
    start_time = time.time()
    pulses = 0
    while (time.time() - start_time) < duration:
        if GPIO.input(config.COLOR_OUT) == GPIO.LOW:
            pulses += 1
            while GPIO.input(config.COLOR_OUT) == GPIO.LOW:
                pass
    return int(pulses / duration)

def read_color():
    GPIO.output(config.COLOR_S2, GPIO.LOW)
    GPIO.output(config.COLOR_S3, GPIO.LOW)
    time.sleep(0.1)
    red = count_pulses()
    GPIO.output(config.COLOR_S2, GPIO.HIGH)
    GPIO.output(config.COLOR_S3, GPIO.HIGH)
    time.sleep(0.1)
    green = count_pulses()
    GPIO.output(config.COLOR_S2, GPIO.LOW)
    GPIO.output(config.COLOR_S3, GPIO.HIGH)
    time.sleep(0.1)
    blue = count_pulses()
    return red, green, blue

def get_weight(hx, samples=5):
    readings = []
    for _ in range(samples):
        readings.append(hx.get_weight())
        time.sleep(0.1)
    raw = sum(readings) / len(readings)
    return raw / config.LOAD_SCALE

# Setup GPIO and sensors
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)
GPIO.setup(config.COLOR_S0, GPIO.OUT)
GPIO.setup(config.COLOR_S1, GPIO.OUT)
GPIO.setup(config.COLOR_S2, GPIO.OUT)
GPIO.setup(config.COLOR_S3, GPIO.OUT)
GPIO.setup(config.COLOR_OUT, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.output(config.COLOR_S0, GPIO.HIGH)
GPIO.output(config.COLOR_S1, GPIO.LOW)

hx = HX711(config.LOADCELL_DT, config.LOADCELL_SCK)
hx.reset()
time.sleep(1)
hx.tare()

print("Collecting training data. Press Ctrl+C to stop.")
print("For each bean: Place it, press Enter, then enter label (1=good, 0=bad).")

with open('training_data.csv', 'w', newline='') as file:
    writer = csv.writer(file)
    writer.writerow(['r', 'g', 'b', 'weight', 'label'])
    
    try:
        while True:
            input("Place bean and press Enter...")
            r, g, b = read_color()
            weight = get_weight(hx)
            label = int(input("Label (1=good, 0=bad): "))
            writer.writerow([r, g, b, weight, label])
            print(f"Logged: R={r}, G={g}, B={b}, Weight={weight:.2f}, Label={label}")
    except KeyboardInterrupt:
        print("Data collection stopped.")

GPIO.cleanup()
