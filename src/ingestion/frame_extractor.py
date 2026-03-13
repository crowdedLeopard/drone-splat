"""
Frame Extraction from RTMP Stream

Extracts frames from RTMP stream using FFmpeg at configured rate.
Provides frames to reconstruction pipeline.

Owner: Amos
"""

import subprocess
import threading
import time
from pathlib import Path
from queue import Queue
from loguru import logger
import cv2


class FrameExtractor:
    """Extracts frames from RTMP stream using FFmpeg"""
    
    def __init__(self, config: dict):
        self.config = config
        self.frame_rate = config['frame_rate']
        self.frames_dir = Path(config['frames_dir'])
        self.frame_format = config['frame_format']
        self.frame_quality = config['frame_quality']
        self.max_buffer = config['max_frames_buffer']
        self.cleanup_old = config['cleanup_old_frames']
        
        self.running = False
        self.frame_queue = Queue(maxsize=self.max_buffer)
        self.frame_count = 0
        self.ffmpeg_process = None
        
        self.frames_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Frame Extractor initialized: {self.frame_rate} fps -> {self.frames_dir}")
    
    def start(self, rtmp_listener):
        """Start extracting frames from RTMP stream"""
        self.running = True
        self.rtmp_url = rtmp_listener.get_stream_url()
        
        # Start extraction thread
        extract_thread = threading.Thread(target=self._extraction_loop, daemon=True)
        extract_thread.start()
        
        logger.info(f"Frame extraction started from {self.rtmp_url}")
    
    def _extraction_loop(self):
        """Main extraction loop using FFmpeg"""
        while self.running:
            try:
                # Wait for stream to be active
                # TODO (Amos): Check stream status from RTMPListener
                time.sleep(2)
                
                # Build FFmpeg command
                output_pattern = str(self.frames_dir / f"frame_%06d.{self.frame_format}")
                
                cmd = [
                    'ffmpeg',
                    '-i', self.rtmp_url.replace('<your-ip>', 'localhost'),  # Replace placeholder
                    '-vf', f'fps={self.frame_rate}',
                    '-q:v', str(100 - self.frame_quality),  # FFmpeg quality is inverse
                    '-update', '1',  # Overwrite output
                    output_pattern
                ]
                
                logger.info(f"Starting FFmpeg extraction: {' '.join(cmd)}")
                
                # TODO (Amos): Implement actual FFmpeg subprocess
                # self.ffmpeg_process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                
                # For now, just wait
                time.sleep(1)
                
            except Exception as e:
                logger.error(f"Frame extraction error: {e}")
                if self.running:
                    time.sleep(5)  # Wait before retry
    
    def get_latest_frames(self, count: int = 1) -> list:
        """
        Get latest N frames
        
        Returns:
            List of frame file paths
        """
        # TODO (Amos): Implement frame retrieval
        frames = []
        return frames
    
    def get_frame_queue(self) -> Queue:
        """Get the frame queue for reconstruction pipeline"""
        return self.frame_queue
    
    def get_stats(self) -> dict:
        """Get extraction statistics"""
        return {
            'frame_rate': self.frame_rate,
            'total_frames': self.frame_count,
            'queue_size': self.frame_queue.qsize(),
        }
    
    def is_healthy(self) -> bool:
        """Check if extractor is healthy"""
        return self.running and (self.ffmpeg_process is None or self.ffmpeg_process.poll() is None)
    
    def stop(self, timeout: int = 30):
        """Stop frame extraction"""
        self.running = False
        
        if self.ffmpeg_process:
            self.ffmpeg_process.terminate()
            try:
                self.ffmpeg_process.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                self.ffmpeg_process.kill()
        
        logger.info("Frame Extractor stopped")
