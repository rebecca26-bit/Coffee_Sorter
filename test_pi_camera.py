#!/usr/bin/env python3

from camera_module import CameraModule
import time

if __name__ == "__main__":
    print("Initializing Pi Camera...")
    camera = CameraModule(resolution=(640, 480))
    
    time.sleep(2)  # Let camera adjust
    
    # Test single image capture
    print("Capturing test image...")
    image = camera.capture_image(filename="test_image.jpg")
    print(f"Image shape: {image.shape}")
    
    # Test video capture
    print("Capturing 5 seconds of video...")
    frames = camera.capture_stream(duration=5)
    print(f"Captured {len(frames)} frames")
    
    camera.stop()
    print("Camera test completed!")