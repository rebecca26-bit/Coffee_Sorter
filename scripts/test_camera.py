"""
================================================================
COFFEE BEAN SORTER - HARDWARE CONFIGURATION
Uganda Christian University | Group Trailblazers
S23B23/056 | S23B23/010 | S23B23/046

This file contains all hardware configuration for the system.
Edit this file to match your physical wiring and setup.

CURRENT HARDWARE:
  ✅ TCS3200 colour sensor
  ✅ Servo motor
  ✅ IR sensor
  ✅ Camera Module 2 (imx219)
  ❌ HX711 load cell (removed)
  ❌ LED ring (not connected)
  ❌ DC motor (not connected yet)

CHANGES FROM ORIGINAL:
  1. GPIO pins corrected to match actual wiring
  2. HX711 pins removed
  3. LED ring pin removed
  4. DC motor pins removed
  5. IR sensor pin added
  6. Conveyor delays added
  7. Colour rule added for TCS3200
  8. Default weigh…
[7:02 PM, 3/6/2026] Beckie: """

import sys
import os
import time
import numpy as np

sys.path.insert(0, 'scripts')

from camera_module import CameraModule
from PIL import Image as PILImage

# ================================================================
# SETTINGS
# ================================================================
IMG_SIZE    = 224       # Must match ML training size
SAVE_DIR    = "data/camera_tests"
os.makedirs(SAVE_DIR, exist_ok=True)

# ================================================================
# STARTUP
# ================================================================
print("\n" + "="*50)
print("  CAMERA MODULE 2 TEST")
print("  Uganda Christian University")
print("  Group Trailblazers")
print("="*50)

# ================================================================
# INITIALISE CAMERA
# ================================================================
print("\n  Initialising Camera Module 2...")
try:
    cam = CameraModule(resolution=(IMG_SIZE, IMG_SIZE))
    print("  Camera ready")
except Exception as e:
    print("  Camera failed: " + str(e))
    sys.exit(1)

# ================================================================
# TEST 1 - BASIC CAPTURE
# ================================================================
print("\n" + "-"*50)
print("  TEST 1 - BASIC CAPTURE")
print("-"*50)

try:
    print("  Capturing image...", end=" ", flush=True)
    img_path  = SAVE_DIR + "/test1_basic.jpg"
    raw_image = cam.capture_image(img_path)
    size      = os.path.getsize(img_path)
    print("done")
    print("  Saved  : " + img_path)
    print("  Size   : " + str(size) + " bytes")
    print("  Shape  : " + str(raw_image.shape))
    print("  Dtype  : " + str(raw_image.dtype))
    print("  TEST 1 : PASSED")
except Exception as e:
    print("  TEST 1 FAILED: " + str(e))

# ================================================================
# TEST 2 - MULTIPLE CAPTURES
# ================================================================
print("\n" + "-"*50)
print("  TEST 2 - MULTIPLE CAPTURES (5 images)")
print("-"*50)

try:
    times = []
    for i in range(5):
        print("  Capturing " + str(i+1) + "/5...", end=" ", flush=True)
        start     = time.time()
        img_path  = SAVE_DIR + "/test2_capture_" + str(i+1) + ".jpg"
        raw_image = cam.capture_image(img_path)
        elapsed   = time.time() - start
        times.append(elapsed)
        print("done in " + str(round(elapsed, 2)) + "s")
        time.sleep(0.5)

    avg_time = round(sum(times) / len(times), 2)
    print("  Average capture time : " + str(avg_time) + "s")
    print("  Estimated throughput : " + str(round(1/avg_time, 1)) + " images/sec")
    print("  TEST 2 : PASSED")
except Exception as e:
    print("  TEST 2 FAILED: " + str(e))

# ================================================================
# TEST 3 - IMAGE QUALITY CHECK
# ================================================================
print("\n" + "-"*50)
print("  TEST 3 - IMAGE QUALITY CHECK")
print("-"*50)

try:
    print("  Capturing for quality check...", end=" ", flush=True)
    img_path  = SAVE_DIR + "/test3_quality.jpg"
    raw_image = cam.capture_image(img_path)
    print("done")

    # Convert to numpy for analysis
    img_array = np.array(raw_image).astype(np.float32)

    # Check brightness
    brightness = np.mean(img_array)
    r_mean     = np.mean(img_array[:,:,0])
    g_mean     = np.mean(img_array[:,:,1])
    b_mean     = np.mean(img_array[:,:,2])

    print("  Brightness (mean pixel): " + str(round(brightness, 1)) + "/255")
    print("  Red channel mean       : " + str(round(r_mean, 1)))
    print("  Green channel mean     : " + str(round(g_mean, 1)))
    print("  Blue channel mean      : " + str(round(b_mean, 1)))

    # Brightness check
    if brightness < 20:
        print("  WARNING: Image very dark - check lighting")
    elif brightness > 235:
        print("  WARNING: Image very bright - may be overexposed")
    else:
        print("  Brightness: OK")

    # Blur check using variance of Laplacian
    gray = np.mean(img_array, axis=2)
    laplacian_var = np.var(np.gradient(np.gradient(gray))[0])
    print("  Sharpness score        : " + str(round(laplacian_var, 2)))
    if laplacian_var < 10:
        print("  WARNING: Image may be blurry - check camera focus")
    else:
        print("  Sharpness: OK")

    print("  TEST 3 : PASSED")
except Exception as e:
    print("  TEST 3 FAILED: " + str(e))

# ================================================================
# TEST 4 - ML READY CAPTURE (224x224 normalised)
# ================================================================
print("\n" + "-"*50)
print("  TEST 4 - ML READY CAPTURE")
print("-"*50)
print("  Place a coffee bean under the camera")
input("  Press Enter when ready...")

try:
    print("  Capturing bean image...", end=" ", flush=True)
    img_path  = SAVE_DIR + "/test4_bean_mlready.jpg"
    raw_image = cam.capture_image(img_path)
    print("done")

    # Resize to exactly 224x224
    pil_img   = PILImage.fromarray(raw_image)
    pil_img   = pil_img.resize((IMG_SIZE, IMG_SIZE), PILImage.LANCZOS)
    img_array = np.array(pil_img).astype(np.float32) / 255.0

    print("  Raw shape    : " + str(raw_image.shape))
    print("  ML shape     : " + str(img_array.shape))
    print("  ML dtype     : " + str(img_array.dtype))
    print("  Pixel range  : " + str(round(img_array.min(), 3)) +
          " to " + str(round(img_array.max(), 3)))
    print("  Mean value   : " + str(round(img_array.mean(), 3)))

    # Check shape is correct for CNN
    if img_array.shape == (IMG_SIZE, IMG_SIZE, 3):
        print("  Shape check  : CORRECT (224x224x3)")
    else:
        print("  Shape check  : WRONG - expected (224,224,3)")

    # Check range is correct for CNN
    if img_array.min() >= 0.0 and img_array.max() <= 1.0:
        print("  Range check  : CORRECT (0.0 to 1.0)")
    else:
        print("  Range check  : WRONG - expected 0.0 to 1.0")

    # Save ML ready version
    ml_path = SAVE_DIR + "/test4_bean_mlready_224x224.jpg"
    pil_img.save(ml_path)
    print("  ML image saved: " + ml_path)
    print("  TEST 4 : PASSED")

except Exception as e:
    print("  TEST 4 FAILED: " + str(e))

# ================================================================
# TEST 5 - BEAN vs NO BEAN COMPARISON
# ================================================================
print("\n" + "-"*50)
print("  TEST 5 - BEAN vs NO BEAN COMPARISON")
print("-"*50)

try:
    # Capture without bean
    input("  Remove any objects from camera view, press Enter...")
    print("  Capturing empty view...", end=" ", flush=True)
    empty_path  = SAVE_DIR + "/test5_empty.jpg"
    empty_image = cam.capture_image(empty_path)
    empty_array = np.array(empty_image).astype(np.float32)
    empty_mean  = np.mean(empty_array)
    print("done  (mean=" + str(round(empty_mean, 1)) + ")")

    # Capture with bean
    input("  Place a coffee bean under camera, press Enter...")
    print("  Capturing bean...", end=" ", flush=True)
    bean_path  = SAVE_DIR + "/test5_bean.jpg"
    bean_image = cam.capture_image(bean_path)
    bean_array = np.array(bean_image).astype(np.float32)
    bean_mean  = np.mean(bean_array)
    print("done  (mean=" + str(round(bean_mean, 1)) + ")")

    # Compare
    diff = abs(bean_mean - empty_mean)
    print("\n  Empty mean : " + str(round(empty_mean, 1)))
    print("  Bean mean  : " + str(round(bean_mean,  1)))
    print("  Difference : " + str(round(diff, 1)))

    if diff > 5:
        print("  Camera detects bean presence : YES")
    else:
        print("  WARNING: Small difference - camera may not see bean clearly")
        print("  Try moving bean closer to camera or improving lighting")

    print("  TEST 5 : PASSED")

except Exception as e:
    print("  TEST 5 FAILED: " + str(e))

# ================================================================
# CLEANUP
# ================================================================
try:
    cam.stop()
except:
    pass

# ================================================================
# FINAL SUMMARY
# ================================================================
print("\n" + "="*50)
print("  CAMERA TEST COMPLETE")
print("="*50)
print("  All test images saved to: " + SAVE_DIR)
print("\n  Files saved:")
for f in sorted(os.listdir(SAVE_DIR)):
    fpath = SAVE_DIR + "/" + f
    size  = os.path.getsize(fpath)
    print("  " + f + " (" + str(size) + " bytes)")
print("="*50)
