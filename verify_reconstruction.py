"""
Quick verification script for reconstruction module
Tests that all components can be imported and basic initialization works
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

print("=" * 60)
print("Reconstruction Module Verification")
print("=" * 60)
print()

# Test imports
print("[1/6] Testing imports...")
try:
    from src.reconstruction import (
        GaussianReconstructor,
        FrameSelector,
        PoseEstimator,
        GaussianTrainer,
        PLYWriter
    )
    print("[OK] All modules imported successfully")
except ImportError as e:
    print(f"[FAIL] Import failed: {e}")
    sys.exit(1)

print()

# Test FrameSelector
print("[2/6] Testing FrameSelector...")
try:
    import numpy as np
    frame_selector = FrameSelector({
        'min_interval': 0.5,
        'max_interval': 2.0,
        'motion_threshold': 5.0,
    })
    
    # Add test frame
    frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
    result = frame_selector.add_frame(frame, 0.0)
    
    print(f"[OK] FrameSelector initialized and working (first frame: {result})")
except Exception as e:
    print(f"[FAIL] FrameSelector failed: {e}")

print()

# Test PoseEstimator
print("[3/6] Testing PoseEstimator...")
try:
    pose_estimator = PoseEstimator({
        'feature_detector': 'sift',
        'min_features': 50,
    })
    print("[OK] PoseEstimator initialized")
except Exception as e:
    print(f"[FAIL] PoseEstimator failed: {e}")

print()

# Test PLYWriter
print("[4/6] Testing PLYWriter...")
try:
    ply_writer = PLYWriter()
    print("[OK] PLYWriter initialized")
except Exception as e:
    print(f"[FAIL] PLYWriter failed: {e}")

print()

# Test GaussianTrainer
print("[5/6] Testing GaussianTrainer...")
try:
    import torch
    cuda_available = torch.cuda.is_available()
    
    trainer_config = {
        'num_iterations': 10,
        'device': 'cuda' if cuda_available else 'cpu'
    }
    
    # This will fail if gsplat not installed, which is expected
    try:
        gaussian_trainer = GaussianTrainer(trainer_config)
        print(f"[OK] GaussianTrainer initialized (device: {trainer_config['device']})")
    except RuntimeError as e:
        if "gsplat" in str(e):
            print(f"[WARN] GaussianTrainer: gsplat not installed (expected on first run)")
            print(f"  Run: scripts\\install_reconstruction.bat")
        else:
            raise
            
except Exception as e:
    print(f"[FAIL] GaussianTrainer failed: {e}")

print()

# Test GaussianReconstructor
print("[6/6] Testing GaussianReconstructor...")
try:
    config = {
        'output_dir': './output/test',
        'min_keyframes': 5,
        'frame_selector': {},
        'pose_estimator': {},
    }
    
    # Skip gaussian_trainer if gsplat not available
    try:
        reconstructor = GaussianReconstructor(config)
        print("[OK] GaussianReconstructor initialized")
    except RuntimeError as e:
        if "gsplat" in str(e):
            print("[WARN] GaussianReconstructor: Skipped (gsplat not installed)")
        else:
            raise
            
except Exception as e:
    print(f"[FAIL] GaussianReconstructor failed: {e}")

print()
print("=" * 60)
print("Verification Summary")
print("=" * 60)

# Check dependencies
print()
print("Checking dependencies...")

try:
    import torch
    print(f"[OK] PyTorch {torch.__version__}")
    print(f"  CUDA available: {torch.cuda.is_available()}")
    if torch.cuda.is_available():
        print(f"  GPU: {torch.cuda.get_device_name(0)}")
        vram = torch.cuda.get_device_properties(0).total_memory / 1e9
        print(f"  VRAM: {vram:.1f} GB")
except ImportError:
    print("[FAIL] PyTorch not installed")
    print("  Run: pip install torch --index-url https://download.pytorch.org/whl/cu118")

try:
    import cv2
    print(f"[OK] OpenCV {cv2.__version__}")
except ImportError:
    print("[FAIL] OpenCV not installed")
    print("  Run: pip install opencv-python")

try:
    import numpy
    print(f"[OK] NumPy {numpy.__version__}")
except ImportError:
    print("[FAIL] NumPy not installed")

try:
    import scipy
    print(f"[OK] SciPy {scipy.__version__}")
except ImportError:
    print("[FAIL] SciPy not installed")

try:
    import yaml
    print(f"[OK] PyYAML installed")
except ImportError:
    print("[FAIL] PyYAML not installed")

try:
    import gsplat
    print(f"[OK] gsplat installed")
except ImportError:
    print("[WARN] gsplat not installed (required for Gaussian training)")
    print("  Run: scripts\\install_reconstruction.bat")

print()
print("=" * 60)
print()

if cuda_available:
    print("[OK] System ready for GPU-accelerated reconstruction")
else:
    print("[WARN] No CUDA GPU detected - reconstruction will be slow on CPU")

print()
print("Next steps:")
print("  1. Run installation: scripts\\install_reconstruction.bat")
print("  2. Check config: config\\reconstruction_config.yaml")
print("  3. Try example: python examples\\example_basic_reconstruction.py")
print()
