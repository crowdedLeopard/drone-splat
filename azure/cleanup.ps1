# Azure cleanup for Splatting demo (PowerShell)
# Removes all Azure resources created by setup.ps1
# Usage: .\cleanup.ps1

param(
    [string]$ResourceGroup = "rg-splatting-demo",
    [switch]$Force
)

$ErrorActionPreference = "Stop"
Write-Host "⚠️  Azure Cleanup - All resources in '$ResourceGroup' will be deleted"

if (-not $Force) {
    $confirm = Read-Host "Type 'yes' to confirm deletion"
    if ($confirm -ne "yes") {
        Write-Host "❌ Cleanup cancelled"
        exit 0
    }
}

Write-Host "🗑️  Deleting resource group: $ResourceGroup..."
try {
    az group delete `
        --name $ResourceGroup `
        --yes `
        --no-wait
    Write-Host "✅ Deletion started. Monitor progress in Azure Portal or run:"
    Write-Host "   az group show --name $ResourceGroup --query '{Name:name, State:properties.provisioningState}'"
} catch {
    Write-Host "❌ Error during cleanup: $_" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "💡 Tip: To monitor deletion progress:"
Write-Host "   az group wait --created --name $ResourceGroup"
Write-Host ""
Write-Host "After deletion, remove from .env file:"
Write-Host "   - AZURE_STORAGE_CONNECTION_STRING"
Write-Host "   - AZURE_CONTAINER_NAME"
Write-Host "   - AZURE_UPLOAD_ENABLED"
