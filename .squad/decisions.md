# Squad Decisions

## Active Decisions

### 1. Architecture: Real-Time 3D Gaussian Splatting System
**Owner:** Holden (Lead Architect)  
**Status:** ✅ Approved  
**Date:** 2026-03-13

**Decision:** Windows-native system with local GPU processing + optional Azure storage
- MediaMTX for RTMP (native Windows binary)
- Feature-based SfM + gsplat for reconstruction
- Web viewer for visualization
- Azure Blob Storage only (no compute)

**Rationale:** Simplifies Windows deployment, leverages existing GPU, minimizes cloud costs

---

### 2. RTMP Ingestion: MediaMTX + FFmpeg Pipe
**Owner:** Amos (Backend/Streaming)  
**Status:** ✅ Approved  
**Date:** 2026-03-13

**Decision:** mediamtx server + FFmpeg direct pipe (no temp files)
- Single binary, no WSL needed
- Frame rate control: 2-5 fps
- Auto-reconnect on stream drop

**Rationale:** Simplest on Windows, minimal dependencies, proven reliability

---

### 3. Reconstruction: Pragmatic Sliding Window SfM
**Owner:** Naomi (CV/3D Reconstruction)  
**Status:** ✅ Approved  
**Date:** 2026-03-13

**Decision:** Feature-based SfM + gsplat optimization (not full SLAM)
- Keyframe selection via optical flow
- SIFT feature matching + RANSAC
- 50-keyframe sliding window
- 300-iteration Gaussian training (default)

**Rationale:** Windows compatibility, manageable scope, demo-quality output. Avoids SplaTAM/MASt3r complexity

---

### 4. Viewer: Web-First + Blender Fallback
**Owner:** Bobbie (Visualization)  
**Status:** ✅ Approved  
**Date:** 2026-03-13

**Decision:** Primary web viewer (localhost:8080) + Blender integration option
- File watcher with 2-second debounce
- Auto-reload on .ply file update
- SuperSplat links for high-quality viewing
- Blender optional for professional work

**Rationale:** Zero install friction for web, auto-reload critical for iterative demos

---

### 5. Azure: Blob Storage Only (Disable by Default)
**Owner:** Alex (Cloud/DevOps)  
**Status:** ✅ Approved  
**Date:** 2026-03-13

**Decision:** Minimal cloud: Blob Storage + static website, disabled by default
- No compute in cloud
- <$0.10/month demo budget
- Graceful degradation (system works without it)
- Optional opt-in via .env

**Rationale:** Reduces complexity, prevents cost surprises, system functional without Azure

---

### 6. Integration Contracts: File-Based Queues
**Owner:** Holden (Lead Architect)  
**Status:** ✅ Approved  
**Date:** 2026-03-13

**Decision:** Queue-based module communication
- Amos → Naomi: Frame queue (numpy arrays + timestamp)
- Naomi → Bobbie: .ply file output directory
- Auto-reconnection logic for resilience

**Rationale:** Simpler than shared memory, loose coupling, easy debugging

---

### 7. Quality Priority Directive
**Owner:** Copilot (via crowdedLeopard)  
**Status:** ✅ Active  
**Date:** 2026-03-14

**Decision:** Prioritize best-quality Gaussian Splatting reconstruction.
- Use MASt3r for pose estimation (not SIFT fallback)
- Use gsplat for rasterization (no PyTorch fallback compromise)
- Configure for 1000+ iterations, SH degree 3
- Implement proper densification + pruning
- Override earlier "pragmatic simplification" decisions

**Rationale:** User explicitly requested quality priority over simplicity. Architecture and implementation details in holden-quality-architecture.md

---

### 8. Path B Architecture Unification
**Owner:** Holden (Lead Architect)  
**Status:** ✅ Implemented  
**Date:** 2026-03-13

**Decision:** Retire Path A (RTMPListener → FrameExtractor → SLAMProcessor), wire in working Path B (RTMPIngestor → GaussianReconstructor → PLYWriter).

**Rationale:** Path A had all stubs; Path B is 90% functional with real implementations.

**Implementation:**
- Rewrote `src/main.py` with Path B components
- Created `demo.py` for drone-free testing (synthetic frames)
- Fixed `src/reconstruction/__init__.py` (only exports Path B)
- Changed from loguru to standard logging

---

### 9. Dependency Installation
**Owner:** Amos (Backend/Streaming)  
**Status:** ✅ Implemented  
**Date:** 2026-03-14

**Decision:** Install missing dependencies and fix requirements.txt.

**Actions:**
- Installed: loguru, opencv-python, watchdog, plyfile, colorama
- Upgraded: azure-storage-blob (2.1.0 → 12.28.0)
- Fixed requirements.txt: removed numpy version cap, commented out pytorch3d, gradio, open3d
- Fixed verify_reconstruction.py Unicode encoding (Windows console)
- Created scripts/install_deps.ps1 for automated setup

**Impact:** Project now imports successfully without dependency errors.

---

### 10. Viewer Implementation (Three.js + Auto-Refresh)
**Owner:** Bobbie (Visualization)  
**Status:** ✅ Implemented  
**Date:** 2026-03-13

**Decision:** Rewrite viewer with Three.js PLY parser + 2-second polling auto-refresh.

**Implementation:**
- `src/viewer/viewer.html`: Complete Three.js viewer with PLY binary/ASCII support
- `src/viewer/viewer_server.py`: Removed loguru, added /api/latest endpoint
- Point size 0.02 for splat rendering, auto-rotate for demo appeal
- Height-based gradient fallback if no vertex colors

**Impact:** ✅ Viewer now fully functional, renders 3D point clouds in real-time

---

### 11. Azure Infrastructure Provisioning
**Owner:** Alex (Cloud/DevOps)  
**Status:** ✅ Implemented  
**Date:** 2026-03-14

**Decision:** Provision Azure storage account `dronesplat4014` in Australia East.

**Resources:**
- Storage account: dronesplat4014 (Hot, LRS)
- Container: gaussian-splats
- Resource group: rg-drone-splat-demo
- Region: Australia East

**Configuration:**
- Connection strings in `.env` (gitignored)
- `.env.example` template updated
- `azure/README.md` with setup guide
- `azure/storage_uploader.py` supports both connection string + Azure AD auth
- Cost: ~$0.02-0.05/month (meets <$0.10/month budget)

**Note:** Subscription policy blocks shared key access; Azure AD auth preferred.

---

### 12. Gaussian Rendering Fix
**Owner:** Naomi (CV/3D Reconstruction)  
**Status:** ✅ Implemented  
**Date:** 2026-03-14

**Decision:** Implement `_render_gaussians()` with dual-path strategy.

**Implementation:**
- Primary: gsplat library rasterization (10-100x faster)
- Fallback: Pure PyTorch differentiable rasterizer (CPU-compatible, 500 Gaussian limit)
- Handles SH evaluation, parameter transforms (log scales, logit opacities)
- Full gradient flow support for training

**Impact:** ✅ Gaussian Splat training now has actual gradient signal

---

### 13. Quality Architecture Decision (MASt3r + gsplat)
**Owner:** Holden (Lead Architect)  
**Status:** ✅ Approved  
**Date:** 2026-03-14

**Decision:** Use MASt3r (pose + dense pointcloud) + gsplat (rasterization) for best reconstruction quality.

**Critical Blocker:** PyTorch installed as CPU-only. GPU support must be reinstalled (Wave 2, Amos).

**Rationale:**
- MASt3r: State-of-the-art accuracy, dense 3D pointmaps, metric scale
- gsplat: 1.5.3 pure Python wheel with JIT CUDA compilation
- Quality gap between MASt3r and SIFT is significant
- Installation plan documented in holden-quality-architecture.md
- Fallbacks defined (DUSt3r, enhanced SIFT) if MASt3r fails

**Configuration:**
- 3000 iterations (vs 300), SH degree 3, densification 500-2000, pruning 0.005
- 10-20 frames per batch (4GB VRAM budget)
- Output: 50k-200k Gaussians per scene

---

### 14. MASt3r Integration Spec
**Owner:** Holden (for Naomi)  
**Status:** ✅ Documented  
**Date:** 2026-03-14

**Detailed specification for Naomi's implementation:**
- Create `src/reconstruction/mast3r_estimator.py` (MASt3r wrapper)
- Update `src/reconstruction/gaussian_trainer.py` (densification, hyperparameters)
- Update `src/reconstruction/reconstructor.py` (integration point)
- Create `config/quality.yaml` (best-quality settings)
- Progressive SH degree training, optimizer updates on densification

**Full API reference and testing commands in holden-naomi-spec.md**

---

## Deferred Decisions

### Performance Optimization
**Status:** Future phase  
**Options:** GPU decode (NVDEC), streaming for large files, LOD support
**Decision point:** After initial testing identifies bottlenecks

### Loop Closure Detection
**Status:** Future enhancement  
**Options:** Enable/disable SLAM loop closure  
**Decision point:** If pose drift issues observed in long sequences

---

## Governance

- All meaningful changes require team consensus
- Document architectural decisions here
- Keep history focused on work, decisions focused on direction
- Major changes go to decisions.md, minor updates to agent history.md
- Wave 1 and Wave 2 decisions consolidated in this file
