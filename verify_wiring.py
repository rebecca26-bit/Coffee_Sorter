#!/usr/bin/env python3
"""Quick wiring verification"""

import RPi.GPIO as GPIO
import time
import config

print("\n" + "="*70)
print(" WIRING VERIFICATION")
print("="*70)

# Expected pins from config.py
print("\nPins defined in config.py:")
print(f"  S0  = GPIO {config.COLOR_S0}")
print(f"  S1  = GPIO {config.COLOR_S1}")
print(f"  S2  = GPIO {config.COLOR_S2}")
print(f"  S3  = GPIO {config.COLOR_S3}")
print(f"  OUT = GPIO {config.COLOR_OUT}")

GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

# Setup all pins
try:
    GPIO.setup(config.COLOR_S0, GPIO.OUT)
    GPIO.setup(config.COLOR_S1, GPIO.OUT)
    GPIO.setup(config.COLOR_S2, GPIO.OUT)
    GPIO.setup(config.COLOR_S3, GPIO.OUT)
    GPIO.setup(config.COLOR_OUT, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
    print("\n✓ All pins configured successfully")
except Exception as e:
    print(f"\n❌ Error configuring pins: {e}")
    GPIO.cleanup()
    exit(1)

# Test: Power on sensor with 20% frequency
print("\nTurning on sensor (20% frequency)...")
GPIO.output(config.COLOR_S0, GPIO.HIGH)
GPIO.output(config.COLOR_S1, GPIO.LOW)
GPIO.output(config.COLOR_S2, GPIO.HIGH)  # Clear filter
GPIO.output(config.COLOR_S3, GPIO.HIGH)

time.sleep(0.5)

print("\nLook at your TCS3200 sensor now:")
response = input("Are the 4 WHITE LEDs lit up? (y/n): ")

if response.lower() != 'y':
    print("\n❌ LEDs NOT LIT - POWER PROBLEM!")
    print("\nPossible causes:")
    print("1. VCC not connected to 3.3V or 5V")
    print("2. GND not connected")
    print("3. Loose wiring")
    GPIO.cleanup()
    exit(1)

print("\n✓ LEDs are on - power is OK")

# Test: Check if OUT pin is receiving signal
print("\nTesting OUT pin (GPIO {})...".format(config.COLOR_OUT))
print("Monitoring pin state for 3 seconds...")

states = []
for i in range(300):
    state = GPIO.input(config.COLOR_OUT)
    states.append(state)
    time.sleep(0.01)

zeros = states.count(0)
ones = states.count(1)

print(f"\nResults:")
print(f"  LOW (0):  {zeros} times ({zeros/3:.0f}%)")
print(f"  HIGH (1): {ones} times ({ones/3:.0f}%)")

if ones == 0:
    print("\n❌ OUT pin stuck at LOW")
    print("Possible causes:")
    print("1. OUT pin not connected")
    print("2. Wrong GPIO pin number in config.py")
    print("3. Sensor malfunction")
elif zeros == 0:
    print("\n❌ OUT pin stuck at HIGH")
    print("Possible causes:")
    print("1. Wiring issue")
    print("2. Sensor malfunction")
else:
    print("\n✓ OUT pin is toggling - sensor is working!")

GPIO.cleanup()
