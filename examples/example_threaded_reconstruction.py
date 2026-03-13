"""
Example: Threaded reconstruction with frame queue
Demonstrates integration with a video stream (e.g., from Amos's RTMP extraction)
"""

import numpy as np
import queue
import threading
import time
from pathlib import Path
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.reconstruction import GaussianReconstructor


def frame_producer(frame_queue: queue.Queue, stop_event: threading.Event):
    """
    Simulates Amos's frame extraction thread
    In reality, this would read from RTMP stream
    """
    print("[Producer] Starting frame generation...")
    
    frame_count = 0
    start_time = time.time()
    
    while not stop_event.is_set() and frame_count < 100:
        # Simulate 30 fps video
        time.sleep(1.0 / 30.0)
        
        # Generate test frame (replace with real RTMP frames)
        frame = np.random.randint(0, 255, (720, 1280, 3), dtype=np.uint8)
        
        # Add visual features
        cv2_available = True
        try:
            import cv2
            angle = (frame_count * 3) % 360
            x = int(640 + 200 * np.cos(np.radians(angle)))
            y = int(360 + 200 * np.sin(np.radians(angle)))
            cv2.circle(frame, (x, y), 50, (255, 0, 0), -1)
            cv2.rectangle(frame, (500, 300), (700, 500), (0, 255, 0), 3)
        except ImportError:
            cv2_available = False
        
        timestamp = time.time() - start_time
        
        # Push to queue
        frame_queue.put((frame, timestamp))
        frame_count += 1
        
        if frame_count % 30 == 0:
            print(f"[Producer] Generated {frame_count} frames")
    
    print(f"[Producer] Finished after {frame_count} frames")


def main():
    print("=" * 60)
    print("Threaded Reconstruction Example")
    print("=" * 60)
    print()
    
    # Load configuration
    config_path = Path(__file__).parent.parent / "config" / "reconstruction_config.yaml"
    
    if config_path.exists():
        print(f"Loading config from: {config_path}")
        reconstructor = GaussianReconstructor.from_config_file(str(config_path))
    else:
        print("Using default configuration")
        config = GaussianReconstructor.create_default_config()
        
        # Adjust for demo
        config['gaussian_trainer']['num_iterations'] = 100
        config['min_keyframes'] = 8
        config['reconstruction_interval'] = 3.0
        
        reconstructor = GaussianReconstructor(config)
    
    print()
    
    # Setup threading
    frame_queue = queue.Queue(maxsize=60)  # Buffer up to 2 seconds at 30fps
    stop_event = threading.Event()
    
    # Start producer thread (simulates Amos's frame extraction)
    producer_thread = threading.Thread(
        target=frame_producer,
        args=(frame_queue, stop_event),
        daemon=True
    )
    producer_thread.start()
    
    # Start reconstruction thread
    print("[Reconstructor] Starting reconstruction thread...")
    recon_thread = threading.Thread(
        target=reconstructor.run,
        args=(frame_queue, stop_event),
        daemon=False
    )
    recon_thread.start()
    
    print()
    print("Both threads running. Ctrl+C to stop.")
    print()
    
    try:
        # Monitor progress
        last_stats = None
        while producer_thread.is_alive():
            time.sleep(2.0)
            
            stats = reconstructor.get_stats()
            
            # Print updates
            if stats != last_stats:
                print(f"[Status] Keyframes: {stats['num_keyframes']}, "
                      f"Reconstructions: {stats['num_reconstructions']}, "
                      f"Queue size: {frame_queue.qsize()}")
                
                if stats['latest_output']:
                    print(f"         Latest: {stats['latest_output']}")
                    
                last_stats = stats.copy()
        
        # Wait for producer to finish
        print()
        print("Waiting for producer thread to complete...")
        producer_thread.join(timeout=5.0)
        
        # Signal reconstruction to stop
        print("Stopping reconstruction thread...")
        stop_event.set()
        recon_thread.join(timeout=10.0)
        
    except KeyboardInterrupt:
        print()
        print("Interrupted! Stopping threads...")
        stop_event.set()
        
        producer_thread.join(timeout=2.0)
        recon_thread.join(timeout=5.0)
    
    # Final stats
    print()
    print("=" * 60)
    print("Final Statistics")
    print("=" * 60)
    
    stats = reconstructor.get_stats()
    for key, value in stats.items():
        print(f"  {key}: {value}")
    
    print()
    
    if stats['latest_output']:
        print("✓ Reconstruction completed!")
        print(f"  Output: {stats['latest_output']}")
        print()
        print("View with:")
        print("  - Blender + Gaussian Splatting addon")
        print("  - SuperSplat: https://playcanvas.com/supersplat")
    else:
        print("⚠ No reconstruction generated (not enough frames)")


if __name__ == '__main__':
    main()
