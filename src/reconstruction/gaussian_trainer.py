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
    from gsplat import rasterization as _gsplat_rasterization

    # Probe CUDA JIT compilation at import time with a tiny render.
    # If the CUDA kernels can't compile (e.g. missing MSVC / incompatible toolkit),
    # we disable gsplat here rather than failing mid-training.
    def _probe_gsplat() -> bool:
        try:
            import torch
            if not torch.cuda.is_available():
                return False
            _N = 4
            _d = "cuda"
            _m = torch.zeros(_N, 3, device=_d)
            _q = torch.zeros(_N, 4, device=_d); _q[:, 0] = 1.0
            _s = torch.ones(_N, 3, device=_d) * 0.1
            _o = torch.ones(_N, device=_d) * 0.5
            _c = torch.ones(_N, 3, device=_d) * 0.5
            _v = torch.eye(4, device=_d).unsqueeze(0)
            _K = torch.tensor([[100, 0, 32], [0, 100, 32], [0, 0, 1]],
                               dtype=torch.float32, device=_d).unsqueeze(0)
            _gsplat_rasterization(_m, _q, _s, _o, _c, _v, _K, 64, 64)
            return True
        except Exception:
            return False

    GSPLAT_AVAILABLE = _probe_gsplat()
    if GSPLAT_AVAILABLE:
        rasterization = _gsplat_rasterization
        print("gsplat CUDA kernels compiled and ready.")
    else:
        print("gsplat installed but CUDA JIT unavailable — using PyTorch CUDA renderer.")
except ImportError:
    GSPLAT_AVAILABLE = False
    rasterization = None
    print("Warning: gsplat not installed — using PyTorch CUDA renderer.")

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
            logger.warning("gsplat library not available - using PyTorch fallback. Install gsplat for better performance: pip install gsplat")
            
        self.num_iterations = config.get('num_iterations', 3000)
        self.learning_rate = config.get('learning_rate', 0.00016)
        self.sh_degree = min(config.get('sh_degree', 3), 3)  # Max degree 3
        self.densify_interval = config.get('densify_interval', 100)
        self.densify_from_iter = config.get('densify_from_iter', 500)
        self.densify_until_iter = config.get('densify_until_iter', 2000)
        self.densify_grad_threshold = config.get('densify_grad_threshold', 0.0002)
        self.prune_opacity_threshold = config.get('prune_opacity_threshold', 0.005)
        
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
        """Progressive SH degree training for 3000 iterations"""
        if iteration < 500:
            return 0
        elif iteration < 1000:
            return min(1, self.sh_degree)
        elif iteration < 1500:
            return min(2, self.sh_degree)
        else:
            return self.sh_degree
    
    def _densify_and_prune(self, iteration: int):
        """
        Densify Gaussians in high-gradient regions, prune transparent ones.
        
        Should be called every densify_interval iterations between 
        densify_from_iter and densify_until_iter.
        """
        if not (self.densify_from_iter <= iteration < self.densify_until_iter):
            return False
            
        if iteration % self.densify_interval != 0:
            return False
            
        if not hasattr(self, '_accumulated_grads'):
            return False
            
        with torch.no_grad():
            # Get accumulated gradient magnitudes
            grad_norms = torch.norm(self._accumulated_grads, dim=-1)
            
            # Densify: clone Gaussians with high gradient and small scale
            scales = torch.exp(self.gaussians.scales)
            avg_scale = scales.mean(dim=-1)
            
            # Clone condition: high gradient, small Gaussian
            clone_mask = (grad_norms > self.densify_grad_threshold) & (avg_scale < 0.01)
            
            densified = False
            if clone_mask.sum() > 0:
                # Clone selected Gaussians
                new_means = self.gaussians.means[clone_mask].clone()
                new_scales = self.gaussians.scales[clone_mask].clone()
                new_quats = self.gaussians.quats[clone_mask].clone()
                new_opacities = self.gaussians.opacities[clone_mask].clone()
                new_sh = self.gaussians.sh_coeffs[clone_mask].clone()
                
                # Perturb positions slightly
                new_means = new_means + torch.randn_like(new_means) * 0.001
                
                # Concatenate
                self.gaussians.means = torch.cat([self.gaussians.means, new_means], dim=0)
                self.gaussians.scales = torch.cat([self.gaussians.scales, new_scales], dim=0)
                self.gaussians.quats = torch.cat([self.gaussians.quats, new_quats], dim=0)
                self.gaussians.opacities = torch.cat([self.gaussians.opacities, new_opacities], dim=0)
                self.gaussians.sh_coeffs = torch.cat([self.gaussians.sh_coeffs, new_sh], dim=0)
                
                # Reset gradient accumulator
                self._accumulated_grads = torch.zeros_like(self.gaussians.means)
                
                logger.info(f"Densified: +{clone_mask.sum().item()} Gaussians")
                densified = True
            
            # Prune: remove Gaussians with low opacity
            opacities = torch.sigmoid(self.gaussians.opacities).squeeze(-1)
            prune_mask = opacities > self.prune_opacity_threshold
            
            if prune_mask.sum() < len(opacities):
                pruned = (~prune_mask).sum().item()
                self.gaussians.means = self.gaussians.means[prune_mask]
                self.gaussians.scales = self.gaussians.scales[prune_mask]
                self.gaussians.quats = self.gaussians.quats[prune_mask]
                self.gaussians.opacities = self.gaussians.opacities[prune_mask]
                self.gaussians.sh_coeffs = self.gaussians.sh_coeffs[prune_mask]
                
                # Update gradient accumulator
                if hasattr(self, '_accumulated_grads'):
                    self._accumulated_grads = self._accumulated_grads[prune_mask]
                
                logger.info(f"Pruned: -{pruned} Gaussians, remaining: {prune_mask.sum().item()}")
                densified = True
                
            # Re-enable gradients
            if densified:
                self.gaussians.means.requires_grad = True
                self.gaussians.scales.requires_grad = True
                self.gaussians.quats.requires_grad = True
                self.gaussians.opacities.requires_grad = True
                self.gaussians.sh_coeffs.requires_grad = True
                
            return densified
            
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
        
        # Initialize gradient accumulator for densification
        self._accumulated_grads = torch.zeros_like(self.gaussians.means)
        
        # Setup optimizer
        optimizer = torch.optim.Adam([
            {'params': self.gaussians.means, 'lr': self.learning_rate},
            {'params': self.gaussians.scales, 'lr': self.learning_rate * 5.0},
            {'params': self.gaussians.quats, 'lr': self.learning_rate * 0.1},
            {'params': self.gaussians.opacities, 'lr': self.learning_rate * 10.0},
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
                
                # Photometric loss (L1)
                loss = torch.nn.functional.l1_loss(rendered, gt_image)
                
                # SSIM loss for better perceptual quality (weight 0.2)
                try:
                    from pytorch_msssim import ssim
                    ssim_loss = 1.0 - ssim(rendered.unsqueeze(0), gt_image.unsqueeze(0), data_range=1.0)
                    loss = 0.8 * loss + 0.2 * ssim_loss
                except ImportError:
                    pass  # SSIM optional
                
                # Backward pass
                loss.backward()
                
                # Accumulate position gradients for densification
                if self.gaussians.means.grad is not None:
                    self._accumulated_grads += self.gaussians.means.grad.abs()
                
                # Optimize
                optimizer.step()
                optimizer.zero_grad()
                
                # Normalize quaternions
                with torch.no_grad():
                    self.gaussians.quats = torch.nn.functional.normalize(
                        self.gaussians.quats, dim=-1
                    )
                
                # Densification and pruning
                densified = self._densify_and_prune(iteration)
                
                # Rebuild optimizer if parameters changed
                if densified:
                    optimizer = torch.optim.Adam([
                        {'params': self.gaussians.means, 'lr': self.learning_rate},
                        {'params': self.gaussians.scales, 'lr': self.learning_rate * 5.0},
                        {'params': self.gaussians.quats, 'lr': self.learning_rate * 0.1},
                        {'params': self.gaussians.opacities, 'lr': self.learning_rate * 10.0},
                        {'params': self.gaussians.sh_coeffs, 'lr': self.learning_rate * 0.25},
                    ])
                
                if iteration % 50 == 0:
                    logger.info(f"Iter {iteration}/{self.num_iterations}: Loss = {loss.item():.4f}, Gaussians = {len(self.gaussians.means)}")
                    
            except Exception as e:
                logger.error(f"Rendering error at iteration {iteration}: {e}")
                # Continue training despite errors
                
        logger.info("Training completed")
        return self.gaussians
        
    def _eval_sh(self, sh_coeffs: torch.Tensor, viewdir: torch.Tensor) -> torch.Tensor:
        """
        Evaluate spherical harmonics to get color.
        
        Args:
            sh_coeffs: (N, K, 3) SH coefficients
            viewdir: (N, 3) view directions (normalized)
            
        Returns:
            (N, 3) RGB colors
        """
        C0 = 0.28209479177387814
        result = C0 * sh_coeffs[:, 0, :]  # DC component only for now
        return result + 0.5  # shift to [0,1] range
    
    def _render_gaussians(self,
                         gaussians: GaussianParams,
                         viewmat: torch.Tensor,
                         fx: float, fy: float,
                         cx: float, cy: float,
                         width: int, height: int) -> torch.Tensor:
        """
        Render Gaussians using gsplat or PyTorch fallback.
        
        Returns:
            Rendered image (3, H, W)
        """
        if GSPLAT_AVAILABLE:
            # Primary path: use gsplat
            try:
                return self._render_gaussians_gsplat(gaussians, viewmat, fx, fy, cx, cy, width, height)
            except Exception as e:
                logger.warning(f"gsplat rendering failed: {e}. Falling back to PyTorch renderer.")
                return self._render_gaussians_pytorch_fallback(gaussians, viewmat, fx, fy, cx, cy, width, height)
        else:
            # Fallback path: PyTorch-only
            return self._render_gaussians_pytorch_fallback(gaussians, viewmat, fx, fy, cx, cy, width, height)
    
    def _render_gaussians_gsplat(self,
                                 gaussians: GaussianParams,
                                 viewmat: torch.Tensor,
                                 fx: float, fy: float,
                                 cx: float, cy: float,
                                 width: int, height: int) -> torch.Tensor:
        """
        Render using gsplat library.
        
        Returns:
            Rendered image (3, H, W)
        """
        # Build intrinsic matrix
        K = torch.tensor([[fx, 0, cx], [0, fy, cy], [0, 0, 1]], 
                         dtype=torch.float32, device=self.device)
        
        # Compute view directions for SH evaluation
        N = gaussians.means.shape[0]
        viewdir = torch.nn.functional.normalize(
            -(viewmat[:3, 3].unsqueeze(0).expand(N, -1)), 
            dim=-1
        )
        
        # Get active SH degree (start with 0, progress gradually)
        active_sh_degree = 0  # For simplicity, use DC only
        
        # Evaluate SH to get colors
        colors = self._eval_sh(gaussians.sh_coeffs, viewdir)
        colors = torch.clamp(colors, 0, 1)
        
        # Call gsplat rasterization (v1.5.x API)
        renders, alphas, info = rasterization(
            means=gaussians.means,                              # (N, 3) world positions
            quats=gaussians.quats,                              # (N, 4) quaternions, wxyz  
            scales=torch.exp(gaussians.scales),                 # (N, 3) POSITIVE scales
            opacities=torch.sigmoid(gaussians.opacities).squeeze(-1),  # (N,) [0,1]
            colors=colors,                                       # (N, 3)
            viewmats=viewmat.unsqueeze(0),                      # (1, 4, 4) world-to-camera
            Ks=K.unsqueeze(0),                                  # (1, 3, 3) intrinsics
            width=width,
            height=height,
            render_mode="RGB",
            sh_degree=active_sh_degree,
        )
        # renders is (C, H, W, 3) - extract and permute to (3, H, W)
        rendered_image = renders[0].permute(2, 0, 1)
        return rendered_image
    
    def _render_gaussians_pytorch_fallback(self,
                                          gaussians: GaussianParams,
                                          viewmat: torch.Tensor,
                                          fx: float, fy: float,
                                          cx: float, cy: float,
                                          width: int, height: int) -> torch.Tensor:
        """PyTorch-only differentiable Gaussian rasterizer fallback."""
        import torch.nn.functional as F
        
        N = gaussians.means.shape[0]
        device = self.device
        
        # Build camera intrinsic matrix
        K = torch.tensor([[fx, 0, cx], [0, fy, cy], [0, 0, 1]], 
                          dtype=torch.float32, device=device)
        
        # Transform means to camera space
        # viewmat is 4x4 world-to-camera
        ones = torch.ones(N, 1, device=device)
        means_h = torch.cat([gaussians.means, ones], dim=1)  # (N, 4)
        means_cam = (viewmat @ means_h.T).T  # (N, 4)
        
        # Keep only points in front of camera
        z = means_cam[:, 2]  # (N,)
        valid = z > 0.01
        if valid.sum() == 0:
            return torch.zeros(3, height, width, device=device)
        
        # Project to screen
        means_cam_valid = means_cam[valid]  # (M, 4)
        z_valid = means_cam_valid[:, 2]
        u = (means_cam_valid[:, 0] / z_valid * fx + cx)  # pixel x
        v = (means_cam_valid[:, 1] / z_valid * fy + cy)  # pixel y
        
        # Get colors from DC SH component
        C0 = 0.28209479177387814
        sh_dc = gaussians.sh_coeffs[valid, 0, :]  # (M, 3) DC component
        colors = torch.clamp(sh_dc * C0 + 0.5, 0, 1)  # (M, 3)
        
        opacities_valid = torch.sigmoid(gaussians.opacities[valid].squeeze(-1))  # (M,)
        
        # Vectorized scatter renderer — O(N) not O(N×H×W).
        # Round projected coordinates to nearest pixel.
        u_px = u.long().clamp(0, width - 1)
        v_px = v.long().clamp(0, height - 1)

        # Keep only in-bounds Gaussians
        in_bounds = (u >= 0) & (u < width) & (v >= 0) & (v < height)
        if in_bounds.sum() == 0:
            return torch.zeros(3, height, width, device=device)

        u_px = u_px[in_bounds]
        v_px = v_px[in_bounds]
        colors = colors[in_bounds]
        opacities_valid = opacities_valid[in_bounds]

        pixel_idx = v_px * width + u_px  # (M,)

        # Weighted accumulate: sum(color × opacity) / sum(opacity) per pixel
        canvas_flat = torch.zeros(3, height * width, device=device)
        weight_flat = torch.zeros(height * width, device=device)

        for c in range(3):
            canvas_flat[c].scatter_add_(0, pixel_idx, colors[:, c] * opacities_valid)
        weight_flat.scatter_add_(0, pixel_idx, opacities_valid)

        # Normalize covered pixels; uncovered pixels stay 0
        covered = weight_flat > 1e-8
        canvas_flat[:, covered] = canvas_flat[:, covered] / weight_flat[covered].unsqueeze(0)

        return canvas_flat.view(3, height, width).clamp(0, 1)
        
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
