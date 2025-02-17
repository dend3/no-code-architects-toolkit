import os
from typing import Optional

# Retrieve the API key from environment variables
API_KEY = os.environ.get('API_KEY')
if not API_KEY:
    raise ValueError("API_KEY environment variable is not set")

# GCP environment variables
GCP_SA_CREDENTIALS = os.environ.get('GCP_SA_CREDENTIALS', '')
GCP_BUCKET_NAME = os.environ.get('GCP_BUCKET_NAME', '')

# MinIO/S3 environment variables
STORAGE_PROVIDER = os.environ.get('STORAGE_PROVIDER', 'minio').lower()  # 'minio', 'gcp', or 's3'
MINIO_ENDPOINT = os.environ.get('MINIO_ENDPOINT', 'http://localhost:9000')
MINIO_ACCESS_KEY = os.environ.get('MINIO_ACCESS_KEY', '')
MINIO_SECRET_KEY = os.environ.get('MINIO_SECRET_KEY', '')
MINIO_BUCKET_NAME = os.environ.get('MINIO_BUCKET_NAME', 'default')
MINIO_SECURE = os.environ.get('MINIO_SECURE', 'true').lower() == 'true'
MINIO_REGION = os.environ.get('MINIO_REGION', '')

# Legacy S3 variables (for backward compatibility)
S3_ENDPOINT_URL = os.environ.get('S3_ENDPOINT_URL', '')
S3_ACCESS_KEY = os.environ.get('S3_ACCESS_KEY', '')
S3_SECRET_KEY = os.environ.get('S3_SECRET_KEY', '')
S3_BUCKET_NAME = os.environ.get('S3_BUCKET_NAME', '')
S3_REGION = os.environ.get('S3_REGION', '')

def validate_env_vars(provider: str):
    """ Validate the necessary environment variables for the selected storage provider """
    required_vars = {
        'GCP': ['GCP_BUCKET_NAME', 'GCP_SA_CREDENTIALS'],
        'S3': ['S3_ACCESS_KEY', 'S3_SECRET_KEY', 'S3_BUCKET_NAME'],
        'MINIO': ['MINIO_ACCESS_KEY', 'MINIO_SECRET_KEY', 'MINIO_BUCKET_NAME']
    }
    
    missing_vars = [var for var in required_vars[provider] if not os.getenv(var)]
    if missing_vars:
        raise ValueError(f"Missing environment variables for {provider} storage: {', '.join(missing_vars)}")

class CloudStorageProvider:
    """ Abstract CloudStorageProvider class to define the upload_file method """
    def upload_file(self, file_path: str) -> str:
        raise NotImplementedError("upload_file must be implemented by subclasses")

class GCPStorageProvider(CloudStorageProvider):
    """ GCP-specific cloud storage provider """
    def __init__(self):
        self.bucket_name = os.getenv('GCP_BUCKET_NAME')

    def upload_file(self, file_path: str) -> str:
        from services.gcp_toolkit import upload_to_gcs
        return upload_to_gcs(file_path, self.bucket_name)

class MinioStorageProvider(CloudStorageProvider):
    """ MinIO-specific storage provider """
    def __init__(self):
        self.endpoint = os.getenv('MINIO_ENDPOINT', 'http://localhost:9000')
        self.access_key = os.getenv('MINIO_ACCESS_KEY')
        self.secret_key = os.getenv('MINIO_SECRET_KEY')
        self.bucket_name = os.getenv('MINIO_BUCKET_NAME', 'default')
        self.secure = os.environ.get('MINIO_SECURE', 'true').lower() == 'true'
        self.region = os.environ.get('MINIO_REGION', '')

    def upload_file(self, file_path: str) -> str:
        from services.s3_toolkit import upload_to_s3
        protocol = 'https' if self.secure else 'http'
        endpoint = self.endpoint.replace('http://', '').replace('https://', '')
        s3_url = f"{protocol}://{endpoint}/{self.bucket_name}"
        return upload_to_s3(
            file_path=file_path,
            s3_url=s3_url,
            access_key=self.access_key,
            secret_key=self.secret_key
        )

class S3CompatibleProvider(CloudStorageProvider):
    """ S3-compatible storage provider (for AWS S3, DigitalOcean Spaces, etc.) """
    def __init__(self):
        self.bucket_name = os.getenv('S3_BUCKET_NAME')
        self.endpoint_url = os.getenv('S3_ENDPOINT_URL')
        self.access_key = os.getenv('S3_ACCESS_KEY')
        self.secret_key = os.getenv('S3_SECRET_KEY')
        self.region = os.getenv('S3_REGION', '')

    def upload_file(self, file_path: str) -> str:
        from services.s3_toolkit import upload_to_s3
        s3_url = f"{self.endpoint_url}/{self.bucket_name}" if self.endpoint_url else f"s3://{self.bucket_name}"
        return upload_to_s3(
            file_path=file_path,
            s3_url=s3_url,
            access_key=self.access_key,
            secret_key=self.secret_key
        )

def get_storage_provider() -> CloudStorageProvider:
    """ Get the appropriate storage provider based on the STORAGE_PROVIDER setting """
    provider = STORAGE_PROVIDER.upper()
    
    if provider == 'MINIO':
        validate_env_vars('MINIO')
        return MinioStorageProvider()
    elif provider == 'GCP' and os.getenv('GCP_BUCKET_NAME'):
        validate_env_vars('GCP')
        return GCPStorageProvider()
    elif provider == 'S3' or (os.getenv('S3_ACCESS_KEY') and os.getenv('S3_BUCKET_NAME')):
        validate_env_vars('S3')
        return S3CompatibleProvider()
    else:
        # Default to MinIO if no specific provider is configured
        validate_env_vars('MINIO')
        return MinioStorageProvider()
