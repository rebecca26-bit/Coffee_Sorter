import pigpio
import time

# Pins (BCM)
PIN_IN1 = 5
PIN_IN2 = 6
PIN_ENA = 13

# Initialize
pi = pigpio.pi()

if not pi.connected:
    print("Error: Run 'sudo pigpiod' in the terminal first!")
    exit()

def test_motor():
    print("--- Starting Motor Test ---")
    
    # 1. Set Directions
    pi.write(PIN_IN1, 1)
    pi.write(PIN_IN2, 0)
    
    # 2. Set Speed (150 out of 255)
    print("Belt should be moving now...")
    pi.set_PWM_dutycycle(PIN_ENA, 150) 
    
    time.sleep(3) # Run for 3 seconds
    
    # 3. Stop
    print("Stopping and cleaning up.")
    pi.set_PWM_dutycycle(PIN_ENA, 0)
    pi.write(PIN_IN1, 0)
    pi.write(PIN_IN2, 0)
    pi.stop()

if __name__ == "__main__":
    test_motor()
