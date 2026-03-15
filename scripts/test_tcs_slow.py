import RPi.GPIO as GPIO
import time

S0  = 17
S1  = 27
S2  = 22
S3  = 23
OUT = 24

GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)
GPIO.setup([S0, S1, S2, S3], GPIO.OUT)
GPIO.setup(OUT, GPIO.IN)
GPIO.output(S0, GPIO.HIGH)
GPIO.output(S1, GPIO.LOW)

def read_channel(s2_val, s3_val):
    GPIO.output(S2, s2_val)
    GPIO.output(S3, s3_val)
    time.sleep(0.05)
    count = 0
    start = time.time()
    last_state = GPIO.input(OUT)
    while time.time() - start < 0.1:
        current_state = GPIO.input(OUT)
        if last_state == GPIO.HIGH and current_state == GPIO.LOW:
            count += 1
        last_state = current_state
    return count

def read_rgb():
    r = read_channel(GPIO.LOW,  GPIO.LOW)
    g = read_channel(GPIO.HIGH, GPIO.HIGH)
    b = read_channel(GPIO.LOW,  GPIO.HIGH)
    return r, g, b

def run_test(label):
    input("Ready for " + label + "? Press Enter...")
    print("Reading for 3 seconds...")
    start = time.time()
    while time.time() - start < 3:
        r, g, b = read_rgb()
        print("R=" + str(r) + " G=" + str(g) + " B=" + str(b))
        time.sleep(0.5)

print("TCS3200 Colour Test - Press Enter before each test")
run_test("TEST 1 - NOTHING")
run_test("TEST 2 - WHITE PAPER")
run_test("TEST 3 - GOOD BEAN")
run_test("TEST 4 - BAD BEAN")
GPIO.cleanup()
print("Done")

