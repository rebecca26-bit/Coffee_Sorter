import RPi.GPIO as GPIO
import time

PIN = 4

GPIO.setmode(GPIO.BCM)
GPIO.setup(PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)

print("IR Test: Block/unblock the sensor.")

try:
    while True:
        print("IR:", GPIO.input(PIN))
        time.sleep(0.2)

except KeyboardInterrupt:
    GPIO.cleanup()

