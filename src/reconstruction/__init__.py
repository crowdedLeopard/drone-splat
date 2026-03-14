"""
3D Reconstruction Module

Performs 3D Gaussian Splatting reconstruction from frame sequences.

Components (Path B - Working):
- GaussianReconstructor: Main incremental reconstruction pipeline (Naomi)
- FrameSelector: Keyframe selection (Naomi)
- PoseEstimator: Camera pose estimation (Naomi)
- GaussianTrainer: 3DGS optimization (Naomi)
- PLYWriter: Output format writer (Naomi)

Legacy Components (Path A - Deprecated):
- SLAMProcessor: Available but not used in main pipeline (uses loguru)
- ModelManager: Available but not used in main pipeline
"""

# Path B modules (working, actively used)
from .reconstructor import GaussianReconstructor
from .frame_selector import FrameSelector
from .pose_estimator import PoseEstimator
from .gaussian_trainer import GaussianTrainer
from .ply_writer import PLYWriter

# Path A modules available for import but not in default exports
# (Avoid importing by default to prevent loguru dependency)
# from .slam_processor import SLAMProcessor
# from .model_manager import ModelManager

__all__ = [
    # Path B exports (actively used)
    'GaussianReconstructor',
    'FrameSelector',
    'PoseEstimator',
    'GaussianTrainer',
    'PLYWriter',
]
