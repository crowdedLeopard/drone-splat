"""
SLAM-based 3D Reconstruction Processor

Performs incremental 3D Gaussian Splatting reconstruction using SLAM approach.
Supports MASt3r, DUST3r, and SplaTAM methods.

Owner: Naomi
"""

import threading
import time
from pathlib import Path
from typing import Callable, Optional
from loguru import logger
import torch


class SLAMProcessor:
    """SLAM-based 3D Gaussian Splatting reconstruction"""
    
    def __init__(self, config: dict):
        self.config = config
        self.method = config['method']
        self.window_size = config['window_size']
        self.window_overlap = config['window_overlap']
        self.output_dir = Path(config['output_dir'])
        self.output_format = config['output_format']
        self.output_filename = config['output_filename']
        self.device = config['device']
        
        self.running = False
        self.frame_buffer = []
        self.reconstruction_count = 0
        self.update_callbacks = []
        
        # Ensure CUDA is available if specified
        if self.device == 'cuda' and not torch.cuda.is_available():
            logger.warning("CUDA requested but not available, falling back to CPU")
            self.device = 'cpu'
        
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"SLAM Processor initialized: method={self.method}, device={self.device}")
        logger.info(f"Window size: {self.window_size}, overlap: {self.window_overlap}")
    
    def start(self, frame_extractor):
        """Start reconstruction processor"""
        self.running = True
        self.frame_extractor = frame_extractor
        
        # Start reconstruction thread
        recon_thread = threading.Thread(target=self._reconstruction_loop, daemon=True)
        recon_thread.start()
        
        logger.info("3D Reconstruction processor started")
    
    def _reconstruction_loop(self):
        """Main reconstruction loop"""
        while self.running:
            try:
                # Get frames from extractor
                new_frames = self.frame_extractor.get_latest_frames(count=self.window_size)
                
                if len(new_frames) < self.window_size:
                    # Not enough frames yet
                    time.sleep(1)
                    continue
                
                # Perform reconstruction
                logger.info(f"Processing {len(new_frames)} frames for reconstruction...")
                output_file = self._process_frames(new_frames)
                
                if output_file:
                    self.reconstruction_count += 1
                    logger.info(f"Reconstruction #{self.reconstruction_count} complete: {output_file}")
                    
                    # Notify callbacks
                    for callback in self.update_callbacks:
                        try:
                            callback(output_file)
                        except Exception as e:
                            logger.error(f"Callback error: {e}")
                
                # Sleep based on update mode
                if self.config['update_mode'] == 'interval':
                    time.sleep(self.config['update_interval_sec'])
                else:
                    time.sleep(1)  # Small delay for continuous mode
                
            except Exception as e:
                logger.error(f"Reconstruction error: {e}", exc_info=True)
                time.sleep(5)
    
    def _process_frames(self, frames: list) -> Optional[Path]:
        """
        Process frames and generate 3D reconstruction
        
        Args:
            frames: List of frame file paths
            
        Returns:
            Path to output file (.splat or .ply)
        """
        # TODO (Naomi): Implement actual reconstruction
        # This is where MASt3r/DUST3r/SplaTAM processing happens
        
        # Placeholder: would load model, process frames, generate splat
        logger.info(f"[TODO] Reconstruct {len(frames)} frames using {self.method}")
        
        # Output file path
        output_file = self.output_dir / self.output_filename
        
        # TODO: Actual reconstruction code here
        # 1. Load frames
        # 2. Run SLAM/reconstruction (MASt3r, DUST3r, or SplaTAM)
        # 3. Generate Gaussian Splatting representation
        # 4. Export to .splat or .ply format
        
        return None  # Return output_file when implemented
    
    def on_update(self, callback: Callable[[Path], None]):
        """Register callback for reconstruction updates"""
        self.update_callbacks.append(callback)
    
    def get_stats(self) -> dict:
        """Get reconstruction statistics"""
        return {
            'method': self.method,
            'device': self.device,
            'reconstruction_count': self.reconstruction_count,
            'frames_buffered': len(self.frame_buffer),
        }
    
    def is_healthy(self) -> bool:
        """Check if processor is healthy"""
        return self.running
    
    def stop(self, timeout: int = 30):
        """Stop reconstruction processor"""
        self.running = False
        logger.info("SLAM Processor stopped")
