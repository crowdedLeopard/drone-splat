# Setup script for mediamtx RTMP server on Windows
# Downloads mediamtx binary and configures firewall

$ErrorActionPreference = "Stop"

$MEDIAMTX_VERSION = "v1.9.3"
$MEDIAMTX_URL = "https://github.com/bluenviron/mediamtx/releases/download/$MEDIAMTX_VERSION/mediamtx_$MEDIAMTX_VERSION`_windows_amd64.zip"
$TOOLS_DIR = "$PSScriptRoot\..\tools\mediamtx"
$ZIP_FILE = "$TOOLS_DIR\mediamtx.zip"

Write-Host "=== mediamtx Setup ===" -ForegroundColor Cyan
Write-Host "Version: $MEDIAMTX_VERSION"
Write-Host ""

# Create tools directory
if (!(Test-Path $TOOLS_DIR)) {
    New-Item -ItemType Directory -Path $TOOLS_DIR -Force | Out-Null
    Write-Host "[+] Created $TOOLS_DIR" -ForegroundColor Green
}

# Download mediamtx if not present
$MEDIAMTX_EXE = "$TOOLS_DIR\mediamtx.exe"
if (!(Test-Path $MEDIAMTX_EXE)) {
    Write-Host "[*] Downloading mediamtx $MEDIAMTX_VERSION..." -ForegroundColor Yellow
    
    try {
        Invoke-WebRequest -Uri $MEDIAMTX_URL -OutFile $ZIP_FILE -UseBasicParsing
        Write-Host "[+] Downloaded to $ZIP_FILE" -ForegroundColor Green
        
        Write-Host "[*] Extracting..." -ForegroundColor Yellow
        Expand-Archive -Path $ZIP_FILE -DestinationPath $TOOLS_DIR -Force
        Remove-Item $ZIP_FILE
        Write-Host "[+] Extracted mediamtx.exe" -ForegroundColor Green
    }
    catch {
        Write-Host "[!] Download failed: $_" -ForegroundColor Red
        exit 1
    }
}
else {
    Write-Host "[+] mediamtx.exe already exists" -ForegroundColor Green
}

# Copy config if not present
$CONFIG_SOURCE = "$PSScriptRoot\..\config\mediamtx.yml"
$CONFIG_DEST = "$TOOLS_DIR\mediamtx.yml"

if (!(Test-Path $CONFIG_DEST)) {
    Copy-Item $CONFIG_SOURCE $CONFIG_DEST
    Write-Host "[+] Copied config to $CONFIG_DEST" -ForegroundColor Green
}
else {
    Write-Host "[+] Config already exists at $CONFIG_DEST" -ForegroundColor Green
}

# Configure Windows Firewall
Write-Host ""
Write-Host "=== Firewall Configuration ===" -ForegroundColor Cyan

$firewallRuleName = "mediamtx RTMP (Port 1935)"
$existingRule = Get-NetFirewallRule -DisplayName $firewallRuleName -ErrorAction SilentlyContinue

if ($existingRule) {
    Write-Host "[+] Firewall rule already exists: $firewallRuleName" -ForegroundColor Green
}
else {
    Write-Host "[*] Creating firewall rule for port 1935..." -ForegroundColor Yellow
    Write-Host "    (This requires Administrator privileges)" -ForegroundColor Gray
    
    try {
        New-NetFirewallRule `
            -DisplayName $firewallRuleName `
            -Direction Inbound `
            -Protocol TCP `
            -LocalPort 1935 `
            -Action Allow `
            -Profile Any `
            -ErrorAction Stop | Out-Null
        
        Write-Host "[+] Firewall rule created successfully" -ForegroundColor Green
    }
    catch {
        Write-Host "[!] Failed to create firewall rule: $_" -ForegroundColor Red
        Write-Host "    Please run this script as Administrator, or manually open port 1935" -ForegroundColor Yellow
    }
}

# Get local IP addresses
Write-Host ""
Write-Host "=== Network Information ===" -ForegroundColor Cyan
Write-Host "Your local IP addresses (use one of these in DJI Fly app):"
Write-Host ""

$adapters = Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.InterfaceAlias -notlike "*Loopback*" }
foreach ($adapter in $adapters) {
    $ip = $adapter.IPAddress
    Write-Host "  - $($adapter.InterfaceAlias): $ip" -ForegroundColor Yellow
    Write-Host "    RTMP URL: rtmp://$ip`:1935/live/drone" -ForegroundColor Gray
}

Write-Host ""
Write-Host "=== Setup Complete ===" -ForegroundColor Green
Write-Host "Next steps:"
Write-Host "  1. Run .\scripts\start_stream.ps1 to start the RTMP server"
Write-Host "  2. Configure DJI Fly app with the RTMP URL above"
Write-Host "  3. Or run .\scripts\test_stream.ps1 to test without a drone"
Write-Host ""
