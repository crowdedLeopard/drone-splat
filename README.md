# Real-Time 3D Gaussian Splatting Demo

A real-time 3D reconstruction system that processes RTMP video streams from a DJI drone and generates incrementally updated 3D Gaussian Splatting models.

## System Overview

This system creates a live 3D reconstruction pipeline:
1. **RTMP Ingestion**: DJI drone streams video via RTMP protocol
2. **Frame Extraction**: Selected frames extracted at controlled rate (2-5 fps)
3. **3D Reconstruction**: SLAM-based Gaussian Splatting reconstruction using sliding window approach
4. **Output**: Continuously updated `.splat` or `.ply` file
5. **Visualization**: Real-time viewing in web-based viewer or Blender
6. **Cloud Storage**: Optional upload to Azure Blob Storage for sharing

**Important**: This is a demo system. Expect reconstruction updates every 3-10 seconds, not 30fps real-time. The reconstruction quality depends on camera movement, scene texture, and compute capability.

## Architecture

```
┌─────────────┐      RTMP      ┌──────────────┐     Frames     ┌──────────────────┐
│  DJI Drone  │ ─────────────> │   MediaMTX   │ ─────────────> │ Frame Extraction │
└─────────────┘                 │ RTMP Server  │                │   (FFmpeg)       │
                                └──────────────┘                └──────────────────┘
                                                                          │
                                                                          │ JPEG frames
                                                                          ▼
                                ┌──────────────┐    .splat/ply   ┌──────────────────┐
                                │  Web Viewer  │ <─────────────  │ 3DGS Reconstruct │
                                │  or Blender  │                 │  (CUDA/PyTorch)  │
                                └──────────────┘                 └──────────────────┘
                                                                          │
                                                                          │ Optional
                                                                          ▼
                                                                 ┌─────────────────┐
                                                                 │  Azure Blob     │
                                                                 │  Storage        │
                                                                 └─────────────────┘
```

## Prerequisites

### Hardware Requirements
- **GPU**: NVIDIA GPU with CUDA support (RTX 3060 or better recommended)
  - Minimum 8GB VRAM for reconstruction
  - CUDA Compute Capability 7.0 or higher
- **CPU**: Modern multi-core processor (Intel i7/AMD Ryzen 7 or better)
- **RAM**: 16GB minimum, 32GB recommended
- **Storage**: 50GB free space for dependencies, model weights, and output

### Software Requirements
- **OS**: Windows 11 (primary development target)
- **Python**: 3.10 or 3.11 (tested on 3.11)
- **CUDA Toolkit**: 11.8 or 12.1 (must match PyTorch CUDA version)
- **FFmpeg**: Latest stable build (for frame extraction)
- **MediaMTX**: v1.5.0 or later (RTMP server)
- **Git**: For cloning repositories
- **Optional**: Blender 4.0+ with Gaussian Splatting addon

### DJI Drone Requirements
- DJI Mini 3 Pro, Air 3, Mavic 3, or similar model with live streaming capability
- DJI Fly app or compatible ground station software
- Custom RTMP URL configuration support

## Installation

### 1. Clone Repository
```bash
git clone <repository-url>
cd Splatting
```

### 2. Install Python Dependencies
```bash
# Create virtual environment
python -m venv venv
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

**Note**: PyTorch with CUDA will be installed. Ensure CUDA Toolkit is installed first. If you encounter CUDA version mismatches, install PyTorch manually:
```bash
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118
```

### 3. Install FFmpeg
Download FFmpeg from https://ffmpeg.org/download.html and add to system PATH, or use Chocolatey:
```bash
choco install ffmpeg
```

### 4. Install MediaMTX (RTMP Server)
Download MediaMTX from https://github.com/bluenviron/mediamtx/releases

```bash
# Extract to project directory
cd Splatting
# Download latest Windows release
curl -LO https://github.com/bluenviron/mediamtx/releases/download/v1.5.1/mediamtx_v1.5.1_windows_amd64.zip
# Extract (or use Windows Explorer)
tar -xf mediamtx_v1.5.1_windows_amd64.zip -C .
```

### 5. Download 3DGS Model Weights
The reconstruction module will download MASt3r/DUST3r weights on first run (~2GB). Ensure stable internet connection.

### 6. Configure Azure (Optional)
If using Azure Blob Storage:
```bash
# Set environment variable with connection string
$env:AZURE_STORAGE_CONNECTION_STRING="<your-connection-string>"
```

Or configure in `config/config.yaml`.

## Configuration

### DJI Drone RTMP Setup

1. **In DJI Fly App (or ground station software)**:
   - Go to Settings → Transmission Settings → Live Streaming
   - Select "Custom RTMP"
   - Enter URL: `rtmp://<your-pc-ip>:1935/live/drone`
   - Enter Stream Key: `drone` (or as configured in config.yaml)

2. **Find your PC's local IP**:
   ```bash
   ipconfig
   # Look for IPv4 Address on your network adapter (e.g., 192.168.1.100)
   ```

3. **Update config/config.yaml** with correct IP if needed

### System Configuration

Edit `config/config.yaml` to adjust:
- RTMP server settings (port, stream key)
- Frame extraction rate (2-5 fps recommended)
- Reconstruction parameters (window size, batch size)
- Output format (.splat or .ply)
- Azure storage settings

## Usage

### 1. Start the RTMP Server
```bash
# From project root
.\mediamtx.exe
# MediaMTX will start on port 1935 (default)
```

### 2. Start the Reconstruction Pipeline
```bash
# In a new terminal, activate venv
venv\Scripts\activate

# Run main pipeline
python src\main.py
```

The pipeline will:
- Wait for RTMP stream connection
- Extract frames at configured rate
- Perform incremental 3D reconstruction
- Update output file as new data arrives
- Optionally upload to Azure Blob Storage

### 3. Connect DJI Drone
- Power on drone and controller
- Open DJI Fly app
- Start live streaming with custom RTMP settings
- The pipeline will automatically detect the stream and begin processing

### 4. View Results

**Option A: Web Viewer (Recommended for demos)**
```bash
python -m http.server 8000 -d src\viewer
# Open browser to http://localhost:8000
# The viewer auto-refreshes when .splat file updates
```

**Option B: Blender**
- Install Blender 4.0+
- Install Gaussian Splatting addon (e.g., SuperSplat import)
- File → Import → Gaussian Splat (.splat or .ply)
- Reload file periodically to see updates

## Project Structure

```
Splatting/
├── src/
│   ├── ingestion/          # RTMP → frames (Amos)
│   │   ├── __init__.py
│   │   ├── rtmp_listener.py
│   │   └── frame_extractor.py
│   ├── reconstruction/     # frames → splats (Naomi)
│   │   ├── __init__.py
│   │   ├── slam_processor.py
│   │   └── model_manager.py
│   ├── viewer/            # splat display (Bobbie)
│   │   ├── __init__.py
│   │   ├── index.html
│   │   └── viewer.js
│   ├── utils/             # shared utilities
│   │   ├── __init__.py
│   │   └── logger.py
│   └── main.py            # pipeline orchestrator (Holden)
├── azure/                 # Azure deployment (Alex)
│   ├── storage_uploader.py
│   └── README.md
├── config/
│   └── config.yaml        # central configuration
├── scripts/               # helper scripts
│   └── test_stream.py     # test RTMP without drone
├── data/                  # runtime data (created automatically)
│   ├── frames/            # extracted frames
│   └── output/            # .splat/.ply files
├── requirements.txt       # Python dependencies
└── README.md             # this file
```

## Performance Expectations

- **Frame extraction**: Real-time (no lag)
- **Reconstruction update**: Every 3-10 seconds (depends on window size, GPU)
- **Output file size**: 10-100 MB for typical scenes
- **Memory usage**: 8-16 GB RAM, 6-10 GB VRAM
- **Latency**: 5-15 seconds from drone capture to viewable 3D update

**Not real-time 30fps**: 3D Gaussian Splatting reconstruction is compute-intensive. This system prioritizes reconstruction quality over speed for demo purposes.

## Troubleshooting

### RTMP Connection Issues
- Verify PC IP address is correct in DJI Fly app
- Check Windows Firewall allows port 1935
- Ensure MediaMTX is running before starting drone stream
- Check MediaMTX logs: `.\mediamtx.exe` (console output)

### CUDA/GPU Issues
- Verify CUDA Toolkit installation: `nvcc --version`
- Check PyTorch CUDA: `python -c "import torch; print(torch.cuda.is_available())"`
- Update GPU drivers to latest version

### Reconstruction Quality Issues
- Improve lighting conditions
- Slow down drone movement (smooth, controlled motion)
- Ensure scene has sufficient texture detail
- Increase frame extraction rate in config.yaml (but watch performance)

### Performance Issues
- Reduce frame extraction rate (try 2 fps)
- Reduce reconstruction window size in config.yaml
- Close other GPU-intensive applications
- Monitor GPU temperature and throttling

## Azure Setup Summary

For minimal-cost demo deployment:
1. Create Azure Storage Account (Standard LRS)
2. Create container named `gaussian-splats`
3. Get connection string from Azure Portal
4. Set environment variable or update config.yaml
5. Enable in config: `azure.enabled: true`

The system will upload each updated .splat file with timestamp. No GPU compute in Azure needed - all processing is local.

## Development

- **Amos**: RTMP ingestion and frame extraction
- **Naomi**: 3D reconstruction pipeline
- **Bobbie**: Viewer implementation
- **Alex**: Azure integration
- **Holden**: Architecture and integration
- **Ralph**: Testing and validation

## License

[Specify license]

## Credits

Built with:
- [MediaMTX](https://github.com/bluenviron/mediamtx) - RTMP server
- [MASt3r](https://github.com/naver/mast3r) - 3D reconstruction
- [gsplat](https://github.com/nerfstudio-project/gsplat) - Gaussian Splatting implementation
- [PyTorch](https://pytorch.org/) - Deep learning framework
