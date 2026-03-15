import RPi.GPIO as GPIO
import time
import json
import os

# ── Pin Configuration (BCM numbering) ─────────────────────────────────────────
PIN_S0  = 17
PIN_S1  = 27
PIN_S2  = 22
PIN_S3  = 23
PIN_OUT = 24
PIN_OE  = None  # No OE pin on this module

# ── Sampling Config ────────────────────────────────────────────────────────────
SAMPLE_COUNT      = 10     # reads per colour channel — more = stabler
SAMPLE_TIMEOUT    = 0.1    # seconds max wait for one pulse
FREQ_SCALE_DELAY  = 0.002  # seconds between channel switches
CAL_FILE          = "colour_calibration.json"

# ── Coffee Colour Thresholds (after normalisation to 0-255) ───────────────────
# These are starting points — run calibrate() with real beans to tune them.
# Ripe cherry-red beans:  R high (>120), G moderate, B low
# Unripe green beans:     G dominant, R low
# Over-ripe / black:      all channels low (<60)
# Foreign (paper/stone):  very high all channels (>200) or unusual ratios
THRESHOLDS = {
    "good_red_min":    56,   # normalised R must be at least this
    "good_rg_margin":  42,    # R must exceed G by at least this
    "good_rb_margin":  51,    # R must exceed B by at least this
    "black_max":       60,    # all channels below → black / mouldy
    "foreign_min":     200,   # all channels above → white / paper / stone
}


class TCS3200:
    """
    Interfaces with the TCS3200 / TCS230 light-to-frequency colour sensor.
    Call calibrate() once with reference black and white samples, then
    classify_bean() for each bean.
    """

    def __init__(self):
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)

        for pin in [PIN_S0, PIN_S1, PIN_S2, PIN_S3]:
            GPIO.setup(pin, GPIO.OUT)
        GPIO.setup(PIN_OUT, GPIO.IN)
        if PIN_OE is not None:
            GPIO.setup(PIN_OE, GPIO.OUT)
            GPIO.output(PIN_OE, GPIO.LOW)  # Enable sensor output

        # Set frequency scaling to 20% (S0=LOW, S1=HIGH)
        GPIO.output(PIN_S0, GPIO.LOW)
        GPIO.output(PIN_S1, GPIO.HIGH)

        # Calibration reference values
        self._cal_black = [0, 0, 0]     # raw counts for dark reference
        self._cal_white = [255, 255, 255]  # raw counts for white reference
        self._calibrated = False

        self._load_calibration()
        print("[Colour] TCS3200 initialised.")

    # ── Low-level reading ──────────────────────────────────────────────────────

    def _set_filter(self, s2: bool, s3: bool):
        """Select photodiode filter: R=(L,L) G=(H,H) B=(L,H) Clear=(H,L)"""
        GPIO.output(PIN_S2, GPIO.HIGH if s2 else GPIO.LOW)
        GPIO.output(PIN_S3, GPIO.HIGH if s3 else GPIO.LOW)
        time.sleep(FREQ_SCALE_DELAY)

    def _read_frequency(self) -> float:
        """
        Measure the output frequency by counting pulse transitions.
        Returns pulses per 10ms window → proportional to light intensity.
        """
        count = 0
        start = time.time()
        window = 0.10  # 100 ms window for stable reading

        # Count rising edges
        last = GPIO.input(PIN_OUT)
        deadline = start + window
        while time.time() < deadline:
            val = GPIO.input(PIN_OUT)
            if val != last:
                count += 1
                last = val

        # count is transitions; divide by 2 for full cycles
        frequency = count / 2.0 / window
        return frequency

    def _read_raw_rgb(self) -> list:
        """Read raw frequency for R, G, B channels and return as list."""
        results = []
        filters = [
            (False, False),  # Red
            (True,  True),   # Green
            (False, True),   # Blue
        ]
        for s2, s3 in filters:
            self._set_filter(s2, s3)
            samples = [self._read_frequency() for _ in range(SAMPLE_COUNT)]
            results.append(sum(samples) / len(samples))
        return results   # [R_freq, G_freq, B_freq]

    # ── Calibration ────────────────────────────────────────────────────────────

    def _normalise(self, raw: list) -> list:
        """Map raw [R,G,B] frequencies to 0-255 using calibration refs."""
        if not self._calibrated:
            # Without calibration, return a rough estimate (clamp 0-255)
            peak = max(raw) if max(raw) > 0 else 1
            return [int(min(255, max(0, v / peak * 255))) for v in raw]

        normalised = []
        for i in range(3):
            span = self._cal_white[i] - self._cal_black[i]
            if span <= 0:
                span = 1
            val = (raw[i] - self._cal_black[i]) / span * 255
            normalised.append(int(min(255, max(0, val))))
        return normalised

    def calibrate(self):
        """
        Interactive calibration.
        Run this once before deployment; results are saved to JSON.
        """
        print("\n[Calibration] Step 1: Place a DARK / BLACK reference under sensor.")
        input("  Press ENTER when ready …")
        raw_black = self._read_raw_rgb()
        print(f"  Black raw: R={raw_black[0]:.1f}  G={raw_black[1]:.1f}  B={raw_black[2]:.1f}")

        print("\n[Calibration] Step 2: Place a WHITE paper reference under sensor.")
        input("  Press ENTER when ready …")
        raw_white = self._read_raw_rgb()
        print(f"  White raw: R={raw_white[0]:.1f}  G={raw_white[1]:.1f}  B={raw_white[2]:.1f}")

        self._cal_black = raw_black
        self._cal_white = raw_white
        self._calibrated = True

        self._save_calibration()
        print("[Calibration] Done. Values saved to", CAL_FILE)

        # Verification pass
        print("\n[Calibration] Now place your GOOD (red/ripe) bean to verify:")
        input("  Press ENTER …")
        rgb = self.read_normalised_rgb()
        label, _ = self._classify(rgb)
        print(f"  Normalised RGB = {rgb}  →  '{label}'")
        print("  (Should read GOOD. If not, re-run calibration with better references.)")

    def _save_calibration(self):
        data = {"black": self._cal_black, "white": self._cal_white}
        with open(CAL_FILE, "w") as f:
            json.dump(data, f, indent=2)

    def _load_calibration(self):
        if os.path.exists(CAL_FILE):
            with open(CAL_FILE) as f:
                data = json.load(f)
            self._cal_black = data.get("black", [0, 0, 0])
            self._cal_white = data.get("white", [255, 255, 255])
            self._calibrated = True
            print(f"[Colour] Loaded calibration from {CAL_FILE}")
        else:
            print(f"[Colour] ⚠ No calibration file found — run calibrate() first!")

    # ── Classification ─────────────────────────────────────────────────────────

    def read_normalised_rgb(self) -> list:
        """Return calibration-normalised [R, G, B] values (0–255 each)."""
        raw = self._read_raw_rgb()
        return self._normalise(raw)

    def _classify(self, rgb: list) -> tuple:
        """
        Classify bean from normalised RGB.
        Returns (label: str, details: dict)

        Good coffee bean (ripe cherry): predominantly RED
          - Arabica ripe cherry:   R≈180-220, G≈60-100, B≈40-80
          - Robusta ripe cherry:   R≈150-190, G≈50-90,  B≈30-70
        Bad beans:
          - Unripe green:          G dominant, R low
          - Black / mouldy:        all channels very low
          - Pale / empty shell:    all channels high but R not dominant
        Foreign objects:
          - White paper:           R≈G≈B all very high
          - Stone (grey):          R≈G≈B moderate-high
          - Stick (brown):         G slightly higher, all moderate
        """
        r, g, b = rgb
        t = THRESHOLDS

        details = {"R": r, "G": g, "B": b}

        # 1. Foreign object: all channels very high (paper/stone)
        if r > t["foreign_min"] and g > t["foreign_min"] and b > t["foreign_min"]:
            return "FOREIGN", details

        # 2. Black / mouldy / over-ripe: everything dark
        if r < t["black_max"] and g < t["black_max"] and b < t["black_max"]:
            return "BAD_BLACK", details

        # 3. Unripe green: green channel dominant
        if g > r and g > b and (g - r) > t["good_rg_margin"]:
            return "BAD_GREEN", details

        # 4. Good ripe red bean: red clearly dominant over both G and B
        if (r >= t["good_red_min"] and
                (r - g) >= t["good_rg_margin"] and
                (r - b) >= t["good_rb_margin"]):
            return "GOOD", details

        # 5. Ambiguous — treat as bad to be safe
        return "BAD_UNKNOWN", details

    def classify_bean(self) -> tuple:
        """
        Read sensor and return (result, rgb, details).
        result is one of: 'GOOD', 'BAD_BLACK', 'BAD_GREEN',
                           'BAD_UNKNOWN', 'FOREIGN'
        """
        rgb = self.read_normalised_rgb()
        label, details = self._classify(rgb)
        print(f"[Colour] RGB={rgb}  →  {label}")
        return label, rgb, details

    def is_good_bean(self) -> bool:
        """Convenience wrapper: True only for a GOOD ripe bean."""
        label, _, _ = self.classify_bean()
        return label == "GOOD"

    def cleanup(self):
        if PIN_OE is not None:
            GPIO.output(PIN_OE, GPIO.HIGH)  # disable sensor
        GPIO.cleanup([PIN_S0, PIN_S1, PIN_S2, PIN_S3, PIN_OUT])
        print("[Colour] GPIO cleaned up.")


# ── Standalone test / calibration ─────────────────────────────────────────────
if __name__ == "__main__":
    import sys
    sensor = TCS3200()

    if len(sys.argv) > 1 and sys.argv[1] == "calibrate":
        sensor.calibrate()
    else:
        print("\nLive colour readings.  Press Ctrl+C to stop.")
        print("Run with argument 'calibrate' to set calibration references.\n")
        try:
            while True:
                label, rgb, _ = sensor.classify_bean()
                print(f"  R={rgb[0]:3d}  G={rgb[1]:3d}  B={rgb[2]:3d}  →  {label}")
                time.sleep(0.5)
        except KeyboardInterrupt:
            pass
        finally:
            sensor.cleanup()
