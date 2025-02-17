import os
import logging
from abc import ABC, abstractmethod
from typing import Optional
from services.gcp_toolkit import upload_to_gcs
from services.s3_toolkit import upload_to_s3
from config import validate_env_vars

logger = logging.getLogger(__name__)

class CloudStorageProvider(ABC):
    @abstractmethod
    def upload_file(self, file_path: str) -> str:
        pass

class GCPStorageProvider(CloudStorageProvider):
    def __init__(self):
        self.bucket_name = os.getenv('GCP_BUCKET_NAME')

    def upload_file(self, file_path: str) -> str:
        return upload_to_gcs(file_path, self.bucket_name)

class MinioStorageProvider(CloudStorageProvider):
    def __init__(self):
        self.endpoint = os.getenv('MINIO_ENDPOINT', 'http://localhost:9000')
        self.access_key = os.getenv('MINIO_ACCESS_KEY')
        self.secret_key = os.getenv('MINIO_SECRET_KEY')
        self.bucket_name = os.getenv('MINIO_BUCKET_NAME', 'default')
        self.secure = os.environ.get('MINIO_SECURE', 'true').lower() == 'true'
        self.region = os.environ.get('MINIO_REGION', '')

    def upload_file(self, file_path: str) -> str:
        protocol = 'https' if self.secure else 'http'
        endpoint = self.endpoint.replace('http://', '').replace('https://', '')
        s3_url = f"{protocol}://{endpoint}/{self.bucket_name}"
        return upload_to_s3(
            file_path=file_path,
            s3_url=s3_url,
            access_key=self.access_key,
            secret_key=self.secret_key,
            region=self.region
        )

class S3CompatibleProvider(CloudStorageProvider):
    def __init__(self):
        self.endpoint_url = os.getenv('S3_ENDPOINT_URL')
        self.access_key = os.getenv('S3_ACCESS_KEY')
        self.secret_key = os.getenv('S3_SECRET_KEY')
        self.bucket_name = os.getenv('S3_BUCKET_NAME')
        self.region = os.getenv('S3_REGION', '')

    def upload_file(self, file_path: str) -> str:
        s3_url = f"{self.endpoint_url}/{self.bucket_name}" if self.endpoint_url else f"s3://{self.bucket_name}"
        return upload_to_s3(
            file_path=file_path,
            s3_url=s3_url,
            access_key=self.access_key,
            secret_key=self.secret_key,
            region=self.region
        )

def get_storage_provider() -> CloudStorageProvider:
    """Get the appropriate storage provider based on environment configuration."""
    provider = os.getenv('STORAGE_PROVIDER', 'minio').lower()
    
    if provider == 'minio':
        validate_env_vars('MINIO')
        return MinioStorageProvider()
    elif provider == 'gcp' and os.getenv('GCP_BUCKET_NAME'):
        validate_env_vars('GCP')
        return GCPStorageProvider()
    elif provider == 's3' or (os.getenv('S3_ACCESS_KEY') and os.getenv('S3_BUCKET_NAME')):
        validate_env_vars('S3')
        return S3CompatibleProvider()
    else:
        # Default to MinIO if no specific provider is configured
        validate_env_vars('MINIO')
        return MinioStorageProvider()

def upload_file(file_path: str) -> str:
    """Upload a file using the configured storage provider.
    
    Args:
        file_path (str): Path to the file to upload
        
    Returns:
        str: URL of the uploaded file
        
    Raises:
        Exception: If upload fails or if storage provider is not properly configured
    """
    provider = get_storage_provider()
    try:
        logger.info(f"Uploading file using {provider.__class__.__name__}: {file_path}")
        url = provider.upload_file(file_path)
        logger.info(f"File uploaded successfully: {url}")
        return url
    except Exception as e:
        logger.error(f"Error uploading file to cloud storage: {e}")
        raise