"""
Example: Basic reconstruction from video frames
Demonstrates the simplest usage of the reconstruction module
"""

import numpy as np
import cv2
from pathlib import Path
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.reconstruction import GaussianReconstructor


def load_example_frames(video_path: str, max_frames: int = 100):
    """Load frames from video file"""
    cap = cv2.VideoCapture(video_path)
    frames = []
    timestamps = []
    
    fps = cap.get(cv2.CAP_PROP_FPS)
    frame_idx = 0
    
    while len(frames) < max_frames:
        ret, frame = cap.read()
        if not ret:
            break
            
        frames.append(frame)
        timestamps.append(frame_idx / fps)
        frame_idx += 1
        
    cap.release()
    
    print(f"Loaded {len(frames)} frames from {video_path}")
    return frames, timestamps


def main():
    # Load configuration
    config = GaussianReconstructor.create_default_config()
    
    # Adjust for quick demo
    config['gaussian_trainer']['num_iterations'] = 100  # Faster
    config['min_keyframes'] = 5  # Start reconstruction sooner
    
    print("Configuration:")
    print(f"  Output: {config['output_dir']}")
    print(f"  Min keyframes: {config['min_keyframes']}")
    print(f"  Iterations: {config['gaussian_trainer']['num_iterations']}")
    print()
    
    # Create reconstructor
    reconstructor = GaussianReconstructor(config)
    
    # Option 1: Load from video file
    # video_path = "path/to/your/video.mp4"
    # frames, timestamps = load_example_frames(video_path)
    
    # Option 2: Synthetic test sequence (rotating camera)
    print("Generating synthetic test sequence...")
    frames = []
    timestamps = []
    
    for i in range(30):
        # Create random test frame (replace with real video)
        frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
        
        # Add some structure so features can be detected
        cv2.circle(frame, (320, 240), 100, (255, 0, 0), -1)
        cv2.rectangle(frame, (100, 100), (200, 200), (0, 255, 0), -1)
        
        frames.append(frame)
        timestamps.append(i * 0.1)  # 10 fps
    
    print(f"Generated {len(frames)} test frames")
    print()
    
    # Process frames
    print("Processing frames...")
    for i, (frame, timestamp) in enumerate(zip(frames, timestamps)):
        triggered = reconstructor.add_frame(frame, timestamp)
        
        if triggered:
            print(f"✓ Reconstruction updated at frame {i}")
            print(f"  Output: {reconstructor.get_output_path()}")
            print()
    
    # Get final stats
    stats = reconstructor.get_stats()
    print("Final Statistics:")
    print(f"  Keyframes selected: {stats['num_keyframes']}")
    print(f"  Reconstructions: {stats['num_reconstructions']}")
    print(f"  Latest output: {stats['latest_output']}")
    
    if stats['latest_output']:
        print()
        print("Success! Open the .ply file in:")
        print("  - Blender (with Gaussian Splatting addon)")
        print("  - SuperSplat: https://playcanvas.com/supersplat")
        print("  - antimatter15 viewer")


if __name__ == '__main__':
    main()
