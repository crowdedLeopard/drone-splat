"""
RTMP frame extractor using FFmpeg.
Pulls frames from RTMP stream and puts them into a queue for reconstruction.
"""

import subprocess
import threading
import queue
import time
import numpy as np
import logging
from typing import Optional, Dict

logger = logging.getLogger(__name__)


class RTMPIngestor:
    """
    Extracts frames from RTMP stream using FFmpeg and puts them in a queue.
    
    Uses FFmpeg pipe output to avoid temp files — cleaner and faster.
    """
    
    def __init__(self, config: Dict):
        """
        config keys:
        - rtmp_url: e.g. "rtmp://localhost:1935/live/drone"
        - frame_rate: extraction fps (e.g. 2.0)
        - width: expected frame width (default 1920)
        - height: expected frame height (default 1080)
        - frame_queue: threading.Queue to put frames into
        """
        self.rtmp_url = config['rtmp_url']
        self.frame_rate = config.get('frame_rate', 2.0)
        self.width = config.get('width', 1920)
        self.height = config.get('height', 1080)
        self.frame_queue = config.get('frame_queue')
        
        self.process: Optional[subprocess.Popen] = None
        self.running = False
        self.frame_count = 0
        
    def start(self) -> bool:
        """Start FFmpeg subprocess to pull RTMP and extract frames."""
        if self.running:
            logger.warning("Ingestor already running")
            return False
            
        ffmpeg_cmd = [
            'ffmpeg',
            '-i', self.rtmp_url,
            '-vf', f'fps={self.frame_rate}',
            '-s', f'{self.width}x{self.height}',
            '-f', 'rawvideo',
            '-pix_fmt', 'bgr24',
            '-loglevel', 'error',
            'pipe:1'
        ]
        
        try:
            self.process = subprocess.Popen(
                ffmpeg_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                bufsize=10**8
            )
            self.running = True
            logger.info(f"FFmpeg started for {self.rtmp_url} at {self.frame_rate} fps")
            return True
        except Exception as e:
            logger.error(f"Failed to start FFmpeg: {e}")
            return False
    
    def stop(self):
        """Stop FFmpeg subprocess cleanly."""
        self.running = False
        if self.process:
            try:
                self.process.terminate()
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
            finally:
                self.process = None
        logger.info("Ingestor stopped")
    
    def run(self, frame_queue: queue.Queue, stop_event: threading.Event):
        """
        Main loop: extract frames from RTMP stream, put into queue.
        
        Args:
            frame_queue: Queue to put extracted frames
            stop_event: Event to signal stop
        """
        self.frame_queue = frame_queue
        
        if not self.start():
            logger.error("Failed to start ingestor")
            return
        
        frame_size = self.width * self.height * 3  # BGR = 3 bytes per pixel
        
        try:
            while self.running and not stop_event.is_set():
                if not self.process or self.process.poll() is not None:
                    logger.error("FFmpeg process died")
                    break
                
                raw_frame = self.process.stdout.read(frame_size)
                
                if len(raw_frame) != frame_size:
                    logger.warning(f"Incomplete frame: got {len(raw_frame)} bytes, expected {frame_size}")
                    continue
                
                frame = np.frombuffer(raw_frame, dtype=np.uint8)
                frame = frame.reshape((self.height, self.width, 3))
                
                frame_data = {
                    'frame': frame,
                    'timestamp': time.time(),
                    'frame_id': self.frame_count
                }
                
                try:
                    frame_queue.put(frame_data, timeout=1.0)
                    self.frame_count += 1
                    
                    if self.frame_count % 10 == 0:
                        logger.debug(f"Extracted {self.frame_count} frames")
                        
                except queue.Full:
                    logger.warning("Frame queue full, dropping frame")
                    
        except KeyboardInterrupt:
            logger.info("Interrupted by user")
        except Exception as e:
            logger.error(f"Error in frame extraction loop: {e}")
        finally:
            self.stop()
            logger.info(f"Extracted total {self.frame_count} frames")
