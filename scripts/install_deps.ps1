# Install all required dependencies for the 3D Gaussian Splatting demo
Write-Host "Installing Python dependencies..." -ForegroundColor Cyan
pip install loguru opencv-python watchdog colorama tqdm requests plyfile
pip install "azure-storage-blob>=12.19.0" --upgrade

Write-Host "Checking core imports..." -ForegroundColor Cyan
python -c "from loguru import logger; import cv2; print('[OK] Core deps installed')"
python -c "from azure.storage.blob import BlobServiceClient; print('[OK] Azure SDK v12 installed')"

Write-Host "Done! Run: python demo.py" -ForegroundColor Green
