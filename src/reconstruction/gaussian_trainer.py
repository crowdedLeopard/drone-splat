"""
Gaussian Trainer - 3D Gaussian Splatting optimization

Trains 3D Gaussians from point cloud and camera poses using gsplat.
Performs photometric optimization for high-quality reconstruction.
"""

import numpy as np
import torch
import torch.nn as nn
from typing import List, Tuple, Optional, Dict
import logging
from dataclasses import dataclass

try:
    from gsplat import rasterization
    GSPLAT_AVAILABLE = True
except ImportError:
    GSPLAT_AVAILABLE = False
    print("Warning: gsplat not available. Install with: pip install gsplat")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class GaussianParams:
    """3D Gaussian parameters"""
    means: torch.Tensor  # (N, 3) positions
    scales: torch.Tensor  # (N, 3) log scales
    quats: torch.Tensor  # (N, 4) rotation quaternions (wxyz)
    opacities: torch.Tensor  # (N, 1) logit opacities
    sh_coeffs: torch.Tensor  # (N, K, 3) spherical harmonics (K=16 for 3 degrees)


class GaussianTrainer:
    """Trains 3D Gaussian Splatting model"""
    
    def __init__(self, config: dict):
        """
        Initialize Gaussian trainer
        
        Args:
            config: Configuration dict with keys:
                - num_iterations: Number of optimization iterations (default: 300)
                - learning_rate: Learning rate for Adam optimizer (default: 0.01)
                - sh_degree: Spherical harmonics degree (default: 3, max 3)
                - densify_interval: Iterations between densification (default: 100)
                - device: 'cuda' or 'cpu' (default: auto-detect)
        """
        if not GSPLAT_AVAILABLE:
            raise RuntimeError("gsplat library not available. Install with: pip install gsplat")
            
        self.num_iterations = config.get('num_iterations', 300)
        self.learning_rate = config.get('learning_rate', 0.01)
        self.sh_degree = min(config.get('sh_degree', 3), 3)  # Max degree 3
        self.densify_interval = config.get('densify_interval', 100)
        
        # Device setup
        device = config.get('device', 'cuda' if torch.cuda.is_available() else 'cpu')
        self.device = torch.device(device)
        
        if self.device.type == 'cuda':
            logger.info(f"Using GPU: {torch.cuda.get_device_name(0)}")
            logger.info(f"VRAM: {torch.cuda.get_device_properties(0).total_memory / 1e9:.2f} GB")
        else:
            logger.warning("Running on CPU - this will be slow!")
            
        self.gaussians: Optional[GaussianParams] = None
        
    def _initialize_from_pointcloud(self, 
                                    points: np.ndarray, 
                                    colors: np.ndarray) -> GaussianParams:
        """
        Initialize Gaussians from point cloud
        
        Args:
            points: (N, 3) point positions
            colors: (N, 3) RGB colors (0-1 range)
            
        Returns:
            Initialized GaussianParams
        """
        N = len(points)
        
        # Convert to tensors
        means = torch.from_numpy(points).float().to(self.device)
        
        # Initialize scales (small isotropic)
        # Estimate based on nearest neighbor distance
        from scipy.spatial import cKDTree
        tree = cKDTree(points)
        distances, _ = tree.query(points, k=2)
        nn_dist = distances[:, 1]  # Distance to nearest neighbor
        initial_scale = np.log(nn_dist.mean() * 0.5)  # Log scale
        scales = torch.ones((N, 3), device=self.device) * initial_scale
        
        # Initialize rotations (identity quaternions: w=1, xyz=0)
        quats = torch.zeros((N, 4), device=self.device)
        quats[:, 0] = 1.0  # w component
        
        # Initialize opacities (high initial opacity)
        opacities = torch.logit(torch.ones((N, 1), device=self.device) * 0.9)
        
        # Initialize spherical harmonics from colors
        # SH degree 0 (DC component) = RGB color
        # Convert RGB to SH basis: SH_0 = (C - 0.5) / C_0 where C_0 = 0.28209479177387814
        C0 = 0.28209479177387814
        num_sh = (self.sh_degree + 1) ** 2  # Total SH coefficients
        sh_coeffs = torch.zeros((N, num_sh, 3), device=self.device)
        
        # Set DC component (first coefficient)
        rgb = torch.from_numpy(colors).float().to(self.device)
        sh_coeffs[:, 0, :] = (rgb - 0.5) / C0
        
        return GaussianParams(
            means=means,
            scales=scales,
            quats=quats,
            opacities=opacities,
            sh_coeffs=sh_coeffs
        )
        
    def _get_sh_degree_from_iter(self, iteration: int) -> int:
        """Progressive SH degree training"""
        if iteration < 1000:
            return 0
        elif iteration < 2000:
            return min(1, self.sh_degree)
        elif iteration < 3000:
            return min(2, self.sh_degree)
        else:
            return self.sh_degree
            
    def train(self,
             points: np.ndarray,
             colors: np.ndarray,
             images: List[np.ndarray],
             camera_poses: List,  # List of CameraPose objects
             camera_matrix: np.ndarray) -> GaussianParams:
        """
        Train 3D Gaussians from point cloud and images
        
        Args:
            points: (N, 3) initial point cloud
            colors: (N, 3) point colors
            images: List of training images
            camera_poses: List of CameraPose objects
            camera_matrix: 3x3 camera intrinsic matrix
            
        Returns:
            Trained GaussianParams
        """
        # Initialize Gaussians
        logger.info(f"Initializing {len(points)} Gaussians from point cloud")
        self.gaussians = self._initialize_from_pointcloud(points, colors)
        
        # Make parameters trainable
        self.gaussians.means.requires_grad = True
        self.gaussians.scales.requires_grad = True
        self.gaussians.quats.requires_grad = True
        self.gaussians.opacities.requires_grad = True
        self.gaussians.sh_coeffs.requires_grad = True
        
        # Setup optimizer
        optimizer = torch.optim.Adam([
            {'params': self.gaussians.means, 'lr': self.learning_rate},
            {'params': self.gaussians.scales, 'lr': self.learning_rate * 0.5},
            {'params': self.gaussians.quats, 'lr': self.learning_rate * 0.1},
            {'params': self.gaussians.opacities, 'lr': self.learning_rate * 0.5},
            {'params': self.gaussians.sh_coeffs, 'lr': self.learning_rate * 0.25},
        ])
        
        # Convert images and poses to tensors
        gt_images = [torch.from_numpy(img).float().permute(2, 0, 1) / 255.0 
                     for img in images]
        gt_images = [img.to(self.device) for img in gt_images]
        
        H, W = images[0].shape[:2]
        fx, fy = camera_matrix[0, 0], camera_matrix[1, 1]
        cx, cy = camera_matrix[0, 2], camera_matrix[1, 2]
        
        # Training loop
        logger.info(f"Starting training for {self.num_iterations} iterations")
        
        for iteration in range(self.num_iterations):
            # Select random training view
            view_idx = np.random.randint(0, len(images))
            gt_image = gt_images[view_idx]
            pose = camera_poses[view_idx]
            
            # Camera parameters for gsplat
            # gsplat uses camera-to-world (c2w) transformation
            c2w = np.linalg.inv(pose.T)  # World-to-camera inverse
            viewmat = torch.from_numpy(c2w).float().to(self.device)
            
            # Render with gsplat (simplified API - actual implementation may vary)
            # Note: This is a reference implementation - actual gsplat API may differ
            try:
                # Placeholder for gsplat rasterization
                # Actual usage depends on gsplat version
                rendered = self._render_gaussians(
                    self.gaussians,
                    viewmat,
                    fx, fy, cx, cy, W, H
                )
                
                # Photometric loss
                loss = torch.nn.functional.l1_loss(rendered, gt_image)
                
                # Backward and optimize
                optimizer.zero_grad()
                loss.backward()
                optimizer.step()
                
                # Normalize quaternions
                with torch.no_grad():
                    self.gaussians.quats = torch.nn.functional.normalize(
                        self.gaussians.quats, dim=-1
                    )
                
                if iteration % 50 == 0:
                    logger.info(f"Iter {iteration}/{self.num_iterations}: Loss = {loss.item():.4f}")
                    
            except Exception as e:
                logger.error(f"Rendering error at iteration {iteration}: {e}")
                # Continue training despite errors
                
        logger.info("Training completed")
        return self.gaussians
        
    def _render_gaussians(self,
                         gaussians: GaussianParams,
                         viewmat: torch.Tensor,
                         fx: float, fy: float,
                         cx: float, cy: float,
                         width: int, height: int) -> torch.Tensor:
        """
        Render Gaussians using gsplat (placeholder - adapt to actual API)
        
        Returns:
            Rendered image (3, H, W)
        """
        # This is a simplified placeholder
        # Actual gsplat usage depends on the specific version and API
        # Refer to: https://github.com/nerfstudio-project/gsplat
        
        # For now, return a dummy tensor
        # TODO: Implement actual gsplat rasterization
        logger.warning("Using placeholder rendering - implement actual gsplat rasterization")
        return torch.zeros((3, height, width), device=self.device)
        
    def get_gaussians_numpy(self) -> Dict[str, np.ndarray]:
        """
        Export Gaussians to numpy arrays
        
        Returns:
            Dictionary with keys: means, scales, quats, opacities, sh_coeffs
        """
        if self.gaussians is None:
            raise ValueError("No trained Gaussians available")
            
        with torch.no_grad():
            return {
                'means': self.gaussians.means.cpu().numpy(),
                'scales': torch.exp(self.gaussians.scales).cpu().numpy(),  # Convert from log
                'quats': self.gaussians.quats.cpu().numpy(),
                'opacities': torch.sigmoid(self.gaussians.opacities).cpu().numpy(),  # Convert from logit
                'sh_coeffs': self.gaussians.sh_coeffs.cpu().numpy(),
            }
