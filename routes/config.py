import os
import logging
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

logger = logging.getLogger(__name__)

# AWS S3 Configuration
AWS_ACCESS_KEY_ID = os.environ.get("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.environ.get("AWS_SECRET_ACCESS_KEY")
AWS_BUCKET_NAME = os.environ.get("AWS_BUCKET_NAME", "projectdevops-blogs-new")
AWS_REGION = os.environ.get("AWS_REGION", "ap-south-1")

# CDN Configuration - REQUIRED for production
# Primary: CDN_BASE_URL (full base URL including https://)
# Example: https://d1om8nyi4q4a7q.cloudfront.net
CDN_BASE_URL = os.environ.get("CDN_BASE_URL")

# Legacy support (backward compatibility)
CLOUDFRONT_DOMAIN = os.environ.get("CLOUDFRONT_DOMAIN", "")  # e.g., d1234567890.cloudfront.net
CLOUDFRONT_ENABLED = os.environ.get("CLOUDFRONT_ENABLED", "false").lower() == "true"
CUSTOM_CDN_DOMAIN = os.environ.get("CUSTOM_CDN_DOMAIN", "")  # e.g., cdn.projectdevops.in


def _validate_cdn_config():
    """
    Validate CDN configuration on startup.
    Raises RuntimeError if CDN_BASE_URL is not configured in production.
    """
    if not CDN_BASE_URL and not CLOUDFRONT_DOMAIN and not CUSTOM_CDN_DOMAIN:
        # Check if we're in production mode
        env = os.environ.get("ENVIRONMENT", "development").lower()
        if env in ["production", "prod"]:
            raise RuntimeError(
                "CDN_BASE_URL environment variable is required in production. "
                "Set CDN_BASE_URL=https://your-cloudfront-domain.cloudfront.net"
            )
        else:
            logger.warning(
                "⚠️ CDN_BASE_URL not configured. Using direct S3 URLs. "
                "Set CDN_BASE_URL for production deployments."
            )


# Validate on module import
_validate_cdn_config()


def get_cdn_url(s3_key: str) -> str:
    """
    Convert S3 key to CDN URL for serving media files.
    
    Args:
        s3_key: S3 object key (e.g., "blogs/image.jpg" or full S3 URL)
    
    Returns:
        CDN URL (primary) or S3 URL (fallback for development)
    
    Examples:
        >>> get_cdn_url("news/abc123.jpg")
        'https://d1om8nyi4q4a7q.cloudfront.net/news/abc123.jpg'
        
        >>> get_cdn_url("https://bucket.s3.region.amazonaws.com/news/abc123.jpg")
        'https://d1om8nyi4q4a7q.cloudfront.net/news/abc123.jpg'
    """
    # Extract key from full S3 URL if provided
    if s3_key and s3_key.startswith("https://"):
        # Handle URL like: https://bucket.s3.region.amazonaws.com/path/to/file.jpg
        # or https://bucket.s3.amazonaws.com/path/to/file.jpg
        if ".s3." in s3_key and ".amazonaws.com/" in s3_key:
            s3_key = s3_key.split(".amazonaws.com/", 1)[-1]
        elif ".cloudfront.net/" in s3_key:
            # Already a CDN URL, extract key
            s3_key = s3_key.split(".cloudfront.net/", 1)[-1]
    
    # Ensure key doesn't start with /
    if s3_key and s3_key.startswith("/"):
        s3_key = s3_key[1:]
    
    # Priority 1: CDN_BASE_URL (new recommended approach)
    if CDN_BASE_URL:
        base = CDN_BASE_URL.rstrip("/")
        return f"{base}/{s3_key}"
    
    # Priority 2: Custom CDN Domain (legacy)
    if CUSTOM_CDN_DOMAIN:
        return f"https://{CUSTOM_CDN_DOMAIN}/{s3_key}"
    
    # Priority 3: CloudFront Domain (legacy)
    if CLOUDFRONT_ENABLED and CLOUDFRONT_DOMAIN:
        return f"https://{CLOUDFRONT_DOMAIN}/{s3_key}"
    
    # Fallback: Direct S3 URL (development only)
    return f"https://{AWS_BUCKET_NAME}.s3.{AWS_REGION}.amazonaws.com/{s3_key}"


def get_s3_direct_url(s3_key: str) -> str:
    """Get direct S3 URL (bypass CDN) - use only for internal operations"""
    return f"https://{AWS_BUCKET_NAME}.s3.{AWS_REGION}.amazonaws.com/{s3_key}"


def extract_s3_key_from_url(url: str) -> str:
    """
    Extract S3 object key from various URL formats.
    
    Args:
        url: Full URL (S3 or CDN)
    
    Returns:
        S3 object key
    
    Examples:
        >>> extract_s3_key_from_url("https://bucket.s3.region.amazonaws.com/news/img.jpg")
        'news/img.jpg'
        >>> extract_s3_key_from_url("https://d123.cloudfront.net/news/img.jpg")
        'news/img.jpg'
    """
    if not url:
        return ""
    
    # Handle S3 URLs
    if ".s3." in url and ".amazonaws.com/" in url:
        return url.split(".amazonaws.com/", 1)[-1]
    
    # Handle CloudFront URLs
    if ".cloudfront.net/" in url:
        return url.split(".cloudfront.net/", 1)[-1]
    
    # Handle custom CDN domains
    if CUSTOM_CDN_DOMAIN and CUSTOM_CDN_DOMAIN in url:
        return url.split(CUSTOM_CDN_DOMAIN + "/", 1)[-1]
    
    # Handle CDN_BASE_URL
    if CDN_BASE_URL and CDN_BASE_URL.rstrip("/") in url:
        return url.split(CDN_BASE_URL.rstrip("/") + "/", 1)[-1]
    
    # Return as-is if no pattern matches (might be just the key)
    return url

