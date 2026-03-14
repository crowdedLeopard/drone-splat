# Azure Integration

This directory contains Azure-specific components for the 3D Gaussian Splatting project.

## Provisioned Resources

**Resource Group**: `rg-drone-splat-demo`  
**Location**: Australia East  
**Storage Account**: `dronesplat4014`  
**Container**: `gaussian-splats`

### Resource Details
- **SKU**: Standard_LRS (Locally Redundant Storage - cheapest option)
- **Tier**: Hot (for frequent access)
- **Authentication**: Azure AD (subscription policy blocks shared key access)
- **Created**: 2026-03-14

### Important: Subscription Policy Restrictions
This subscription enforces Azure security policies that:
- **Block shared key access** (account key authentication disabled)
- **Block public blob access** (anonymous access disabled)

**Solution**: Use Azure AD authentication (DefaultAzureCredential) instead of connection strings.

## Components

- **storage_uploader.py**: Uploads .splat/.ply files to Azure Blob Storage (supports both connection string and Azure AD auth)

## Setup

### Prerequisites
- Azure CLI installed: https://docs.microsoft.com/en-us/cli/azure/install-azure-cli-windows
- Authenticated: `az login`

### Quick Start (Resources Already Provisioned)

**Option 1: Azure AD Authentication (Recommended for this subscription)**

1. **Ensure you're logged in**:
   ```powershell
   az login
   ```

2. **Set environment variable**:
   ```powershell
   $env:AZURE_STORAGE_ACCOUNT_NAME = "dronesplat4014"
   ```

3. **Add to `.env` file**:
   ```
   AZURE_STORAGE_ACCOUNT_NAME=dronesplat4014
   AZURE_CONTAINER_NAME=gaussian-splats
   AZURE_UPLOAD_ENABLED=true
   ```

4. **Assign RBAC role** (one-time setup):
   ```powershell
   # Get your user object ID
   $userId = az ad signed-in-user show --query id -o tsv
   
   # Assign Storage Blob Data Contributor role
   az role assignment create `
     --role "Storage Blob Data Contributor" `
     --assignee $userId `
     --scope "/subscriptions/5392abeb-13ac-438a-aa5a-bebd2ccc154b/resourceGroups/rg-drone-splat-demo/providers/Microsoft.Storage/storageAccounts/dronesplat4014"
   ```

**Option 2: Connection String (if shared key access enabled)**

This won't work on the current subscription due to policy restrictions, but for reference:

1. **Get Connection String**:
   ```powershell
   az storage account show-connection-string `
     --name dronesplat4014 `
     --resource-group rg-drone-splat-demo `
     --query connectionString -o tsv
   ```

2. **Set in `.env`**:
   ```
   AZURE_STORAGE_CONNECTION_STRING=<your-connection-string>
   AZURE_CONTAINER_NAME=gaussian-splats
   AZURE_UPLOAD_ENABLED=true
   ```

### Verify Setup

```powershell
# Test connection with Azure AD
$env:AZURE_STORAGE_ACCOUNT_NAME = "dronesplat4014"

python -c "
from azure.storage.blob import BlobServiceClient
from azure.identity import DefaultAzureCredential

credential = DefaultAzureCredential()
client = BlobServiceClient(account_url='https://dronesplat4014.blob.core.windows.net', credential=credential)
containers = list(client.list_containers())
print(f'✓ Connected! Found {len(containers)} container(s)')
for c in containers:
    print(f'  - {c.name}')
"
```

## Manual Provisioning (if starting from scratch)

If you need to recreate resources or set up in a different subscription:

```powershell
# Variables
$RESOURCE_GROUP = "rg-drone-splat-demo"
$LOCATION = "australiaeast"
$STORAGE_ACCOUNT = "dronesplat$(Get-Random -Minimum 1000 -Maximum 9999)"
$CONTAINER_NAME = "gaussian-splats"

# Create resource group
az group create --name $RESOURCE_GROUP --location $LOCATION

# Create storage account (Standard_LRS = cheapest)
az storage account create `
  --name $STORAGE_ACCOUNT `
  --resource-group $RESOURCE_GROUP `
  --location $LOCATION `
  --sku Standard_LRS `
  --kind StorageV2 `
  --access-tier Hot

# Create container with Azure AD auth
az storage container create `
  --name $CONTAINER_NAME `
  --account-name $STORAGE_ACCOUNT `
  --auth-mode login

# Assign RBAC permissions
$userId = az ad signed-in-user show --query id -o tsv
az role assignment create `
  --role "Storage Blob Data Contributor" `
  --assignee $userId `
  --scope "/subscriptions/<subscription-id>/resourceGroups/$RESOURCE_GROUP/providers/Microsoft.Storage/storageAccounts/$STORAGE_ACCOUNT"
```

### Manual Setup via Azure Portal
1. Go to Azure Portal: https://portal.azure.com
2. Create Storage Account:
   - Name: globally unique, lowercase, 3-24 chars
   - Location: Australia East (or closest region)
   - Performance: Standard
   - Redundancy: Locally-redundant storage (LRS)
3. Create Container:
   - Name: `gaussian-splats`
   - Public access level: Private (due to subscription policy)
4. Assign RBAC Role:
   - Storage Account → Access Control (IAM)
   - Add role assignment: "Storage Blob Data Contributor"
   - Assign to your user account

## Cost Estimation

**Current Configuration (Standard_LRS in Australia East)**:
- **Storage**: ~$0.018/GB/month (AU pricing)
- **Operations**: 
  - First 10,000 write operations: FREE
  - Additional: ~$0.05 per 10,000 operations
- **Bandwidth**: 
  - First 100GB egress/month: FREE
  - Within Azure: FREE
  - To internet (AU): ~$0.13/GB after first 100GB

**Demo Budget Estimate**:
- 1GB of .splat files stored: ~$0.02/month
- 500 uploads/month: FREE (within first 10k)
- Blob access via Azure AD: FREE (no data egress if accessing from Azure or local machine with login)
- **Total**: ~$0.02-0.05/month ✅ (within $0.10 budget)

**Example Scenarios**:
- 10 GB stored, 1000 uploads/month: ~$0.18/month
- 50 GB stored, 5000 uploads/month: ~$0.90/month

## Usage

The uploader is automatically initialized by `src/main.py` if Azure is enabled.

Files are uploaded:
- After each reconstruction update (if `upload_on_update: true` in config.yaml)
- With timestamp suffix (if `use_timestamp: true`)
- To path: `<blob_prefix>/<filename>_<timestamp>.<ext>`

**Authentication Methods**:
1. Azure AD (DefaultAzureCredential) - set `AZURE_STORAGE_ACCOUNT_NAME`
2. Connection string - set `AZURE_STORAGE_CONNECTION_STRING` (if subscription allows)

**Blob URLs**:
```
https://dronesplat4014.blob.core.windows.net/gaussian-splats/<filename>
```

**Note**: Since public access is blocked, URLs require authentication (SAS token or Azure AD).

## Cleanup

To delete all Azure resources and avoid any charges:

```powershell
# Delete the entire resource group (removes everything)
az group delete --name rg-drone-splat-demo --yes --no-wait
```

**IMPORTANT**: This is irreversible and will delete:
- Storage account `dronesplat4014`
- Container `gaussian-splats`
- All uploaded blobs

## Troubleshooting

### "Key based authentication not permitted"
This subscription enforces a policy blocking shared key access. Use Azure AD authentication:

1. Set `AZURE_STORAGE_ACCOUNT_NAME=dronesplat4014` in `.env`
2. Remove or comment out `AZURE_STORAGE_CONNECTION_STRING`
3. Ensure you have RBAC role assigned (Storage Blob Data Contributor)
4. Run `az login` to authenticate

### "Public access not allowed"
The subscription blocks anonymous blob access. This is expected. Blobs can still be:
- Accessed by authenticated users (Azure AD)
- Shared via SAS tokens (time-limited URLs)

To generate a SAS URL:
```powershell
az storage blob generate-sas `
  --account-name dronesplat4014 `
  --container-name gaussian-splats `
  --name <blob-name> `
  --permissions r `
  --expiry 2026-12-31 `
  --auth-mode login `
  --as-user `
  --full-uri
```

### "Cannot list containers"
Ensure you have the "Storage Blob Data Contributor" role assigned:
```powershell
az role assignment list --scope "/subscriptions/5392abeb-13ac-438a-aa5a-bebd2ccc154b/resourceGroups/rg-drone-splat-demo/providers/Microsoft.Storage/storageAccounts/dronesplat4014"
```

## Dependencies

Add to `requirements.txt`:
```
azure-storage-blob>=12.19.0
azure-identity>=1.15.0
```

Install:
```powershell
pip install azure-storage-blob azure-identity
```

## Owner

This module is maintained by **Alex** (Cloud/DevOps Engineer).  
Last updated: 2026-03-14
