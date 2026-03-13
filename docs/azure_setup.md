# Azure Setup Guide: 3D Gaussian Splatting Demo

## Overview

This guide walks you through deploying the minimal Azure infrastructure for the real-time Gaussian Splatting demo. The system is designed for local inference with optional cloud storage for sharing results.

**TL;DR:** Azure is *optional*. The demo works 100% locally. Cloud storage (~$0.01–0.10/month) is only for sharing .ply files remotely.

---

## Prerequisites

### Required
- **Azure CLI** (`az` command-line tool) — [Install here](https://learn.microsoft.com/en-us/cli/azure/install-azure-cli)
- **Active Azure Subscription** — [Free trial available](https://azure.microsoft.com/en-us/free/)
- **Bash or PowerShell** — Use `setup.sh` (bash/WSL) or `setup.ps1` (PowerShell)

### Optional
- Azure Portal account (for monitoring and cost alerts)

### Verify Installation
```bash
# Check Azure CLI version
az --version

# Login to Azure
az login
# (Browser opens for authentication)
```

---

## Option 1: Quick Setup (Recommended)

### Linux / macOS / WSL

```bash
cd azure/
chmod +x setup.sh
./setup.sh
```

This script will:
1. Create a resource group (`rg-splatting-demo`)
2. Create a storage account with LRS (lowest cost)
3. Enable static website hosting
4. Create a public `splats` container
5. Output the connection string and configuration

### Windows PowerShell

```powershell
cd azure/
.\setup.ps1
```

Same setup, Windows-native style.

---

## Option 2: Manual Setup (Step-by-Step)

If the scripts don't work, follow these steps manually:

### Step 1: Create Resource Group

```bash
LOCATION="eastus"
RESOURCE_GROUP="rg-splatting-demo"

az group create \
  --name $RESOURCE_GROUP \
  --location $LOCATION \
  --tags "project=splatting-demo"
```

Choose a region near you:
- **US:** `eastus`, `westus`, `westus2`, `northcentralus`
- **Europe:** `northeurope`, `westeurope`
- **APAC:** `eastasia`, `australiaeast`

Cost per GB varies slightly by region; `eastus` is typically cheapest.

### Step 2: Create Storage Account

```bash
# Generate a unique name (storage account names must be globally unique)
STORAGE_NAME="splattingdemo$(openssl rand -hex 4)"
# Or on Windows: $STORAGE_NAME = "splattingdemo$(Get-Random)"

az storage account create \
  --name $STORAGE_NAME \
  --resource-group $RESOURCE_GROUP \
  --location $LOCATION \
  --sku Standard_LRS \
  --kind StorageV2 \
  --access-tier Hot \
  --allow-blob-public-access true
```

**Key options explained:**
- `Standard_LRS`: Locally redundant, lowest cost (~$0.0184/GB/month)
- `StorageV2`: Supports blobs, tables, queues (full-featured)
- `Hot`: Files accessed immediately (default access tier)
- `allow-blob-public-access`: Required for viewer access

### Step 3: Enable Static Website Hosting

```bash
az storage blob service-properties update \
  --account-name $STORAGE_NAME \
  --static-website \
  --index-document index.html \
  --404-document index.html
```

This makes `index.html` the default landing page and handles 404s gracefully.

### Step 4: Create Container for Splat Files

```bash
az storage container create \
  --name splats \
  --account-name $STORAGE_NAME \
  --public-access blob
```

`--public-access blob` allows unauthenticated read-only access (required for sharing).

### Step 5: Get Connection String

```bash
CONN_STRING=$(az storage account show-connection-string \
  --name $STORAGE_NAME \
  --resource-group $RESOURCE_GROUP \
  --query connectionString -o tsv)

echo $CONN_STRING
```

Save this output—you'll need it for `.env`.

---

## Configuration

### 1. Upload Static Website (index.html)

```bash
az storage blob upload \
  --name index.html \
  --container-name '$web' \
  --account-name $STORAGE_NAME \
  --file ./azure/index.html
```

The `$web` container is created automatically for static websites.

### 2. Create `.env` File

In your project root, copy `.env.example` to `.env` and fill in:

```bash
cp .env.example .env
```

Edit `.env`:

```env
# From setup output:
AZURE_STORAGE_CONNECTION_STRING=DefaultEndpointsProtocol=https;AccountName=splattingdemo...;AccountKey=...;EndpointSuffix=core.windows.net

AZURE_CONTAINER_NAME=splats

# Enable cloud upload (demo: set to false for local-only)
AZURE_UPLOAD_ENABLED=true

# Local paths
RTMP_URL=rtmp://localhost:1935/live/drone
OUTPUT_DIR=output/splats
```

### 3. Install Azure Python SDK (if using uploader)

```bash
pip install azure-storage-blob
```

---

## Using the Uploader in Your Code

### Python

```python
from src.utils.azure_uploader import AzureUploader

# Create uploader from .env
uploader = AzureUploader.from_env()

# Upload .ply file
if uploader.enabled:
    try:
        url = uploader.upload_splat("output/splats/model.ply")
        print(f"Available at: {url}")
    except Exception as e:
        print(f"Upload failed: {e}, using local file")
else:
    print("Azure upload disabled (local mode)")

# Or: conditional upload
url = uploader.upload_if_enabled("output/splats/model.ply")
if url:
    print(f"Shared URL: {url}")
else:
    print("Local mode: share file manually")
```

### Test Upload

```bash
# Create test file
echo "test" > test.txt

# Upload
az storage blob upload \
  --name test.txt \
  --container-name splats \
  --account-name $STORAGE_NAME \
  --file test.txt

# Get public URL
echo "https://${STORAGE_NAME}.blob.core.windows.net/splats/test.txt"

# Clean up
az storage blob delete \
  --name test.txt \
  --container-name splats \
  --account-name $STORAGE_NAME
```

---

## Cost Monitoring

### Set Spending Alert

1. Go to [Azure Portal](https://portal.azure.com)
2. Navigate to **Cost Management + Billing** → **Budgets**
3. Create Budget:
   - Amount: **$1.00** (safe upper limit for demo)
   - Alert at **100%** (notify when reached)
   - Contact: Your email

### View Actual Usage

```bash
# Storage metrics
az monitor metrics list \
  --resource /subscriptions/$(az account show -q id -o tsv)/resourceGroups/rg-splatting-demo/providers/Microsoft.Storage/storageAccounts/$STORAGE_NAME \
  --metric UsedCapacity \
  --start-time "$(date -u -d '7 days ago' +%Y-%m-%dT%H:%M:%S)Z"

# Or simple: check container size
az storage blob list \
  --container-name splats \
  --account-name $STORAGE_NAME \
  --query "[].{name:name, size:properties.contentLength}" \
  -o table
```

For details, see `azure/cost_estimate.md`.

---

## Accessing Your Data

### Public Blob URL
```
https://{storage-account}.blob.core.windows.net/splats/{filename}.ply
```

### Static Website URL
```
https://{storage-account}.z13.web.core.windows.net/
```

Replace `{storage-account}` with your actual account name (from setup output).

### View in SuperSplat
Paste the `.ply` URL into [PlayCanvas SuperSplat Viewer](https://playcanvas.com/supersplat):
1. Go to https://playcanvas.com/supersplat
2. Click **+ Add URL**
3. Paste your blob URL
4. View interactively in browser

---

## Cleanup

### When Demo Is Done

Delete all resources and stop charges:

```bash
# Option 1: PowerShell
.\azure\cleanup.ps1

# Option 2: Bash
az group delete --name rg-splatting-demo --yes
```

This removes:
- Storage account
- All containers and blobs
- Resource group
- All associated costs (immediate)

**Note:** Charges stop immediately after deletion. Cached data in Azure CDN or viewer caches may persist for hours, but billing ends right away.

---

## Troubleshooting

### "Authentication failed" / "Resource not found"

```bash
# Re-login
az logout
az login

# Verify subscription
az account show
```

### Blob upload fails with 403

```bash
# Check public access is enabled
az storage account update \
  --name $STORAGE_NAME \
  --allow-blob-public-access true

# Check container access level
az storage container show \
  --name splats \
  --account-name $STORAGE_NAME \
  --query publicAccess
# Should output: "blob"
```

### Can't find connection string

```bash
# Re-generate
az storage account show-connection-string \
  --name $STORAGE_NAME \
  --resource-group $RESOURCE_GROUP
```

### Static website not loading

```bash
# Verify index.html is in $web container
az storage blob list --container-name '$web' --account-name $STORAGE_NAME
```

---

## Next Steps

1. **Disable Azure for local-only testing:**
   ```env
   AZURE_UPLOAD_ENABLED=false
   ```

2. **Enable Azure once inference is working:**
   ```env
   AZURE_UPLOAD_ENABLED=true
   ```

3. **Share results:**
   - Copy blob URL from container
   - Paste into SuperSplat viewer
   - Send link to collaborators

4. **Archive old models:**
   ```bash
   # Move to cheaper tier after 30 days
   az storage blob set-tier --name old_model.ply \
     --container-name splats --account-name $STORAGE_NAME --tier Cool
   ```

---

## References

- [Azure Storage Pricing](https://azure.microsoft.com/en-us/pricing/details/storage/blobs/)
- [Azure CLI Storage Commands](https://learn.microsoft.com/en-us/cli/azure/storage/blob)
- [Cost Optimization Guide](../azure/cost_estimate.md)
- [PlayCanvas SuperSplat Viewer](https://playcanvas.com/supersplat)

---

**Questions?** Check `.squad/decisions/inbox/alex-azure-design.md` for architectural decisions.
