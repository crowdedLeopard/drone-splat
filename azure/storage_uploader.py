"""
Azure Blob Storage Uploader

Uploads reconstruction output to Azure Blob Storage for sharing and archival.

Owner: Alex
"""

from pathlib import Path
from datetime import datetime
from loguru import logger

try:
    from azure.storage.blob import BlobServiceClient
    AZURE_AVAILABLE = True
except ImportError:
    AZURE_AVAILABLE = False
    logger.warning("azure-storage-blob not installed. Azure upload will not work.")


class AzureUploader:
    """Uploads .splat/.ply files to Azure Blob Storage"""
    
    def __init__(self, config: dict):
        if not AZURE_AVAILABLE:
            raise ImportError("azure-storage-blob package is required for Azure upload")
        
        self.config = config
        self.storage_config = config['storage']
        self.container_name = self.storage_config['container_name']
        self.blob_prefix = self.storage_config.get('blob_prefix', 'demo')
        self.use_timestamp = self.storage_config.get('use_timestamp', True)
        
        # Get connection string from config or environment
        connection_string = self.storage_config.get('connection_string')
        if not connection_string:
            import os
            connection_string = os.getenv('AZURE_STORAGE_CONNECTION_STRING')
        
        if not connection_string:
            raise ValueError("Azure Storage connection string not found in config or AZURE_STORAGE_CONNECTION_STRING env var")
        
        # Initialize blob service client
        self.blob_service_client = BlobServiceClient.from_connection_string(connection_string)
        self.container_client = self.blob_service_client.get_container_client(self.container_name)
        
        # Ensure container exists
        self._ensure_container()
        
        logger.info(f"Azure Uploader initialized: container={self.container_name}")
    
    def _ensure_container(self):
        """Ensure blob container exists"""
        try:
            self.container_client.get_container_properties()
            logger.info(f"Using existing container: {self.container_name}")
        except Exception:
            try:
                self.container_client.create_container()
                logger.info(f"Created new container: {self.container_name}")
            except Exception as e:
                logger.error(f"Failed to create container: {e}")
                raise
    
    def upload(self, file_path: Path) -> str:
        """
        Upload file to Azure Blob Storage
        
        Args:
            file_path: Path to file to upload
            
        Returns:
            Blob URL
        """
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        # Generate blob name
        blob_name = self._generate_blob_name(file_path)
        
        logger.info(f"Uploading {file_path} to Azure as {blob_name}...")
        
        try:
            # Upload file
            blob_client = self.container_client.get_blob_client(blob_name)
            
            with open(file_path, 'rb') as data:
                blob_client.upload_blob(data, overwrite=True)
            
            blob_url = blob_client.url
            logger.info(f"Upload complete: {blob_url}")
            
            return blob_url
            
        except Exception as e:
            logger.error(f"Upload failed: {e}")
            raise
    
    def _generate_blob_name(self, file_path: Path) -> str:
        """Generate blob name with optional timestamp"""
        filename = file_path.name
        
        if self.use_timestamp:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            name_parts = filename.rsplit('.', 1)
            if len(name_parts) == 2:
                filename = f"{name_parts[0]}_{timestamp}.{name_parts[1]}"
            else:
                filename = f"{filename}_{timestamp}"
        
        if self.blob_prefix:
            return f"{self.blob_prefix}/{filename}"
        else:
            return filename
    
    def list_blobs(self, prefix: str = None) -> list:
        """List blobs in container"""
        if prefix is None:
            prefix = self.blob_prefix
        
        blobs = self.container_client.list_blobs(name_starts_with=prefix)
        return [blob.name for blob in blobs]
