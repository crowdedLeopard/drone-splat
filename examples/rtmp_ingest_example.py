"""
Example: Simple frame extraction from RTMP stream

Run this after starting mediamtx (.\scripts\start_stream.ps1)
and either:
1. Starting a test stream (.\scripts\test_stream.ps1), or
2. Streaming from DJI Fly app
"""

import queue
import threading
import time
import logging
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.ingestion import RTMPIngestor, StreamMonitor

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%H:%M:%S'
)

logger = logging.getLogger(__name__)


def status_callback(status: str, info: dict):
    """Called when stream connection status changes."""
    logger.info(f"Stream status changed: {status} {info}")


def main():
    # Configuration
    config = {
        'rtmp_url': 'rtmp://localhost:1935/live/drone',
        'frame_rate': 2.0,      # Extract 2 frames per second
        'width': 1920,
        'height': 1080
    }
    
    # Create frame queue
    frame_queue = queue.Queue(maxsize=100)
    stop_event = threading.Event()
    
    # Create ingestor and monitor
    logger.info("Creating RTMP ingestor...")
    ingestor = RTMPIngestor(config)
    
    logger.info("Creating stream monitor...")
    monitor = StreamMonitor(
        ingestor,
        check_interval=5.0,
        reconnect_delay=10.0,
        max_reconnect_attempts=0  # infinite retries
    )
    monitor.set_status_callback(status_callback)
    monitor.start()
    
    # Start ingestion thread
    logger.info("Starting ingestion thread...")
    ingest_thread = threading.Thread(
        target=ingestor.run,
        args=(frame_queue, stop_event),
        daemon=True
    )
    ingest_thread.start()
    
    # Process frames
    logger.info("Ready to receive frames. Press Ctrl+C to stop.")
    logger.info(f"Waiting for stream at: {config['rtmp_url']}")
    logger.info("")
    
    frame_count = 0
    start_time = time.time()
    
    try:
        while True:
            try:
                frame_data = frame_queue.get(timeout=5.0)
                
                frame = frame_data['frame']
                timestamp = frame_data['timestamp']
                frame_id = frame_data['frame_id']
                
                frame_count += 1
                elapsed = time.time() - start_time
                fps = frame_count / elapsed if elapsed > 0 else 0
                
                logger.info(
                    f"Frame {frame_id:04d}: shape={frame.shape}, "
                    f"dtype={frame.dtype}, avg_fps={fps:.2f}"
                )
                
                # Here you would pass the frame to reconstruction module
                # For now, just count frames
                
            except queue.Empty:
                logger.warning("No frames received in last 5 seconds (stream not connected?)")
                
    except KeyboardInterrupt:
        logger.info("\nStopping...")
        
    finally:
        # Cleanup
        stop_event.set()
        monitor.stop()
        ingest_thread.join(timeout=3)
        
        elapsed = time.time() - start_time
        if elapsed > 0:
            avg_fps = frame_count / elapsed
            logger.info(f"Total frames: {frame_count}, average FPS: {avg_fps:.2f}")
        
        logger.info("Done.")


if __name__ == '__main__':
    main()
