"""
MASt3r-based pose and pointcloud estimation.
Replaces SIFT-based PoseEstimator for higher quality reconstruction.
"""

import sys
import numpy as np
import torch
from pathlib import Path
from typing import List, Optional
from dataclasses import dataclass
import logging
import tempfile
import shutil
import cv2

logger = logging.getLogger(__name__)

# Add MASt3r to path
MAST3R_PATH = Path(__file__).parent.parent.parent / "tools" / "mast3r"
DUST3R_PATH = MAST3R_PATH / "dust3r"

if not MAST3R_PATH.exists():
    raise ImportError(
        f"MASt3r not found at {MAST3R_PATH}. "
        f"Run: git clone --recursive https://github.com/naver/mast3r.git tools/mast3r"
    )

sys.path.insert(0, str(MAST3R_PATH))
sys.path.insert(0, str(DUST3R_PATH))

from mast3r.model import AsymmetricMASt3R  # type: ignore
from mast3r.fast_nn import fast_reciprocal_NNs  # type: ignore
from dust3r.inference import inference  # type: ignore
from dust3r.utils.image import load_images  # type: ignore
from dust3r.image_pairs import make_pairs  # type: ignore
from dust3r.cloud_opt import global_aligner, GlobalAlignerMode  # type: ignore


@dataclass
class MASt3rResult:
    """Result from MASt3r reconstruction"""
    points: np.ndarray          # (N, 3) 3D points
    colors: np.ndarray          # (N, 3) RGB colors [0-1]
    confidences: np.ndarray     # (N,) confidence scores
    poses: List[np.ndarray]     # List of (4, 4) camera-to-world matrices
    intrinsics: List[np.ndarray] # List of (3, 3) camera intrinsics


def voxel_downsample(points: np.ndarray, colors: np.ndarray, 
                      voxel_size: float = 0.002) -> tuple:
    """Downsample point cloud using voxel grid to ~100k points max."""
    if len(points) == 0:
        return points, colors
    
    # Create voxel indices
    mins = points.min(axis=0)
    voxel_idx = np.floor((points - mins) / voxel_size).astype(int)
    
    # One point per voxel (first encountered)
    keys = voxel_idx[:, 0] * 1000000 + voxel_idx[:, 1] * 1000 + voxel_idx[:, 2]
    _, unique_idx = np.unique(keys, return_index=True)
    
    return points[unique_idx], colors[unique_idx]


class MASt3rEstimator:
    """Dense reconstruction using MASt3r"""
    
    def __init__(self, config: dict):
        """
        Args:
            config: Configuration dict with keys:
                - model_name: MASt3r checkpoint name (default: 'naver/MASt3R_ViTLarge_BaseDecoder_512_catmlpdpt_metric')
                - device: 'cuda' or 'cpu'
                - image_size: Target resolution (default: 512)
                - confidence_threshold: Min confidence to keep point (default: 0.5)
        """
        self.model_name = config.get('model_name', 
            'naver/MASt3R_ViTLarge_BaseDecoder_512_catmlpdpt_metric')
        self.device = config.get('device', 'cuda' if torch.cuda.is_available() else 'cpu')
        self.image_size = config.get('image_size', 512)
        self.confidence_threshold = config.get('confidence_threshold', 0.5)
        
        logger.info(f"Loading MASt3r model: {self.model_name}")
        self.model = AsymmetricMASt3R.from_pretrained(self.model_name).to(self.device)
        logger.info("MASt3r model loaded")
        
    def reconstruct(self, images: List[np.ndarray]) -> MASt3rResult:
        """
        Reconstruct 3D scene from images.
        
        Args:
            images: List of RGB images (H, W, 3) as uint8 numpy arrays
            
        Returns:
            MASt3rResult with points, colors, confidences, poses, intrinsics
        """
        if len(images) < 2:
            raise ValueError("Need at least 2 images for reconstruction")
            
        # Prepare images for MASt3r
        temp_dir = tempfile.mkdtemp()
        temp_paths = []
        
        try:
            for i, img in enumerate(images):
                # Ensure RGB format
                if img.shape[2] == 4:  # RGBA
                    img = img[:, :, :3]
                path = Path(temp_dir) / f"frame_{i:04d}.png"
                cv2.imwrite(str(path), cv2.cvtColor(img, cv2.COLOR_RGB2BGR))
                temp_paths.append(str(path))
                
            # Load images with MASt3r preprocessing
            imgs = load_images(temp_paths, size=self.image_size)
            
            # Create all pairs for dense matching
            pairs = make_pairs(imgs, scene_graph='complete', prefilter=None)
            
            # Run inference
            output = inference(pairs, self.model, self.device, batch_size=1)
            
            # Global alignment to get consistent poses
            scene = global_aligner(
                output, 
                device=self.device,
                mode=GlobalAlignerMode.ModularPointCloudOptimizer
            )
            
            # Optimize (100 iterations usually sufficient)
            loss = scene.compute_global_alignment(
                init="mst", 
                niter=100, 
                schedule='cosine',
                lr=0.01
            )
            
            # Extract results
            points_3d = scene.get_pts3d()      # List of (H, W, 3) per image
            confidences = scene.get_conf()      # List of (H, W) per image
            poses = scene.get_im_poses()        # List of (4, 4) c2w matrices
            intrinsics = scene.get_intrinsics() # List of (3, 3) K matrices
            
            # Merge all pointmaps into single point cloud
            all_points = []
            all_colors = []
            all_confs = []
            
            for i, (pts, conf, img) in enumerate(zip(points_3d, confidences, images)):
                # pts is (H, W, 3) in camera space
                pts_np = pts.cpu().numpy()
                conf_np = conf.cpu().numpy()
                
                H, W = pts_np.shape[:2]
                pts_flat = pts_np.reshape(-1, 3)
                conf_flat = conf_np.reshape(-1)
                
                # Get corresponding colors from original image
                # Resize image to match pointmap size
                img_resized = cv2.resize(img, (W, H))
                colors_flat = img_resized.reshape(-1, 3) / 255.0
                
                # Filter by confidence
                mask = conf_flat > self.confidence_threshold
                
                all_points.append(pts_flat[mask])
                all_colors.append(colors_flat[mask])
                all_confs.append(conf_flat[mask])
                
            # Stack all
            points = np.vstack(all_points)
            colors = np.vstack(all_colors)
            confidences = np.concatenate(all_confs)
            
            logger.info(f"MASt3r reconstruction: {len(points)} points from {len(images)} images")
            
            # Downsample for VRAM budget (4GB RTX 500 Ada)
            if len(points) > 200000:
                points, colors = voxel_downsample(points, colors, voxel_size=0.003)
                logger.info(f"Downsampled to {len(points)} points for VRAM budget")
            
            return MASt3rResult(
                points=points,
                colors=colors,
                confidences=confidences,
                poses=[p.cpu().numpy() for p in poses],
                intrinsics=[k.cpu().numpy() for k in intrinsics]
            )
            
        finally:
            # Cleanup temp files
            shutil.rmtree(temp_dir, ignore_errors=True)
    
    @classmethod
    def is_available(cls) -> bool:
        """Check if MASt3r is installed and importable."""
        try:
            mast3r_path = Path(__file__).parent.parent.parent / "tools" / "mast3r"
            if not mast3r_path.exists():
                return False
            sys.path.insert(0, str(mast3r_path))
            import mast3r.model  # type: ignore
            return True
        except ImportError:
            return False
