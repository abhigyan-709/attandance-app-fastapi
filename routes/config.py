import os
import logging
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

logger = logging.getLogger(__name__)

# AWS S3 Configuration
AWS_ACCESS_KEY_ID = os.environ.get("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.environ.get("AWS_SECRET_ACCESS_KEY")
AWS_REGION = os.environ.get("AWS_REGION", "ap-south-1")

# S3 Bucket Configuration - NEW bucket for news images
AWS_BUCKET_NAME = os.environ.get("AWS_BUCKET_NAME", "gobarsahitimes-news-images")

# S3 Base URL for direct access (NO CloudFront)
S3_BASE_URL = f"https://{AWS_BUCKET_NAME}.s3.{AWS_REGION}.amazonaws.com"


def get_s3_url(s3_key: str) -> str:
    """
    Generate direct S3 URL for a given key.
    
    Args:
        s3_key: S3 object key (e.g., "news/image.jpg")
    
    Returns:
        Full S3 URL
    
    Examples:
        >>> get_s3_url("news/abc123.jpg")
        'https://gobarsahitimes-news-images.s3.ap-south-1.amazonaws.com/news/abc123.jpg'
    """
    # Ensure key doesn't start with /
    if s3_key and s3_key.startswith("/"):
        s3_key = s3_key[1:]
    
    return f"{S3_BASE_URL}/{s3_key}"


def extract_s3_key_from_url(url: str) -> str:
    """
    Extract S3 object key from S3 URL.
    
    Args:
        url: Full S3 URL
    
    Returns:
        S3 object key
    
    Examples:
        >>> extract_s3_key_from_url("https://gobarsahitimes-news-images.s3.ap-south-1.amazonaws.com/news/img.jpg")
        'news/img.jpg'
    """
    if not url:
        return ""
    
    # Handle S3 URLs
    if ".s3." in url and ".amazonaws.com/" in url:
        return url.split(".amazonaws.com/", 1)[-1]
    
    # Handle old CloudFront URLs (for migration)
    if ".cloudfront.net/" in url:
        return url.split(".cloudfront.net/", 1)[-1]
    
    # Return as-is if no pattern matches (might be just the key)
    return url


# Backward compatibility aliases
def get_cdn_url(s3_key: str) -> str:
    """Alias for get_s3_url - kept for backward compatibility during migration"""
    return get_s3_url(s3_key)


def get_s3_direct_url(s3_key: str) -> str:
    """Alias for get_s3_url - kept for backward compatibility"""
    return get_s3_url(s3_key)

