from gpiozero import LED
from time import sleep

# Define the LED on GPIO pin 18
led = LED(26)

try:
    while True:
        print("LED is ON")
        led.on()       # Turn the LED on
        sleep(1)       # Wait 1 second
        
        print("LED is OFF")
        led.off()      # Turn the LED off
        sleep(1)       # Wait 1 second

except KeyboardInterrupt:
    # This allows you to stop the script safely by pressing Ctrl+C
    print("\nProgram stopped by user")
