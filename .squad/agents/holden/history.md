# holden — Project History

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

✅ **Path B Architecture Unification (2026-03-13)**
- Rewrote `src/main.py` to use working Path B components (RTMPIngestor → GaussianReconstructor)
- Created `demo.py` for synthetic frame testing (no drone required)
- Fixed `src/reconstruction/__init__.py` to avoid loguru dependency
- All imports verified working

## Learnings

### Architecture Phase (2024)

**System Design Decisions**:
- **MediaMTX over NGINX-RTMP**: Native Windows support critical for target platform - no WSL/Docker complexity
- **MASt3r for reconstruction**: Best balance of quality and integration ease for drone footage. SplaTAM has better SLAM but harder C++ integration
- **Web viewer over Blender**: Demo-friendliness trumps rendering quality - browser-based auto-refresh is killer feature
- **Blob Storage only**: No Azure GPU needed - all compute local keeps costs under $1/month

**Performance Realism**:
- Set expectations early: **3-10 second updates, not 30fps real-time**
- Frame extraction at 2-5 fps is sweet spot (higher doesn't help reconstruction, hurts performance)
- Sliding window (10 frames, 3 overlap) balances quality vs latency
- RTX 3060+ minimum for acceptable reconstruction speed

**Interface Contracts**:
- Clean separation: Amos (frames) → Naomi (splats) → Bobbie (view) → Alex (upload)
- File-based handoffs simpler than shared memory for demo
- Callback pattern for reconstruction updates enables loose coupling

**Configuration Philosophy**:
- Single `config.yaml` beats scattered configs
- Sensible defaults = zero required configuration for basic demo
- Document hardware requirements upfront (CUDA version mismatches kill projects)

**Risk Mitigation**:
- Windows Firewall port 1935 exception will bite users - documented in README
- DJI app RTMP configuration needs screenshots (non-obvious UI)
- Model weight downloads (2GB) need stable internet - warn in README

**Project Structure**:
- Domain-driven directories (ingestion/reconstruction/viewer) map to team members
- Stub implementations with TODO comments guide team
- Central orchestrator (`main.py`) owns integration, not individual components

**What I'd Do Differently Next Time**:
- Could use message queue (Redis/RabbitMQ) instead of file polling, but adds dependency
- Docker might simplify MediaMTX distribution, but Windows Docker Desktop licensing is murky
- Real-time updates possible with WebSocket, but file polling simpler for MVP

**Key Insight**: 
Demo systems need honest performance expectations. Better to under-promise (3-10 sec updates) and over-deliver than promise "real-time" and disappoint. Users appreciate transparency.

### Path Unification (2026-03-13)

**Competing Architectures Identified**:
- **Path A (broken)**: RTMPListener → FrameExtractor → SLAMProcessor — all stubs with TODOs, doesn't work
- **Path B (90% working)**: RTMPIngestor → GaussianReconstructor → PLYWriter — real implementations, only blocked by one TODO

**Decision: Retire Path A, commit to Path B**:
- Rewrote `src/main.py` to use Path B components exclusively
- Changed from loguru to standard logging (loguru may not be installed)
- Wired RTMPIngestor frames directly into GaussianReconstructor.add_frame()
- Registered callback for reconstruction updates → viewer notification + Azure upload

**Config Mapping Patterns**:
- Bridged config.yaml keys to what components actually expect
- Example: `rtmp.host` + `rtmp.port` → full `rtmp_url` for RTMPIngestor
- Allows flexible config without component coupling

**Demo Entry Point Created**:
- `demo.py` generates synthetic frames (no drone/RTMP needed)
- Checkerboard texture + simulated camera pan provides feature points
- Tests full pipeline: frame generation → reconstruction → viewer → file output
- Auto-opens browser to view results

**Import Cleanup Strategy**:
- `slam_processor.py` uses loguru, kept as legacy but not imported by default
- `__init__.py` exports only Path B components (avoids transitive loguru dependency)
- Verified all imports work without errors

**Key Insight**:
When two architectures exist, **audit both and pick the winner decisively**. Half-finished code is worse than no code—delete or clearly mark as legacy. Don't let "maybe we'll use this later" create import/dependency complexity.

### Quality Architecture Decision (2026-03-14)

**System Audit Findings**:
- GPU: RTX 500 Ada (4GB VRAM, CUDA 13.0) — adequate for 10-20 frame batches
- **Critical blocker**: PyTorch installed as CPU-only (`torch 2.10.0+cpu`) — must reinstall with CUDA
- gsplat 1.5.3 available as pure-Python wheel (JIT compiles CUDA at runtime) — will work after torch fix
- MASt3r repo accessible, requires clone + 2GB model weights
- hloc/vggt not on PyPI — would require complex source installs

**Architecture Decision: MASt3r + gsplat**:
- MASt3r for SOTA dense reconstruction (replaces SIFT)
- gsplat for high-performance rasterization (no PyTorch fallback)
- 3000 iterations, SH degree 3, proper densification/pruning

**Install Sequence**:
1. Uninstall cpu-only torch: `pip uninstall torch torchvision torchaudio -y`
2. Install CUDA 12.1 torch: `pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121`
3. Install gsplat: `pip install gsplat`
4. Clone MASt3r to tools/, install requirements, download weights

**VRAM Budget (4GB)**:
- MASt3r model: ~1.5GB
- 10 frames @ 512px: ~200MB
- Pointmap + Gaussians: ~1.3GB
- gsplat rendering: ~500MB
- Total: ~3.5GB ✅ (leaves margin)

**Key Insight**:
Always check `torch.version.cuda` before assuming GPU support. A CPU-only PyTorch install is invisible until you try to use CUDA. The fix is straightforward but blocking — catch it early.

