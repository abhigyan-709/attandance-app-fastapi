import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# AWS S3 Configuration
AWS_ACCESS_KEY_ID = os.environ.get("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.environ.get("AWS_SECRET_ACCESS_KEY")
AWS_BUCKET_NAME = os.environ.get("AWS_BUCKET_NAME")
AWS_REGION = os.environ.get("AWS_REGION")

# CDN Configuration
# Option 1: CloudFront CDN (Recommended)
CLOUDFRONT_DOMAIN = os.environ.get("CLOUDFRONT_DOMAIN", "")  # e.g., d1234567890.cloudfront.net
CLOUDFRONT_ENABLED = os.environ.get("CLOUDFRONT_ENABLED", "false").lower() == "true"

# Option 2: Custom CDN Domain
CUSTOM_CDN_DOMAIN = os.environ.get("CUSTOM_CDN_DOMAIN", "")  # e.g., cdn.projectdevops.in

# Helper function to get CDN URL
def get_cdn_url(s3_key: str) -> str:
    """
    Convert S3 key to CDN URL
    
    Args:
        s3_key: S3 object key (e.g., "blogs/image.jpg" or full S3 URL)
    
    Returns:
        CDN URL or S3 URL (fallback)
    """
    # Extract key from full S3 URL if provided
    if s3_key.startswith("https://"):
        # Extract key from URL like: https://bucket.s3.region.amazonaws.com/path/to/file.jpg
        parts = s3_key.split(f"{AWS_BUCKET_NAME}.s3.")
        if len(parts) > 1:
            s3_key = parts[1].split("/", 1)[1] if "/" in parts[1] else ""
    
    # Priority: Custom CDN > CloudFront > Direct S3
    if CUSTOM_CDN_DOMAIN:
        return f"https://{CUSTOM_CDN_DOMAIN}/{s3_key}"
    elif CLOUDFRONT_ENABLED and CLOUDFRONT_DOMAIN:
        return f"https://{CLOUDFRONT_DOMAIN}/{s3_key}"
    else:
        # Fallback to direct S3 URL
        return f"https://{AWS_BUCKET_NAME}.s3.{AWS_REGION}.amazonaws.com/{s3_key}"


def get_s3_direct_url(s3_key: str) -> str:
    """Get direct S3 URL (bypass CDN)"""
    return f"https://{AWS_BUCKET_NAME}.s3.{AWS_REGION}.amazonaws.com/{s3_key}"

