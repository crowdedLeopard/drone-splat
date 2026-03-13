"""
Frame Selector - Keyframe selection for reconstruction

Selects keyframes from video stream based on motion and timing criteria.
Avoids redundant near-duplicate frames.
"""

import numpy as np
import cv2
from typing import List, Tuple, Optional
from dataclasses import dataclass
import time


@dataclass
class KeyFrame:
    """Represents a selected keyframe with metadata"""
    image: np.ndarray
    timestamp: float
    frame_id: int
    motion_score: float = 0.0


class FrameSelector:
    """Selects keyframes from incoming video stream"""
    
    def __init__(self, config: dict):
        """
        Initialize frame selector
        
        Args:
            config: Configuration dict with keys:
                - min_interval: Minimum seconds between keyframes (default: 0.5)
                - max_interval: Maximum seconds between keyframes (default: 2.0)
                - motion_threshold: Optical flow threshold for motion detection (default: 5.0)
                - max_keyframes: Maximum keyframes to maintain in sliding window (default: 50)
        """
        self.min_interval = config.get('min_interval', 0.5)
        self.max_interval = config.get('max_interval', 2.0)
        self.motion_threshold = config.get('motion_threshold', 5.0)
        self.max_keyframes = config.get('max_keyframes', 50)
        
        self.keyframes: List[KeyFrame] = []
        self.last_keyframe_time: Optional[float] = None
        self.prev_gray: Optional[np.ndarray] = None
        self.frame_counter = 0
        
    def should_select_frame(self, frame: np.ndarray, timestamp: float) -> bool:
        """
        Determine if frame should be selected as keyframe
        
        Args:
            frame: Input frame (BGR or RGB)
            timestamp: Frame timestamp in seconds
            
        Returns:
            True if frame should be selected as keyframe
        """
        self.frame_counter += 1
        
        # First frame is always a keyframe
        if self.last_keyframe_time is None:
            return True
            
        time_since_last = timestamp - self.last_keyframe_time
        
        # Force keyframe if max interval exceeded
        if time_since_last >= self.max_interval:
            return True
            
        # Skip if min interval not met
        if time_since_last < self.min_interval:
            return False
            
        # Check motion via optical flow
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY) if len(frame.shape) == 3 else frame
        
        if self.prev_gray is not None:
            motion_score = self._compute_motion_score(self.prev_gray, gray)
            if motion_score > self.motion_threshold:
                return True
                
        return False
        
    def add_frame(self, frame: np.ndarray, timestamp: float) -> bool:
        """
        Add frame and determine if it's selected as keyframe
        
        Args:
            frame: Input frame
            timestamp: Frame timestamp
            
        Returns:
            True if frame was selected as keyframe
        """
        if not self.should_select_frame(frame, timestamp):
            # Update prev_gray for next comparison
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY) if len(frame.shape) == 3 else frame
            self.prev_gray = gray
            return False
            
        # Add as keyframe
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY) if len(frame.shape) == 3 else frame
        motion_score = 0.0
        if self.prev_gray is not None:
            motion_score = self._compute_motion_score(self.prev_gray, gray)
            
        keyframe = KeyFrame(
            image=frame.copy(),
            timestamp=timestamp,
            frame_id=self.frame_counter,
            motion_score=motion_score
        )
        
        self.keyframes.append(keyframe)
        self.last_keyframe_time = timestamp
        self.prev_gray = gray
        
        # Maintain sliding window
        if len(self.keyframes) > self.max_keyframes:
            self.keyframes.pop(0)
            
        return True
        
    def _compute_motion_score(self, prev_gray: np.ndarray, curr_gray: np.ndarray) -> float:
        """
        Compute motion score between two frames using optical flow
        
        Args:
            prev_gray: Previous grayscale frame
            curr_gray: Current grayscale frame
            
        Returns:
            Motion score (higher = more motion)
        """
        try:
            # Use sparse optical flow with FAST features
            detector = cv2.FastFeatureDetector_create()
            prev_pts = detector.detect(prev_gray)
            
            if len(prev_pts) == 0:
                return 0.0
                
            prev_pts = np.array([kp.pt for kp in prev_pts], dtype=np.float32).reshape(-1, 1, 2)
            
            # Calculate optical flow
            next_pts, status, _ = cv2.calcOpticalFlowPyrLK(
                prev_gray, curr_gray, prev_pts, None,
                winSize=(21, 21), maxLevel=3
            )
            
            # Compute median displacement
            if next_pts is None or status is None:
                return 0.0
                
            good_prev = prev_pts[status == 1]
            good_next = next_pts[status == 1]
            
            if len(good_prev) == 0:
                return 0.0
                
            displacements = np.linalg.norm(good_next - good_prev, axis=1)
            motion_score = np.median(displacements)
            
            return float(motion_score)
            
        except Exception as e:
            print(f"Error computing motion score: {e}")
            return 0.0
            
    def get_keyframes(self) -> List[KeyFrame]:
        """Get all current keyframes"""
        return self.keyframes.copy()
        
    def get_recent_keyframes(self, n: int = 10) -> List[KeyFrame]:
        """Get n most recent keyframes"""
        return self.keyframes[-n:] if len(self.keyframes) >= n else self.keyframes.copy()
        
    def clear(self):
        """Clear all keyframes and reset state"""
        self.keyframes.clear()
        self.last_keyframe_time = None
        self.prev_gray = None
        self.frame_counter = 0
