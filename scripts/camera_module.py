"""
Camera Module for Coffee Sorter
================================
Improved version with:
- Error handling for camera initialization
- Context manager support (__enter__/__exit__)
- Proper docstrings
- Logging support

Author: Group Trailblazers
Version: 2.0.0
"""

import time
import logging
from picamera2 import Picamera2
import cv2
import numpy as np

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger ('CameraModule')


class CameraError(Exception):
    """Custom exception for camera-related errors"""
    pass


class CameraModule:
    """
    Raspberry Pi Camera Module wrapper using Picamera2.
    
    Provides methods for capturing images and video streams
    from the Raspberry Pi camera.
    
    Attributes:
        resolution (tuple): Camera resolution (width, height)
        picamera2 (Picamera2): Picamera2 instance
    """
    
    def __init__(self, resolution=(640, 480)):
        """
        Initialize the Pi camera.
        
        Args:
            resolution (tuple): Camera resolution as (width, height). 
                                Default is (640, 480).
        
        Raises:
            CameraError: If camera initialization fails
        """
        self.resolution = resolution
        self.picam2 = None
        self._is_initialized = False
        
        try:
            logger.info(f"Initializing camera with resolution {resolution}")
            self.picam2 = Picamera2()
            self.config = self.picam2.create_preview_configuration(
                main={"format": 'RGB888', "size": resolution}
            )
            self.picam2.configure(self.config)
            self.picam2.start()
            
            # Give camera time to warm up
            time.sleep(2)
            
            self._is_initialized = True
            logger.info("Camera initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize camera: {e}")
            raise CameraError(f"Camera initialization failed: {e}")
    
    def __enter__(self):
        """Context manager entry - returns self"""
        if not self._is_initialized:
            raise CameraError("Camera not initialized")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - cleanup resources"""
        self.stop()
        return False
    
    def __del__(self):
        """Destructor - ensure camera is stopped"""
        if self._is_initialized:
            self.stop()
    
    def is_initialized(self):
        """Check if camera is properly initialized"""
        return self._is_initialized
    
    def capture_image(self, filename=None):
        """
        Capture a single image from the camera.
        
        Args:
            filename (str, optional): Path to save the image. 
                                      If None, image is not saved to disk.
        
        Returns:
            numpy.ndarray: Captured image as RGB array
        
        Raises:
            CameraError: If capture fails
        """
        if not self._is_initialized:
            raise CameraError("Camera not initialized")
        
        try:
            array = self.picam2.capture_array()
            
            if filename:
                # Convert RGB to BGR for OpenCV
                bgr_array = cv2.cvtColor(array, cv2.COLOR_RGB2BGR)
                cv2.imwrite(filename, bgr_array)
                logger.debug(f"Image saved to {filename}")
            
            return array
            
        except Exception as e:
            logger.error(f"Failed to capture image: {e}")
            raise CameraError(f"Image capture failed: {e}")
    
    def capture_stream(self, duration=5):
        """
        Capture video stream for specified duration.
        
        Args:
            duration (float): Duration to capture in seconds.
        
        Returns:
            list: List of captured frames as numpy arrays
        
        Raises:
            CameraError: If stream capture fails
        """
        if not self._is_initialized:
            raise CameraError("Camera not initialized")
        
        frames = []
        start_time = time.time()
        
        try:
            logger.info(f"Capturing stream for {duration} seconds")
            
            while time.time() - start_time < duration:
                frame = self.picam2.capture_array()
                frames.append(frame)
            
            logger.info(f"Captured {len(frames)} frames")
            return frames
            
        except Exception as e:
            logger.error(f"Failed to capture stream: {e}")
            raise CameraError(f"Stream capture failed: {e}")
    
    def capture_and_process(self, processing_fn=None):
        """
        Capture an image and optionally process it.
        
        Args:
            processing_fn (callable, optional): Function to process the image.
                                               Should take numpy array and return processed result.
        
        Returns:
            tuple: (raw_image, processed_result) or just raw_image if no processing function
        
        Raises:
            CameraError: If capture or processing fails
        """
        if not self._is_initialized:
            raise CameraError("Camera not initialized")
        
        image = self.capture_image()
        
        if processing_fn is not None:
            try:
                processed = processing_fn(image)
                return image, processed
            except Exception as e:
                logger.error(f"Processing failed: {e}")
                raise CameraError(f"Image processing failed: {e}")
        
        return image
    
    def adjust_brightness(self, image, factor):
        """
        Adjust image brightness.
        
        Args:
            image: Input image (numpy array)
            factor: Brightness factor (1.0 = original, >1.0 = brighter, <1.0 = darker)
        
        Returns:
            numpy.ndarray: Brightness-adjusted image
        """
        return cv2.convertScaleAbs(image, alpha=factor, beta=0)
    
    def adjust_contrast(self, image, factor):
        """
        Adjust image contrast.
        
        Args:
            image: Input image (numpy array)
            factor: Contrast factor (1.0 = original, >1.0 = more contrast)
        
        Returns:
            numpy.ndarray: Contrast-adjusted image
        """
        return cv2.convertScaleAbs(image, alpha=factor, beta=0)
    
    def get_roi(self, image, x, y, width, height):
        """
        Extract region of interest from image.
        
        Args:
            image: Input image (numpy array)
            x, y: Top-left corner coordinates
            width, height: ROI dimensions
        
        Returns:
            numpy.ndarray: Extracted ROI
        """
        return image[y:y+height, x:x+width]
    
    def stop(self):
        """
        Stop the camera and release resources.
        
        This method safely stops the camera and should always be called
        when done using the camera to release hardware resources.
        """
        if self._is_initialized:
            try:
                logger.info("Stopping camera")
                self.picam2.stop()
                self.picam2.close()
                self._is_initialized = False
                logger.info("Camera stopped successfully")
            except Exception as e:
                logger.error(f"Error stopping camera: {e}")
            finally:
                self.picam2 = None


# Convenience function for simple usage
def capture_single_image(filename=None, resolution=(640, 480)):
    """
    Convenience function to capture a single image.
    
    Args:
        filename (str, optional): Path to save the image
        resolution (tuple): Camera resolution
    
    Returns:
        numpy.ndarray: Captured image
    """
    with CameraModule(resolution=resolution) as camera:
        return camera.capture_image(filename)
