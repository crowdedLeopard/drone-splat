# Azure Integration

This directory contains Azure-specific components for the 3D Gaussian Splatting project.

## Components

- **storage_uploader.py**: Uploads .splat/.ply files to Azure Blob Storage

## Setup

1. Create Azure Storage Account (Standard LRS recommended for demo)
2. Create container named `gaussian-splats` (or as configured in config.yaml)
3. Get connection string from Azure Portal:
   - Storage Account → Access keys → Connection string

4. Set environment variable:
   ```bash
   $env:AZURE_STORAGE_CONNECTION_STRING="DefaultEndpointsProtocol=https;AccountName=...;AccountKey=...;EndpointSuffix=core.windows.net"
   ```

   Or add to `config/config.yaml`:
   ```yaml
   azure:
     enabled: true
     storage:
       connection_string: "DefaultEndpointsProtocol=https;..."
   ```

5. Enable in config:
   ```yaml
   azure:
     enabled: true
   ```

## Cost Estimation

For demo/development (minimal cost):
- **Storage Account**: Standard LRS (Locally Redundant Storage)
- **Container**: Standard blob tier
- **Estimated cost**: 
  - Storage: ~$0.02/GB/month
  - Operations: ~$0.0004 per 10,000 operations
  - Egress: Free up to 100GB/month (within region)

Example: 10 GB stored, 1000 uploads/month = ~$0.25/month

## Usage

The uploader is automatically initialized by `src/main.py` if `azure.enabled: true` in config.

Files are uploaded:
- After each reconstruction update (if `upload_on_update: true`)
- With timestamp suffix (if `use_timestamp: true`)
- To path: `<blob_prefix>/<filename>_<timestamp>.<ext>`

## Owner

This module is maintained by **Alex** (Azure/DevOps specialist).
