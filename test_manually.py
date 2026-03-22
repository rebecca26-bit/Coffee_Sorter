import time
import numpy as np
import RPi.GPIO as GPIO
from gpiozero import Servo
import tflite_runtime.interpreter as tflite
from camera_module import CameraModule, CameraError

# ─────────────────────────────────────────────
# MODEL PATH — update after running:
#   find / -name "*.tflite" 2>/dev/null
# ─────────────────────────────────────────────
TFLITE_MODEL_PATH = "models/cnn_model.tflite"  # update full path if needed

# ─────────────────────────────────────────────
# GPIO / PIN CONFIG
# ─────────────────────────────────────────────
S0, S1, S2, S3, OUT = 17, 27, 22, 23, 24
IR_PIN    = 16
SERVO_PIN = 18

# ─────────────────────────────────────────────
# THRESHOLDS (calibrated to real hardware readings)
# ─────────────────────────────────────────────
# WEIGHT_MIN   = 0.10   # grams (commented out — no HX711)
# WEIGHT_MAX   = 0.35   # grams (commented out — no HX711)
BRIGHTNESS_MAX = 400   # avg RGB > 400 → foreign object (bean_0002 averaged ~1527)
GREY_DIFF_MAX  = 15    # |R-G| and |G-B| both < 15 → stone (grey)
R_G_DIFF_MIN   = 25    # good beans have R-G >= 30, bad beans <= 17

# Servo positions
POS_GOOD   = -0.6   # left  chute → good bin
POS_BAD    =  0.6   # right chute → reject bin
POS_CENTER =  0.0   # neutral / reset

# ─────────────────────────────────────────────
# SETUP — GPIO
# ─────────────────────────────────────────────
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

for pin in [S0, S1, S2, S3]:
    GPIO.setup(pin, GPIO.OUT)
GPIO.setup(OUT, GPIO.IN)
GPIO.setup(IR_PIN, GPIO.IN)

GPIO.output(S0, GPIO.HIGH)
GPIO.output(S1, GPIO.LOW)

servo = Servo(SERVO_PIN)

# ─────────────────────────────────────────────
# SETUP — TFLite CNN
# ─────────────────────────────────────────────
print("Loading TFLite model...")
interpreter = tflite.Interpreter(model_path=TFLITE_MODEL_PATH)
interpreter.allocate_tensors()
input_details  = interpreter.get_input_details()
output_details = interpreter.get_output_details()
CNN_INPUT_SIZE = (input_details[0]['shape'][1], input_details[0]['shape'][2])
print(f"Model loaded. Input size: {CNN_INPUT_SIZE}")

# ─────────────────────────────────────────────
# SERVO
# ─────────────────────────────────────────────
def servo_move(position, label=""):
    print(f"  🔧 Servo → {label} ({position})")
    servo.value = position
    time.sleep(0.4)

def servo_reset():
    servo_move(POS_CENTER, "CENTER")

# ─────────────────────────────────────────────
# COLOUR READING (pulse counting, Trixie-safe)
# ─────────────────────────────────────────────
def read_channel(s2_val, s3_val, duration=0.1):
    GPIO.output(S2, s2_val)
    GPIO.output(S3, s3_val)
    time.sleep(0.02)
    count = 0
    start = time.time()
    last  = GPIO.input(OUT)
    while (time.time() - start) < duration:
        current = GPIO.input(OUT)
        if current != last:
            count += 1
            last = current
    return count // 2

def read_colour():
    r = read_channel(GPIO.LOW,  GPIO.LOW)
    g = read_channel(GPIO.HIGH, GPIO.HIGH)
    b = read_channel(GPIO.LOW,  GPIO.HIGH)
    return r, g, b

# ─────────────────────────────────────────────
# WEIGHT READING (commented out — no HX711)
# ─────────────────────────────────────────────
# def read_weight():
#     try:
#         raw = float(input("    Enter weight in grams: ").strip() or "0.18")
#         return raw
#     except ValueError:
#         return 0.0

# ─────────────────────────────────────────────
# CNN CLASSIFICATION
# ─────────────────────────────────────────────
def run_cnn(image):
    """
    Run MobileNetV2 TFLite model on captured image.
    Returns 'GOOD' or 'BAD'.
    """
    resized = __import__('cv2').resize(image, CNN_INPUT_SIZE)
    input_data = np.expand_dims(resized.astype(np.float32) / 255.0, axis=0)
    interpreter.set_tensor(input_details[0]['index'], input_data)
    interpreter.invoke()
    output = interpreter.get_tensor(output_details[0]['index'])[0]
    confidence = float(np.max(output))
    label = "GOOD" if np.argmax(output) == 1 else "BAD"
    print(f"  CNN → {label} (confidence: {confidence:.2f})")
    return label

# ─────────────────────────────────────────────
# FOREIGN OBJECT REJECTION GATE
# ─────────────────────────────────────────────
def is_valid_bean(r, g, b):
    """
    Returns (True, 'OK') or (False, reason).
    Weight checks commented out — re-enable when HX711 is connected.
    """
    # # Weight gate (commented out — no HX711)
    # if weight <= 0:
    #     return False, "NO_OBJECT (weight = 0)"
    # if weight < WEIGHT_MIN:
    #     return False, f"TOO_LIGHT ({weight:.2f}g) — stick or debris"
    # if weight > WEIGHT_MAX:
    #     return False, f"TOO_HEAVY ({weight:.2f}g) — probably a stone"

    # 1. Brightness gate — paper / white objects
    brightness = (r + g + b) / 3
    if brightness > BRIGHTNESS_MAX:
        return False, f"TOO_BRIGHT (avg={brightness:.0f}) — probably paper"

    # 2. Grey gate — stones
    if abs(r - g) < GREY_DIFF_MAX and abs(g - b) < GREY_DIFF_MAX:
        return False, f"GREY OBJECT R={r} G={g} B={b} — probably a stone"

    # 3. Colour separation gate
    if (r - g) < R_G_DIFF_MIN:
        return False, f"LOW R-G DIFF ({r - g}) — not bean-like colour"

    return True, "OK"

# ─────────────────────────────────────────────
# COLOUR CLASSIFICATION
# ─────────────────────────────────────────────
def classify_colour(r, g, b):
    """Colour-based rule classifier. Replace with Decision Tree predict()."""
    if (r - g) > 50:
        return "GOOD"
    return "BAD"

# ─────────────────────────────────────────────
# FUSION DECISION — either BAD = reject
# ─────────────────────────────────────────────
def fuse(colour_result, cnn_result):
    """
    Either sensor saying BAD = final result is BAD.
    Both must say GOOD for the bean to pass.
    """
    if colour_result == "BAD" or cnn_result == "BAD":
        return "BAD"
    return "GOOD"

# ─────────────────────────────────────────────
# MAIN MANUAL TEST LOOP
# ─────────────────────────────────────────────
def run_test():
    print("\n" + "="*55)
    print("  GROUP TRAILBLAZERS — Manual Reject + Servo Test")
    print("  Fusion: Colour + CNN (either BAD = reject)")
    print("="*55)
    print("Place an object on the sensor and press Enter each step.")
    print("Ctrl+C to quit.\n")

    servo_reset()
    bean_count = 0

    try:
        camera = CameraModule(resolution=(640, 480))
    except CameraError as e:
        print(f"❌ Camera failed to initialise: {e}")
        GPIO.cleanup()
        return

    try:
        while True:
            bean_count += 1
            print(f"\n─── Object #{bean_count} ───────────────────────────────")
            input("  [STEP 1] Place object, then press Enter to read colour...")

            # Step 1: Read colour
            r, g, b = read_colour()
            print(f"  Colour →  R={r}  G={g}  B={b}")

            # # Weight — commented out (no HX711)
            # input("  Press Enter to read weight...")
            # weight = read_weight()
            # print(f"  Weight → {weight:.2f}g")

            input("  [STEP 2] Press Enter to capture image + classify...")

            # Step 2: Foreign object gate
            valid, reason = is_valid_bean(r, g, b)
            if not valid:
                print(f"\n  ❌ REJECTED (colour gate) — {reason}")
                servo_move(POS_BAD, "BAD/REJECT")
                time.sleep(0.5)
                servo_reset()
                continue

            # Step 3: Colour classification
            colour_result = classify_colour(r, g, b)
            print(f"  Colour result  → {colour_result}")

            # Step 4: CNN classification
            try:
                image = camera.capture_image()
                cnn_result = run_cnn(image)
            except CameraError as e:
                print(f"  ⚠️  Camera error: {e} — defaulting CNN to BAD")
                cnn_result = "BAD"

            # Step 5: Fusion
            final = fuse(colour_result, cnn_result)
            print(f"\n  ══ FUSION RESULT: {final} ══")
            print(f"     Colour={colour_result}  CNN={cnn_result}")

            if final == "GOOD":
                print("  ✅ Sending to GOOD bin")
                servo_move(POS_GOOD, "GOOD")
            else:
                print("  ❌ Sending to BAD bin")
                servo_move(POS_BAD, "BAD")

            time.sleep(0.5)
            servo_reset()
            print("  ↺ Servo reset. Ready for next object.")

    except KeyboardInterrupt:
        print("\n\nTest ended. Cleaning up...")
        camera.stop()
        servo_reset()
        GPIO.cleanup()
        print("Done.")

if __name__ == "__main__":
    run_test()
