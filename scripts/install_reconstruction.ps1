# Installation script for 3D Gaussian Splatting Reconstruction Module
# PowerShell version - Windows 11, Python 3.9+, NVIDIA GPU with CUDA

Write-Host "================================================" -ForegroundColor Cyan
Write-Host "3D Gaussian Splatting Reconstruction Setup" -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""

# Check Python
Write-Host "[1/6] Checking Python..." -ForegroundColor Yellow
try {
    $pythonVersion = python --version 2>&1
    Write-Host $pythonVersion -ForegroundColor Green
} catch {
    Write-Host "ERROR: Python not found. Please install Python 3.9 or later." -ForegroundColor Red
    exit 1
}

# Check current CUDA availability
Write-Host ""
Write-Host "[2/6] Checking CUDA availability..." -ForegroundColor Yellow
try {
    python -c "import torch; print(f'CUDA available: {torch.cuda.is_available()}')" 2>$null
} catch {
    Write-Host "PyTorch not yet installed, will install with CUDA support..." -ForegroundColor Yellow
}

# Install PyTorch with CUDA
Write-Host ""
Write-Host "[3/6] Installing PyTorch with CUDA 11.8..." -ForegroundColor Yellow
Write-Host "This may take several minutes..." -ForegroundColor Gray
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118

if ($LASTEXITCODE -ne 0) {
    Write-Host "WARNING: PyTorch installation had issues. Trying CUDA 12.1..." -ForegroundColor Yellow
    pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
}

# Install gsplat
Write-Host ""
Write-Host "[4/6] Installing gsplat (3D Gaussian Splatting library)..." -ForegroundColor Yellow
Write-Host "NOTE: This requires CUDA toolkit installed separately" -ForegroundColor Gray
pip install gsplat

if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "WARNING: gsplat installation failed!" -ForegroundColor Red
    Write-Host "This usually means:" -ForegroundColor Yellow
    Write-Host "  1. CUDA Toolkit is not installed" -ForegroundColor Yellow
    Write-Host "  2. Visual C++ Build Tools not installed" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Install requirements:" -ForegroundColor Cyan
    Write-Host "  - CUDA Toolkit 11.8 or 12.x: https://developer.nvidia.com/cuda-downloads" -ForegroundColor Cyan
    Write-Host "  - Visual Studio Build Tools: https://visualstudio.microsoft.com/downloads/" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "You can try installing gsplat manually later." -ForegroundColor Yellow
}

# Install OpenCV
Write-Host ""
Write-Host "[5/6] Installing OpenCV and computer vision dependencies..." -ForegroundColor Yellow
pip install opencv-python opencv-contrib-python

# Install other dependencies
Write-Host ""
Write-Host "[6/6] Installing scientific computing libraries..." -ForegroundColor Yellow
pip install numpy scipy pyyaml

# Verify installation
Write-Host ""
Write-Host "Verifying installation..." -ForegroundColor Yellow
python -c "import torch; import cv2; import numpy; print('Core dependencies: OK')"

$gsplatOK = $false
try {
    python -c "import gsplat; print('gsplat: OK')" 2>$null
    $gsplatOK = $true
} catch {
    Write-Host "gsplat: NOT INSTALLED (see warnings above)" -ForegroundColor Red
}

# Summary
Write-Host ""
Write-Host "================================================" -ForegroundColor Cyan
Write-Host "Installation Summary" -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan

python -c "import torch; print(f'PyTorch version: {torch.__version__}')"
python -c "import torch; print(f'CUDA available: {torch.cuda.is_available()}')"
python -c "import torch; print(f'CUDA version: {torch.version.cuda if torch.cuda.is_available() else \"N/A\"}')"
python -c "import torch; print(f'GPU: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else \"N/A\"}')"
python -c "import cv2; print(f'OpenCV version: {cv2.__version__}')"

Write-Host ""
Write-Host "================================================" -ForegroundColor Cyan
Write-Host "VRAM Requirements" -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan
Write-Host "Minimum: 4GB GPU memory for demo quality" -ForegroundColor Yellow
Write-Host "Recommended: 8GB+ GPU memory" -ForegroundColor Green
Write-Host "Current GPU memory:" -ForegroundColor Cyan
python -c "import torch; print(f'{torch.cuda.get_device_properties(0).total_memory / 1e9:.1f} GB' if torch.cuda.is_available() else 'N/A')"

Write-Host ""
Write-Host "================================================" -ForegroundColor Cyan
Write-Host "Next Steps" -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan
Write-Host "1. Verify CUDA toolkit is installed (nvcc --version)" -ForegroundColor White
Write-Host "2. If gsplat failed, install CUDA Toolkit and Visual C++ Build Tools" -ForegroundColor White
Write-Host "3. Run: python -m src.reconstruction.reconstructor" -ForegroundColor White
Write-Host "4. Check example config: config/reconstruction_config.yaml" -ForegroundColor White
Write-Host ""
