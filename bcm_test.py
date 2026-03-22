import RPi.GPIO as GPIO
import time

# Use the GPIO labels (BCM)
IN1 = 5  # Physical Pin 29
IN2 = 6  # Physical Pin 31

GPIO.setmode(GPIO.BCM) 
GPIO.setup([IN1, IN2], GPIO.OUT)

try:
    print("--- TESTING GPIO 5 & 6 ---")
    print("Setting GPIO 5 (IN1) HIGH...")
    GPIO.output(IN1, GPIO.HIGH)
    
    print("Setting GPIO 6 (IN2) LOW...")
    GPIO.output(IN2, GPIO.LOW)
    
    print("\nSUCCESS: Check the tiny LEDs behind the IN1/IN2 pins.")
    print("If they are ON, your motor should be spinning.")
    
    time.sleep(10)
    
except KeyboardInterrupt:
    print("\nStopped.")
finally:
    GPIO.cleanup()
