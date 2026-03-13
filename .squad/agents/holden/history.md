# holden — Project History

## Project Context
- **Project:** Real-time 3D Gaussian Splatting from DJI RTMP drone stream
- **User:** crowdedLeopard
- **Stack:** Python, FFmpeg, MASt3r/DUST3r/3DGS (CUDA), Azure (demo-budget), Blender
- **Goal:** RTMP stream from DJI drone → frame extraction → real-time 3D Gaussian Splat → view in Blender
- **Constraints:** Local Windows machine + Azure minimal cost. Demo only.
- **Key files:** (to be discovered during development)

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

