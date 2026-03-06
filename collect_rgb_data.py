import csv
import time
import RPi.GPIO as GPIO

# ----------------------------
#  PIN SETUP
# ----------------------------
TCS_OUT = 17
S0 = 24
S1 = 25
S2 = 22
S3 = 27

GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

GPIO.setup(TCS_OUT, GPIO.IN)
GPIO.setup(S0, GPIO.OUT)
GPIO.setup(S1, GPIO.OUT)
GPIO.setup(S2, GPIO.OUT)
GPIO.setup(S3, GPIO.OUT)

GPIO.output(S0, GPIO.HIGH)
GPIO.output(S1, GPIO.LOW)

# ----------------------------
#  CALIBRATION VALUES (YOUR VALUES)
# ----------------------------
WHITE = {"R": 2400, "G": 2350, "B": 2750}
BLACK = {"R": 1437.5, "G": 1362.5, "B": 1725}

# ----------------------------
#  SENSOR FUNCTIONS
# ----------------------------
def set_filter(color):
    if color == 'R':
        GPIO.output(S2, GPIO.LOW)
        GPIO.output(S3, GPIO.LOW)
    elif color == 'G':
        GPIO.output(S2, GPIO.HIGH)
        GPIO.output(S3, GPIO.HIGH)
    else:  # BLUE
        GPIO.output(S2, GPIO.LOW)
        GPIO.output(S3, GPIO.HIGH)

def read_freq(duration=0.08):
    count = 0
    start = time.time()
    last_state = GPIO.input(TCS_OUT)

    while time.time() - start < duration:
        curr = GPIO.input(TCS_OUT)
        if last_state == 0 and curr == 1:
            count += 1
        last_state = curr
        time.sleep(0.0001)

    return count / duration

def normalize(value, color):
    return (value - BLACK[color]) / (WHITE[color] - BLACK[color])

# ----------------------------
#  DATA COLLECTION LOOP
# ----------------------------
print("\nDATA COLLECTION (RGB normalized)")
print("Press ENTER to sample a bean.")
print("Type GOOD or WRONG when prompted.\n")

with open("events_labeled_rgb.csv", "a", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["r","g","b","label"])

    try:
        while True:
            input("Place bean → press ENTER...")

            raw = {}
            for c in ['R','G','B']:
                set_filter(c)
                time.sleep(0.05)
                raw[c] = read_freq()

            rn = max(0, min(1, normalize(raw["R"], "R")))
            gn = max(0, min(1, normalize(raw["G"], "G")))
            bn = max(0, min(1, normalize(raw["B"], "B")))

            print(f"Raw: {raw}")
            print(f"Normalized: R={rn}, G={gn}, B={bn}")

            label = input("Label (GOOD/WRONG): ").strip().upper()
            writer.writerow([rn, gn, bn, label])

            print("Saved.\n")

    except KeyboardInterrupt:
        GPIO.cleanup()
        print("Stopped data collection.")
