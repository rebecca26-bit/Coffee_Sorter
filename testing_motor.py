import RPi.GPIO as GPIO
import time

# Pins (BCM numbering)
IN1 = 5
IN2 = 6
ENA = 13 # Move ENA wire here

GPIO.setmode(GPIO.BCM)
GPIO.setup([IN1, IN2, ENA], GPIO.OUT)

# Start PWM on the ENA pin at 100Hz frequency
pwm = GPIO.PWM(ENA, 100)
pwm.start(0) # Start at 0% speed

def set_speed(duty_cycle):
    """Sets motor speed from 0 to 100"""
    pwm.ChangeDutyCycle(duty_cycle)

try:
    # Set direction
    GPIO.output(IN1, GPIO.HIGH)
    GPIO.output(IN2, GPIO.LOW)

    print("Starting at 30% speed...")
    set_speed(30)
    time.sleep(3)

    print("Increasing to 60% speed...")
    set_speed(60)
    time.sleep(3)

    print("Stopping...")
    set_speed(0)

except KeyboardInterrupt:
    pass
finally:
    pwm.stop()
    GPIO.cleanup()
