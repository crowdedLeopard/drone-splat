# Setup script for 3D Gaussian Splatting viewer
# Checks dependencies and sets up viewer environment

Write-Host "=" * 60
Write-Host "3D Gaussian Splatting Viewer Setup" -ForegroundColor Cyan
Write-Host "=" * 60
Write-Host ""

$ErrorActionPreference = "Continue"

# Check Python
Write-Host "Checking Python..." -ForegroundColor Yellow
$pythonVersion = python --version 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host "  ✓ $pythonVersion" -ForegroundColor Green
} else {
    Write-Host "  ✗ Python not found" -ForegroundColor Red
    Write-Host "    Install from: https://www.python.org/downloads/" -ForegroundColor Gray
    exit 1
}

# Check required Python packages
Write-Host ""
Write-Host "Checking Python packages..." -ForegroundColor Yellow

$packages = @("watchdog")
foreach ($package in $packages) {
    $installed = python -c "import $package; print('OK')" 2>&1
    if ($installed -eq "OK") {
        Write-Host "  ✓ $package" -ForegroundColor Green
    } else {
        Write-Host "  ✗ $package not installed" -ForegroundColor Red
        Write-Host "    Installing $package..." -ForegroundColor Gray
        pip install $package
        if ($LASTEXITCODE -eq 0) {
            Write-Host "    ✓ Installed $package" -ForegroundColor Green
        } else {
            Write-Host "    ✗ Failed to install $package" -ForegroundColor Red
        }
    }
}

# Check Blender (optional)
Write-Host ""
Write-Host "Checking Blender (optional)..." -ForegroundColor Yellow
$blenderVersion = blender --version 2>&1 | Select-String -Pattern "Blender" | Select-Object -First 1
if ($blenderVersion) {
    Write-Host "  ✓ $blenderVersion" -ForegroundColor Green
} else {
    Write-Host "  ⚠ Blender not found (optional)" -ForegroundColor Yellow
    Write-Host "    Web viewer will work without Blender" -ForegroundColor Gray
    Write-Host "    Install from: https://www.blender.org/download/" -ForegroundColor Gray
}

# Create output directory
Write-Host ""
Write-Host "Creating directories..." -ForegroundColor Yellow
$outputDir = "output"
if (!(Test-Path $outputDir)) {
    New-Item -ItemType Directory -Path $outputDir | Out-Null
    Write-Host "  ✓ Created $outputDir/" -ForegroundColor Green
} else {
    Write-Host "  ✓ $outputDir/ already exists" -ForegroundColor Green
}

# Download test .ply file (optional)
Write-Host ""
Write-Host "Downloading test splat file..." -ForegroundColor Yellow
$testFile = "$outputDir\test.ply"
if (!(Test-Path $testFile)) {
    Write-Host "  Downloading sample splat..." -ForegroundColor Gray
    try {
        # Try to download a small test splat
        # Note: This is a placeholder URL - replace with actual test file
        $url = "https://huggingface.co/datasets/dylanebert/3dgs/resolve/main/bonsai/point_cloud.ply"
        Invoke-WebRequest -Uri $url -OutFile $testFile -ErrorAction SilentlyContinue
        if (Test-Path $testFile) {
            Write-Host "  ✓ Downloaded test.ply ($([math]::Round((Get-Item $testFile).Length / 1MB, 2)) MB)" -ForegroundColor Green
        } else {
            Write-Host "  ⚠ Could not download test file (network issue)" -ForegroundColor Yellow
        }
    } catch {
        Write-Host "  ⚠ Could not download test file" -ForegroundColor Yellow
        Write-Host "    This is optional - viewer will work when reconstruction creates .ply files" -ForegroundColor Gray
    }
} else {
    Write-Host "  ✓ test.ply already exists" -ForegroundColor Green
}

# Copy viewer.html to output directory for easy access
Write-Host ""
Write-Host "Setting up web viewer..." -ForegroundColor Yellow
$viewerSrc = "src\viewer\viewer.html"
$viewerDest = "viewer.html"
if (Test-Path $viewerSrc) {
    Copy-Item $viewerSrc $viewerDest -Force
    Write-Host "  ✓ Copied viewer.html to project root" -ForegroundColor Green
} else {
    Write-Host "  ✗ viewer.html not found at $viewerSrc" -ForegroundColor Red
}

# Summary
Write-Host ""
Write-Host "=" * 60
Write-Host "Setup Complete!" -ForegroundColor Green
Write-Host "=" * 60
Write-Host ""
Write-Host "Quick Start:" -ForegroundColor Cyan
Write-Host "  python scripts\viewer\watch_and_reload.py --mode web" -ForegroundColor White
Write-Host ""
Write-Host "This will:" -ForegroundColor Gray
Write-Host "  1. Start a web server at http://localhost:8080" -ForegroundColor Gray
Write-Host "  2. Open your browser with the viewer" -ForegroundColor Gray
Write-Host "  3. Watch for new .ply files and auto-refresh" -ForegroundColor Gray
Write-Host ""
Write-Host "For more options, see: docs\viewer_setup.md" -ForegroundColor Gray
Write-Host ""
