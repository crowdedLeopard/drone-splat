"""
Gaussian Reconstructor - Main reconstruction pipeline

Orchestrates the complete 3D Gaussian Splatting reconstruction pipeline:
- Frame buffering and keyframe selection
- Pose estimation via structure-from-motion
- Point cloud generation from triangulation
- Gaussian optimization
- Export to .ply/.splat formats
"""

import numpy as np
import queue
import threading
import time
import logging
from pathlib import Path
from typing import Optional, List
import yaml

from .frame_selector import FrameSelector, KeyFrame
from .pose_estimator import PoseEstimator, CameraPose
from .gaussian_trainer import GaussianTrainer
from .ply_writer import PLYWriter

try:
    from .mast3r_estimator import MASt3rEstimator, MASt3rResult
    MAST3R_AVAILABLE = MASt3rEstimator.is_available()
except ImportError:
    MAST3R_AVAILABLE = False

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class GaussianReconstructor:
    """Main 3D Gaussian Splatting reconstruction pipeline"""
    
    def __init__(self, config: dict):
        """
        Initialize reconstructor
        
        Args:
            config: Configuration dictionary with sections:
                - output_dir: Directory for output files
                - output_format: 'ply' or 'splat' (default: 'ply')
                - reconstruction_interval: Seconds between reconstruction updates (default: 5.0)
                - min_keyframes: Minimum keyframes before reconstruction (default: 10)
                - frame_selector: Config for FrameSelector
                - pose_estimator: Config for PoseEstimator
                - gaussian_trainer: Config for GaussianTrainer
        """
        self.config = config
        
        # Output settings
        self.output_dir = Path(config.get('output_dir', './output'))
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.output_format = config.get('output_format', 'ply')
        
        # Reconstruction settings
        self.reconstruction_interval = config.get('reconstruction_interval', 5.0)
        self.min_keyframes = config.get('min_keyframes', 10)
        
        # Initialize components
        self.frame_selector = FrameSelector(config.get('frame_selector', {}))
        
        # Choose pose estimator based on MASt3r availability
        use_mast3r = config.get('use_mast3r', True) and MAST3R_AVAILABLE
        if use_mast3r:
            logger.info("Using MASt3r for pose estimation (best quality)")
            self.pose_estimator = MASt3rEstimator(config.get('mast3r', {}))
            self.use_mast3r = True
        else:
            if config.get('use_mast3r', True) and not MAST3R_AVAILABLE:
                logger.warning("MASt3r requested but not available - falling back to SIFT")
            self.pose_estimator = PoseEstimator(config.get('pose_estimator', {}))
            self.use_mast3r = False
            
        self.gaussian_trainer = GaussianTrainer(config.get('gaussian_trainer', {}))
        self.ply_writer = PLYWriter()
        
        # State
        self.last_reconstruction_time = 0.0
        self.reconstruction_count = 0
        self.latest_output_path: Optional[str] = None
        self.is_running = False
        
        logger.info("GaussianReconstructor initialized")
        logger.info(f"Output directory: {self.output_dir}")
        logger.info(f"Reconstruction interval: {self.reconstruction_interval}s")
        
    def add_frame(self, frame: np.ndarray, timestamp: float) -> bool:
        """
        Add a new frame to the reconstruction pipeline
        
        Args:
            frame: Input frame (BGR or RGB numpy array)
            timestamp: Frame timestamp in seconds
            
        Returns:
            True if a reconstruction update was triggered
        """
        # Add to frame selector
        is_keyframe = self.frame_selector.add_frame(frame, timestamp)
        
        if is_keyframe:
            logger.info(f"Keyframe selected at t={timestamp:.2f}s "
                       f"(total: {len(self.frame_selector.keyframes)})")
                       
        # Check if we should trigger reconstruction
        time_since_last = timestamp - self.last_reconstruction_time
        num_keyframes = len(self.frame_selector.keyframes)
        
        should_reconstruct = (
            num_keyframes >= self.min_keyframes and
            time_since_last >= self.reconstruction_interval
        )
        
        if should_reconstruct:
            logger.info(f"Triggering reconstruction with {num_keyframes} keyframes")
            success = self._reconstruct()
            if success:
                self.last_reconstruction_time = timestamp
                return True
                
        return False
        
    def _reconstruct(self) -> bool:
        """
        Run reconstruction pipeline on current keyframes
        
        Returns:
            True if reconstruction succeeded
        """
        try:
            keyframes = self.frame_selector.get_keyframes()
            
            if len(keyframes) < self.min_keyframes:
                logger.warning(f"Not enough keyframes: {len(keyframes)} < {self.min_keyframes}")
                return False
                
            images = [kf.image for kf in keyframes]
            
            # Step 1: Estimate camera poses and get point cloud
            if self.use_mast3r:
                logger.info("Running MASt3r reconstruction...")
                result = self.pose_estimator.reconstruct(images)
                points = result.points
                colors = result.colors
                
                # Convert MASt3r poses to CameraPose objects
                poses = []
                for i, p in enumerate(result.poses):
                    # p is (4, 4) camera-to-world
                    # CameraPose expects world-to-camera (T matrix)
                    T = np.linalg.inv(p)
                    pose = CameraPose(R=T[:3, :3], t=T[:3, 3:], frame_id=i)
                    poses.append(pose)
                
                camera_matrix = result.intrinsics[0] if result.intrinsics else None
                
                if camera_matrix is None:
                    logger.error("MASt3r did not return camera intrinsics")
                    return False
                    
            else:
                # Original SIFT path
                logger.info("Estimating camera poses...")
                poses = self.pose_estimator.estimate_poses_sequential(images)
                
                if len(poses) < 2:
                    logger.error("Failed to estimate poses")
                    return False
                    
                # Step 2: Generate point cloud via triangulation
                logger.info("Generating point cloud...")
                points, colors = self.pose_estimator.get_point_cloud(images, poses)
                
                camera_matrix = self.pose_estimator.K
            
            if len(points) < 100:
                logger.error(f"Not enough points for reconstruction: {len(points)}")
                return False
            
            # Step 3: Train Gaussians
            logger.info("Training Gaussian Splats...")
            
            gaussians = self.gaussian_trainer.train(
                points, colors, images, poses, camera_matrix
            )
            
            # Step 4: Export to file
            logger.info("Exporting to file...")
            gaussian_dict = self.gaussian_trainer.get_gaussians_numpy()
            
            self.reconstruction_count += 1
            output_filename = f"reconstruction_{self.reconstruction_count:04d}.{self.output_format}"
            output_path = self.output_dir / output_filename
            
            self.ply_writer.write_from_dict(
                str(output_path),
                gaussian_dict,
                format=self.output_format
            )
            
            self.latest_output_path = str(output_path)
            
            logger.info(f"Reconstruction completed: {output_path}")
            logger.info(f"Total Gaussians: {len(gaussian_dict['means'])}")
            
            return True
            
        except Exception as e:
            logger.error(f"Reconstruction failed: {e}", exc_info=True)
            return False
            
    def get_output_path(self) -> str:
        """
        Get path to latest output file
        
        Returns:
            Path to latest .ply/.splat file, or empty string if none
        """
        return self.latest_output_path or ""
        
    def run(self, frame_queue: queue.Queue, stop_event: threading.Event):
        """
        Main loop: consume frames from queue and periodically reconstruct
        
        Args:
            frame_queue: Queue of (frame, timestamp) tuples
            stop_event: Threading event to signal stop
        """
        self.is_running = True
        logger.info("Reconstructor thread started")
        
        try:
            while not stop_event.is_set():
                try:
                    # Get frame from queue with timeout
                    frame, timestamp = frame_queue.get(timeout=0.1)
                    
                    # Process frame
                    self.add_frame(frame, timestamp)
                    
                    frame_queue.task_done()
                    
                except queue.Empty:
                    continue
                except Exception as e:
                    logger.error(f"Error processing frame: {e}", exc_info=True)
                    
        except KeyboardInterrupt:
            logger.info("Received keyboard interrupt")
        finally:
            self.is_running = False
            logger.info("Reconstructor thread stopped")
            
    def save_config(self, filepath: str):
        """Save current configuration to YAML file"""
        with open(filepath, 'w') as f:
            yaml.dump(self.config, f, default_flow_style=False)
            
    @classmethod
    def from_config_file(cls, filepath: str) -> 'GaussianReconstructor':
        """Create reconstructor from YAML config file"""
        with open(filepath, 'r') as f:
            config = yaml.safe_load(f)
        return cls(config)
        
    def get_stats(self) -> dict:
        """
        Get reconstruction statistics
        
        Returns:
            Dictionary with current stats
        """
        return {
            'num_keyframes': len(self.frame_selector.keyframes),
            'num_reconstructions': self.reconstruction_count,
            'latest_output': self.latest_output_path,
            'is_running': self.is_running,
            'last_reconstruction_time': self.last_reconstruction_time,
        }


def create_default_config() -> dict:
    """Create default configuration for GaussianReconstructor"""
    return {
        'output_dir': './output/reconstructions',
        'output_format': 'ply',  # 'ply' or 'splat'
        'reconstruction_interval': 5.0,  # seconds between reconstructions
        'min_keyframes': 10,
        
        'frame_selector': {
            'min_interval': 0.5,  # seconds
            'max_interval': 2.0,
            'motion_threshold': 5.0,  # pixels
            'max_keyframes': 50,
        },
        
        'pose_estimator': {
            'focal_length': None,  # Auto-estimate
            'principal_point': None,  # Auto-estimate (image center)
            'feature_detector': 'sift',  # 'sift' or 'orb'
            'min_features': 100,
            'ransac_threshold': 1.0,
        },
        
        'gaussian_trainer': {
            'num_iterations': 300,  # Quick iterations for demo
            'learning_rate': 0.01,
            'sh_degree': 3,
            'densify_interval': 100,
            'device': 'cuda',  # 'cuda' or 'cpu'
        },
    }


if __name__ == '__main__':
    # Example usage
    config = create_default_config()
    reconstructor = GaussianReconstructor(config)
    
    # Save default config
    reconstructor.save_config('./config/reconstruction_config.yaml')
    print("Default config saved to ./config/reconstruction_config.yaml")
