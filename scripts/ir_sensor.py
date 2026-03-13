"""
ir_sensor.py — Fixed IR Sensor Module for Coffee Bean Sorter
Group Trailblazers | Uganda Christian University

FIXES APPLIED:
  - Added software debounce (confirmation sampling) to eliminate false triggers
  - Sensor is confirmed LOW (bean present) across multiple reads before accepting
  - Warm-up delay on startup to let sensor stabilise
  - Configurable sensitivity via CONFIRM_SAMPLES and CONFIRM_INTERVAL
"""

import RPi.GPIO as GPIO
import time

# ── Pin Configuration ──────────────────────────────────────────────────────────
IR_PIN = 16  # GPIO16 (BCM)

# ── Debounce Configuration ─────────────────────────────────────────────────────
WARMUP_DELAY      = 2.0   # seconds: wait for sensor to stabilise on startup
DEBOUNCE_DELAY    = 0.05  # seconds: wait after first edge before re-reading
CONFIRM_SAMPLES   = 3     # number of consecutive LOW reads required to confirm bean
CONFIRM_INTERVAL  = 0.01  # seconds between confirmation reads
BEAN_GONE_SAMPLES = 3     # consecutive HIGH reads to confirm bean has passed
COOLDOWN_TIME     = 0.4   # seconds: minimum time between two successive detections


class IRSensor:
    """
    Reliable IR proximity sensor reader with debounce.

    Typical IR obstacle sensors (like the FC-51 or TCRT5000-based modules)
    output LOW when an object is detected and HIGH when clear.
    If your module is inverted, set active_low=False in the constructor.
    """

    def __init__(self, pin=IR_PIN, active_low=True):
        self.pin = pin
        self.active_low = active_low
        self._last_trigger_time = 0.0

        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        GPIO.setup(self.pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)

        print(f"[IR] Warming up on pin {self.pin} … ({WARMUP_DELAY}s)")
        time.sleep(WARMUP_DELAY)
        print("[IR] Ready.")

    # ── Low-level helpers ──────────────────────────────────────────────────────

    def _raw_detected(self) -> bool:
        """Return True if the raw GPIO reading indicates an object."""
        val = GPIO.input(self.pin)
        return (val == GPIO.LOW) if self.active_low else (val == GPIO.HIGH)

    def _confirm(self, expected_state: bool, samples: int, interval: float) -> bool:
        """
        Read the sensor `samples` times, return True only if ALL reads
        match `expected_state`.  This eliminates single-sample noise spikes.
        """
        for _ in range(samples):
            if self._raw_detected() != expected_state:
                return False
            time.sleep(interval)
        return True

    # ── Public API ─────────────────────────────────────────────────────────────

    def wait_for_bean(self, timeout: float = 30.0) -> bool:
        """
        Block until a coffee bean is reliably detected or timeout expires.

        Returns True  → bean confirmed present
                False → timed out with no bean
        """
        deadline = time.time() + timeout
        while time.time() < deadline:
            if self._raw_detected():
                # Potential hit — wait for bounce to settle then confirm
                time.sleep(DEBOUNCE_DELAY)
                if self._confirm(True, CONFIRM_SAMPLES, CONFIRM_INTERVAL):
                    # Enforce minimum time between successive triggers
                    now = time.time()
                    if (now - self._last_trigger_time) >= COOLDOWN_TIME:
                        self._last_trigger_time = now
                        print("[IR] ✓ Bean detected (confirmed)")
                        return True
            time.sleep(0.005)  # tight poll without hammering CPU

        print("[IR] ✗ Timeout — no bean detected")
        return False

    def wait_for_bean_clear(self, timeout: float = 5.0) -> bool:
        """
        Block until the bean has passed the sensor (sensor reads clear again).
        Useful for knowing when to stop the belt or take an image.
        """
        deadline = time.time() + timeout
        while time.time() < deadline:
            if not self._raw_detected():
                time.sleep(DEBOUNCE_DELAY)
                if self._confirm(False, BEAN_GONE_SAMPLES, CONFIRM_INTERVAL):
                    print("[IR] Bean cleared sensor.")
                    return True
            time.sleep(0.005)
        return False

    def is_bean_present(self) -> bool:
        """
        Non-blocking: returns True only when a bean is confirmed present right now.
        Suitable for polling inside a loop.
        """
        if not self._raw_detected():
            return False
        time.sleep(DEBOUNCE_DELAY)
        return self._confirm(True, CONFIRM_SAMPLES, CONFIRM_INTERVAL)

    def cleanup(self):
        GPIO.cleanup(self.pin)
        print("[IR] GPIO cleaned up.")


# ── Standalone test ────────────────────────────────────────────────────────────
if __name__ == "__main__":
    sensor = IRSensor()
    print("Place beans under the IR sensor.  Press Ctrl+C to stop.\n")
    try:
        count = 0
        while True:
            if sensor.wait_for_bean(timeout=60):
                count += 1
                print(f"  → Bean #{count} detected!")
                sensor.wait_for_bean_clear()
    except KeyboardInterrupt:
        print(f"\nTotal beans detected: {count}")
    finally:
        sensor.cleanup()
