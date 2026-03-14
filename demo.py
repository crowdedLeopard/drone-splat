"""
Demo: Synthetic Frame Testing for 3D Gaussian Splatting Pipeline

Tests the full pipeline without needing a drone or RTMP stream.
Generates synthetic frames and feeds them through the reconstruction system.

Author: Holden (Lead Architect)
"""

import sys
import time
import logging
import webbrowser
from pathlib import Path
import numpy as np
import yaml

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from reconstruction.reconstructor import GaussianReconstructor
from viewer.viewer_server import ViewerServer

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def generate_synthetic_frames(n=50, width=640, height=480):
    """
    Generate synthetic frames simulating a slow camera pan.
    
    Creates a textured checkerboard pattern with simulated camera motion.
    Adds noise to provide feature points for reconstruction.
    
    Args:
        n: Number of frames to generate
        width: Frame width in pixels
        height: Frame height in pixels
        
    Returns:
        List of numpy arrays (BGR format)
    """
    logger.info(f"Generating {n} synthetic frames ({width}x{height})...")
    frames = []
    
    for i in range(n):
        frame = np.zeros((height, width, 3), dtype=np.uint8)
        
        # Add checkerboard texture (provides feature points)
        for y in range(0, height, 32):
            for x in range(0, width, 32):
                if (x//32 + y//32) % 2 == 0:
                    frame[y:y+32, x:x+32] = [200, 180, 160]
                else:
                    frame[y:y+32, x:x+32] = [100, 90, 80]
        
        # Simulate camera motion (horizontal pan)
        offset = i * 2
        frame = np.roll(frame, offset, axis=1)
        
        # Add random noise (provides additional texture)
        noise = np.random.randint(0, 20, frame.shape, dtype=np.uint8)
        frame = np.clip(frame.astype(int) + noise, 0, 255).astype(np.uint8)
        
        # Add some vertical variation
        if i % 10 == 0:
            vertical_offset = (i // 10) * 5
            frame = np.roll(frame, vertical_offset, axis=0)
        
        frames.append(frame)
        
        if (i + 1) % 10 == 0:
            logger.debug(f"Generated {i + 1}/{n} frames")
    
    logger.info(f"Synthetic frame generation complete")
    return frames


def load_config_with_overrides():
    """
    Load config.yaml and override for demo mode
    
    Returns:
        Configuration dict optimized for demo
    """
    config_path = Path(__file__).parent / 'config' / 'config.yaml'
    
    if not config_path.exists():
        logger.warning(f"Config file not found at {config_path}, using defaults")
        config = {}
    else:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
    
    # Demo overrides
    demo_output_dir = Path(__file__).parent / 'data' / 'output'
    demo_output_dir.mkdir(parents=True, exist_ok=True)
    
    demo_config = {
        'output_dir': str(demo_output_dir),
        'output_format': 'ply',
        'reconstruction_interval': 3.0,  # Reconstruct every 3 seconds
        'min_keyframes': 5,  # Fewer keyframes needed for demo
        'frame_selector': {
            'min_interval': 0.3,
            'max_interval': 1.0,
            'motion_threshold': 3.0,
            'max_keyframes': 20,
        },
        'pose_estimator': {
            'feature_detector': 'sift',
            'min_features': 50,
        },
        'gaussian_trainer': {
            'num_iterations': 200,  # Faster for demo
            'device': config.get('reconstruction', {}).get('device', 'cuda'),
        },
    }
    
    # Viewer config
    viewer_config = config.get('viewer', {})
    if not viewer_config:
        viewer_config = {
            'type': 'web',
            'web': {
                'host': 'localhost',
                'port': 8080,
                'auto_refresh_interval': 2000,
            }
        }
    
    return demo_config, viewer_config


def main():
    """Main demo entry point"""
    logger.info("=" * 60)
    logger.info("3D Gaussian Splatting Demo - Synthetic Frames")
    logger.info("=" * 60)
    
    # Load configuration
    reconstructor_config, viewer_config = load_config_with_overrides()
    
    logger.info(f"Output directory: {reconstructor_config['output_dir']}")
    logger.info(f"Device: {reconstructor_config['gaussian_trainer']['device']}")
    
    # Initialize components
    logger.info("Initializing reconstructor...")
    reconstructor = GaussianReconstructor(reconstructor_config)
    
    logger.info("Initializing viewer...")
    viewer = ViewerServer(viewer_config)
    viewer.start()
    
    viewer_url = f"http://{viewer_config['web']['host']}:{viewer_config['web']['port']}"
    logger.info(f"Viewer available at: {viewer_url}")
    
    # Generate synthetic frames
    frames = generate_synthetic_frames(n=50, width=640, height=480)
    
    logger.info("=" * 60)
    logger.info("Starting reconstruction from synthetic frames...")
    logger.info("This may take a few minutes depending on your GPU")
    logger.info("=" * 60)
    
    # Process frames
    start_time = time.time()
    reconstruction_count = 0
    
    for i, frame in enumerate(frames):
        timestamp = i * 0.5  # Simulate 2 fps
        
        updated = reconstructor.add_frame(frame, timestamp)
        
        if updated:
            reconstruction_count += 1
            output_path = reconstructor.get_output_path()
            logger.info(f"Reconstruction #{reconstruction_count} saved: {output_path}")
            
            # Notify viewer
            if viewer and output_path:
                viewer.notify_update(Path(output_path))
        
        # Small delay to simulate real-time
        time.sleep(0.05)
    
    elapsed = time.time() - start_time
    
    logger.info("=" * 60)
    logger.info(f"Demo complete!")
    logger.info(f"Processed {len(frames)} frames in {elapsed:.1f} seconds")
    logger.info(f"Generated {reconstruction_count} reconstruction(s)")
    
    if reconstruction_count > 0:
        output_path = reconstructor.get_output_path()
        logger.info(f"Latest output: {output_path}")
        logger.info(f"View at: {viewer_url}")
        
        # Open browser automatically
        try:
            logger.info("Opening viewer in browser...")
            webbrowser.open(viewer_url)
        except Exception as e:
            logger.warning(f"Could not auto-open browser: {e}")
    else:
        logger.warning("No reconstructions generated - check logs above for errors")
    
    logger.info("=" * 60)
    logger.info("Press Ctrl+C to exit")
    
    # Keep viewer running
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        viewer.stop()
        logger.info("Demo stopped")


if __name__ == '__main__':
    main()
