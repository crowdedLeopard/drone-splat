"""
PLY Writer - Export 3D Gaussian Splats to standard formats

Writes .ply files compatible with:
- Blender Gaussian Splatting addon
- SuperSplat web viewer
- antimatter15's splat viewer
"""

import numpy as np
import struct
from typing import Dict
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PLYWriter:
    """Writes 3D Gaussian Splats to PLY format"""
    
    def __init__(self, config: dict = None):
        """
        Initialize PLY writer
        
        Args:
            config: Optional configuration (reserved for future use)
        """
        self.config = config or {}
        
    @staticmethod
    def _construct_list_of_attributes(sh_degree: int = 3):
        """Construct list of PLY vertex properties for Gaussians"""
        l = ['x', 'y', 'z', 'nx', 'ny', 'nz']
        
        # Spherical harmonics (DC + rest)
        # DC component (3 channels)
        for i in range(3):
            l.append(f'f_dc_{i}')
            
        # Rest components
        num_rest = (sh_degree + 1) ** 2 - 1
        for i in range(num_rest * 3):
            l.append(f'f_rest_{i}')
            
        l.append('opacity')
        
        # Scale (3 values)
        for i in range(3):
            l.append(f'scale_{i}')
            
        # Rotation quaternion (4 values: w, x, y, z)
        for i in range(4):
            l.append(f'rot_{i}')
            
        return l
        
    def write_ply(self,
                  filepath: str,
                  means: np.ndarray,
                  scales: np.ndarray,
                  quats: np.ndarray,
                  opacities: np.ndarray,
                  sh_coeffs: np.ndarray) -> None:
        """
        Write Gaussians to PLY file
        
        Args:
            filepath: Output .ply file path
            means: (N, 3) Gaussian positions
            scales: (N, 3) Gaussian scales
            quats: (N, 4) Gaussian rotations as quaternions (w, x, y, z)
            opacities: (N, 1) or (N,) Gaussian opacities
            sh_coeffs: (N, K, 3) Spherical harmonics coefficients
        """
        N = len(means)
        sh_degree = int(np.sqrt(sh_coeffs.shape[1])) - 1
        
        logger.info(f"Writing {N} Gaussians to {filepath}")
        logger.info(f"SH degree: {sh_degree}")
        
        # Ensure opacities is 2D
        if opacities.ndim == 1:
            opacities = opacities.reshape(-1, 1)
            
        # Normals (not used in Gaussian splatting, set to zero)
        normals = np.zeros_like(means)
        
        # Prepare SH coefficients
        # Split into DC (first component) and rest
        sh_dc = sh_coeffs[:, 0, :]  # (N, 3) - DC component
        if sh_coeffs.shape[1] > 1:
            sh_rest = sh_coeffs[:, 1:, :].reshape(N, -1)  # (N, (K-1)*3)
        else:
            sh_rest = np.zeros((N, 0))
            
        # Prepare all vertex attributes
        dtype_list = [
            ('x', 'f4'), ('y', 'f4'), ('z', 'f4'),
            ('nx', 'f4'), ('ny', 'f4'), ('nz', 'f4'),
        ]
        
        # Add SH DC
        for i in range(3):
            dtype_list.append((f'f_dc_{i}', 'f4'))
            
        # Add SH rest
        for i in range(sh_rest.shape[1]):
            dtype_list.append((f'f_rest_{i}', 'f4'))
            
        dtype_list.append(('opacity', 'f4'))
        
        # Add scales
        for i in range(3):
            dtype_list.append((f'scale_{i}', 'f4'))
            
        # Add rotations
        for i in range(4):
            dtype_list.append((f'rot_{i}', 'f4'))
            
        # Create structured array
        vertices = np.zeros(N, dtype=dtype_list)
        
        # Fill positions
        vertices['x'] = means[:, 0]
        vertices['y'] = means[:, 1]
        vertices['z'] = means[:, 2]
        
        # Fill normals (zeros)
        vertices['nx'] = normals[:, 0]
        vertices['ny'] = normals[:, 1]
        vertices['nz'] = normals[:, 2]
        
        # Fill SH DC
        for i in range(3):
            vertices[f'f_dc_{i}'] = sh_dc[:, i]
            
        # Fill SH rest
        for i in range(sh_rest.shape[1]):
            vertices[f'f_rest_{i}'] = sh_rest[:, i]
            
        # Fill opacity
        vertices['opacity'] = opacities.flatten()
        
        # Fill scales
        for i in range(3):
            vertices[f'scale_{i}'] = scales[:, i]
            
        # Fill rotations (quaternion: w, x, y, z)
        for i in range(4):
            vertices[f'rot_{i}'] = quats[:, i]
            
        # Write PLY file
        self._write_ply_binary(filepath, vertices)
        
        logger.info(f"Successfully wrote PLY to {filepath}")
        
    def _write_ply_binary(self, filepath: str, vertices: np.ndarray) -> None:
        """Write binary PLY file"""
        with open(filepath, 'wb') as f:
            # Write header
            f.write(b'ply\n')
            f.write(b'format binary_little_endian 1.0\n')
            f.write(f'element vertex {len(vertices)}\n'.encode())
            
            # Write property definitions
            for name in vertices.dtype.names:
                f.write(f'property float {name}\n'.encode())
                
            f.write(b'end_header\n')
            
            # Write binary data
            vertices.tofile(f)
            
    def write_splat(self,
                   filepath: str,
                   means: np.ndarray,
                   scales: np.ndarray,
                   quats: np.ndarray,
                   opacities: np.ndarray,
                   sh_coeffs: np.ndarray) -> None:
        """
        Write to .splat format (antimatter15's binary format)
        
        .splat format (simplified):
        - Direct binary dump of Gaussian parameters
        - Used by web-based viewers
        
        Args:
            filepath: Output .splat file path
            means: (N, 3) positions
            scales: (N, 3) scales
            quats: (N, 4) quaternions
            opacities: (N, 1) opacities
            sh_coeffs: (N, K, 3) SH coefficients
        """
        logger.info(f"Writing .splat format to {filepath}")
        
        # Convert SH to RGB (simplified - use DC component)
        C0 = 0.28209479177387814
        rgb = sh_coeffs[:, 0, :] * C0 + 0.5
        rgb = np.clip(rgb * 255, 0, 255).astype(np.uint8)
        
        N = len(means)
        
        # .splat format structure (simplified version):
        # Each splat: position (3f), scale (3f), color (4B), quaternion (4f)
        with open(filepath, 'wb') as f:
            for i in range(N):
                # Position (float32 x 3)
                f.write(struct.pack('fff', *means[i]))
                
                # Scale (float32 x 3)
                f.write(struct.pack('fff', *scales[i]))
                
                # Color RGBA (uint8 x 4)
                alpha = int(opacities[i, 0] * 255) if opacities.ndim > 1 else int(opacities[i] * 255)
                f.write(struct.pack('BBBB', rgb[i, 0], rgb[i, 1], rgb[i, 2], alpha))
                
                # Quaternion (float32 x 4) - wxyz order
                f.write(struct.pack('ffff', *quats[i]))
                
        logger.info(f"Successfully wrote .splat to {filepath}")
        
    def write_from_dict(self, filepath: str, gaussian_dict: Dict[str, np.ndarray], format: str = 'ply') -> None:
        """
        Write Gaussians from dictionary
        
        Args:
            filepath: Output file path
            gaussian_dict: Dictionary with keys: means, scales, quats, opacities, sh_coeffs
            format: 'ply' or 'splat'
        """
        required_keys = ['means', 'scales', 'quats', 'opacities', 'sh_coeffs']
        for key in required_keys:
            if key not in gaussian_dict:
                raise ValueError(f"Missing required key: {key}")
                
        if format.lower() == 'ply':
            self.write_ply(
                filepath,
                gaussian_dict['means'],
                gaussian_dict['scales'],
                gaussian_dict['quats'],
                gaussian_dict['opacities'],
                gaussian_dict['sh_coeffs']
            )
        elif format.lower() == 'splat':
            self.write_splat(
                filepath,
                gaussian_dict['means'],
                gaussian_dict['scales'],
                gaussian_dict['quats'],
                gaussian_dict['opacities'],
                gaussian_dict['sh_coeffs']
            )
        else:
            raise ValueError(f"Unknown format: {format}. Use 'ply' or 'splat'")
