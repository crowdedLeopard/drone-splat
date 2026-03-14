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

