# Squad Team> Splatting

## Coordinator
| Name | Role | Notes |
|------|------|-------|
| Squad | Coordinator | Routes work, enforces handoffs and reviewer gates. |

## Members
| Name | Role | Charter | Status |
|------|------|---------|--------|
| Holden | Lead / Architect | .squad/agents/holden/charter.md | active |
| Naomi | CV / 3D Reconstruction | .squad/agents/naomi/charter.md | active |
| Amos | Backend / Streaming | .squad/agents/amos/charter.md | active |
| Alex | Cloud / DevOps | .squad/agents/alex/charter.md | active |
| Bobbie | Visualization | .squad/agents/bobbie/charter.md | active |
| Scribe | Scribe | .squad/agents/scribe/charter.md | active |
| Ralph | Work Monitor | — | active |

## Project Context
- **Project:** Real-time 3D Gaussian Splatting from DJI RTMP drone stream
- **User:** crowdedLeopard
- **Created:** 2026-03-13
- **Stack:** Python, FFmpeg, MASt3r/DUST3r/3DGS (CUDA), Azure (demo-budget), Blender viewer
- **Goal:** RTMP stream → frame extraction → real-time 3D Gaussian Splat → Blender visualization
- **Constraints:** Local Windows machine + Azure (minimal cost, demo only). DJI drone as source.
- **Viewer:** Blender with .splat/.ply support, or equivalent lightweight viewer
- **Universe:** The Expanse
