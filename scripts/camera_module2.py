import time
import os
import json
import numpy as np
from picamera2 import Picamera2
from libcamera import controls as libcontrols

# ── Camera Configuration ───────────────────────────────────────────────────────
CAPTURE_RESOLUTION  = (1280, 960)   # lower than max → faster ISP, still good
PREVIEW_RESOLUTION  = (320, 240)    # low-res preview stream (optional)
WARMUP_FRAMES       = 20            # frames to capture and discard on startup
SETTLE_TIME         = 0.3           # seconds to wait after controls change
ROI_CONFIG_FILE     = "models/roi_config.json"

# ── Exposure settings ──────────────────────────────────────────────────────────
# Set USE_FIXED_EXPOSURE = True once you have good lighting set up.
# Then tune EXPOSURE_US until beans appear well-lit (not washed out / dark).
USE_FIXED_EXPOSURE  = False         # False = let auto-exposure handle it
EXPOSURE_US         = 20000         # microseconds (20 ms is good for indoor LED)
ANALOGUE_GAIN       = 2.0           # sensor gain (1.0 = ISO 100 equiv)


class CameraModule:
    """
    Single-instance camera wrapper.
    Open once, capture many times — avoids init overhead and blank frames.
    """

    def __init__(self):
        self._cam = None
        self._roi = self._load_roi()
        self._open()

    # ── Initialisation ─────────────────────────────────────────────────────────

    def _load_roi(self) -> dict | None:
        if os.path.exists(ROI_CONFIG_FILE):
            try:
                with open(ROI_CONFIG_FILE) as f:
                    roi = json.load(f)
                print(f"[Camera] ROI loaded: {roi}")
                return roi
            except Exception as e:
                print(f"[Camera] Warning — could not load ROI config: {e}")
        return None

    def _open(self):
        """Initialise the Picamera2 instance and let it warm up."""
        print("[Camera] Opening camera …")
        self._cam = Picamera2()

        # Create a still configuration — this gives the best image quality
        config = self._cam.create_still_configuration(
            main={"size": CAPTURE_RESOLUTION, "format": "RGB888"},
            lores={"size": PREVIEW_RESOLUTION, "format": "YUV420"},
            display=None,   # no display needed
            buffer_count=2
        )
        self._cam.configure(config)

        # Apply exposure settings before starting
        if USE_FIXED_EXPOSURE:
            self._cam.set_controls({
                "AeEnable":      False,
                "ExposureTime":  EXPOSURE_US,
                "AnalogueGain":  ANALOGUE_GAIN,
            })
        else:
            # Let AE run, but use centre-spot metering so the bean drives it
            self._cam.set_controls({
                "AeEnable":         True,
                "AeMeteringMode":   libcontrols.AeMeteringModeEnum.CentreWeighted,
                "AwbEnable":        True,
            })

        self._cam.start()

        # ── Warm-up: discard frames while AE/AWB converge ─────────────────────
        print(f"[Camera] Warming up ({WARMUP_FRAMES} frames) …")
        for _ in range(WARMUP_FRAMES):
            self._cam.capture_array("main")
        print("[Camera] Ready.")

    # ── Capture ────────────────────────────────────────────────────────────────

    def capture_bean(self, save_path: str | None = None) -> np.ndarray:
        """
        Capture a single bean image.

        Returns a numpy array (H×W×3, uint8, RGB).
        If save_path is given, the image is also written as JPEG.

        IMPORTANT: Call this only AFTER the IR sensor confirms a bean is present
                   so the bean is centred under the camera.
        """
        # Let AE settle for this bean's reflectance
        time.sleep(SETTLE_TIME)

        frame = self._cam.capture_array("main")  # RGB888 numpy array

        # ── Apply ROI crop if configured ───────────────────────────────────────
        if self._roi:
            frame = self._apply_roi(frame)

        # ── Save image if requested ────────────────────────────────────────────
        if save_path:
            self._save(frame, save_path)

        return frame

    def _apply_roi(self, frame: np.ndarray) -> np.ndarray:
        """Crop frame to the ROI rectangle specified in roi_config.json."""
        roi = self._roi
        h, w = frame.shape[:2]

        # Support both pixel and normalised (0.0-1.0) coordinates
        if all(isinstance(v, float) and v <= 1.0
               for v in [roi.get("x", 0), roi.get("y", 0),
                          roi.get("width", 1), roi.get("height", 1)]):
            x      = int(roi["x"]      * w)
            y      = int(roi["y"]      * h)
            width  = int(roi["width"]  * w)
            height = int(roi["height"] * h)
        else:
            x      = int(roi.get("x", 0))
            y      = int(roi.get("y", 0))
            width  = int(roi.get("width",  w))
            height = int(roi.get("height", h))

        # Clamp to valid range
        x      = max(0, min(x, w - 1))
        y      = max(0, min(y, h - 1))
        width  = max(1, min(width,  w - x))
        height = max(1, min(height, h - y))

        return frame[y:y + height, x:x + width]

    def _save(self, frame: np.ndarray, path: str):
        """Save numpy array as JPEG using OpenCV or PIL (whichever is available)."""
        try:
            import cv2
            # OpenCV expects BGR
            bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
            cv2.imwrite(path, bgr)
        except ImportError:
            from PIL import Image
            Image.fromarray(frame).save(path)
        print(f"[Camera] Saved → {path}")

    def capture_image(self, save_path: str | None = None) -> np.ndarray:
        """Alias kept for backward compatibility with old sorter_main.py."""
        return self.capture_bean(save_path=save_path)

    # ── Cleanup ────────────────────────────────────────────────────────────────

    def close(self):
        if self._cam:
            self._cam.stop()
            self._cam.close()
            self._cam = None
            print("[Camera] Closed.")

    def __del__(self):
        self.close()


# ── Standalone test ────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("Camera module test.  Taking 5 test shots …\n")
    cam = CameraModule()
    os.makedirs("test_shots", exist_ok=True)

    for i in range(1, 6):
        path = f"test_shots/test_{i:02d}.jpg"
        frame = cam.capture_bean(save_path=path)
        print(f"  Shot {i}: shape={frame.shape}  min={frame.min()}  max={frame.max()}")
        time.sleep(1)

    cam.close()
    print("\nDone. Check the test_shots/ folder.")
