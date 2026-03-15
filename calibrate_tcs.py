import RPi.GPIO as GPIO
import time

GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)  # Suppress warnings

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

GPIO.output(S0, GPIO.HIGH)
GPIO.output(S1, GPIO.LOW)

def set_filter(color):
    if color == 'R':
        GPIO.output(S2, GPIO.LOW)
        GPIO.output(S3, GPIO.LOW)
    elif color == 'G':
        GPIO.output(S2, GPIO.HIGH)
        GPIO.output(S3, GPIO.HIGH)
    else:
        GPIO.output(S2, GPIO.LOW)
        GPIO.output(S3, GPIO.HIGH)

def read_freq(duration=0.08):  # Adjusted to match your original duration
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

print("\n--- WHITE Calibration ---")
input("Place a WHITE paper/object and press Enter...")

white = {}
for c in ['R', 'G', 'B']:
    set_filter(c)
    time.sleep(0.1)
    white[c] = read_freq()
print("White:", white)

print("\n--- BLACK Calibration ---")
input("Place a BLACK surface and press Enter...")

black = {}
for c in ['R', 'G', 'B']:
    set_filter(c)
    time.sleep(0.1)
    black[c] = read_freq()
print("Black:", black)

print("\nCopy these into sorter_service.py under sensor normalization.")
GPIO.cleanup()
