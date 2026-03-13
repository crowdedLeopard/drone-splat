"""
RTMP Stream Listener

Monitors RTMP stream using MediaMTX server.
Provides stream status and connectivity information.

Owner: Amos
"""

import time
import requests
from pathlib import Path
from loguru import logger


class RTMPListener:
    """Listens for and monitors RTMP stream from MediaMTX server"""
    
    def __init__(self, config: dict):
        self.config = config
        self.host = config['host']
        self.port = config['port']
        self.app = config['app']
        self.stream_key = config['stream_key']
        self.running = False
        self.stream_active = False
        
        # RTMP URL that DJI drone should connect to
        # Note: User needs to replace <your-ip> with actual IP
        self.rtmp_url = f"rtmp://<your-ip>:{self.port}/{self.app}/{self.stream_key}"
        
        logger.info(f"RTMP Listener initialized for stream: {self.rtmp_url}")
    
    def start(self):
        """Start listening for RTMP stream"""
        self.running = True
        logger.info(f"RTMP Listener started. Waiting for stream at {self.rtmp_url}")
        logger.info("Configure DJI drone to stream to this URL")
        
        # Note: Actual implementation would monitor MediaMTX API or log files
        # For now, this is a stub that Amos will implement
    
    def is_stream_active(self) -> bool:
        """Check if RTMP stream is currently active"""
        # TODO (Amos): Implement stream detection via MediaMTX API
        # MediaMTX provides HTTP API at http://localhost:9997/v1/paths/list
        return self.stream_active
    
    def get_stream_url(self) -> str:
        """Get the RTMP stream URL for connection"""
        return self.rtmp_url
    
    def get_stats(self) -> dict:
        """Get stream statistics"""
        return {
            'active': self.stream_active,
            'rtmp_url': self.rtmp_url,
        }
    
    def is_healthy(self) -> bool:
        """Check if listener is healthy"""
        return self.running
    
    def stop(self, timeout: int = 30):
        """Stop the RTMP listener"""
        self.running = False
        logger.info("RTMP Listener stopped")
