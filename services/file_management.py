import os
import uuid
import time
import mimetypes
import requests
from urllib.parse import urlparse, parse_qs
import logging

logger = logging.getLogger(__name__)

# Default storage path for temporary files
STORAGE_PATH = "/tmp/"

def download_file(url, storage_path=STORAGE_PATH):
    """Download a file from a URL (supports MinIO, S3, and HTTP URLs).
    
    Args:
        url (str): URL to download from (can be MinIO, S3, or HTTP URL)
        storage_path (str): Local path to store the downloaded file
        
    Returns:
        str: Path to the downloaded file
    """
    # Parse the URL to extract information
    parsed_url = urlparse(url)
    
    # Generate a unique file ID
    file_id = str(uuid.uuid4())
    
    # Ensure the storage directory exists
    if not os.path.exists(storage_path):
        os.makedirs(storage_path)
    
    # Try to determine the file extension from the URL path or content type
    extension = os.path.splitext(parsed_url.path)[-1]
    if not extension:
        # If no extension in URL, try to get it from content type
        try:
            response = requests.head(url)
            content_type = response.headers.get('content-type', '')
            extension = mimetypes.guess_extension(content_type) or '.bin'
        except:
            extension = '.bin'
    
    # Create the local filename with the determined extension
    local_filename = os.path.join(storage_path, f"{file_id}{extension}")
    
    logger.info(f"Downloading file from {url} to {local_filename}")
    
    # Download the file
    try:
        response = requests.get(url, stream=True)
        response.raise_for_status()
        
        with open(local_filename, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        logger.info(f"File downloaded successfully to {local_filename}")
        return local_filename
    except Exception as e:
        logger.error(f"Error downloading file from {url}: {e}")
        raise

def delete_old_files(max_age_seconds=3600):
    """Delete files older than the specified age from the storage directory.
    
    Args:
        max_age_seconds (int): Maximum age of files in seconds before deletion
    """
    now = time.time()
    deleted_count = 0
    
    try:
        for filename in os.listdir(STORAGE_PATH):
            file_path = os.path.join(STORAGE_PATH, filename)
            if os.path.isfile(file_path):
                file_age = now - os.stat(file_path).st_mtime
                if file_age > max_age_seconds:
                    os.remove(file_path)
                    deleted_count += 1
        
        if deleted_count > 0:
            logger.info(f"Deleted {deleted_count} old files from {STORAGE_PATH}")
    except Exception as e:
        logger.error(f"Error cleaning up old files: {e}")
        raise
