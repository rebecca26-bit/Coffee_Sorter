import time
import RPi.GPIO as GPIO

TCS_OUT = 17
TCS_S0 = 24
TCS_S1 = 25
TCS_S2 = 22
TCS_S3 = 27
# LED_PIN = 18  # Commented out for now

GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

GPIO.setup(TCS_OUT, GPIO.IN)
GPIO.setup(TCS_S0, GPIO.OUT)
GPIO.setup(TCS_S1, GPIO.OUT)
GPIO.setup(TCS_S2, GPIO.OUT)
GPIO.setup(TCS_S3, GPIO.OUT)
# GPIO.setup(LED_PIN, GPIO.OUT)  # Commented out

GPIO.output(TCS_S0, GPIO.HIGH)
GPIO.output(TCS_S1, GPIO.LOW)
# GPIO.output(LED_PIN, GPIO.HIGH)  # Commented out

def set_filter(color):
    if color == 'R':
        GPIO.output(TCS_S2, GPIO.LOW)
        GPIO.output(TCS_S3, GPIO.LOW)
    elif color == 'G':
        GPIO.output(TCS_S2, GPIO.HIGH)
        GPIO.output(TCS_S3, GPIO.HIGH)
    else:
        GPIO.output(TCS_S2, GPIO.LOW)
        GPIO.output(TCS_S3, GPIO.HIGH)

def read_freq(duration=0.1):
    count = 0
    start = time.time()
    last_state = GPIO.input(TCS_OUT)
    while time.time() - start < duration:
        current_state = GPIO.input(TCS_OUT)
        if last_state == 0 and current_state == 1:  # Rising edge
            count += 1
        last_state = current_state
        time.sleep(0.0001)  # Small delay to avoid busy-waiting too hard
    return count / duration

try:
    while True:
        for c in ['R', 'G', 'B']:
            set_filter(c)
            time.sleep(0.05)
            freq = read_freq(0.1)
            print(f"{c}: {freq} Hz")
        print("---")
        time.sleep(0.5)

except KeyboardInterrupt:
    GPIO.cleanup()
