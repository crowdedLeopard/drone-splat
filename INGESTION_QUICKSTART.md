# RTMP Ingestion Pipeline — Quick Reference

## Setup (First Time Only)

```powershell
# 1. Install FFmpeg (if not already installed)
#    Download from: https://ffmpeg.org/download.html
#    Add to PATH

# 2. Run setup script
.\scripts\setup_mediamtx.ps1
```

## Usage

### Start RTMP Server
```powershell
.\scripts\start_stream.ps1
```

This shows your PC's IP and the RTMP URL for DJI Fly app configuration.

### Test Without Drone
```powershell
.\scripts\test_stream.ps1
```

Generates a synthetic test stream to verify the pipeline works.

### Use in Python
```python
from src.ingestion import RTMPIngestor, StreamMonitor
import queue, threading

config = {
    'rtmp_url': 'rtmp://localhost:1935/live/drone',
    'frame_rate': 2.0,
    'width': 1920,
    'height': 1080
}

frame_queue = queue.Queue(maxsize=100)
stop_event = threading.Event()

ingestor = RTMPIngestor(config)
monitor = StreamMonitor(ingestor)
monitor.start()

# Run in background thread
thread = threading.Thread(
    target=ingestor.run,
    args=(frame_queue, stop_event),
    daemon=True
)
thread.start()

# Get frames
while True:
    frame_data = frame_queue.get()
    # frame_data['frame'] is numpy BGR array (H, W, 3) uint8
    # frame_data['timestamp'] is Unix timestamp
    # frame_data['frame_id'] is sequential int
```

See `examples\rtmp_ingest_example.py` for complete example.

## DJI Fly App Configuration

1. **Settings** → **Transmission** → **Live Streaming**
2. Select **Custom RTMP**
3. Enter: `rtmp://<your-pc-ip>:1935/live/drone`
4. Start streaming

See `docs\dji_setup.md` for detailed instructions.

## Troubleshooting

| Problem | Solution |
|---------|----------|
| "FFmpeg not found" | Install FFmpeg and add to PATH |
| "Cannot connect to RTMP server" | Check firewall (port 1935), verify mediamtx running |
| Stream stuttering | Reduce to 720p in DJI Fly, check WiFi |
| "Frame queue full" | Reduce frame_rate or increase queue size |

## Files Created

```
src/ingestion/
  __init__.py              RTMPIngestor, StreamMonitor exports
  rtmp_ingestor.py         Frame extraction via FFmpeg pipe
  stream_monitor.py        Connection monitoring & reconnect
  README.md                Full documentation

scripts/
  setup_mediamtx.ps1       Download & configure mediamtx
  start_stream.ps1         Start RTMP server
  test_stream.ps1          Test without drone

config/
  mediamtx.yml             RTMP server config

docs/
  dji_setup.md             DJI drone setup instructions

examples/
  rtmp_ingest_example.py   Usage example

.squad/decisions/inbox/
  amos-ingestion-design.md Design decisions & rationale
```

## Frame Output Format

```python
{
    'frame': numpy.ndarray,  # Shape: (1080, 1920, 3), dtype: uint8, BGR
    'timestamp': float,      # Unix time
    'frame_id': int         # Sequential counter
}
```

**Note:** BGR format (OpenCV standard), not RGB.

## Performance

- **Latency:** 100-300ms (drone → queue)
- **CPU:** <20% for 2 fps extraction
- **Bandwidth:** 4-8 Mbps from drone

## Next Integration Point

This module delivers frames to `threading.Queue`. **Naomi's reconstruction module** consumes from this queue at 2-5 fps for 3DGS processing.
