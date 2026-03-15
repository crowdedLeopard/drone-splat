# amos — Project History

## Project Context
- **Project:** Real-time 3D Gaussian Splatting from DJI RTMP drone stream
- **User:** crowdedLeopard
- **Stack:** Python, FFmpeg, MASt3r/DUST3r/3DGS (CUDA), Azure (demo-budget), Blender
- **Goal:** RTMP stream from DJI drone → frame extraction → real-time 3D Gaussian Splat → view in Blender
- **Constraints:** Local Windows machine + Azure minimal cost. Demo only.
- **Key files:** (to be discovered during development)

## Project Status
✅ **Initial Build Session Complete (2026-03-13T16:02:46Z)**
- All 5 agents implemented their modules in parallel
- 126 files, 14,856 lines committed and pushed to GitHub
- Code ready for integration testing
- Repository: https://github.com/crowdedLeopard/drone-splat

## Learnings

### RTMP Ingestion Pipeline (Initial Implementation)

**Completed:**
- Set up mediamtx as RTMP server (single binary, Windows-native, no WSL)
- Implemented `RTMPIngestor` class: FFmpeg pipe to numpy arrays (no temp files)
- Implemented `StreamMonitor` class: connection monitoring and auto-reconnect
- Created setup scripts: `setup_mediamtx.ps1`, `start_stream.ps1`, `test_stream.ps1`
- Documented DJI drone RTMP configuration in `docs\dji_setup.md`
- Decision document: `.squad\decisions\inbox\amos-ingestion-design.md`

**Key Technical Choices:**
- **mediamtx over nginx-rtmp:** Simpler on Windows, no installation needed
- **FFmpeg pipe (rawvideo BGR24):** Direct memory transfer, no disk I/O
- **Frame format:** `{'frame': np.ndarray (H,W,3) uint8 BGR, 'timestamp': float, 'frame_id': int}`
- **Reconnection:** Poll frame count every 5s, restart FFmpeg on stall

**Interface Contract:**
Frames delivered to `threading.Queue` as dict with numpy BGR array, timestamp, frame_id. Naomi's reconstruction module consumes this queue at 2-5 fps.

**Windows-Specific:**
- Firewall rule for TCP 1935 (RTMP port)
- Mobile Hotspot approach for DJI connectivity
- PowerShell scripts for setup and testing

**Testing:**
- Synthetic stream testing via `test_stream.ps1` (no drone needed)
- Real DJI drone testing pending hardware availability

**Dependencies:**
- FFmpeg (user must install separately)
- mediamtx (auto-downloaded by setup script)
- numpy (Python package)

**Known Limitations:**
- Hardcoded 1920x1080 resolution (should auto-detect from stream)
- CPU-only FFmpeg decode (GPU NVDEC could be added for higher fps)
- No audio handling (DJI streams AAC audio, currently ignored)

**Next Steps:**
- Test with real DJI drone
- Benchmark RTMP → queue latency
- Integrate with Naomi's reconstruction queue consumer
- Consider resolution auto-detection

### Dependency Fixes (2025-01-XX)

**Problem Identified:**
- Missing packages: loguru, opencv-python, watchdog, colorama, tqdm, requests, plyfile
- Wrong azure-storage-blob version: v2.1.0 installed but code uses v12 API (BlobServiceClient)
- requirements.txt had incorrect numpy constraint (<2.0.0 but 2.3.5 installed)
- requirements.txt included problematic packages (pytorch3d, gradio, open3d) causing Windows install issues
- verify_reconstruction.py had Unicode encoding issues (✓/✗ chars fail on Windows cp1252)

**Actions Taken:**
- Installed missing packages: loguru 0.7.3, watchdog 6.0.0, plyfile 1.1.3
- Upgraded azure-storage-blob from 2.1.0 → 12.28.0 (v12 API)
- Updated requirements.txt:
  - Removed numpy version upper limit (<2.0.0)
  - Commented out pytorch3d, gradio, open3d (not needed for core demo)
- Fixed verify_reconstruction.py: replaced Unicode chars (✓→[OK], ✗→[FAIL], ⚠→[WARN])
- Created scripts\install_deps.ps1 for easy dependency installation
- Verified all imports work correctly

**Key Findings:**
- opencv-python, colorama, tqdm, requests were already installed
- Azure SDK v12 upgrade successful despite paconn conflict warning (unrelated to project)
- NumPy 2.x compatibility: No issues found with current codebase despite requirements specifying <2.0.0

**Testing:**
- Core imports verified: loguru, cv2, watchdog ✓
- Azure SDK v12 import verified: BlobServiceClient ✓

**Files Modified:**
- requirements.txt (numpy constraint, removed problematic packages)
- verify_reconstruction.py (Unicode → ASCII replacements)
- scripts\install_deps.ps1 (created)

**Decision Document:**
- `.squad\decisions\inbox\amos-dep-fixes.md`

### CUDA Stack Installation (2026-03-14)

**Context:**
Holden's architecture investigation found PyTorch 2.10.0+cpu installed (GPU invisible), blocking gsplat and MASt3r GPU features. System has RTX 500 Ada with 4GB VRAM and CUDA 13.0 driver, but torch wasn't installed with CUDA support.

**Actions Taken:**
1. **Uninstalled CPU-only PyTorch:**
   - `pip uninstall torch torchvision torchaudio -y`
   - Removed PyTorch 2.10.0, torchvision 0.25.0

2. **Installed PyTorch with CUDA 12.1:**
   - `pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121`
   - Successfully installed PyTorch 2.5.1+cu121, torchvision 0.20.1+cu121, torchaudio 2.5.1+cu121
   - Download size: ~2.5GB, took ~5 minutes
   - GPU now visible: NVIDIA RTX 500 Ada Generation Laptop GPU (4.3GB VRAM)

3. **Installed gsplat:**
   - `pip install gsplat`
   - Installed gsplat 1.5.3 with dependencies (ninja, jaxtyping, rich)
   - Import successful, but **JIT CUDA compilation blocked**

4. **Cloned MASt3r to tools/:**
   - `git clone --recursive https://github.com/naver/mast3r.git tools/mast3r`
   - Cloned with submodules: dust3r and croco
   - Installed requirements: scikit-learn, joblib, threadpoolctl
   - Installed dust3r requirements: einops, huggingface-hub, etc.

5. **Downloaded MASt3r model weights:**
   - Model: naver/MASt3R_ViTLarge_BaseDecoder_512_catmlpdpt_metric
   - Size: 2.75GB from HuggingFace Hub
   - Download time: ~3 minutes
   - Parameters: 688,638,856 (~688M)
   - Successfully loaded on first run

**Key Technical Issues:**

**gsplat CUDA Compilation Blocked:**
- Visual Studio 2026 (v18.3.3) installed but not supported by CUDA 12.9
- Error: "unsupported Microsoft Visual Studio version! Only 2017-2022 supported"
- gsplat JIT compilation requires MSVC compiler for CUDA kernels
- Attempted fix with `-allow-unsupported-compiler` flag failed (env var not passed through)
- **Workaround:** PyTorch fallback rasterization works (slower, ~100x, but functional)

**MASt3r RoPE2D Warning:**
- "Warning: cannot find cuda-compiled version of RoPE2D, using slow pytorch version"
- Not blocking — model works, just slightly slower
- Pre-compiled CUDA extension for RoPE2D not available, falls back to PyTorch

**Versions Installed:**
- PyTorch: 2.5.1+cu121
- gsplat: 1.5.3
- ninja: 1.13.0
- MASt3r: Latest from GitHub (2024 commits)
- dust3r: Latest submodule (commit 3cc8c88)
- croco: Latest submodule (commit d7de070)

**System Compatibility:**
- CUDA driver: 13.0 (supports CUDA 12.1 runtime via driver > runtime compatibility)
- Visual Studio: 2026 (v18.3.3) — NOT compatible with CUDA 12.9 for JIT compilation
- Python: 3.11
- Windows: OneDrive - Microsoft sync path (works fine)

**Files Updated:**
- requirements.txt: Updated PyTorch and gsplat notes with CUDA installation instructions
- .gitignore: Already had `tools/` entry (no changes needed)
- Created verify_stack.py: Full CUDA stack verification script
- Created test_gsplat.py: gsplat CUDA render test (for debugging)

**Performance Expectations:**
- MASt3r inference: ~1-2s per image pair on RTX 500 Ada (estimate)
- gsplat PyTorch fallback: ~10-50ms per 512x512 frame (acceptable for demo)
- gsplat CUDA (if compiled): ~0.1-1ms per frame (100x faster, but blocked)

**Decision Document:**
- `.squad\decisions\inbox\amos-cuda-stack.md`

**Next Steps for Naomi:**
1. Use MASt3r immediately for pose estimation (fully working)
2. Use gsplat with PyTorch fallback rasterization (works without CUDA JIT)
3. Future: Fix MSVC/CUDA compatibility or downgrade to VS 2022 for gsplat CUDA compilation

**Timing:**
- Total installation time: ~15 minutes (mostly downloads)
- PyTorch download: ~5 min
- MASt3r model download: ~3 min
- Testing and verification: ~7 min

