"""
Blender integration module for loading 3D Gaussian Splatting .ply files.

Provides utilities to launch Blender and load .ply files via subprocess.
"""

import subprocess
from pathlib import Path
from typing import Optional


class BlenderLoader:
    """
    Launch Blender with a 3D Gaussian Splatting .ply file.
    
    Requires:
    - Blender 3.3+ installed and in PATH
    - Gaussian Splatting addon installed in Blender
      (https://github.com/ReshotAI/gaussian-splatting-blender-addon)
    """
    
    def __init__(self, blender_path: Optional[str] = None):
        """
        Args:
            blender_path: Optional path to Blender executable.
                         If None, assumes 'blender' is in PATH.
        """
        self.blender_path = blender_path or "blender"
    
    def load_splat(self, ply_path: Path, background: bool = False) -> subprocess.Popen:
        """
        Launch Blender and load a .ply file.
        
        Args:
            ply_path: Path to the .ply file
            background: If True, run Blender in background mode (no UI)
        
        Returns:
            subprocess.Popen: The Blender process
        """
        script_path = self._get_load_script()
        
        if not script_path.exists():
            raise FileNotFoundError(f"Blender load script not found: {script_path}")
        
        if not ply_path.exists():
            raise FileNotFoundError(f"PLY file not found: {ply_path}")
        
        cmd = [self.blender_path]
        
        if background:
            cmd.append("--background")
        
        cmd.extend(["--python", str(script_path), "--", str(ply_path)])
        
        print(f"[BlenderLoader] Launching: {' '.join(cmd)}")
        
        try:
            process = subprocess.Popen(cmd)
            return process
        except FileNotFoundError:
            raise FileNotFoundError(
                f"Blender not found at '{self.blender_path}'. "
                "Install Blender or provide correct path."
            )
    
    def _get_load_script(self) -> Path:
        """Get path to the Blender load script."""
        # Assume we're in src/viewer, script is in scripts/viewer
        return Path(__file__).parent.parent.parent / "scripts" / "viewer" / "load_splat.py"
    
    def check_installation(self) -> bool:
        """
        Check if Blender is installed and accessible.
        
        Returns:
            bool: True if Blender is found
        """
        try:
            result = subprocess.run(
                [self.blender_path, "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                print(f"[BlenderLoader] Found Blender: {result.stdout.splitlines()[0]}")
                return True
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass
        
        print(f"[BlenderLoader] Blender not found at '{self.blender_path}'")
        return False
