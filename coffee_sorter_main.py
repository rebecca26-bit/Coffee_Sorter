import RPi.GPIO as GPIO
import time

# -----------------------
# GPIO Pin Definitions
# -----------------------
# IR Sensor
IR_PIN = 4  # GPIO4 / Pin 7

# LEDs
GREEN_LED = 25  # GPIO25 / Pin 22
RED_LED = 26    # GPIO26 / Pin 37

# Servo
SERVO_PIN = 18  # GPIO18 / Pin 12

# TCS3200 Pins
S0 = 17  # GPIO17 / Pin 11
S1 = 27  # GPIO27 / Pin 13
S2 = 22  # GPIO22 / Pin 15
S3 = 23  # GPIO23 / Pin 16
OUT = 24 # GPIO24 / Pin 18

# -----------------------
# Setup GPIO
# -----------------------
GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)

# IR Sensor
GPIO.setup(IR_PIN, GPIO.IN)

# LEDs
GPIO.setup(GREEN_LED, GPIO.OUT)
GPIO.setup(RED_LED, GPIO.OUT)

# Servo
GPIO.setup(SERVO_PIN, GPIO.OUT)
servo = GPIO.PWM(SERVO_PIN, 50)  # 50Hz
servo.start(7.5)  # Middle position (~90°)
time.sleep(1)

# TCS3200
GPIO.setup(S0, GPIO.OUT)
GPIO.setup(S1, GPIO.OUT)
GPIO.setup(S2, GPIO.OUT)
GPIO.setup(S3, GPIO.OUT)
GPIO.setup(OUT, GPIO.IN)

GPIO.output(S0, True)   # Frequency scaling 100%
GPIO.output(S1, False)

# -----------------------
# Servo Helper Function
# -----------------------
def set_servo_angle(angle):
    """Move servo to specified angle (0-180°)"""
    duty = 2 + (angle / 18)
    print(f"[SERVO] Moving to {angle}° (Duty={duty})")
    servo.ChangeDutyCycle(duty)
    time.sleep(1)  # wait for servo to move

# -----------------------
# TCS3200 Helper Functions
# -----------------------
def measure_pulse(duration=0.1):
    """Measure number of pulses from TCS3200"""
    start_time = time.time()
    count = 0
    while time.time() - start_time < duration:
        if GPIO.input(OUT) == 0:
            count += 1
            while GPIO.input(OUT) == 0:
                pass
    return count

def read_color():
    """Read color and return 'green', 'red', or 'unknown'"""
    # Red filter
    GPIO.output(S2, False)
    GPIO.output(S3, False)
    time.sleep(0.1)
    red = measure_pulse()
    
    # Green filter
    GPIO.output(S2, True)
    GPIO.output(S3, True)
    time.sleep(0.1)
    green = measure_pulse()
    
    print(f"[COLOR] Red={red}, Green={green}")
    
    if red < green:
        return "green"
    elif green < red:
        return "red"
    else:
        return "unknown"

# -----------------------
# Main Sorting Loop
# -----------------------
print("Coffee Sorter Running... Press Ctrl+C to stop.")

try:
    while True:
        if GPIO.input(IR_PIN) == 0:  # Bean detected
            print("[IR] Bean detected!")
            color = read_color()
            print(f"[RESULT] Color detected: {color}")
            
            if color == "green":
                GPIO.output(GREEN_LED, True)
                GPIO.output(RED_LED, False)
                set_servo_angle(120)  # move to green bin
            elif color == "red":
                GPIO.output(GREEN_LED, False)
                GPIO.output(RED_LED, True)
                set_servo_angle(60)   # move to red bin
            else:
                GPIO.output(GREEN_LED, False)
                GPIO.output(RED_LED, False)
                set_servo_angle(90)   # center
                
            time.sleep(1)  # wait before next bean
        else:
            GPIO.output(GREEN_LED, False)
            GPIO.output(RED_LED, False)
            time.sleep(0.1)

except KeyboardInterrupt:
    print("Stopping Coffee Sorter...")
    servo.stop()
    GPIO.cleanup()
