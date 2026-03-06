"""
================================================================
COFFEE BEAN SORTER — HARDWARE CONFIGURATION
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
  8. Default weight added (no HX711)
================================================================
"""

# ================================================================
# GPIO PIN CONFIGURATION (BCM numbering)
# ================================================================
PINS = {
    # ── TCS3200 Colour Sensor ─────────────────────────────────
    # CHANGE 1: Corrected from wrong pins (23,25,8,7) to actual pins
    "TCS_S0"  : 17,     # Frequency scaling pin S0 (was 23)
    "TCS_S1"  : 27,     # Frequency scaling pin S1 (was 25)
    "TCS_S2"  : 22,     # Colour filter select S2  (was 8)
    "TCS_S3"  : 23,     # Colour filter select S3  (was 7)
    "TCS_OUT" : 24,     # Digital output           (unchanged)

    # ── Servo Motor ───────────────────────────────────────────
    # CHANGE 1: Corrected from GPIO 12 to GPIO 18
    "SERVO"   : 18,     # Servo signal pin         (was 12)

    # ── IR Sensor ─────────────────────────────────────────────
    # CHANGE 5: Added IR sensor pin
    "IR"      : 16,     # IR sensor output pin     (new)

    # ── HX711 Load Cell ───────────────────────────────────────
    # CHANGE 2: HX711 removed — pins commented out
    # "HX_DT"  : 5,     # REMOVED — HX711 not connected
    # "HX_SCK" : 6,     # REMOVED — HX711 not connected

    # ── LED Ring ──────────────────────────────────────────────
    # CHANGE 3: LED ring removed — pin commented out
    # "LED"    : 18,    # REMOVED — no LED ring connected

    # ── DC Motor (Conveyor Belt) ──────────────────────────────
    # CHANGE 4: DC motor removed — pins commented out
    # "MOTOR_IN1": 20,  # REMOVED — no DC motor yet
    # "MOTOR_IN2": 21,  # REMOVED — no DC motor yet
    # "MOTOR_EN" : 16,  # REMOVED — pin now used for IR sensor
}

# ================================================================
# SERVO SETTINGS
# ================================================================
SERVO = {
    "PASS_ANGLE"  : 0,      # Degrees — gate open (bean passes through)
    "REJECT_ANGLE": 90,     # Degrees — gate closed (bean diverted to reject)
    "PWM_FREQ"    : 50,     # Hz — standard servo frequency
    "HOLD_TIME"   : 0.5,    # Seconds to hold reject position
    "RESET_TIME"  : 0.3,    # Seconds after servo resets
}

# ================================================================
# TCS3200 COLOUR SENSOR SETTINGS
# ================================================================
COLOUR_SENSOR = {
    "FREQ_SCALING_S0" : True,   # S0=HIGH for 20% frequency scaling
    "FREQ_SCALING_S1" : False,  # S1=LOW  for 20% frequency scaling
    "READ_DURATION"   : 0.2,    # Seconds to count pulses per channel
    "SETTLE_TIME"     : 0.1,    # Seconds to settle before reading
    "SAMPLES"         : 3,      # Number of readings to average
}

# ================================================================
# CAMERA SETTINGS
# ================================================================
CAMERA = {
    "RESOLUTION"    : (224, 224),   # Must match ML training size
    "WARMUP_TIME"   : 2,            # Seconds for camera to initialise
    "EXPOSURE_TIME" : 50000,        # Microseconds (higher = brighter)
    "ANALOGUE_GAIN" : 4.0,          # Gain (higher = brighter, more noise)
}

# ================================================================
# CONVEYOR BELT TIMING
# CHANGE 6: Added conveyor delays
# Adjust these to match your belt speed
# Current: 1 bean per 5 seconds, sensors 5-10cm apart
# ================================================================
CONVEYOR = {
    "DELAY_IR_TO_COLOUR" : 1.5,   # Seconds: IR detection → colour sensor
    "DELAY_COLOUR_TO_CAM": 1.5,   # Seconds: colour sensor → camera
    "DELAY_CAM_TO_SERVO" : 1.0,   # Seconds: camera → servo gate
    "DELAY_SERVO_RESET"  : 0.3,   # Seconds: after servo resets
    "BELT_SPEED_PCT"     : 0,     # % belt speed (0 = manual, no DC motor)
}

# ================================================================
# ML MODEL SETTINGS
# ================================================================
ML = {
    "DT_WEIGHT"       : 0.65,   # Decision Tree contribution to fusion
    "CNN_WEIGHT"      : 0.35,   # CNN contribution to fusion
    "FUSION_THRESHOLD": 0.5,    # Score >= this = GOOD bean
    "IMG_SIZE"        : 224,    # Image size for CNN input
    "DEFAULT_WEIGHT"  : 0.30,   # Default bean weight (no HX711)
}

# ================================================================
# COLOUR RULE SETTINGS
# CHANGE 7: Added colour rule for TCS3200 decision
# ================================================================
COLOUR_RULE = {
    # True  = use R-G difference rule from TCS3200
    # False = use trained Decision Tree model
    "USE_COLOUR_RULE": True,

    # R-G difference threshold
    # Good beans (reddish/brown): R >> G → high difference
    # Bad beans  (green/grey)   : R ≈ G → low difference
    # From testing: good=273 R-G=109, bad=207 R-G=12
    "DIFF_THRESHOLD" : 50,
}

# ================================================================
# HX711 SETTINGS (DISABLED — not connected)
# CHANGE 2: HX711 removed
# Uncomment when load cell is reconnected and calibrated
# ================================================================
# HX711 = {
#     "SCALE_RATIO"   : 102,    # Calibration value — adjust for your load cell
#     "WEIGHT_SAMPLES": 5,      # Number of readings to average
#     "TARE_ON_START" : True,   # Auto-tare when system starts
#     "MIN_WEIGHT"    : 0.05,   # Minimum weight to trigger sort (grams)
# }

# ================================================================
# DC MOTOR SETTINGS (DISABLED — not connected yet)
# CHANGE 4: DC motor removed
# Uncomment when conveyor motor is connected
# ================================================================
# DC_MOTOR = {
#     "SPEED_PCT"     : 40,     # Belt speed 0-100%
#     "PWM_FREQ"      : 100,    # Hz — DC motor PWM frequency
#     "DIRECTION"     : "FWD",  # FWD or REV
# }

# ================================================================
# FILE PATHS
# ================================================================
PATHS = {
    "DT_MODEL"    : "models/decision_tree_model.pkl",
    "CNN_MODEL"   : "models/cnn_model.tflite",
    "SCALER"      : "models/scaler.pkl",
    "FUSION_CFG"  : "models/fusion_config.json",
    "LOG_CSV"     : "data/sorting_results.csv",
    "LOG_TXT"     : "data/sorter_log.txt",
    "IMAGES_DIR"  : "data/bean_images/",
}

# ================================================================
# SYSTEM SETTINGS
# ================================================================
SYSTEM = {
    "STATS_INTERVAL": 10,       # Print stats every N beans
    "LOG_LEVEL"     : "INFO",   # INFO, DEBUG, WARNING, ERROR
    "SAVE_IMAGES"   : True,     # Save captured bean images to disk
    "SESSION_NAME"  : "default",# Name for this sorting session
}

# ================================================================
# QUICK REFERENCE — Current wiring summary
# ================================================================
"""
WIRING SUMMARY
==============
Component       Pi Pin    GPIO    Notes
─────────────── ──────── ─────── ──────────────────────────
TCS3200 VCC     Pin 1    3.3V    Both VCC pins connected
TCS3200 VCC     Pin 17   3.3V    Bottom VCC pin
TCS3200 LED     Pin 1    3.3V    Onboard LEDs power
TCS3200 GND     Pin 6    GND     Top GND pin
TCS3200 GND     Pin 9    GND     Bottom GND pin
TCS3200 S0      Pin 11   GPIO17  Frequency scaling
TCS3200 S1      Pin 13   GPIO27  Frequency scaling
TCS3200 S2      Pin 15   GPIO22  Colour filter select
TCS3200 S3      Pin 16   GPIO23  Colour filter select
TCS3200 OUT     Pin 18   GPIO24  Pulse output to Pi

Servo Signal    Pin 12   GPIO18  PWM signal
Servo VCC       Pin 2    5V      Servo power
Servo GND       Pin 14   GND     Servo ground

IR Sensor OUT   Pin 36   GPIO16  Detection output
IR Sensor VCC   Pin 1    3.3V    IR power
IR Sensor GND   Pin 6    GND     IR ground

Camera          CSI port         Ribbon cable connector
"""
