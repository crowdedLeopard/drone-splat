# DJI Drone RTMP Streaming Setup

This guide covers how to configure DJI drones to stream RTMP video to the ingestion pipeline.

## Supported DJI Drones

The following DJI drones support RTMP live streaming via the DJI Fly app or DJI RC controller:

- **Mini Series:** Mini 3 Pro, Mini 4 Pro
- **Air Series:** Air 2S, Air 3
- **Mavic Series:** Mavic 3, Mavic 3 Pro, Mavic 3 Classic
- **Enterprise Series:** Mavic 3E, Mavic 3T (via DJI Pilot 2 app)

## Network Setup

You need the drone controller and your PC on the same network. There are several approaches:

### Option 1: PC as Hotspot (Recommended for Windows)
1. Enable Mobile Hotspot on your Windows PC:
   - Settings → Network & Internet → Mobile hotspot
   - Turn on "Share my Internet connection"
   - Note the network name and password
2. Connect your phone/tablet (running DJI Fly) to the PC's hotspot
3. Your PC's IP will be the gateway IP (usually `192.168.137.1`)
4. RTMP URL: `rtmp://192.168.137.1:1935/live/drone`

### Option 2: Same WiFi Network
1. Connect both PC and phone/tablet to the same WiFi network
2. Find your PC's IP address: `ipconfig` in PowerShell (look for IPv4 Address)
3. RTMP URL: `rtmp://<your-pc-ip>:1935/live/drone`

### Option 3: Direct WiFi (DJI RC Pro / RC-N1 with Ethernet)
Some DJI controllers support direct network connection. Consult your controller's manual.

## DJI Fly App Configuration

### Step 1: Enable Live Streaming
1. Open the DJI Fly app
2. Connect to your drone
3. Tap the camera view to enter flight mode
4. Tap the **three dots (...)** in the top-right corner
5. Scroll down and select **Transmission**
6. Find **Live Streaming** section

### Step 2: Configure Custom RTMP
1. In Live Streaming settings, select **Custom RTMP**
2. Enter your RTMP URL:
   ```
   rtmp://<your-pc-ip>:1935/live/drone
   ```
   Example: `rtmp://192.168.137.1:1935/live/drone`
3. (Optional) Set stream quality:
   - **Auto:** Adapts to network conditions
   - **1080p:** 1920x1080 (recommended)
   - **720p:** 1280x720 (lower bandwidth)

### Step 3: Start Streaming
1. Return to the camera view
2. Tap the **Go Live** button (usually in the top menu)
3. Confirm RTMP settings
4. Stream will start — you should see "LIVE" indicator

## Expected Stream Specifications

| Parameter      | Typical Value         |
|----------------|-----------------------|
| Resolution     | 1920x1080 (1080p30)   |
| Frame Rate     | 30 fps                |
| Bitrate        | 4-8 Mbps              |
| Codec          | H.264                 |
| Audio          | AAC (optional)        |

The ingestion pipeline extracts frames at **2-5 fps** from this 30fps stream (reconstruction can't keep up with 30fps).

## Windows Firewall Requirements

The setup script (`scripts\setup_mediamtx.ps1`) should have configured this, but if you have issues:

1. Open **Windows Defender Firewall with Advanced Security**
2. Create a new **Inbound Rule**:
   - Rule Type: Port
   - Protocol: TCP
   - Port: 1935
   - Action: Allow
   - Profile: All (Domain, Private, Public)
   - Name: "mediamtx RTMP (Port 1935)"

Or via PowerShell (as Administrator):
```powershell
New-NetFirewallRule -DisplayName "mediamtx RTMP (Port 1935)" -Direction Inbound -Protocol TCP -LocalPort 1935 -Action Allow -Profile Any
```

## Troubleshooting

### "Cannot connect to RTMP server"
- Verify PC and phone/tablet are on the same network
- Check PC's firewall allows port 1935
- Verify mediamtx is running: `Get-Process -Name mediamtx`
- Ping the PC from phone/tablet to test connectivity

### Stream stuttering or dropping frames
- Reduce stream quality to 720p in DJI Fly settings
- Move closer to WiFi router/hotspot
- Check network bandwidth (4-8 Mbps needed)
- Check PC CPU usage (FFmpeg frame extraction is lightweight, but reconstruction might bottleneck)

### "LIVE" indicator shows but no frames extracted
- Check mediamtx logs for incoming connection
- Verify RTMP URL path is exactly `/live/drone`
- Test with `scripts\test_stream.ps1` to confirm pipeline works
- Check Python ingestion logs

### Black screen or frozen video
- Restart DJI Fly app
- Restart drone
- Check camera settings (ensure camera is not in photo mode)

## Testing Without a Drone

Use the test script to verify the pipeline without a drone:

```powershell
.\scripts\test_stream.ps1
```

This generates a synthetic video stream to `rtmp://localhost:1935/live/drone` — useful for testing the ingestion pipeline before flying.

## Security Note

This setup uses **unencrypted RTMP** on a local network. This is fine for a demo/development environment. For production use:
- Use RTMPS (RTMP over TLS)
- Use a VPN if streaming over public networks
- Configure mediamtx authentication (username/password)

## References

- [DJI Fly App User Manual](https://www.dji.com/support/product/dji-fly)
- [mediamtx Documentation](https://github.com/bluenviron/mediamtx)
- [FFmpeg RTMP Documentation](https://trac.ffmpeg.org/wiki/StreamingGuide)
