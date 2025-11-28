# ============= COLOR SENSOR SETTINGS =============
COLOR_FREQUENCY_SCALE = "100%"  # Options: "2%", "20%", "100%"
COLOR_PULSE_DURATION = 0.05
# config.py - Configuration file for the coffee sorter project

# Color Sensor Pins (TCS3200)
# Make sure the numbers match your physical wiring to avoid errors or damage.
COLOR_S0 = 17 
COLOR_S1 = 18
COLOR_S2 = 27
COLOR_S3 = 22
COLOR_OUT =24

# You can add other pins later if other scripts complain they are missing
# VALVE_PIN = 24 
# LED_PIN = 25 
# ============= SERVO SETTINGS =============
SERVO_PIN = 18  # Or whatever GPIO your servo is on

# Servo positions (in degrees 0-180)
SERVO_HOME = 90   # Home/neutral position (90°)
SERVO_GOOD = 45   # Good bean bin (45°)
SERVO_BAD = 135   # Bad bean bin (135°)

# Servo timing
SERVO_MOVE_DELAY = 0.5  # Seconds to wait for servo to reach position

COLOR_CALIBRATION = {
    'white': {'r': 7676, 'g': 111882, 'b': 22040},
    'black': {'r': 3863, 'g': 57776, 'b': 11557},
    'good_reference': {'r': 5616, 'g': 78890, 'b': 15887},
    'bad_reference': {'r': 5401, 'g': 76952, 'b': 15366}
}



     # HX711 Data (DOUT) pin

LOADCELL_DT = 5  # GPIO 5 (physical pin 29)



     # HX711 Clock (PD_SCK) pin

LOADCELL_SCK = 6  # GPIO 6 (physical pin 31)
LOAD_SCALE = -0.01

# Tare is handled by hx.tare() in code
# Scale is applied manually in readings: weight = raw / LOAD_SCALE
# LEDs
LED_GREEN = 23
LED_RED = 25

# IR sensor
IR_SENSOR = 4
