import RPi.GPIO as GPIO
import time

RELAY_PIN = 13

GPIO.setmode(GPIO.BCM)
GPIO.setup(RELAY_PIN, GPIO.OUT)

print("Testing relay...")

try:
    while True:
        print("Relay ON")
        GPIO.output(RELAY_PIN, GPIO.HIGH)
        time.sleep(2)
        print("Relay OFF")
        GPIO.output(RELAY_PIN, GPIO.LOW)
        time.sleep(2)
except KeyboardInterrupt:
    GPIO.cleanup()
