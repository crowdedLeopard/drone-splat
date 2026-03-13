# Test RTMP pipeline without a drone
# Generates synthetic video stream using FFmpeg

$ErrorActionPreference = "Stop"

$RTMP_URL = "rtmp://localhost:1935/live/drone"

Write-Host "=== RTMP Stream Test ===" -ForegroundColor Cyan
Write-Host ""

# Check if FFmpeg is available
try {
    $ffmpegVersion = & ffmpeg -version 2>&1 | Select-Object -First 1
    Write-Host "[+] FFmpeg detected: $ffmpegVersion" -ForegroundColor Green
}
catch {
    Write-Host "[!] FFmpeg not found in PATH" -ForegroundColor Red
    Write-Host "    Install FFmpeg from: https://ffmpeg.org/download.html" -ForegroundColor Yellow
    exit 1
}

# Check if mediamtx is running
$mediamtxProcess = Get-Process -Name "mediamtx" -ErrorAction SilentlyContinue
if (!$mediamtxProcess) {
    Write-Host "[!] mediamtx not running. Start it first with: .\scripts\start_stream.ps1" -ForegroundColor Red
    exit 1
}

Write-Host "[+] mediamtx is running (PID: $($mediamtxProcess.Id))" -ForegroundColor Green
Write-Host ""

# Check if test video exists
$testVideo = "$PSScriptRoot\..\test_video.mp4"
$useTestVideo = Test-Path $testVideo

Write-Host "=== Starting Test Stream ===" -ForegroundColor Cyan
Write-Host "Target: $RTMP_URL" -ForegroundColor Yellow
Write-Host ""

if ($useTestVideo) {
    Write-Host "[*] Using test video: $testVideo" -ForegroundColor Yellow
    Write-Host "[*] Streaming in loop mode..." -ForegroundColor Gray
    Write-Host ""
    Write-Host "Press Ctrl+C to stop" -ForegroundColor Green
    Write-Host ""
    
    # Stream from test video file (loop mode)
    & ffmpeg -re -stream_loop -1 -i $testVideo -c:v libx264 -preset ultrafast -tune zerolatency -c:a aac -f flv $RTMP_URL
}
else {
    Write-Host "[*] No test video found, generating synthetic test pattern" -ForegroundColor Yellow
    Write-Host "[*] Resolution: 1280x720 @ 30fps" -ForegroundColor Gray
    Write-Host ""
    Write-Host "Press Ctrl+C to stop" -ForegroundColor Green
    Write-Host ""
    
    # Generate synthetic test pattern (moving color bars with timestamp)
    & ffmpeg -re -f lavfi -i "testsrc=size=1280x720:rate=30,drawtext=text='%{localtime\:%T}':fontcolor=white:fontsize=48:x=(w-text_w)/2:y=h-100" -c:v libx264 -preset ultrafast -tune zerolatency -f flv $RTMP_URL
}

Write-Host ""
Write-Host "[+] Stream ended" -ForegroundColor Green
