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

