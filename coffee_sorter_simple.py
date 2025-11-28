#!/usr/bin/env python3
"""
Coffee Bean Sorter - Simple Version with Angle-Based Servo
Sorts coffee beans using color sensor and servo motor
Uses 20% frequency with value scaling
"""

import RPi.GPIO as GPIO
import time
import json
from pathlib import Path
import config

class CoffeeSorter:
    def __init__(self):
        """Initialize the coffee sorter"""
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        
        # Color sensor pins
        GPIO.setup(config.COLOR_S0, GPIO.OUT)
        GPIO.setup(config.COLOR_S1, GPIO.OUT)
        GPIO.setup(config.COLOR_S2, GPIO.OUT)
        GPIO.setup(config.COLOR_S3, GPIO.OUT)
        GPIO.setup(config.COLOR_OUT, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
        
        # Servo pin
        GPIO.setup(config.SERVO_PIN, GPIO.OUT)
        self.servo = GPIO.PWM(config.SERVO_PIN, 50)  # 50Hz PWM
        self.servo.start(0)
        
        # Set color sensor to 20% frequency (stable for RPi)
        GPIO.output(config.COLOR_S0, GPIO.HIGH)
        GPIO.output(config.COLOR_S1, GPIO.LOW)
        
        # Sensor settings (matching calibration)
        self.SCALING_FACTOR = 0.1  # Reduces ~12000 to ~1200
        self.SAMPLE_DURATION = 0.05  # 50ms sampling
        
        # Calibration data
        self.calibration = None
        self.color_threshold = 1200  # Default threshold
        
        # Servo positions (angles in degrees)
        self.SERVO_HOME = getattr(config, 'SERVO_HOME', 90)
        self.SERVO_GOOD = getattr(config, 'SERVO_GOOD', 45)
        self.SERVO_BAD = getattr(config, 'SERVO_BAD', 135)
        self.SERVO_MOVE_DELAY = getattr(config, 'SERVO_MOVE_DELAY', 0.5)
        
        # Statistics
        self.stats = {
            'total': 0,
            'good': 0,
            'bad': 0,
            'start_time': time.time()
        }
        
        print("✓ Coffee sorter initialized")
        
        # Move servo to home position
        self.set_servo_angle(self.SERVO_HOME)
        print(f"✓ Servo at HOME position ({self.SERVO_HOME}°)")
        
        self.load_calibration()
    
    def load_calibration(self):
        """Load color sensor calibration data"""
        cal_file = Path('../data/color_calibration.json')
        
        if cal_file.exists():
            with open(cal_file, 'r') as f:
                self.calibration = json.load(f)
            
            # Calculate threshold from calibration
            good_avg = sum(self.calibration['good_beans']['mean'].values()) / 3
            bad_avg = sum(self.calibration['bad_beans']['mean'].values()) / 3
            self.color_threshold = (good_avg + bad_avg) / 2
            
            print(f"✓ Calibration loaded")
            print(f"  Good beans avg: {int(good_avg)}")
            print(f"  Bad beans avg: {int(bad_avg)}")
            print(f"  Threshold: {int(self.color_threshold)}")
        else:
            print("⚠️  No calibration found - using default threshold")
            print(f"  Default threshold: {int(self.color_threshold)}")
            print("  Run: python3 calibrate_color_sensor_slow.py")
    
    def angle_to_duty_cycle(self, angle):
        """Convert angle (0-180) to duty cycle (2-12)
        
        Args:
            angle: Servo angle in degrees (0-180)
            
        Returns:
            duty_cycle: PWM duty cycle percentage (2-12)
        """
        # Map 0-180 degrees to 2-12% duty cycle
        # 0° = 2%, 90° = 7%, 180° = 12%
        duty_cycle = 2 + (angle / 180) * 10
        return duty_cycle
    
    def set_servo_angle(self, angle):
        """Set servo to specific angle
        
        Args:
            angle: Target angle in degrees (0-180)
        """
        if not 0 <= angle <= 180:
            print(f"⚠️  Warning: Angle {angle} out of range (0-180)")
            angle = max(0, min(180, angle))
        
        duty_cycle = self.angle_to_duty_cycle(angle)
        self.servo.ChangeDutyCycle(duty_cycle)
        time.sleep(self.SERVO_MOVE_DELAY)
        self.servo.ChangeDutyCycle(0)  # Stop sending signal
    
    def select_filter(self, color):
        """Select color filter (R, G, B, or Clear)"""
        if color == 'R':
            GPIO.output(config.COLOR_S2, GPIO.LOW)
            GPIO.output(config.COLOR_S3, GPIO.LOW)
        elif color == 'G':
            GPIO.output(config.COLOR_S2, GPIO.HIGH)
            GPIO.output(config.COLOR_S3, GPIO.HIGH)
        elif color == 'B':
            GPIO.output(config.COLOR_S2, GPIO.LOW)
            GPIO.output(config.COLOR_S3, GPIO.HIGH)
        elif color == 'Clear':
            GPIO.output(config.COLOR_S2, GPIO.HIGH)
            GPIO.output(config.COLOR_S3, GPIO.LOW)
        
        time.sleep(0.01)  # Let filter stabilize
    
    def count_pulses(self, duration):
        """Count pulses from color sensor for specified duration"""
        count = 0
        prev_state = GPIO.input(config.COLOR_OUT)
        
        start = time.time()
        while time.time() - start < duration:
            current_state = GPIO.input(config.COLOR_OUT)
            if current_state == 1 and prev_state == 0:
                count += 1
            prev_state = current_state
        
        return count
    
    def read_rgb(self):
        """Read RGB values from color sensor"""
        # Read red
        self.select_filter('R')
        red_raw = self.count_pulses(self.SAMPLE_DURATION)
        red = int(red_raw * self.SCALING_FACTOR)
        
        # Read green
        self.select_filter('G')
        green_raw = self.count_pulses(self.SAMPLE_DURATION)
        green = int(green_raw * self.SCALING_FACTOR)
        
        # Read blue
        self.select_filter('B')
        blue_raw = self.count_pulses(self.SAMPLE_DURATION)
        blue = int(blue_raw * self.SCALING_FACTOR)
        
        return red, green, blue
    
    def classify_bean(self, r, g, b):
        """Classify bean as good or bad based on RGB values
        
        Returns: 'GOOD' or 'BAD'
        """
        rgb_sum = r + g + b
        
        # Higher RGB sum = lighter/better bean
        if rgb_sum > self.color_threshold:
            return 'GOOD'
        else:
            return 'BAD'
    
    def set_servo_position(self, position):
        """Set servo to sorting position
        
        Args:
            position: 'GOOD' or 'BAD'
        """
        if position == 'GOOD':
            angle = self.SERVO_GOOD
            print(f"  → Moving to GOOD bin ({angle}°)")
        else:
            angle = self.SERVO_BAD
            print(f"  → Moving to BAD bin ({angle}°)")
        
        self.set_servo_angle(angle)
        
        # Return to home after delay
        time.sleep(0.3)
        self.set_servo_angle(self.SERVO_HOME)
    
    def sort_bean(self):
        """Sort a single bean"""
        # Read color
        r, g, b = self.read_rgb()
        rgb_sum = r + g + b
        
        # Classify
        classification = self.classify_bean(r, g, b)
        
        # Update statistics
        self.stats['total'] += 1
        if classification == 'GOOD':
            self.stats['good'] += 1
        else:
            self.stats['bad'] += 1
        
        # Display result
        status_symbol = '✓' if classification == 'GOOD' else '✗'
        print(f"Bean #{self.stats['total']:3d} | "
              f"R:{r:4d} G:{g:4d} B:{b:4d} | "
              f"Sum:{rgb_sum:5d} | "
              f"{classification:4s} {status_symbol}")
        
        # Move servo to sort
        self.set_servo_position(classification)
        
        return classification
    
    def print_statistics(self):
        """Print sorting statistics"""
        elapsed = time.time() - self.stats['start_time']
        good_pct = (self.stats['good'] / self.stats['total'] * 100) if self.stats['total'] > 0 else 0
        bad_pct = (self.stats['bad'] / self.stats['total'] * 100) if self.stats['total'] > 0 else 0
        rate = self.stats['total'] / elapsed if elapsed > 0 else 0
        
        print("\n" + "="*70)
        print(" SORTING STATISTICS")
        print("="*70)
        print(f"Total beans sorted: {self.stats['total']}")
        print(f"Good beans: {self.stats['good']} ({good_pct:.1f}%)")
        print(f"Bad beans:  {self.stats['bad']} ({bad_pct:.1f}%)")
        print(f"Sorting rate: {rate:.1f} beans/second")
        print(f"Runtime: {elapsed:.1f} seconds")
        print("="*70)
    
    def run_manual_mode(self):
        """Run in manual mode - sort one bean at a time"""
        print("\n" + "="*70)
        print(" COFFEE SORTER - MANUAL MODE")
        print("="*70)
        print("\nPlace one bean at a time on the sensor")
        print("Press Enter to sort each bean")
        print("Press Ctrl+C to stop and see statistics")
        print("="*70 + "\n")
        
        try:
            while True:
                input("Press Enter to sort next bean (Ctrl+C to stop)... ")
                self.sort_bean()
                time.sleep(0.5)  # Brief pause
        
        except KeyboardInterrupt:
            print("\n\nSorting stopped by user")
            self.print_statistics()
    
    def run_auto_mode(self, delay=2.0):
        """Run in automatic mode - sorts continuously
        
        Args:
            delay: seconds between reads (default 2.0)
        """
        print("\n" + "="*70)
        print(" COFFEE SORTER - AUTOMATIC MODE")
        print("="*70)
        print(f"\nSorting automatically every {delay} seconds")
        print("Make sure beans are fed continuously")
        print("Press Ctrl+C to stop and see statistics")
        print("="*70 + "\n")
        
        try:
            while True:
                self.sort_bean()
                time.sleep(delay)
        
        except KeyboardInterrupt:
            print("\n\nSorting stopped by user")
            self.print_statistics()
    
    def test_servo(self):
        """Test servo movement through all positions"""
        print("\n" + "="*70)
        print(" SERVO TEST")
        print("="*70)
        
        positions = [
            (self.SERVO_HOME, f"HOME ({self.SERVO_HOME}°)"),
            (self.SERVO_GOOD, f"GOOD BIN ({self.SERVO_GOOD}°)"),
            (self.SERVO_BAD, f"BAD BIN ({self.SERVO_BAD}°)"),
            (0, "MINIMUM (0°)"),
            (180, "MAXIMUM (180°)")
        ]
        
        for angle, description in positions:
            print(f"\nMoving to {description}...")
            self.set_servo_angle(angle)
            time.sleep(1)
        
        print(f"\nReturning to HOME ({self.SERVO_HOME}°)...")
        self.set_servo_angle(self.SERVO_HOME)
        
        print("\n✓ Servo test complete")
    
    def test_color_sensor(self, num_reads=10):
        """Test color sensor readings"""
        print("\n" + "="*70)
        print(" COLOR SENSOR TEST")
        print("="*70)
        print(f"\nTaking {num_reads} readings...")
        print(f"Threshold: {int(self.color_threshold)}\n")
        
        for i in range(num_reads):
            r, g, b = self.read_rgb()
            rgb_sum = r + g + b
            classification = self.classify_bean(r, g, b)
            
            print(f"Read {i+1:2d}: R:{r:4d} G:{g:4d} B:{b:4d} | "
                  f"Sum:{rgb_sum:5d} | {classification}")
            
            time.sleep(1)
        
        print("\n✓ Color sensor test complete")
    
    def cleanup(self):
        """Cleanup GPIO"""
        # Return servo to home
        self.set_servo_angle(self.SERVO_HOME)
        self.servo.stop()
        GPIO.cleanup()
        print("\n✓ GPIO cleaned up")

def main():
    """Main function with menu"""
    sorter = CoffeeSorter()
    
    try:
        print("\n" + "="*70)
        print(" COFFEE BEAN SORTER - MAIN MENU")
        print("="*70)
        print("\nSelect mode:")
        print("  1. Manual mode (press Enter for each bean)")
        print("  2. Automatic mode (continuous sorting)")
        print("  3. Test servo movement")
        print("  4. Test color sensor")
        print("  5. Exit")
        print("="*70)
        
        choice = input("\nEnter choice (1-5): ").strip()
        
        if choice == '1':
            sorter.run_manual_mode()
        elif choice == '2':
            delay = input("Enter delay between beans (seconds, default 2): ").strip()
            delay = float(delay) if delay else 2.0
            sorter.run_auto_mode(delay)
        elif choice == '3':
            sorter.test_servo()
        elif choice == '4':
            sorter.test_color_sensor()
        elif choice == '5':
            print("\nExiting...")
        else:
            print("\nInvalid choice")
    
    except KeyboardInterrupt:
        print("\n\nProgram interrupted by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        sorter.cleanup()

if __name__ == "__main__":
    main()
