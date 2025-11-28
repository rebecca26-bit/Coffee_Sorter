import RPi.GPIO as GPIO
import time

IR_PIN = 4
INDUCTIVE_PIN = 12

GPIO.setmode(GPIO.BCM)
GPIO.setup(IR_PIN, GPIO.IN)
GPIO.setup(INDUCTIVE_PIN, GPIO.IN)

print("Testing proximity sensors... (Press CTRL+C to stop)")

try:
    while True:
        ir_val = GPIO.input(IR_PIN)
        ind_val = GPIO.input(INDUCTIVE_PIN)
        print(f"IR: {'OBJECT DETECTED' if ir_val == 0 else 'CLEAR'} | "
              f"Inductive: {'METAL DETECTED' if ind_val == 0 else 'CLEAR'}")
        time.sleep(0.5)
except KeyboardInterrupt:
    GPIO.cleanup()
