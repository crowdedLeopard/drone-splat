# Start mediamtx RTMP server for DJI drone streaming

$ErrorActionPreference = "Stop"

$MEDIAMTX_DIR = "$PSScriptRoot\..\tools\mediamtx"
$MEDIAMTX_EXE = "$MEDIAMTX_DIR\mediamtx.exe"
$CONFIG_FILE = "$MEDIAMTX_DIR\mediamtx.yml"

Write-Host "=== Starting RTMP Server ===" -ForegroundColor Cyan
Write-Host ""

# Check if mediamtx exists
if (!(Test-Path $MEDIAMTX_EXE)) {
    Write-Host "[!] mediamtx not found. Run setup_mediamtx.ps1 first." -ForegroundColor Red
    exit 1
}

# Check if already running
$existingProcess = Get-Process -Name "mediamtx" -ErrorAction SilentlyContinue
if ($existingProcess) {
    Write-Host "[!] mediamtx is already running (PID: $($existingProcess.Id))" -ForegroundColor Yellow
    Write-Host "    To stop: Stop-Process -Id $($existingProcess.Id)" -ForegroundColor Gray
    Write-Host ""
}
else {
    # Start mediamtx
    Write-Host "[*] Starting mediamtx..." -ForegroundColor Yellow
    
    Push-Location $MEDIAMTX_DIR
    try {
        $process = Start-Process -FilePath $MEDIAMTX_EXE -ArgumentList $CONFIG_FILE -PassThru -WindowStyle Normal
        Write-Host "[+] mediamtx started (PID: $($process.Id))" -ForegroundColor Green
        Start-Sleep -Seconds 2
    }
    finally {
        Pop-Location
    }
    Write-Host ""
}

# Display connection info
Write-Host "=== RTMP Server Ready ===" -ForegroundColor Green
Write-Host ""
Write-Host "Your local IP addresses:" -ForegroundColor Cyan

$adapters = Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.InterfaceAlias -notlike "*Loopback*" }
foreach ($adapter in $adapters) {
    $ip = $adapter.IPAddress
    Write-Host "  Interface: $($adapter.InterfaceAlias)" -ForegroundColor Yellow
    Write-Host "  IP: $ip" -ForegroundColor White
    Write-Host "  RTMP URL: rtmp://$ip`:1935/live/drone" -ForegroundColor Cyan
    Write-Host ""
}

Write-Host "=== DJI Fly App Configuration ===" -ForegroundColor Cyan
Write-Host "1. Open DJI Fly app on your phone/tablet"
Write-Host "2. Go to: Settings → Transmission → Live Streaming"
Write-Host "3. Select 'Custom RTMP'"
Write-Host "4. Enter RTMP URL: rtmp://<your-ip>:1935/live/drone"
Write-Host "5. Start streaming from the camera view"
Write-Host ""
Write-Host "Ensure your drone controller and PC are on the same network!"
Write-Host ""
Write-Host "To test without drone: .\scripts\test_stream.ps1"
Write-Host "To stop: Stop-Process -Name mediamtx"
Write-Host ""
