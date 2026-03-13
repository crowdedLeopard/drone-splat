"""
Azure Blob Storage uploader for 3D Gaussian Splatting demo output files.
Enables optional cloud storage of .splat/.ply files with public sharing.
"""

import os
from typing import Optional
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class AzureUploader:
    """
    Manages uploads to Azure Blob Storage.
    
    Configuration:
    - azure_connection_string: Azure Storage connection string
    - container_name: Blob container name (default: "splats")
    - enabled: Enable/disable uploads (default: False for local-only mode)
    """

    def __init__(self, config: dict = None):
        """
        Initialize Azure uploader with configuration.
        
        Args:
            config: Configuration dict with keys:
                - connection_string: Azure Storage connection string
                - container_name: Container name for uploads
                - enabled: Boolean to enable/disable uploads (default False)
        """
        if config is None:
            config = {}

        self.enabled = config.get("enabled", False)
        self.connection_string = config.get("connection_string", "")
        self.container_name = config.get("container_name", "splats")
        self.client = None

        if self.enabled and self.connection_string:
            try:
                from azure.storage.blob import BlobServiceClient
                self.client = BlobServiceClient.from_connection_string(
                    self.connection_string
                )
                logger.info(f"✓ Azure uploader initialized (container: {self.container_name})")
            except ImportError:
                logger.warning(
                    "⚠ Azure SDK not installed. Run: pip install azure-storage-blob"
                )
                self.enabled = False
            except Exception as e:
                logger.error(f"✗ Failed to initialize Azure client: {e}")
                self.enabled = False
        elif self.enabled:
            logger.warning(
                "⚠ Azure uploader enabled but connection_string not provided. "
                "Set AZURE_STORAGE_CONNECTION_STRING environment variable."
            )
            self.enabled = False

    @classmethod
    def from_env(cls) -> "AzureUploader":
        """
        Create uploader from environment variables.
        
        Environment variables:
        - AZURE_STORAGE_CONNECTION_STRING: Storage connection string
        - AZURE_CONTAINER_NAME: Container name (default: splats)
        - AZURE_UPLOAD_ENABLED: Enable uploads (default: false)
        
        Returns:
            AzureUploader instance (always succeeds, may have enabled=False)
        """
        return cls(
            {
                "connection_string": os.getenv("AZURE_STORAGE_CONNECTION_STRING", ""),
                "container_name": os.getenv("AZURE_CONTAINER_NAME", "splats"),
                "enabled": os.getenv("AZURE_UPLOAD_ENABLED", "false").lower() == "true",
            }
        )

    def upload_splat(self, local_path: str) -> str:
        """
        Upload .ply/.splat file to Azure Blob Storage.
        
        Args:
            local_path: Path to local .ply or .splat file
            
        Returns:
            Public URL to uploaded file on Azure
            
        Raises:
            ValueError: If uploader not enabled or file doesn't exist
            Exception: If upload fails
        """
        if not self.enabled:
            raise ValueError(
                "Azure uploader not enabled. Set AZURE_UPLOAD_ENABLED=true in .env"
            )

        if not os.path.exists(local_path):
            raise FileNotFoundError(f"Local file not found: {local_path}")

        try:
            path = Path(local_path)
            blob_name = path.name  # Use original filename

            container_client = self.client.get_container_client(self.container_name)

            logger.info(f"Uploading {path.name} to Azure...")
            with open(local_path, "rb") as data:
                container_client.upload_blob(blob_name, data, overwrite=True)

            # Construct public URL
            account_url = self.client.account_name
            public_url = (
                f"https://{account_url}.blob.core.windows.net"
                f"/{self.container_name}/{blob_name}"
            )

            logger.info(f"✓ Upload successful: {public_url}")
            return public_url

        except Exception as e:
            logger.error(f"✗ Upload failed: {e}")
            raise

    def upload_if_enabled(self, local_path: str) -> Optional[str]:
        """
        Upload file only if Azure is enabled.
        
        Args:
            local_path: Path to local file
            
        Returns:
            Public URL if uploaded, None if Azure disabled
        """
        if not self.enabled:
            logger.debug(f"Azure upload disabled. Keeping local: {local_path}")
            return None

        try:
            return self.upload_splat(local_path)
        except Exception as e:
            logger.error(f"Cloud upload failed, using local file: {e}")
            return None

    def list_splats(self) -> list:
        """
        List all .ply/.splat files in the container.
        
        Returns:
            List of blob names
        """
        if not self.enabled:
            return []

        try:
            container_client = self.client.get_container_client(self.container_name)
            return [blob.name for blob in container_client.list_blobs()]
        except Exception as e:
            logger.error(f"Failed to list blobs: {e}")
            return []

    def get_latest_splat_url(self) -> Optional[str]:
        """
        Get the URL of the most recently uploaded splat file.
        
        Returns:
            Public URL to latest file, or None if no files exist
        """
        if not self.enabled:
            return None

        try:
            container_client = self.client.get_container_client(self.container_name)
            blobs = list(container_client.list_blobs())

            if not blobs:
                return None

            # Get most recently modified blob
            latest = max(blobs, key=lambda b: b.last_modified)
            account_url = self.client.account_name

            return (
                f"https://{account_url}.blob.core.windows.net"
                f"/{self.container_name}/{latest.name}"
            )

        except Exception as e:
            logger.error(f"Failed to get latest splat: {e}")
            return None
