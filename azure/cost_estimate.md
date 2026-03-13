# Azure Cost Estimate: 3D Gaussian Splatting Demo

## Executive Summary
**Monthly Cost for Demo Usage: ~$0.02–0.10**

This is the minimal cost approach using only Azure Blob Storage with static website hosting. No compute, no GPU, no databases—just file storage.

---

## Service Breakdown

### Azure Blob Storage (Standard, LRS, Hot tier)

| Component | Cost | Notes |
|-----------|------|-------|
| Storage (per GB/month) | $0.0184 | Standard LRS, Hot tier access |
| Write operations (per 10k) | $0.0005 | Low frequency for demo |
| Read operations (per 10k) | $0.0001 | Viewers accessing .ply files |
| Data transfer (egress, per GB) | $0.0087 | After first 1GB free |

### Typical Demo Usage

**Scenario 1: Light Demo (Single Session)**
- Files stored: 5 × 50MB .ply files = ~250MB
- Storage cost: 250MB × $0.0184/GB = ~$0.005/month
- Write operations: 5 uploads = 0.0005 operations cost
- Read operations: 50 reads @ 1MB each = ~0.0001 cost
- **Monthly total: ~$0.01**

**Scenario 2: Active Demo (Multiple Sessions)**
- Files stored: 20 × 30MB files = ~600MB
- 100 viewer requests/month
- Storage: 600MB × $0.0184/GB = ~$0.011/month
- Operations: 20 writes + 1000 reads = ~$0.002/month
- Data egress: 600MB = 0.6GB × $0.0087 = ~$0.005/month
- **Monthly total: ~$0.02–0.03**

**Scenario 3: Archive of Sessions**
- Files stored: 200 × 20MB files = ~4GB
- Storage: 4GB × $0.0184 = ~$0.074/month
- **Monthly total: ~$0.08–0.10**

---

## Cost Optimization Tips

### 1. **Use Cool Tier for Archive**
Move old files to Cool tier ($0.01/GB/month) after 30 days:
```bash
az storage blob set-tier --name myfile.ply --container-name splats \
  --account-name mystorageacct --tier Cool
```

### 2. **Lifecycle Policy to Auto-Delete**
Delete files older than 90 days:
```bash
cat > lifecycle.json <<EOF
{
  "rules": [
    {
      "enabled": true,
      "name": "DeleteOldSplats",
      "type": "Lifecycle",
      "definition": {
        "actions": {
          "baseBlob": {
            "delete": {
              "daysAfterModificationGreaterThan": 90
            }
          }
        },
        "filters": {
          "blobTypes": ["blockBlob"]
        }
      }
    }
  ]
}
EOF

az storage account management-policy create \
  --account-name mystorageacct \
  --resource-group rg-splatting-demo \
  --policy @lifecycle.json
```

### 3. **Enable Alerts**
Set spending alert at $0.50/month (safe upper limit for demo):
```bash
# Via Azure Portal:
# Cost Management + Billing → Budgets → Create Budget → Set Alert at $0.50
```

### 4. **Monitor Usage**
Check actual consumption:
```bash
# Last 30 days
az consumption usage list --interval iso8601 --metric "ActualCost" \
  --time-period "$(date -u +'%Y-%m-%dT00:00:00Z' -d '30 days ago')-$(date -u +'%Y-%m-%dT23:59:59Z')" \
  --query "value[*].{Resource:id, Cost:meterDetails.meterName, Actual:properties.usageEnd}" \
  -o table

# Real-time metrics (Storage Account)
az monitor metrics list --resource /subscriptions/{sub-id}/resourceGroups/rg-splatting-demo/providers/Microsoft.Storage/storageAccounts/splattingdemo{id} \
  --metric "UsedCapacity,Ingress,Egress"
```

---

## Free Tier Consideration

Azure Free Account includes **5 GB of blob storage for 12 months**, but static website hosting requires a Standard storage account (which has associated costs). The minimal cost approach ($0.01–0.03/month) is preferred over managing free tier lifecycle.

---

## Cleanup to $0.00/month

Delete the entire resource group when demo is complete:
```bash
az group delete --name rg-splatting-demo --yes
```

This removes all storage accounts, containers, and charges stop immediately.

---

## Monthly Spending Forecast

| Usage Level | Storage | Operations | Egress | Total/Month |
|-------------|---------|------------|--------|------------|
| 100MB (1 session) | $0.002 | $0.000 | $0.000 | ~$0.01 |
| 500MB (3 sessions) | $0.009 | $0.001 | $0.004 | ~$0.02 |
| 1GB (5 sessions) | $0.018 | $0.002 | $0.009 | ~$0.03 |
| 4GB (archive) | $0.074 | $0.005 | $0.035 | ~$0.11 |

---

## Related Commands

**View current storage metrics:**
```bash
az storage account show --name <storage-acct> \
  --resource-group rg-splatting-demo \
  --query "[id, type, properties.primaryLocation, sku.name, accessTier]"
```

**Estimate before uploading:**
- 1 hour of 1080p video @ 25fps = ~2GB raw
- After reconstruction to 3D splat: typically 10-50MB per .ply file
- 10 splat models = 100-500MB total storage

---

## References

- [Azure Blob Storage Pricing](https://azure.microsoft.com/en-us/pricing/details/storage/blobs/)
- [Cost Optimization Best Practices](https://learn.microsoft.com/en-us/azure/storage/common/storage-best-practices-disaster-recovery)
- [Lifecycle Management Policies](https://learn.microsoft.com/en-us/azure/storage/blobs/lifecycle-management-overview)
