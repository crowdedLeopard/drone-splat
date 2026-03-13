# 3D Gaussian Splatting Viewer Setup

This guide explains how to view the 3D Gaussian Splat reconstructions from the DJI drone footage.

## Quick Start: Web Viewer (Recommended)

The easiest way to view splats is using the built-in web viewer:

```bash
python scripts/viewer/watch_and_reload.py --output-dir ./output --mode web
```

This will:
1. Start a local web server at http://localhost:8080
2. Auto-open your browser with the viewer
3. Watch for new .ply files and auto-refresh

**Benefits:**
- No installation required
- Auto-reloads when new data arrives
- Works on any platform
- Lightweight and fast

---

## Option 2: SuperSplat (Best Quality)

[SuperSplat](https://playcanvas.com/supersplat) is a free, high-quality web-based viewer:

1. Go to https://playcanvas.com/supersplat
2. Drag and drop your `.ply` file
3. Use mouse to rotate, scroll to zoom
4. Adjust quality settings in the UI

**Benefits:**
- Highest quality rendering
- No setup required
- Advanced visualization controls
- Supports large splats

**Limitations:**
- Manual drag-and-drop (no auto-reload)
- Requires internet connection

---

## Option 3: Blender Integration

For advanced users who want to edit or composite splats:

### Prerequisites

1. **Install Blender 3.3+**
   - Download from https://www.blender.org/download/
   - Add Blender to your PATH

2. **Install Gaussian Splatting Addon**
   - Method 1: Blender Extensions
     - Open Blender → Edit → Preferences → Get Extensions
     - Search for "Gaussian Splatting"
     - Click Install
   
   - Method 2: Manual Install
     - Download from https://github.com/ReshotAI/gaussian-splatting-blender-addon
     - Blender → Edit → Preferences → Add-ons → Install
     - Select the downloaded .zip file

### Usage

**Manual loading:**
```bash
blender --python scripts/viewer/load_splat.py -- path/to/output.ply
```

**Auto-reload mode:**
```bash
python scripts/viewer/watch_and_reload.py --output-dir ./output --mode blender
```

This will automatically open Blender whenever a new .ply file is detected.

### Blender Tips

- **Viewport shading:** Switch to "Rendered" mode (Z key → Rendered) for best quality
- **Camera control:** Numpad 0 to view through camera
- **Performance:** Reduce viewport samples if slow (Render Properties → Sampling)
- **GPU acceleration:** Preferences → System → Cycles Render Devices → CUDA/OptiX (NVIDIA) or HIP (AMD)

---

## File Format Details

The `.ply` files contain 3D Gaussian Splatting data with these properties:

- **Position:** x, y, z (float32)
- **Normals:** nx, ny, nz (float32)
- **Spherical Harmonics:** f_dc_0, f_dc_1, f_dc_2, f_rest_0...f_rest_44 (RGB color encoding)
- **Opacity:** (float32, pre-sigmoid)
- **Scale:** scale_0, scale_1, scale_2 (float32, log scale)
- **Rotation:** rot_0, rot_1, rot_2, rot_3 (quaternion)

All viewers (web, SuperSplat, Blender addon) support this standard format.

---

## Troubleshooting

### The model looks wrong (upside down, wrong scale, etc.)

**Cause:** DJI drone footage uses different coordinate systems than the reconstruction.

**Solutions:**
- In Blender: Rotate the object (R X 180 for X-axis rotation)
- In SuperSplat: Use the transform controls to adjust
- In code: Adjust camera matrices in `src/reconstruction/camera.py`

### Blender: "Gaussian Splatting addon not found"

1. Verify addon is installed: Edit → Preferences → Add-ons → search "Gaussian"
2. Enable the addon (checkbox)
3. Restart Blender

### Web viewer: Canvas is blank

**Cause:** No .ply file in output directory yet.

**Solution:** Wait for reconstruction to generate first .ply file, or:
```bash
# Download test splat
curl -o output/test.ply https://huggingface.co/datasets/dylanebert/3dgs/resolve/main/bonsai/point_cloud.ply
```

### Blender: Out of memory / crashes

**Cause:** Large splat files (>500MB) can overwhelm GPU memory.

**Solutions:**
- Use web viewer or SuperSplat instead
- Reduce splat resolution in reconstruction config
- Enable "Simplify" in Blender Render Properties
- Use CPU rendering instead of GPU

### Web viewer doesn't auto-reload

**Cause:** File watcher may not be running.

**Check:**
1. Is `watch_and_reload.py` still running?
2. Are new .ply files actually being written to output dir?
3. Check console for error messages

---

## Performance Recommendations

### For real-time viewing during reconstruction:
- **Use web viewer** (lowest overhead)
- **Output smaller splats** (reduce point count in reconstruction config)
- **Use SSD** for output directory (faster file I/O)

### For final quality visualization:
- **Use SuperSplat** (best rendering quality)
- **Use Blender** if you need to composite with other 3D elements

### For GPU memory constraints:
- **Web viewer:** ~2GB VRAM for medium splats
- **SuperSplat:** ~4GB VRAM for large splats
- **Blender:** ~8GB+ VRAM for large splats with real-time preview

---

## Next Steps

- See `README.md` for end-to-end pipeline setup
- See `src/reconstruction/README.md` for reconstruction parameters
- See `.squad/decisions/` for architecture decisions
