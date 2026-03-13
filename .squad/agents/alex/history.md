# alex — Project History

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

### Azure Infrastructure Design (Session 1)
- **Decision:** Blob Storage only (Standard LRS, Hot tier) — no compute, no GPU in cloud
- **Cost:** ~$0.01–0.10/month for demo usage; instant cleanup to $0.00
- **Architecture:** Local machine handles all inference; Azure is optional storage layer
- **Config:** Disable by default (`AZURE_UPLOAD_ENABLED=false`) → graceful degradation
- **Key insight:** "Disable by default" principle means demo works perfectly without Azure configured
- **Tooling:** Bash + PowerShell setup scripts provided; Python uploader client ready
- **Deliverables:** 
  - Setup automation: `setup.sh` (bash), `setup.ps1` (PowerShell)
  - Cleanup: `cleanup.ps1` (one-command teardown)
  - Python client: `src/utils/azure_uploader.py` (optional upload library)
  - Static web viewer: `azure/index.html` (blob listing + SuperSplat links)
  - Config template: `.env.example` (with sensible defaults)
  - Documentation: `docs/azure_setup.md` (step-by-step guide for operators)
  - Cost transparency: `azure/cost_estimate.md` (pricing breakdown + optimization)
  - Decision record: `.squad/decisions/inbox/alex-azure-design.md`

### Cost Control Strategy
- **Monthly spend:** Likely <$0.05 with demo usage; budget alert at $1.00/month as safety
- **Cleanup:** Delete resource group to hit $0.00/month (no long-term costs)
- **Optimization:** Lifecycle policies can auto-delete old files if archive grows

### Why This Beats Alternatives
- Blob Storage (cheap) > GPU Compute ($200+/month)
- No Functions/orchestration needed (keep it simple)
- Works on Windows + Linux; no OS-specific bloat
- Single Azure service = minimal ops overhead

