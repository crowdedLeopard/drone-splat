# Azure setup for 3D Gaussian Splatting demo (PowerShell)
# Minimal, cost-conscious infrastructure using only Blob Storage
# Usage: .\setup.ps1

param(
    [string]$Location = "eastus",
    [string]$ResourceGroup = "rg-splatting-demo"
)

$ErrorActionPreference = "Stop"
Write-Host "🚀 Starting Azure setup for Splatting demo..."

# Configuration
$storageAccountBase = "splattingdemo"

# Generate unique storage account name
$subscriptionId = (az account show --query id -o tsv) -replace "-", ""
$uniqueId = $subscriptionId.Substring(0, 8)
$storageAccount = "$storageAccountBase$uniqueId"

Write-Host "📍 Resource Group: $ResourceGroup"
Write-Host "📍 Location: $Location"
Write-Host "📍 Storage Account: $storageAccount"

# Create resource group
Write-Host "📦 Creating resource group..."
az group create `
    --name $ResourceGroup `
    --location $Location `
    --tags "project=splatting-demo" "cost-center=demo"

# Create storage account (LRS = lowest cost)
Write-Host "💾 Creating storage account..."
az storage account create `
    --name $storageAccount `
    --resource-group $ResourceGroup `
    --location $Location `
    --sku Standard_LRS `
    --kind StorageV2 `
    --access-tier Hot `
    --allow-blob-public-access true `
    --tags "project=splatting-demo" "cost-center=demo"

# Enable static website hosting
Write-Host "🌐 Enabling static website hosting..."
az storage blob service-properties update `
    --account-name $storageAccount `
    --static-website `
    --index-document index.html `
    --404-document index.html

# Create splats container (public read access)
Write-Host "🗂️ Creating splats container..."
az storage container create `
    --name splats `
    --account-name $storageAccount `
    --public-access blob

# Get connection details
Write-Host "📋 Retrieving connection details..."
$connString = az storage account show-connection-string `
    --name $storageAccount `
    --resource-group $ResourceGroup `
    --query connectionString -o tsv

$storageUrl = az storage account show `
    --name $storageAccount `
    --resource-group $ResourceGroup `
    --query "primaryEndpoints.blob" -o tsv

# Display configuration
Write-Host ""
Write-Host "✅ Setup complete! Configuration:" -ForegroundColor Green
Write-Host "======================================"
Write-Host "Storage Account: $storageAccount"
Write-Host "Resource Group: $ResourceGroup"
Write-Host "Blob URL: $($storageUrl)splats/"
Write-Host ""
Write-Host "📝 Add this to your .env file:"
Write-Host "AZURE_STORAGE_CONNECTION_STRING=$connString"
Write-Host "AZURE_CONTAINER_NAME=splats"
Write-Host "AZURE_UPLOAD_ENABLED=true"
Write-Host ""
Write-Host "💰 Monthly cost estimate: ~$0.02-0.10 (demo usage)"
Write-Host "======================================"
