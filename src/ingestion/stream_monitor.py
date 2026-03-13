"""
Stream connection monitor and reconnection logic.
"""

import time
import logging
import threading
from typing import Callable, Optional

logger = logging.getLogger(__name__)


class StreamMonitor:
    """
    Monitors RTMP stream connection health and handles reconnection.
    """
    
    def __init__(self, 
                 ingestor,
                 check_interval: float = 5.0,
                 reconnect_delay: float = 10.0,
                 max_reconnect_attempts: int = 0):  # 0 = infinite
        """
        Args:
            ingestor: RTMPIngestor instance to monitor
            check_interval: How often to check connection (seconds)
            reconnect_delay: Delay before reconnect attempt (seconds)
            max_reconnect_attempts: Max reconnect tries (0 = infinite)
        """
        self.ingestor = ingestor
        self.check_interval = check_interval
        self.reconnect_delay = reconnect_delay
        self.max_reconnect_attempts = max_reconnect_attempts
        
        self.running = False
        self.monitor_thread: Optional[threading.Thread] = None
        self.last_frame_count = 0
        self.last_check_time = time.time()
        self.reconnect_count = 0
        
        self.status_callback: Optional[Callable] = None
        
    def set_status_callback(self, callback: Callable[[str, dict], None]):
        """
        Set callback for status updates.
        
        callback(status: str, info: dict)
        status: 'connected', 'disconnected', 'reconnecting', 'failed'
        """
        self.status_callback = callback
        
    def _notify_status(self, status: str, **kwargs):
        """Notify status change via callback."""
        if self.status_callback:
            self.status_callback(status, kwargs)
        logger.info(f"Stream status: {status} {kwargs}")
        
    def start(self):
        """Start monitoring."""
        if self.running:
            return
            
        self.running = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        logger.info("Stream monitor started")
        
    def stop(self):
        """Stop monitoring."""
        self.running = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        logger.info("Stream monitor stopped")
        
    def _is_alive(self) -> bool:
        """Check if stream is alive (frames flowing)."""
        if not self.ingestor.process:
            return False
            
        if self.ingestor.process.poll() is not None:
            return False
            
        current_count = self.ingestor.frame_count
        is_alive = current_count > self.last_frame_count
        
        self.last_frame_count = current_count
        return is_alive
        
    def _reconnect(self) -> bool:
        """Attempt to reconnect."""
        logger.info("Attempting reconnection...")
        self._notify_status('reconnecting', attempt=self.reconnect_count + 1)
        
        self.ingestor.stop()
        time.sleep(self.reconnect_delay)
        
        if self.ingestor.start():
            self.reconnect_count = 0
            self._notify_status('connected')
            return True
        else:
            self.reconnect_count += 1
            return False
            
    def _monitor_loop(self):
        """Main monitoring loop."""
        last_alive = True
        stale_count = 0
        
        while self.running:
            time.sleep(self.check_interval)
            
            is_alive = self._is_alive()
            
            if is_alive:
                if not last_alive:
                    logger.info("Stream recovered")
                    self._notify_status('connected')
                stale_count = 0
            else:
                stale_count += 1
                logger.warning(f"Stream appears dead (check {stale_count})")
                
                if stale_count >= 2:  # Confirm it's really dead
                    if last_alive:
                        logger.error("Stream disconnected")
                        self._notify_status('disconnected')
                    
                    if self.max_reconnect_attempts == 0 or self.reconnect_count < self.max_reconnect_attempts:
                        if not self._reconnect():
                            logger.error(f"Reconnect attempt {self.reconnect_count} failed")
                    else:
                        logger.error("Max reconnect attempts reached, giving up")
                        self._notify_status('failed', reason='max_reconnects')
                        self.running = False
                        break
            
            last_alive = is_alive
            
        logger.info("Monitor loop exited")
