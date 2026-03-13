# Work Routing

## Routing Table
| Work Type | Route To | Examples |
|-----------|----------|----------|
| System architecture, pipeline design, integration | Holden | End-to-end design, component wiring, technical decisions |
| Gaussian Splatting, 3DGS, SLAM, CV algorithms | Naomi | MASt3r integration, splat generation, reconstruction quality |
| RTMP server, FFmpeg, frame extraction, streaming | Amos | nginx-rtmp, frame pipeline, buffering, Python streaming code |
| Azure infra, cost management, cloud config, DevOps | Alex | Azure Container Instances, Blob Storage, deployment scripts |
| Blender integration, viewer, .splat/.ply formats | Bobbie | Blender Python API, real-time preview, output visualization |
| Code review | Holden | Review PRs, check quality, suggest improvements |
| Testing / validation | Naomi or Amos | Reconstruction quality tests, pipeline integration tests |
| Scope & priorities | Holden | What to build next, trade-offs, decisions |
| Session logging | Scribe | Automatic — never needs routing |

## Issue Routing
| Label | Action | Who |
|-------|--------|-----|
| squad | Triage: analyze issue, assign squad:{member} label | Holden |
| squad:holden | Architecture, design, integration | Holden |
| squad:naomi | CV, Gaussian Splatting, reconstruction | Naomi |
| squad:amos | Streaming, backend pipeline | Amos |
| squad:alex | Azure, cloud infra | Alex |
| squad:bobbie | Visualization, Blender | Bobbie |

## Rules
1. **Eager by default** — spawn all agents who could usefully start work in parallel.
2. **Scribe always runs** after substantial work, always as background. Never blocks.
3. **Quick facts → coordinator answers directly.**
4. **When two agents could handle it**, pick the one whose domain is the primary concern.
5. **"Team, ..." → fan-out.** Spawn all relevant agents in parallel as background.
6. **Anticipate downstream work.** If pipeline is being built, spawn Naomi for CV integration simultaneously.
