import RPi.GPIO as GPIO
import time

# Use PHYSICAL pin numbers
# GPIO 5  = Physical Pin 29
# GPIO 6  = Physical Pin 31
# GPIO 13 = Physical Pin 33 (ENA)
IN1 = 29 
IN2 = 31
ENA = 33

GPIO.setmode(GPIO.BOARD) 
GPIO.setup([IN1, IN2, ENA], GPIO.OUT)

try:
    print("--- HARDWARE FORCE TEST ---")
    print(f"Setting Pin {IN1} (IN1) HIGH")
    GPIO.output(IN1, GPIO.HIGH)
    
    print(f"Setting Pin {IN2} (IN2) LOW")
    GPIO.output(IN2, GPIO.LOW)
    
    print(f"Setting Pin {ENA} (ENA) HIGH")
    GPIO.output(ENA, GPIO.HIGH) # Full power
    
    print("\nSUCCESS: Pins are now LIVE. Check the L298N LEDs.")
    print("The motor should be spinning. Press Ctrl+C to stop.")
    
    # Keep it on for 10 seconds to give you time to check wires
    time.sleep(10)
    
except KeyboardInterrupt:
    print("\nStopped by user.")
finally:
    print("Cleaning up GPIO pins.")
    GPIO.cleanup()
