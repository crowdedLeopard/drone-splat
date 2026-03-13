"""
Blender Python script to load a 3DGS .ply file.

Usage:
    blender --python scripts/viewer/load_splat.py -- path/to/output.ply

Requirements:
    - Blender 3.3+
    - Gaussian Splatting addon installed
      (https://github.com/ReshotAI/gaussian-splatting-blender-addon)
      or search Blender Extensions for "Gaussian Splatting"

The addon adds the operator: bpy.ops.import_scene.gaussian_splat()
"""

import bpy
import sys
from pathlib import Path


def clear_scene():
    """Clear all objects from the scene."""
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()


def import_gaussian_splat(filepath: str):
    """
    Import a 3D Gaussian Splatting .ply file.
    
    Args:
        filepath: Path to the .ply file
    """
    print(f"[Blender] Loading Gaussian Splat: {filepath}")
    
    clear_scene()
    
    # Try to use Gaussian Splatting addon
    try:
        if hasattr(bpy.ops.import_scene, 'gaussian_splat'):
            bpy.ops.import_scene.gaussian_splat(filepath=filepath)
            print("[Blender] Loaded with Gaussian Splatting addon")
        else:
            print("[Blender] WARNING: Gaussian Splatting addon not found")
            print("[Blender] Falling back to standard PLY import (may not render correctly)")
            bpy.ops.import_mesh.ply(filepath=filepath)
    except AttributeError as e:
        print(f"[Blender] ERROR: {e}")
        print("[Blender] Install Gaussian Splatting addon from:")
        print("  https://github.com/ReshotAI/gaussian-splatting-blender-addon")
        
        # Try standard PLY import as last resort
        try:
            bpy.ops.import_mesh.ply(filepath=filepath)
            print("[Blender] Imported as standard PLY mesh (not a true Gaussian Splat)")
        except:
            print("[Blender] FAILED: Could not import file")
            return
    
    # Set up camera and lighting
    setup_scene()
    
    # Save as .blend file next to the .ply
    blend_path = Path(filepath).with_suffix('.blend')
    bpy.ops.wm.save_as_mainfile(filepath=str(blend_path))
    print(f"[Blender] Saved scene to: {blend_path}")


def setup_scene():
    """Set up camera and lighting for the scene."""
    # Add camera if not present
    if not bpy.data.cameras:
        bpy.ops.object.camera_add(location=(10, -10, 10))
        camera = bpy.context.object
        camera.rotation_euler = (1.1, 0, 0.785)
        bpy.context.scene.camera = camera
    
    # Add light if not present
    if not bpy.data.lights:
        bpy.ops.object.light_add(type='SUN', location=(5, 5, 10))
        light = bpy.context.object
        light.data.energy = 2.0


def main():
    """Main entry point when run as Blender script."""
    # Get arguments after '--'
    argv = sys.argv
    
    if "--" not in argv:
        print("[Blender] ERROR: No file path provided")
        print("Usage: blender --python load_splat.py -- path/to/file.ply")
        return
    
    argv = argv[argv.index("--") + 1:]
    
    if not argv:
        print("[Blender] ERROR: No file path provided after '--'")
        return
    
    filepath = argv[0]
    
    if not Path(filepath).exists():
        print(f"[Blender] ERROR: File not found: {filepath}")
        return
    
    import_gaussian_splat(filepath)


if __name__ == "__main__":
    main()
