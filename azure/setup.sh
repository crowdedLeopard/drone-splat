#!/bin/bash
# Azure setup for 3D Gaussian Splatting demo
# Minimal, cost-conscious infrastructure using only Blob Storage
# Usage: ./setup.sh

set -e

echo "🚀 Starting Azure setup for Splatting demo..."

# Configuration
RESOURCE_GROUP="rg-splatting-demo"
LOCATION="eastus"
STORAGE_ACCOUNT_BASE="splattingdemo"

# Generate unique storage account name (lowercase, alphanumeric only)
UNIQUE_ID=$(az account show --query id -o tsv | head -c 8 | tr -d '-')
STORAGE_ACCOUNT="${STORAGE_ACCOUNT_BASE}${UNIQUE_ID}"

echo "📍 Resource Group: $RESOURCE_GROUP"
echo "📍 Location: $LOCATION"
echo "📍 Storage Account: $STORAGE_ACCOUNT"

# Create resource group
echo "📦 Creating resource group..."
az group create \
  --name "$RESOURCE_GROUP" \
  --location "$LOCATION" \
  --tags "project=splatting-demo" "cost-center=demo"

# Create storage account (LRS = lowest cost, Standard, Hot tier for immediate access)
echo "💾 Creating storage account..."
az storage account create \
  --name "$STORAGE_ACCOUNT" \
  --resource-group "$RESOURCE_GROUP" \
  --location "$LOCATION" \
  --sku Standard_LRS \
  --kind StorageV2 \
  --access-tier Hot \
  --allow-blob-public-access true \
  --tags "project=splatting-demo" "cost-center=demo"

# Enable static website hosting (required for index.html serving)
echo "🌐 Enabling static website hosting..."
az storage blob service-properties update \
  --account-name "$STORAGE_ACCOUNT" \
  --static-website \
  --index-document index.html \
  --404-document index.html

# Create container for splat files (public read access for sharing)
echo "🗂️  Creating splats container..."
az storage container create \
  --name splats \
  --account-name "$STORAGE_ACCOUNT" \
  --public-access blob

# Get storage account connection string and key
CONN_STRING=$(az storage account show-connection-string \
  --name "$STORAGE_ACCOUNT" \
  --resource-group "$RESOURCE_GROUP" \
  --query connectionString -o tsv)

STORAGE_KEY=$(az storage account keys list \
  --account-name "$STORAGE_ACCOUNT" \
  --resource-group "$RESOURCE_GROUP" \
  --query "[0].value" -o tsv)

STORAGE_URL=$(az storage account show \
  --name "$STORAGE_ACCOUNT" \
  --resource-group "$RESOURCE_GROUP" \
  --query primaryEndpoints.blob -o tsv)

# Output configuration
echo ""
echo "✅ Setup complete! Configuration:"
echo "======================================"
echo "Storage Account: $STORAGE_ACCOUNT"
echo "Resource Group: $RESOURCE_GROUP"
echo "Blob URL: ${STORAGE_URL}splats/"
echo ""
echo "📝 Add this to your .env file:"
echo "AZURE_STORAGE_CONNECTION_STRING=$CONN_STRING"
echo "AZURE_CONTAINER_NAME=splats"
echo "AZURE_UPLOAD_ENABLED=true"
echo ""
echo "💰 Monthly cost estimate: ~\$0.02-0.10 (demo usage)"
echo "======================================"
