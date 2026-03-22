import RPi.GPIO as GPIO
import time

GPIO.setmode(GPIO.BCM)
GPIO.setup(18, GPIO.OUT)
pwm = GPIO.PWM(18, 50)
pwm.start(0)
time.sleep(1)

for angle in [0, 90, 0, 90]:
    duty = 2 + (angle / 18)
    print(f"Setting {angle}° → duty {duty}")
    pwm.ChangeDutyCycle(duty)
    time.sleep(1.0)          # long hold
    pwm.ChangeDutyCycle(0)
    time.sleep(0.5)

pwm.stop()
GPIO.cleanup()
