# Quick Start: 3D Gaussian Splatting Reconstruction

Get up and running with the reconstruction module in 5 minutes.

## Step 1: Install Dependencies

```bash
# From project root
scripts\install_reconstruction.bat
```

Wait for installation to complete. This installs:
- PyTorch with CUDA
- gsplat (3D Gaussian Splatting)
- OpenCV (computer vision)
- Other dependencies

**Note:** If gsplat fails, you may need to install:
1. CUDA Toolkit: https://developer.nvidia.com/cuda-downloads
2. Visual Studio Build Tools: https://visualstudio.microsoft.com/downloads/

## Step 2: Verify Installation

```bash
python verify_reconstruction.py
```

You should see:
```
✓ All modules imported successfully
✓ FrameSelector initialized and working
✓ PoseEstimator initialized
✓ PLYWriter initialized
✓ GaussianTrainer initialized
✓ PyTorch 2.x
✓ CUDA available: True
✓ GPU: [Your GPU name]
✓ VRAM: X.X GB
```

## Step 3: Try Basic Example

```bash
python examples\example_basic_reconstruction.py
```

This generates a synthetic test sequence and reconstructs it.

Output:
```
Generated 30 test frames
Processing frames...
✓ Reconstruction updated at frame 15
  Output: ./output/reconstructions/reconstruction_0001.ply

Success! Open the .ply file in:
  - Blender (with Gaussian Splatting addon)
  - SuperSplat: https://playcanvas.com/supersplat
```

## Step 4: View Your Reconstruction

### Option A: Blender

1. Install Blender: https://www.blender.org/download/
2. Install Gaussian Splatting addon
3. File → Import → Gaussian Splat (.ply)
4. Select `./output/reconstructions/reconstruction_0001.ply`

### Option B: SuperSplat (Web Viewer)

1. Go to: https://playcanvas.com/supersplat
2. Click "Load File"
3. Select your .ply file
4. Rotate/zoom to view

### Option C: antimatter15's Viewer

1. Download viewer from: https://antimatter15.com/splat/
2. Load local .ply file

## Step 5: Integrate with Your Video Stream

```python
from src.reconstruction import GaussianReconstructor
import queue
import threading

# Create reconstructor
config = GaussianReconstructor.create_default_config()
config['output_dir'] = './output/my_drone_footage'
config['min_keyframes'] = 10

reconstructor = GaussianReconstructor(config)

# Setup queue
frame_queue = queue.Queue()
stop_event = threading.Event()

# Start reconstruction thread
thread = threading.Thread(
    target=reconstructor.run,
    args=(frame_queue, stop_event)
)
thread.start()

# Feed frames from your video stream
# frame: np.ndarray (H, W, 3) uint8
# timestamp: float (seconds)
frame_queue.put((frame, timestamp))

# When done
stop_event.set()
thread.join()

# Get output
print(f"Reconstruction: {reconstructor.get_output_path()}")
```

## Configuration

Edit `config/reconstruction_config.yaml`:

```yaml
# For faster updates (lower quality)
gaussian_trainer:
  num_iterations: 100  # Default: 300

reconstruction_interval: 3.0  # Default: 5.0

# For better quality (slower)
gaussian_trainer:
  num_iterations: 500  # Default: 300

min_keyframes: 15  # Default: 10
```

## Common Issues

### "gsplat not installed"

```bash
# Install CUDA Toolkit first, then:
pip install gsplat --no-cache-dir
```

### "CUDA out of memory"

Edit config:
```yaml
gaussian_trainer:
  num_iterations: 100  # Reduce from 300
  
frame_selector:
  max_keyframes: 30  # Reduce from 50
```

### "No GPU detected"

The module will work on CPU but will be very slow. Consider:
- Using a machine with NVIDIA GPU
- Reducing iterations to 50-100
- Reducing image resolution

## Next Steps

1. **Test with real footage:** Use actual drone video
2. **Tune parameters:** Adjust config for your use case
3. **Monitor performance:** Check VRAM usage with `nvidia-smi`
4. **Experiment with quality:** Try different iteration counts

## Need Help?

- **Module docs:** `src/reconstruction/README.md`
- **Full decision:** `.squad/decisions/inbox/naomi-reconstruction-approach.md`
- **Examples:** `examples/` directory

---

**Ready to reconstruct!** 🚁 → 🎥 → 🔧 → 📦 → 👁️
