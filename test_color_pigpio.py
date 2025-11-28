#!/usr/bin/env python3
# test_color_pigpio.py - Using pigpio for better timing
import pigpio
import time
import config

print("TCS3200 Test using pigpio library")
print("=" * 50)

# Connect to pigpio daemon
pi = pigpio.pi()

if not pi.connected:
    print("ERROR: pigpio daemon not running")
    print("Start with: sudo pigpiod")
    exit()

# Setup pins
pi.set_mode(config.COLOR_S0, pigpio.OUTPUT)
pi.set_mode(config.COLOR_S1, pigpio.OUTPUT)
pi.set_mode(config.COLOR_S2, pigpio.OUTPUT)
pi.set_mode(config.COLOR_S3, pigpio.OUTPUT)
pi.set_mode(config.COLOR_OUT, pigpio.INPUT)

# Set frequency to 20%
pi.write(config.COLOR_S0, 1)
pi.write(config.COLOR_S1, 0)

def read_color_pigpio(color):
    """Read color using pigpio"""
    # Set filter
    if color == 'red':
        pi.write(config.COLOR_S2, 0)
        pi.write(config.COLOR_S3, 0)
    elif color == 'green':
        pi.write(config.COLOR_S2, 1)
        pi.write(config.COLOR_S3, 1)
    elif color == 'blue':
        pi.write(config.COLOR_S2, 0)
        pi.write(config.COLOR_S3, 1)
    
    time.sleep(0.1)  # Settle time
    
    # Count frequency using pigpio
    # Read for 100ms
    pi.set_glitch_filter(config.COLOR_OUT, 1000)  # 1us glitch filter
    
    count = 0
    start = time.time()
    last_tick = pi.read(config.COLOR_OUT)
    
    while (time.time() - start) < 0.5:
        current_tick = pi.read(config.COLOR_OUT)
        if current_tick == 1 and last_tick == 0:
            count += 1
        last_tick = current_tick
    
    freq = int(count / 0.5)
    return freq

try:
    print("\nReading colors...\n")
    
    while True:
        r = read_color_pigpio('red')
        g = read_color_pigpio('green')
        b = read_color_pigpio('blue')
        
        print(f"R:{r:5d}  G:{g:5d}  B:{b:5d}")
        time.sleep(1)
        
except KeyboardInterrupt:
    print("\nStopped")
    pi.stop()
