# bobbie — Project History

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

### Viewer Architecture (Initial Setup)
- **Web-first approach:** Built web viewer as primary option (zero install, auto-reload, cross-platform)
- **File watcher pattern:** Using `watchdog` library with 2-second debouncing for reliable .ply detection
- **Viewer options evaluated:**
  - SuperSplat (https://playcanvas.com/supersplat) — best quality, drag-and-drop, no install
  - antimatter15/splat — embeddable WebGL viewer for local serving
  - Blender + Gaussian Splatting addon — professional quality but heavier setup
- **Implementation:** Python HTTP server + polling client (no WebSocket needed for 2-second refresh rate)
- **Format compatibility:** All viewers support standard 3DGS .ply format (positions, SH coefficients, opacity, scale, rotation)
- **.ply file structure:** Standard properties: x/y/z, normals, f_dc_*/f_rest_* (spherical harmonics), opacity, scale_*, rot_* (quaternion)
- **Blender integration:** Requires Gaussian Splatting addon (https://github.com/ReshotAI/gaussian-splatting-blender-addon)
- **Trade-offs documented:** Web viewer for demo/quick viewing, Blender for professional quality/compositing

### Viewer Consolidation & Fixes (2026-03-13)
- **Problem:** Two conflicting server implementations (viewer_server.py, web_viewer.py) and two HTML files (index.html, viewer.html)
- **Solution:** Unified viewer.html with working Three.js implementation
- **Removed loguru dependency:** Changed viewer_server.py to use standard logging (loguru not installed)
- **Added /api/latest endpoint:** Integrated web_viewer.py's polling endpoint into viewer_server.py
- **Implemented PLY rendering:** Full Three.js r128 implementation with PLY parser for binary and ASCII formats
- **Features implemented:**
  - Polls /api/latest every 2 seconds for new .ply files
  - Renders point clouds with vertex colors (or height-based gradient if no colors)
  - Auto-rotates at 0.003 rad/frame for demo appeal
  - Dark theme (#1a1a1a background) optimized for 3D point cloud viewing
  - Status indicators: loading (orange), ready (green), error (red)
  - Displays point count, file size, and last update time
  - Supports both binary and ASCII PLY formats
- **Technical details:**
  - Three.js BufferGeometry with position + color attributes
  - PointsMaterial with vertexColors and sizeAttenuation
  - Auto-calculates camera distance based on bounding sphere
  - Point size: 0.02 (optimal for Gaussian splat visualization)
  - Serves from project root to access both viewer HTML and output directory

### Files Created
- `src/viewer/__init__.py` — Module exports
- `src/viewer/file_watcher.py` — Watchdog-based .ply file monitor with debouncing
- `src/viewer/web_viewer.py` — HTTP server with /api/latest endpoint
- `src/viewer/viewer.html` — Client with polling, metadata display, SuperSplat link
- `src/viewer/blender_loader.py` — Subprocess launcher for Blender
- `scripts/viewer/load_splat.py` — Blender Python script for .ply import
- `scripts/viewer/watch_and_reload.py` — CLI tool for auto-reload
- `scripts/setup_viewer.ps1` — Dependency checker and setup automation
- `docs/viewer_setup.md` — Comprehensive setup guide (web, SuperSplat, Blender)

### Files Modified
- `src/viewer/viewer_server.py` — Replaced loguru with standard logging, added /api/latest endpoint, serves viewer.html
- `src/viewer/viewer.html` — Complete rewrite with Three.js PLY rendering

### Next Steps for Integration
- Test with actual .ply output from Naomi's reconstruction module
- Optimize for large files (typical drone splats: 50-500 MB)
- Consider streaming/LOD for better performance with large datasets

