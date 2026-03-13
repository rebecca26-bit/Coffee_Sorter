import time
import statistics
from colour_sensor import TCS3200, THRESHOLDS

def read_n_beans(sensor: TCS3200, label: str, n: int = 5) -> list:
    readings = []
    print(f"\n  → Place {label} beans one at a time. {n} readings needed.")
    for i in range(1, n + 1):
        input(f"     Bean {i}/{n} — press ENTER to read …")
        rgb = sensor.read_normalised_rgb()
        readings.append(rgb)
        print(f"       R={rgb[0]:3d}  G={rgb[1]:3d}  B={rgb[2]:3d}")
    return readings


def suggest_thresholds(good_readings, bad_readings):
    good_r = [r[0] for r in good_readings]
    good_g = [r[1] for r in good_readings]
    good_b = [r[2] for r in good_readings]
    bad_r  = [r[0] for r in bad_readings]

    good_r_min = min(good_r)
    good_rg    = min(r[0] - r[1] for r in good_readings)
    good_rb    = min(r[0] - r[2] for r in good_readings)

    print("\n" + "═" * 50)
    print("  Suggested thresholds for colour_sensor.py")
    print("═" * 50)
    print(f"  good_red_min   = {max(0, good_r_min - 10)}  "
          f"  (measured min R of good beans: {good_r_min})")
    print(f"  good_rg_margin = {max(0, good_rg - 5)}  "
          f"  (min R-G gap of good beans: {good_rg})")
    print(f"  good_rb_margin = {max(0, good_rb - 5)}  "
          f"  (min R-B gap of good beans: {good_rb})")
    print()
    print("  Copy these values into the THRESHOLDS dict in colour_sensor.py")
    print("═" * 50)


def main():
    print("=" * 50)
    print("  TCS3200 Calibration Tool — Group Trailblazers")
    print("=" * 50)

    sensor = TCS3200()

    # Step 1 & 2: black/white calibration
    sensor.calibrate()

    # Step 3: read good beans
    good = read_n_beans(sensor, "GOOD (ripe red)", n=5)

    # Step 4: read bad beans
    bad  = read_n_beans(sensor, "BAD (green or black)", n=5)

    # Step 5: suggest thresholds
    suggest_thresholds(good, bad)

    sensor.cleanup()
    print("\nCalibration complete.")


if __name__ == "__main__":
    main()
