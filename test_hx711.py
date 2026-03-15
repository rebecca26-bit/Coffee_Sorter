import time
import RPi.GPIO as GPIO
from hx711 import HX711

# -------------------------------------------------------
# CLEAN GPIO FIRST (prevents frozen HX711 pins)
# -------------------------------------------------------
GPIO.setwarnings(False)
GPIO.cleanup()
time.sleep(0.1)

# -------------------------------------------------------
# HX711 Setup (DT=5, SCK=6)
# -------------------------------------------------------
hx = HX711(5, 6)

hx.set_reading_format("MSB", "MSB")
hx.set_reference_unit(1)

hx.reset()
hx.tare()

print("\nGPIO cleaned.")
print("Tare complete. Remove all weight.")
print("Now place a known weight...\n")

try:
    while True:
        val = hx.get_weight(5)
        print("Raw reading:", val)
        hx.power_down()
        hx.power_up()
        time.sleep(0.5)

except KeyboardInterrupt:
    print("\nTest stopped by user.")

finally:
    # -------------------------------------------------------
    # CLEAN GPIO ON EXIT
    # -------------------------------------------------------
    GPIO.cleanup()
    print("GPIO cleaned. HX711 test closed safely.")
