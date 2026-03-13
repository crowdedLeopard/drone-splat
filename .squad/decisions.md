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
