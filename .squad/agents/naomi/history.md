# naomi — Project History

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

### 2024 - Initial Reconstruction Pipeline Implementation

**Reconstruction Approach Decision**
- Chose pragmatic sliding-window approach over full SLAM for Windows compatibility
- Feature-based SfM (OpenCV) + gsplat optimization provides good demo quality
- Avoids complex dependencies (SplaTAM, MASt3r-SLAM) that have Windows build issues

**Key Design Choices**
1. **Keyframe Selection**: Optical flow-based motion detection (5px threshold)
   - Prevents redundant near-duplicate frames
   - Maintains sliding window of 50 keyframes max to limit memory
   
2. **Pose Estimation**: SIFT features + Essential matrix + incremental accumulation
   - More robust than ORB for outdoor drone footage
   - Sliding window prevents pose drift accumulation
   
3. **Gaussian Training**: gsplat library (300 iterations default)
   - Balances quality vs. speed for demo use case
   - Nearest-neighbor scale initialization from point cloud
   - Progressive SH degree training (0→3 over iterations)
   
4. **Output Format**: Standard 3DGS .ply (binary little-endian)
   - Compatible with Blender, SuperSplat, antimatter15 viewer
   - Optional .splat format for web delivery

**VRAM Considerations**
- Demo quality: 4GB minimum (10-50K Gaussians, 300 iterations)
- Recommended: 8GB+ for better quality (50-200K Gaussians)
- Point cloud + gradients + optimizer state all consume VRAM

**Windows-Specific Challenges**
- gsplat requires CUDA Toolkit + Visual C++ Build Tools
- Installation script checks prerequisites and provides detailed error messages
- Fallback option: pure PyTorch Gaussian rasterization (slower)

**Integration Points Defined**
- **For Amos**: Frame queue interface `(frame: np.ndarray, timestamp: float)`
- **For Bobbie**: Standard .ply output at `./output/reconstructions/reconstruction_NNNN.ply`
- Thread-safe queue-based processing with stop event

**Performance Expectations**
- Keyframe rate: 0.5-2 frames/second (from 30fps input)
- Reconstruction update: every 5 seconds (when 10+ keyframes available)
- Reconstruction time: 10-30 seconds per update (GPU-dependent)
- Not real-time rendering, but incremental "growing" reconstruction

**Technical Debt & Future Work**
1. Placeholder rendering in `gaussian_trainer.py` - needs actual gsplat API integration
2. Could add COLMAP integration for higher quality poses
3. Loop closure detection would reduce drift in long sequences
4. Progressive densification (add Gaussians during training) per original paper
5. Semantic masking to filter sky/dynamic objects

**Files Created**
- `src/reconstruction/__init__.py` - Module exports
- `src/reconstruction/frame_selector.py` - Keyframe selection (optical flow)
- `src/reconstruction/pose_estimator.py` - SfM and triangulation
- `src/reconstruction/gaussian_trainer.py` - gsplat optimization
- `src/reconstruction/ply_writer.py` - Standard .ply/.splat export
- `src/reconstruction/reconstructor.py` - Main pipeline orchestration
- `scripts/install_reconstruction.bat|.ps1` - Windows installation scripts
- `.squad/decisions/inbox/naomi-reconstruction-approach.md` - Comprehensive decision doc

**Next Steps for Integration**
1. Implement actual gsplat rasterization API (placeholder currently)
2. Integration testing with Amos's frame extraction
3. Verify .ply loading in Blender with Bobbie
4. Performance profiling on target GPU (VRAM usage, timing)
5. Add configuration validation and error handling

