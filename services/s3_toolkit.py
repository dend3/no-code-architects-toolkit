import os
import boto3
import logging
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

def parse_s3_url(s3_url):
    """Parse S3 URL to extract bucket name and endpoint URL.
    Supports both MinIO and other S3-compatible services."""
    parsed_url = urlparse(s3_url)
    
    # Extract bucket name from the path
    path_parts = parsed_url.path.strip('/').split('/')
    bucket_name = path_parts[0] if path_parts else None
    
    if not bucket_name:
        # If bucket is not in path, try to get it from hostname
        bucket_name = parsed_url.hostname.split('.')[0]
    
    # Construct endpoint URL
    if parsed_url.scheme and parsed_url.netloc:
        endpoint_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
    else:
        # Default to localhost MinIO if no specific endpoint is provided
        endpoint_url = "http://localhost:9000"
    
    return bucket_name, endpoint_url

def upload_to_s3(file_path, s3_url, access_key, secret_key, region=None):
    """Upload a file to MinIO or other S3-compatible storage.
    
    Args:
        file_path (str): Path to the file to upload
        s3_url (str): URL of the S3 bucket (can be MinIO URL)
        access_key (str): Access key for authentication
        secret_key (str): Secret key for authentication
        region (str, optional): Region name (not required for MinIO)
    
    Returns:
        str: URL of the uploaded file
    """
    # Parse the S3 URL into bucket and endpoint
    bucket_name, endpoint_url = parse_s3_url(s3_url)
    
    session = boto3.Session(
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        region_name=region
    )
    
    # Configure S3 client with MinIO compatibility
    client = session.client('s3',
                          endpoint_url=endpoint_url,
                          config=boto3.Config(
                              s3={'addressing_style': 'path'},
                              signature_version='s3v4'
                          ))

    try:
        # Upload the file to the specified bucket
        with open(file_path, 'rb') as data:
            client.upload_fileobj(
                data, 
                bucket_name, 
                os.path.basename(file_path),
                ExtraArgs={'ACL': 'public-read'}
            )

        # Construct the file URL
        file_url = f"{endpoint_url}/{bucket_name}/{os.path.basename(file_path)}"
        logger.info(f"File uploaded successfully to: {file_url}")
        return file_url
    except Exception as e:
        logger.error(f"Error uploading file to MinIO/S3: {e}")
        raise
