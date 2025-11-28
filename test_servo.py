#!/usr/bin/env python3
# test_servo.py - Test servo motor
import RPi.GPIO as GPIO
import time
import config

print("=" * 50)
print("SERVO MOTOR TEST")
print("=" * 50)

# Setup
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)
GPIO.setup(config.SERVO_PIN, GPIO.OUT)

# Create PWM instance (50Hz for servo)
pwm = GPIO.PWM(config.SERVO_PIN, 50)
pwm.start(0)

def set_angle(angle):
    """Move servo to angle (0-180 degrees)"""
    duty = 2 + (angle / 18)
    pwm.ChangeDutyCycle(duty)
    time.sleep(0.5)
    pwm.ChangeDutyCycle(0)  # Stop signal to reduce jitter

print("\nServo will sweep through different positions")
print("Watch the servo horn move!")
print("\n⚠️  If servo doesn't move:")
print("   - Check if separate 5V power supply is connected")
print("   - Verify signal wire to GPIO18 (Pin 12)")
print("   - Ensure common ground connection")
print("\nPress Ctrl+C to exit\n")

try:
    positions = [
        (config.SERVO_HOME, "HOME (90°)"),
        (config.SERVO_GOOD, "GOOD BIN (45°)"),
        (config.SERVO_BAD, "BAD BIN (135°)"),
        (0, "MINIMUM (0°)"),
        (180, "MAXIMUM (180°)")
    ]
    
    while True:
        for angle, label in positions:
            print(f"Moving to {label}...")
            set_angle(angle)
            time.sleep(2)
        
        print()  # Blank line between cycles
        
except KeyboardInterrupt:
    print("\n\nTest stopped")
    
finally:
    # Return to home position
    set_angle(config.SERVO_HOME)
    time.sleep(0.5)
    pwm.stop()
    GPIO.cleanup()
    print("Servo returned to home position")
