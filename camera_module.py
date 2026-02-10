import time
from picamera2 import Picamera2
import cv2
import numpy as np

class CameraModule:
    def __init__(self, resolution=(640, 480)):
        """Initialize the Pi camera"""
        self.picam2 = Picamera2()
        self.config = self.picam2.create_preview_configuration(
            main={"format": 'RGB888', "size": resolution}
        )
        self.picam2.configure(self.config)
        self.picam2.start()
        self.resolution = resolution
        
    def capture_image(self, filename=None):
        """Capture a single image"""
        array = self.picam2.capture_array()
        
        if filename:
            cv2.imwrite(filename, cv2.cvtColor(array, cv2.COLOR_RGB2BGR))
            print(f"Image saved to {filename}")
        
        return array
    
    def capture_stream(self, duration=5, fps=30):
        """Capture video stream for specified duration"""
        frames = []
        start_time = time.time()
        
        while time.time() - start_time < duration:
            frame = self.picam2.capture_array()
            frames.append(frame)
        
        return frames
    
    def stop(self):
        """Stop the camera"""
        self.picam2.stop()
        self.picam2.close()