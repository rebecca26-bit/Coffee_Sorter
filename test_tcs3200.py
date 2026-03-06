import RPi.GPIO as GPIO
import time

# Pin setup
GPIO.setmode(GPIO.BCM)
TCS_OUT = 17
S2 = 22
S3 = 27
S0 = 24
S1 = 25

GPIO.setup(TCS_OUT, GPIO.IN)
GPIO.setup(S2, GPIO.OUT)
GPIO.setup(S3, GPIO.OUT)
GPIO.setup(S0, GPIO.OUT)
GPIO.setup(S1, GPIO.OUT)

# Set frequency scaling (20%)
GPIO.output(S0, GPIO.HIGH)
GPIO.output(S1, GPIO.LOW)

def set_filter(color):
    if color == 'R':
        GPIO.output(S2, GPIO.LOW)
        GPIO.output(S3, GPIO.LOW)
    elif color == 'G':
        GPIO.output(S2, GPIO.HIGH)
        GPIO.output(S3, GPIO.HIGH)
    elif color == 'B':
        GPIO.output(S2, GPIO.LOW)
        GPIO.output(S3, GPIO.HIGH)

def read_freq(duration=0.1):
    count = 0
    start = time.time()
    while time.time() - start < duration:
        GPIO.wait_for_edge(TCS_OUT, GPIO.RISING, timeout=duration*1000)
        count += 1
    return int(count / duration)

try:
    print("TCS3200 Test: show RED, GREEN, BLUE objects near sensor")

    while True:
        for c in ['R', 'G', 'B']:
            set_filter(c)
            f = read_freq()
            print(f"{c} freq:", f)
        print("---")
        time.sleep(0.5)

except KeyboardInterrupt:
    GPIO.cleanup()
    print("Exiting…")
