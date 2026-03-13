"""
3D Reconstruction Module

Performs 3D Gaussian Splatting reconstruction from frame sequences.

Components:
- SLAMProcessor: SLAM-based processing (Holden)
- ModelManager: Model lifecycle management (Holden)
- GaussianReconstructor: Main incremental reconstruction pipeline (Naomi)
- FrameSelector: Keyframe selection (Naomi)
- PoseEstimator: Camera pose estimation (Naomi)
- GaussianTrainer: 3DGS optimization (Naomi)
- PLYWriter: Output format writer (Naomi)
"""

# Holden's modules
from .slam_processor import SLAMProcessor
from .model_manager import ModelManager

# Naomi's modules
from .reconstructor import GaussianReconstructor
from .frame_selector import FrameSelector
from .pose_estimator import PoseEstimator
from .gaussian_trainer import GaussianTrainer
from .ply_writer import PLYWriter

__all__ = [
    # Holden's modules
    'SLAMProcessor',
    'ModelManager',
    # Naomi's modules
    'GaussianReconstructor',
    'FrameSelector',
    'PoseEstimator',
    'GaussianTrainer',
    'PLYWriter',
]
