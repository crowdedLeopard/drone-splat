# RTMP Ingestion Module

Real-time video frame extraction from DJI drone RTMP streams.

## Quick Start

### 1. Setup (One-time)

```powershell
# Install mediamtx and configure firewall
.\scripts\setup_mediamtx.ps1
```

### 2. Start RTMP Server

```powershell
# Start mediamtx and display connection info
.\scripts\start_stream.ps1
```

This will show your PC's IP addresses and the RTMP URL to use in the DJI Fly app.

### 3. Configure DJI Drone

See `docs\dji_setup.md` for detailed instructions.

**Quick steps:**
1. Open DJI Fly app
2. Settings → Transmission → Live Streaming → Custom RTMP
3. Enter: `rtmp://<your-pc-ip>:1935/live/drone`
4. Start streaming

### 4. Test Without Drone

```powershell
# Generate synthetic test stream
.\scripts\test_stream.ps1
```

## Python Usage

```python
import queue
import threading
from src.ingestion import RTMPIngestor, StreamMonitor

# Create frame queue
frame_queue = queue.Queue(maxsize=100)
stop_event = threading.Event()

# Configure ingestor
config = {
    'rtmp_url': 'rtmp://localhost:1935/live/drone',
    'frame_rate': 2.0,  # Extract 2 frames per second
    'width': 1920,
    'height': 1080
}

ingestor = RTMPIngestor(config)

# Optional: Add connection monitoring
monitor = StreamMonitor(ingestor)
monitor.start()

# Start ingestion in background thread
ingest_thread = threading.Thread(
    target=ingestor.run,
    args=(frame_queue, stop_event),
    daemon=True
)
ingest_thread.start()

# Process frames
try:
    while True:
        frame_data = frame_queue.get(timeout=5.0)
        
        # frame_data = {
        #     'frame': np.ndarray,   # BGR image (H, W, 3) uint8
        #     'timestamp': float,    # time.time()
        #     'frame_id': int        # sequential frame number
        # }
        
        # Your processing here
        print(f"Got frame {frame_data['frame_id']}, shape: {frame_data['frame'].shape}")
        
except KeyboardInterrupt:
    print("Stopping...")
    stop_event.set()
    monitor.stop()
```

## Frame Format

Frames are delivered as dictionaries:

```python
{
    'frame': numpy.ndarray,   # Shape: (height, width, 3), dtype: uint8, format: BGR
    'timestamp': float,       # Unix timestamp (time.time())
    'frame_id': int          # Sequential frame number starting from 0
}
```

**Note:** OpenCV format is BGR, not RGB.

## Requirements

### System Requirements
- Windows 11 (or Windows 10)
- Administrator access (for firewall configuration)
- Network connectivity (WiFi or Ethernet)

### Software Requirements
- **FFmpeg:** Must be installed and in PATH
  - Download: https://ffmpeg.org/download.html
  - Windows builds: https://www.gyan.dev/ffmpeg/builds/
  - Verify: `ffmpeg -version` in PowerShell
  
- **Python 3.8+** with packages:
  - `numpy` (for frame arrays)
  - Standard library: `threading`, `subprocess`, `queue`, `logging`

### Network Requirements
- Port 1935 (TCP) open in Windows Firewall
- PC and drone controller on the same network

## Architecture

```
DJI Drone
   ↓ RTMP stream (1080p30, H.264)
mediamtx (RTMP server, port 1935)
   ↓ RTMP stream
FFmpeg (frame extraction, fps filter)
   ↓ raw BGR24 frames (pipe)
RTMPIngestor (Python)
   ↓ numpy arrays
threading.Queue
   ↓
Reconstruction Module (Naomi)
```

## Troubleshooting

### "FFmpeg not found"
Install FFmpeg and add to PATH. Verify with: `ffmpeg -version`

### "Cannot connect to RTMP server" (from DJI Fly)
1. Check mediamtx is running: `Get-Process -Name mediamtx`
2. Verify firewall rule exists: `Get-NetFirewallRule -DisplayName "*mediamtx*"`
3. Check network: PC and phone on same network
4. Test with: `.\scripts\test_stream.ps1`

### Stream stuttering or dropping frames
1. Reduce DJI stream quality to 720p
2. Check WiFi signal strength
3. Check PC CPU usage (should be <20% for ingestion alone)
4. Reduce extraction frame_rate (try 1.0 fps)

### "Frame queue full, dropping frame"
Reconstruction is slower than ingestion. Either:
- Reduce `frame_rate` in ingestor config
- Increase queue `maxsize`
- Optimize reconstruction pipeline

## Performance

**Typical latency:** 100-300ms from drone camera to Python queue

**CPU usage:**
- mediamtx: <1%
- FFmpeg decode + resample: 5-15% (single core)
- Python ingestion: <1%

**Bandwidth:**
- DJI stream: 4-8 Mbps (1080p30)
- Extraction output: 2-5 fps (~0.5 MB/s if 1080p)

## Files

```
src/ingestion/
  __init__.py              # Module exports
  rtmp_ingestor.py         # Main frame extraction class
  stream_monitor.py        # Connection monitoring and reconnect

scripts/
  setup_mediamtx.ps1       # One-time setup
  start_stream.ps1         # Start RTMP server
  test_stream.ps1          # Test without drone

config/
  mediamtx.yml             # RTMP server configuration

docs/
  dji_setup.md             # DJI Fly app configuration guide

tools/
  mediamtx/                # mediamtx binary (downloaded by setup)
    mediamtx.exe
    mediamtx.yml
```

## License

This module uses:
- **mediamtx:** MIT License (https://github.com/bluenviron/mediamtx)
- **FFmpeg:** LGPL/GPL (https://ffmpeg.org/legal.html)

Check licenses before commercial use.
