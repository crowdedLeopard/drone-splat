@echo off
REM Installation script for 3D Gaussian Splatting Reconstruction Module
REM Windows 11, Python 3.9+, NVIDIA GPU with CUDA

echo ================================================
echo 3D Gaussian Splatting Reconstruction Setup
echo ================================================
echo.

REM Check Python version
python --version
IF %ERRORLEVEL% NEQ 0 (
    echo ERROR: Python not found. Please install Python 3.9 or later.
    pause
    exit /b 1
)

echo.
echo [1/6] Checking CUDA availability...
python -c "import torch; print(f'CUDA available: {torch.cuda.is_available()}')" 2>nul
IF %ERRORLEVEL% NEQ 0 (
    echo PyTorch not yet installed, will install with CUDA support...
)

echo.
echo [2/6] Installing PyTorch with CUDA 11.8...
echo This may take several minutes...
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
IF %ERRORLEVEL% NEQ 0 (
    echo WARNING: PyTorch installation had issues. Trying CUDA 12.1...
    pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
)

echo.
echo [3/6] Installing gsplat (3D Gaussian Splatting library)...
echo NOTE: This requires CUDA toolkit installed separately
echo If this fails, install CUDA Toolkit from: https://developer.nvidia.com/cuda-downloads
pip install gsplat
IF %ERRORLEVEL% NEQ 0 (
    echo.
    echo WARNING: gsplat installation failed!
    echo This usually means:
    echo   1. CUDA Toolkit is not installed
    echo   2. Visual C++ Build Tools not installed
    echo.
    echo Install requirements:
    echo   - CUDA Toolkit 11.8 or 12.x: https://developer.nvidia.com/cuda-downloads
    echo   - Visual Studio Build Tools: https://visualstudio.microsoft.com/downloads/
    echo.
    echo You can try installing gsplat manually later.
)

echo.
echo [4/6] Installing OpenCV and computer vision dependencies...
pip install opencv-python opencv-contrib-python

echo.
echo [5/6] Installing scientific computing libraries...
pip install numpy scipy pyyaml

echo.
echo [6/6] Verifying installation...
python -c "import torch; import cv2; import numpy; print('Core dependencies: OK')"
python -c "import gsplat; print('gsplat: OK')" 2>nul || echo "gsplat: NOT INSTALLED (see warnings above)"

echo.
echo ================================================
echo Installation Summary
echo ================================================
python -c "import torch; print(f'PyTorch version: {torch.__version__}')"
python -c "import torch; print(f'CUDA available: {torch.cuda.is_available()}')"
python -c "import torch; print(f'CUDA version: {torch.version.cuda if torch.cuda.is_available() else \"N/A\"}')"
python -c "import torch; print(f'GPU: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else \"N/A\"}')"
python -c "import cv2; print(f'OpenCV version: {cv2.__version__}')"

echo.
echo ================================================
echo VRAM Requirements
echo ================================================
echo Minimum: 4GB GPU memory for demo quality
echo Recommended: 8GB+ GPU memory
echo Current GPU memory:
python -c "import torch; print(f'{torch.cuda.get_device_properties(0).total_memory / 1e9:.1f} GB' if torch.cuda.is_available() else 'N/A')"

echo.
echo ================================================
echo Next Steps
echo ================================================
echo 1. Verify CUDA toolkit is installed (nvcc --version)
echo 2. If gsplat failed, install CUDA Toolkit and Visual C++ Build Tools
echo 3. Run: python -m src.reconstruction.reconstructor
echo 4. Check example config: config/reconstruction_config.yaml
echo.

pause
