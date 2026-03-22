import RPi.GPIO as GPIO
import time

# ── Pin config (BCM) ──────────────────────────────────────────
IR_PIN = 16
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)
GPIO.setup(IR_PIN, GPIO.IN)

# ─────────────────────────────────────────────────────────────

def wait_for_bean(label, timeout=30):
    """Wait for IR sensor to trigger. Returns timestamp or None."""
    print(f"  Waiting for mark at {label}...")
    start = time.time()
    # wait for beam to be clear first
    while GPIO.input(IR_PIN) == 0:
        if time.time() - start > timeout:
            print("  Timeout — beam not clearing.")
            return None
        time.sleep(0.01)
    # now wait for object to break beam
    while GPIO.input(IR_PIN) == 1:
        if time.time() - start > timeout:
            print("  Timeout — no trigger detected.")
            return None
        time.sleep(0.005)
    t = time.time()
    print(f"  ✓ Detected!  [{t:.4f}s]")
    return t


def measure_speed():
    print("\n" + "="*55)
    print("  STEP 1 — BELT SPEED")
    print("="*55)
    print("""
  Instructions:
  1. Put two pieces of tape on the belt surface
  2. Measure the distance between them with a ruler
  3. Start the belt
  4. The IR sensor will detect each mark automatically
    """)

    dist_cm = float(input("  Distance between the two marks (cm): "))

    print("\n  Belt running — waiting for Mark 1...")
    t1 = wait_for_bean("MARK 1")
    if t1 is None:
        return None

    print("  Waiting for Mark 2...")
    t2 = wait_for_bean("MARK 2")
    if t2 is None:
        return None

    elapsed   = t2 - t1
    speed_cms = dist_cm / elapsed
    speed_mms = speed_cms * 10

    print(f"\n  ── Results ──")
    print(f"  Distance : {dist_cm} cm")
    print(f"  Time     : {elapsed:.3f} s")
    print(f"  Speed    : {speed_cms:.2f} cm/s  ({speed_mms:.1f} mm/s)")

    return speed_mms


def measure_distances(speed_mms):
    print("\n" + "="*55)
    print("  STEP 2 — SENSOR DISTANCES")
    print("="*55)
    print("""
  Instructions:
  1. Use a ruler to measure the physical distance
     between each pair of sensors on your belt frame
  2. Enter each measurement when prompted
  3. Timing constants will be calculated automatically
    """)

    segments = [
        ("IR  →  Colour sensor", "BELT_IR_TO_COLOUR"),
        ("Colour  →  Camera",    "BELT_COLOUR_TO_CAM"),
        ("Camera  →  Servo",     "BELT_CAM_TO_SERVO"),
    ]

    results = {}

    for label, config_key in segments:
        print(f"\n  ── {label} ──")
        dist_mm = float(input(f"  Distance (mm): "))
        elapsed = dist_mm / speed_mms

        print(f"  Time constant : {elapsed:.3f} s")
        print(f"  → {config_key} = {elapsed:.3f}")

        results[config_key] = elapsed

    print("\n" + "="*55)
    print("  FINAL RESULTS — Copy these into config.py")
    print("="*55)
    for key, val in results.items():
        print(f"  {key:30s} = {val:.3f}  # seconds")
    print("="*55)

    return results


def main():
    print("\n" + "="*55)
    print("  BELT CALIBRATION TOOL")
    print("  Uganda Christian University | Group Trailblazers")
    print("="*55)
    print("\n  Options:")
    print("  1 - Measure belt speed only")
    print("  2 - Calculate sensor distances only (enter speed manually)")
    print("  3 - Both (recommended)")

    choice = input("\n  Enter choice (1/2/3): ").strip()

    speed = None

    if choice in ("1", "3"):
        speed = measure_speed()
        if speed is None:
            print("  Speed measurement failed. Exiting.")
            return

    if choice in ("2", "3"):
        if speed is None:
            speed = float(input("\n  Enter belt speed in mm/s: "))
        measure_distances(speed)

    print("\n  Done! Update config.py with the values above.")
    print("  Then re-run test_manual.py to verify timing.\n")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n  Interrupted.")
    finally:
        GPIO.cleanup()
