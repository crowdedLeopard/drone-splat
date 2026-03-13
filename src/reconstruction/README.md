# 3D Gaussian Splatting Reconstruction Module

Incremental 3D reconstruction pipeline for converting video streams to 3D Gaussian Splat models.

## Overview

This module implements a pragmatic approach to real-time 3D Gaussian Splatting reconstruction:

1. **Keyframe Selection** - Selects important frames based on motion
2. **Pose Estimation** - Estimates camera poses using feature matching
3. **Point Cloud Generation** - Triangulates 3D points from multiple views
4. **Gaussian Training** - Optimizes 3D Gaussians using gsplat
5. **Export** - Outputs standard .ply files for viewing

## Quick Start

### Installation

**Windows 11 with NVIDIA GPU:**

```bash
# Run installation script
scripts\install_reconstruction.bat
# or
scripts\install_reconstruction.ps1
```

**Requirements:**
- Python 3.9+
- NVIDIA GPU with 4GB+ VRAM
- CUDA Toolkit 11.8 or 12.x
- Visual C++ Build Tools

### Basic Usage

```python
from src.reconstruction import GaussianReconstructor
import numpy as np

# Create reconstructor with default config
config = GaussianReconstructor.create_default_config()
reconstructor = GaussianReconstructor(config)

# Add frames
frame = np.random.randint(0, 255, (720, 1280, 3), dtype=np.uint8)
timestamp = 0.0

reconstructor.add_frame(frame, timestamp)

# Get output path
output_path = reconstructor.get_output_path()
print(f"Reconstruction saved to: {output_path}")
```

### Threaded Usage (Recommended)

```python
import queue
import threading
from src.reconstruction import GaussianReconstructor

# Setup
config = GaussianReconstructor.create_default_config()
reconstructor = GaussianReconstructor(config)

frame_queue = queue.Queue()
stop_event = threading.Event()

# Start reconstruction thread
thread = threading.Thread(
    target=reconstructor.run,
    args=(frame_queue, stop_event)
)
thread.start()

# Feed frames
frame_queue.put((frame, timestamp))

# Stop when done
stop_event.set()
thread.join()
```

## Configuration

Create a YAML config file:

```yaml
output_dir: './output/reconstructions'
output_format: 'ply'  # or 'splat'
reconstruction_interval: 5.0  # seconds between updates
min_keyframes: 10

frame_selector:
  min_interval: 0.5      # min seconds between keyframes
  max_interval: 2.0      # force keyframe after this time
  motion_threshold: 5.0  # optical flow threshold (pixels)
  max_keyframes: 50      # sliding window size

pose_estimator:
  feature_detector: 'sift'  # 'sift' or 'orb'
  min_features: 100
  ransac_threshold: 1.0

gaussian_trainer:
  num_iterations: 300    # optimization iterations
  learning_rate: 0.01
  sh_degree: 3          # spherical harmonics degree (max 3)
  device: 'cuda'        # 'cuda' or 'cpu'
```

Load config:

```python
reconstructor = GaussianReconstructor.from_config_file('config.yaml')
```

## Architecture

### Components

**FrameSelector** - Intelligent keyframe selection
- Optical flow-based motion detection
- Temporal spacing constraints
- Sliding window memory management

**PoseEstimator** - Camera pose recovery
- SIFT/ORB feature detection and matching
- Essential matrix estimation with RANSAC
- Incremental structure-from-motion
- Multi-view triangulation

**GaussianTrainer** - 3D Gaussian optimization
- Point cloud initialization
- Differentiable rasterization (gsplat)
- Photometric loss optimization
- Spherical harmonics for view-dependent color

**PLYWriter** - Standard format export
- Binary little-endian PLY format
- Compatible with Blender, SuperSplat, web viewers
- Optional .splat format support

### Pipeline Flow

```
Input Frames
    ↓
Frame Selector (keyframes only)
    ↓
Pose Estimator (camera poses)
    ↓
Point Cloud Generator (triangulation)
    ↓
Gaussian Trainer (optimization)
    ↓
PLY Writer (.ply file)
    ↓
Output: reconstruction_NNNN.ply
```

## Performance

### Expected Behavior

- **Input:** 30 fps video stream
- **Keyframe Rate:** 0.5-2 keyframes/second
- **Reconstruction Update:** Every 5 seconds
- **Processing Time:** 10-30 seconds per update (GPU-dependent)

### VRAM Requirements

| Quality | VRAM | Gaussians | Iterations |
|---------|------|-----------|------------|
| Demo    | 4GB  | 10-50K    | 300        |
| Good    | 8GB  | 50-200K   | 500        |
| High    | 12GB+| 200K+     | 1000+      |

## Output Format

Standard 3D Gaussian Splatting .ply format:

**Vertex Properties:**
- Position: x, y, z
- Normal: nx, ny, nz (zeros)
- SH DC: f_dc_0, f_dc_1, f_dc_2
- SH Rest: f_rest_0...f_rest_44 (for degree 3)
- Opacity: opacity
- Scale: scale_0, scale_1, scale_2
- Rotation: rot_0, rot_1, rot_2, rot_3 (quaternion)

**Compatible With:**
- ✅ Blender Gaussian Splatting addon
- ✅ SuperSplat (https://playcanvas.com/supersplat)
- ✅ antimatter15 splat viewer
- ✅ Standard 3DGS tools

## Integration

### For Frame Provider (Amos)

Provide frames via queue:

```python
# Queue format: (frame, timestamp)
frame_queue.put((frame, timestamp))

# Where:
# - frame: np.ndarray, shape (H, W, 3), dtype uint8, BGR or RGB
# - timestamp: float, seconds since start
```

### For Visualization (Bobbie)

Access output files:

```python
# Get latest file
output_path = reconstructor.get_output_path()

# Or watch output directory
import os
files = sorted(os.listdir('./output/reconstructions'))
latest = files[-1]  # reconstruction_NNNN.ply
```

## Troubleshooting

### gsplat Installation Fails

**Symptoms:** `pip install gsplat` errors

**Solutions:**
1. Install CUDA Toolkit: https://developer.nvidia.com/cuda-downloads
2. Install Visual C++ Build Tools: https://visualstudio.microsoft.com/downloads/
3. Verify CUDA: `nvcc --version`
4. Try manual build: `pip install gsplat --no-cache-dir`

### Low GPU Memory Error

**Symptoms:** CUDA out of memory

**Solutions:**
1. Reduce `num_iterations` (300 → 100)
2. Reduce `max_keyframes` (50 → 30)
3. Subsample point cloud in training

### Poor Reconstruction Quality

**Symptoms:** Noisy or incomplete reconstruction

**Solutions:**
1. Increase `num_iterations` (300 → 500)
2. Use SIFT instead of ORB (`feature_detector: 'sift'`)
3. Reduce `motion_threshold` to select more keyframes
4. Ensure good lighting and camera motion (avoid pure rotation)

### Slow Performance

**Symptoms:** Takes too long per reconstruction

**Solutions:**
1. Reduce `num_iterations` (300 → 100-150)
2. Increase `reconstruction_interval` (5.0 → 10.0)
3. Reduce `min_keyframes` (10 → 5)
4. Check GPU utilization with `nvidia-smi`

## Development

### Running Tests

```bash
# Unit tests (future)
pytest tests/reconstruction/

# Integration test
python tests/test_reconstruction_pipeline.py
```

### Code Structure

```
src/reconstruction/
├── __init__.py           # Module exports
├── frame_selector.py     # Keyframe selection logic
├── pose_estimator.py     # SfM and pose recovery
├── gaussian_trainer.py   # 3D Gaussian optimization
├── ply_writer.py         # Output format writers
└── reconstructor.py      # Main pipeline orchestration
```

## References

- **3D Gaussian Splatting Paper:** https://repo-sam.inria.fr/fungraph/3d-gaussian-splatting/
- **gsplat Library:** https://github.com/nerfstudio-project/gsplat
- **SplaTAM:** https://github.com/spla-tam/SplaTAM
- **MASt3r:** https://github.com/naver/mast3r
- **SuperSplat Viewer:** https://playcanvas.com/supersplat

## License

See project root LICENSE file.

## Authors

**Naomi** - CV / 3D Reconstruction Engineer

For questions or issues, see `.squad/decisions/inbox/naomi-reconstruction-approach.md`
