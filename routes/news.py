# routes/news.py — gtnews18 news API (blogs parity)
import math
import os
import re
import uuid
import logging
import pytz
from datetime import datetime, date, timedelta
from typing import List, Optional, Dict, Any, Union
from pydantic import BaseModel, EmailStr, Field
import boto3
import requests
from bs4 import BeautifulSoup
from bson import ObjectId
from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    Request,
    UploadFile,
    Body,
)
from fastapi.responses import HTMLResponse
from pymongo import MongoClient, DESCENDING, ASCENDING

from database.db import db
from models.news import (
    NewsPost, Comment, Category,
    DailyHoroscope, ZodiacPrediction, ZodiacSign,
    CreateHoroscopeRequest, UpdateHoroscopeRequest,
    LiveStream, StreamPlatform, CreateLiveStreamRequest, UpdateLiveStreamRequest
)
from models.user import User
from routes.config import (
    AWS_ACCESS_KEY_ID, 
    AWS_SECRET_ACCESS_KEY, 
    AWS_REGION, 
    AWS_BUCKET_NAME,
    get_s3_url,
    extract_s3_key_from_url
)
from routes.user import get_current_user

from pydantic import BaseModel, Field

# Import fresh news push notification system
try:
    from routes.news_push import broadcast_to_all_news_subscribers
except ImportError:
    broadcast_to_all_news_subscribers = None

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

news_router = APIRouter()

# S3 client for uploads (bucket remains private, served via CloudFront CDN)
s3_client = boto3.client(
    "s3",
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    region_name=AWS_REGION,
)

# --- web-push notify plumbing (kept SAME as blogs) ---
PUBLIC_API_BASE = os.getenv("PUBLIC_API_BASE", "http://localhost:8000")
ADMIN_API_TOKEN = os.getenv("ADMIN_API_TOKEN")
# For canonical links in meta; defaults to gtnews18
NEWS_BASE_URL = os.getenv("NEWS_BASE_URL", "https://gobarsahitimes.com")


# Hindi to Latin transliteration map for URL slugs
HINDI_TO_LATIN = {
    # Vowels
    'अ': 'a', 'आ': 'aa', 'इ': 'i', 'ई': 'ee', 'उ': 'u', 'ऊ': 'oo', 
    'ए': 'e', 'ऐ': 'ai', 'ओ': 'o', 'औ': 'au', 'ऋ': 'ri',
    # Consonants
    'क': 'k', 'ख': 'kh', 'ग': 'g', 'घ': 'gh', 'ङ': 'ng',
    'च': 'ch', 'छ': 'chh', 'ज': 'j', 'झ': 'jh', 'ञ': 'ny',
    'ट': 't', 'ठ': 'th', 'ड': 'd', 'ढ': 'dh', 'ण': 'n',
    'त': 't', 'थ': 'th', 'द': 'd', 'ध': 'dh', 'न': 'n',
    'प': 'p', 'फ': 'ph', 'ब': 'b', 'भ': 'bh', 'म': 'm',
    'य': 'y', 'र': 'r', 'ल': 'l', 'व': 'v', 'w': 'w',
    'श': 'sh', 'ष': 'sh', 'स': 's', 'ह': 'h',
    'क़': 'q', 'ख़': 'kh', 'ग़': 'gh', 'ज़': 'z', 'ड़': 'r', 'ढ़': 'rh', 'फ़': 'f',
    # Vowel signs (matras)
    'ा': 'aa', 'ि': 'i', 'ी': 'ee', 'ु': 'u', 'ू': 'oo', 
    'े': 'e', 'ै': 'ai', 'ो': 'o', 'ौ': 'au', 'ं': 'n', 'ः': 'h', '्': '',
    # Numbers
    '०': '0', '१': '1', '२': '2', '३': '3', '४': '4', 
    '५': '5', '६': '6', '७': '7', '८': '8', '९': '9',
}

def _transliterate_hindi(text: str) -> str:
    """Convert Hindi text to Latin script for SEO-friendly URLs"""
    result = []
    for char in text:
        if char in HINDI_TO_LATIN:
            result.append(HINDI_TO_LATIN[char])
        elif char.isalnum() or char in ('-', '_'):
            result.append(char.lower())
        else:
            result.append('-')
    return ''.join(result)

def _slugify(s: str) -> str:
    """Legacy simple slugify - kept for backward compatibility"""
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")

def _generate_seo_slug(title: str, news_id: str) -> str:
    """Generate SEO-friendly slug from title with Hindi transliteration
    
    Examples:
        मोतीझील में फंस जाते हैं परीक्षार्थी → motijheel-men-phans-jaate-hain-pareeksharthee-{id}
        Bihar Election 2025 → bihar-election-2025-{id}
        पटना में भारी बारिश → patna-men-bhaaree-baarish-{id}
    """
    # Transliterate Hindi to Latin
    transliterated = _transliterate_hindi(title)
    
    # Clean up: remove multiple dashes, leading/trailing dashes
    base_slug = re.sub(r'-+', '-', transliterated).strip('-')
    
    # Limit length for cleaner URLs (max 60 chars before ID)
    if len(base_slug) > 60:
        # Try to break at word boundary
        base_slug = base_slug[:60].rsplit('-', 1)[0]
    
    # Ensure we have something, fallback to "news" if empty after transliteration
    if not base_slug or base_slug == '-':
        base_slug = 'news'
    
    # Add ID for uniqueness (last 8 chars of ObjectId for shorter URLs)
    short_id = news_id[-8:] if len(news_id) >= 8 else news_id
    return f"{base_slug}-{short_id}"

def _extract_meta_description(content: str, max_length: int = 160) -> str:
    """Extract clean meta description from HTML content"""
    if not content:
        return ""
    # Remove HTML tags and get plain text
    soup = BeautifulSoup(content, "html.parser")
    text = soup.get_text().strip()
    # Return first 160 characters for meta description
    return text[:max_length] + "..." if len(text) > max_length else text

def _calculate_word_count(content: str) -> int:
    """Calculate word count from HTML content"""
    if not content:
        return 0
    soup = BeautifulSoup(content, "html.parser")
    text = soup.get_text()
    # Count Hindi + English words
    words = re.findall(r'[\u0900-\u097F]+|[a-zA-Z]+', text)
    return len(words)

def _calculate_reading_time(word_count: int) -> int:
    """Calculate reading time in minutes (average 200 words/min for Hindi)"""
    return max(1, round(word_count / 200))

def _extract_keywords(title: str, content: str, categories: str) -> List[str]:
    """Auto-extract keywords from title, content, and categories"""
    keywords = []
    
    # Add category as keyword
    if categories:
        keywords.append(categories.lower())
    
    # Extract important words from title (Hindi and English)
    title_words = re.findall(r'[\u0900-\u097F]+|[a-zA-Z]+', title.lower())
    keywords.extend([word for word in title_words if len(word) > 3])
    
    # Remove duplicates and limit to 10 keywords
    return list(dict.fromkeys(keywords))[:10]


# ==================== SEO/SCHEMA.ORG HELPERS ====================

# Publisher info for JSON-LD (configure these for your site)
PUBLISHER_NAME = os.getenv("NEWS_PUBLISHER_NAME", "GT News 18")
PUBLISHER_LOGO_URL = os.getenv("NEWS_PUBLISHER_LOGO", "https://gobarsahitimes.com/logo.png")
PUBLISHER_URL = os.getenv("NEWS_BASE_URL", "https://gobarsahitimes.com")


def _generate_news_article_jsonld(doc: Dict[str, Any], db_client: MongoClient) -> Dict[str, Any]:
    """
    Generate Google News compliant JSON-LD structured data for a news article.
    
    This schema is CRITICAL for:
    - Google News inclusion
    - Rich snippets in search results
    - Better SEO ranking
    
    Schema: https://schema.org/NewsArticle
    """
    news_id = str(doc.get("_id", ""))
    title = doc.get("title", "")
    slug = doc.get("slug") or _generate_seo_slug(title, news_id)
    canonical_url = doc.get("canonical_url_override") or f"{NEWS_BASE_URL}/news/{slug}"
    
    # Get clean text content
    content = doc.get("content", "")
    plain_text = _extract_meta_description(content, max_length=5000)  # Full article text
    description = doc.get("meta_description") or _extract_meta_description(content, 160)
    
    # Calculate word count and reading time if not stored
    word_count = doc.get("word_count") or _calculate_word_count(content)
    reading_time = doc.get("reading_time_minutes") or _calculate_reading_time(word_count)
    
    # Dates in ISO 8601 format
    created_at = doc.get("created_at", datetime.utcnow())
    updated_at = doc.get("updated_at") or created_at
    
    if isinstance(created_at, datetime):
        date_published = created_at.strftime("%Y-%m-%dT%H:%M:%S+05:30")  # IST
    else:
        date_published = str(created_at)
    
    if isinstance(updated_at, datetime):
        date_modified = updated_at.strftime("%Y-%m-%dT%H:%M:%S+05:30")
    else:
        date_modified = str(updated_at)
    
    # Author information
    author_details = doc.get("author_details") or {}
    author_name = author_details.get("full_name") or doc.get("author_username", "Editorial Team")
    author_url = f"{NEWS_BASE_URL}/author/{doc.get('author_username', 'team')}"
    
    # Image
    image_url = doc.get("image_url", "")
    image_alt = doc.get("image_alt") or title
    
    # Keywords
    keywords = doc.get("keywords") or _extract_keywords(title, content, doc.get("categories", ""))
    
    # Determine article type
    article_type = "NewsArticle"
    if doc.get("is_opinion"):
        article_type = "OpinionNewsArticle"
    
    # Build the JSON-LD schema
    jsonld = {
        "@context": "https://schema.org",
        "@type": article_type,
        "mainEntityOfPage": {
            "@type": "WebPage",
            "@id": canonical_url
        },
        "headline": title[:110],  # Google recommends max 110 chars
        "description": description,
        "image": {
            "@type": "ImageObject",
            "url": image_url,
            "alt": image_alt
        } if image_url else None,
        "author": {
            "@type": "Person",
            "name": author_name,
            "url": author_url
        },
        "publisher": {
            "@type": "Organization",
            "name": PUBLISHER_NAME,
            "logo": {
                "@type": "ImageObject",
                "url": PUBLISHER_LOGO_URL
            },
            "url": PUBLISHER_URL
        },
        "datePublished": date_published,
        "dateModified": date_modified,
        "articleSection": doc.get("categories", "News"),
        "keywords": ", ".join(keywords) if keywords else None,
        "wordCount": word_count,
        "inLanguage": "hi-IN",
        "isAccessibleForFree": True,
        "articleBody": plain_text[:5000]  # First 5000 chars
    }
    
    # Add breaking news indicator if applicable
    if doc.get("is_breaking_news"):
        jsonld["@type"] = "NewsArticle"
        jsonld["genre"] = "Breaking News"
    
    # Remove None values
    jsonld = {k: v for k, v in jsonld.items() if v is not None}
    
    return jsonld


def _generate_breadcrumb_jsonld(doc: Dict[str, Any]) -> Dict[str, Any]:
    """Generate BreadcrumbList JSON-LD for navigation"""
    category = doc.get("categories", "समाचार")
    title = doc.get("title", "")
    slug = doc.get("slug") or _generate_seo_slug(title, str(doc.get("_id", "")))
    
    return {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {
                "@type": "ListItem",
                "position": 1,
                "name": "होम",
                "item": NEWS_BASE_URL
            },
            {
                "@type": "ListItem",
                "position": 2,
                "name": category,
                "item": f"{NEWS_BASE_URL}/category/{category}"
            },
            {
                "@type": "ListItem",
                "position": 3,
                "name": title[:50],
                "item": f"{NEWS_BASE_URL}/news/{slug}"
            }
        ]
    }


def _notify_new_blog_async(title: str, url: str, image: Optional[str] = None):
    """Kept identical to your blogs notifier per request."""
    try:
        payload = {
            "title": title,
            "body": "New post just landed! Tap to read.",
            "url": url,
            "image": image,
            "tag": "new-blog",
        }
        headers = {"Content-Type": "application/json"}
        if ADMIN_API_TOKEN:
            headers["x-admin-token"] = ADMIN_API_TOKEN
        requests.post(
            f"{PUBLIC_API_BASE}/push/notify-new-blog",
            json=payload,
            headers=headers,
            timeout=5,
        )
    except Exception as e:
        logger.warning(f"notify_new_blog failed: {e}")


# ------------------------- Auth helpers -------------------------
def get_current_author_or_admin_user(current_user: User = Depends(get_current_user)):
    if current_user.role not in ["admin", "author"]:
        raise HTTPException(
            status_code=403,
            detail="Not authorized to perform this action. Requires admin or author role.",
        )
    return current_user


def get_current_admin_user(current_user: User = Depends(get_current_user)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized to perform this action")
    return current_user


# ---------- helper: default to published-only for anonymous/public requests ----------
def _should_force_published_only(request: Request, published_param: Optional[bool]) -> bool:
    if published_param is not None:
        return False
    auth = (request.headers.get("Authorization") or "").strip()
    return not bool(auth)


# ---------- IST Timezone & Scheduling Helpers ----------
IST = pytz.timezone('Asia/Kolkata')

def _parse_ist_datetime(datetime_str: str) -> datetime:
    """Parse datetime string in IST and return UTC datetime for storage
    
    Expected format: YYYY-MM-DDTHH:MM (24-hour format)
    Example: 2025-12-05T14:30
    """
    try:
        # Parse the datetime string (assumes IST input)
        naive_dt = datetime.strptime(datetime_str, "%Y-%m-%dT%H:%M")
        
        # Localize to IST
        ist_dt = IST.localize(naive_dt)
        
        # Convert to UTC for storage
        utc_dt = ist_dt.astimezone(pytz.UTC).replace(tzinfo=None)
        
        return utc_dt
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid datetime format. Expected: YYYY-MM-DDTHH:MM (24-hour IST). Error: {str(e)}"
        )


def _utc_to_ist(utc_dt: datetime) -> datetime:
    """Convert UTC datetime to IST for display"""
    if utc_dt is None:
        return None
    utc_dt = pytz.UTC.localize(utc_dt) if utc_dt.tzinfo is None else utc_dt
    return utc_dt.astimezone(IST).replace(tzinfo=None)


def _is_scheduled_post_ready(scheduled_at: datetime) -> bool:
    """Check if a scheduled post should be published now (UTC comparison)"""
    if scheduled_at is None:
        return False
    current_utc = datetime.utcnow()
    return current_utc >= scheduled_at


def _process_scheduled_posts(db_client: MongoClient):
    """Background task to auto-publish scheduled posts that are due
    
    This should be called periodically or on each request
    """
    try:
        coll = db_client[db.db_name][NEWS_COLL]
        current_utc = datetime.utcnow()
        
        # Find scheduled posts that are ready to publish
        scheduled_posts = coll.find({
            "scheduled_publish": True,
            "published": False,
            "scheduled_at": {"$lte": current_utc}
        })
        
        updated_count = 0
        auto_published_posts = []
        for post in scheduled_posts:
            # Auto-publish the post
            # IMPORTANT: Update created_at to scheduled_at so post appears as latest
            scheduled_time = post.get("scheduled_at", datetime.utcnow())
            coll.update_one(
                {"_id": post["_id"]},
                {
                    "$set": {
                        "published": True,
                        "scheduled_publish": False,
                        "created_at": scheduled_time,  # Update to scheduled time so it appears as latest
                        "updated_at": datetime.utcnow()
                    }
                }
            )
            
            # Increment author's article count when auto-publishing
            author_username = post.get("author_username")
            if author_username:
                db_client[db.db_name]["user"].update_one(
                    {"username": author_username},
                    {"$inc": {"articles_count": 1}}
                )
            
            updated_count += 1
            auto_published_posts.append(post)
            logger.info(f"Auto-published scheduled post: {post['_id']} at scheduled time: {scheduled_time} - created_at updated to match scheduled time")
        
        # Send news push notifications for auto-published posts
        if broadcast_to_all_news_subscribers and auto_published_posts:
            for post in auto_published_posts:
                try:
                    news_url = f"{NEWS_BASE_URL}/news/{post.get('slug', str(post['_id']))}"
                    summary_text = _extract_meta_description(post.get('content', ''), max_length=120)
                    broadcast_to_all_news_subscribers(
                        title=post.get('title', 'New News'),
                        body=summary_text,
                        url=news_url,
                        image=post.get('image_url'),
                        news_id=str(post['_id']),
                        db_client=db_client
                    )
                    logger.info(f"[news-push] Sent notification for auto-published: {post['_id']}")
                except Exception as notify_error:
                    logger.error(f"[news-push] Failed to notify for auto-published: {notify_error}")
        
        return updated_count
    except Exception as e:
        logger.error(f"Error processing scheduled posts: {e}")
        return 0


NEWS_COLL = "news"
NEWS_COMMENTS_COLL = "news_comments"  # separate from blogs "comments"


def _get_author_details(username: str, db_client: MongoClient) -> Optional[Dict[str, Any]]:
    """
    Fetch author details from user collection
    Returns author profile information or None if not found
    """
    try:
        users_collection = db_client[db.db_name]["user"]
        author = users_collection.find_one(
            {"username": username},
            {
                "password": 0,  # Exclude password
                "email": 0      # Exclude email for privacy
            }
        )
        
        if not author:
            return None
        
        # Get author profile image and convert S3 URL to CDN URL if needed
        author_profile_image = author.get("author_profile_image")
        if author_profile_image and ".s3." in author_profile_image and ".amazonaws.com" in author_profile_image:
            # Convert legacy S3 URL to CDN URL
            author_profile_image = get_s3_url(author_profile_image)
        
        # Build author details object
        author_details = {
            "username": username,
            "full_name": f"{author.get('first_name', '')} {author.get('last_name', '')}".strip(),
            "author_profile_image": author_profile_image,
            "author_designation": author.get("author_designation"),
            "author_bio": author.get("author_bio")
        }
        
        return author_details
    except Exception as e:
        logger.error(f"Error fetching author details for {username}: {e}")
        return None


def _normalize_news(doc: Dict[str, Any], db_client: MongoClient) -> Dict[str, Any]:
    doc["_id"] = str(doc["_id"])
    
    # Fetch and embed author details if not already present
    if not doc.get("author_details") and doc.get("author_username"):
        author_details = _get_author_details(doc["author_username"], db_client)
        if author_details:
            doc["author_details"] = author_details
    
    # attach comments by news_id (string id)
    comments = list(
        db_client[db.db_name][NEWS_COMMENTS_COLL].find({"news_id": doc["_id"]}).sort("created_at", DESCENDING)
    )
    for c in comments:
        c["_id"] = str(c["_id"])
        # Normalize phone to string to satisfy response model (some entries may have numeric phones)
        if "phone" in c and c["phone"] is not None:
            try:
                c["phone"] = str(c["phone"]).strip()
            except Exception:
                c["phone"] = None
    doc["comments"] = comments
    # counters
    doc["views"] = doc.get("views", 0)
    doc["viewed_ips"] = doc.get("viewed_ips", [])
    doc["likes"] = doc.get("likes", 0)
    doc["liked_ips"] = doc.get("liked_ips", [])
    raw_gallery = doc.get("content_images") or []
    normalized_gallery = []
    for entry in raw_gallery:
        if isinstance(entry, dict):
            url = entry.get("url")
            caption = entry.get("caption")
        elif isinstance(entry, str):
            url = entry
            caption = None
        else:
            continue
        if not url:
            continue
        normalized_gallery.append(
            {
                "url": url,
                "caption": caption if caption not in (None, "") else None,
            }
        )
    doc["content_images"] = normalized_gallery
    
    # SEO fields (backward compatible - add if missing)
    # Note: slug is now required for new posts, but old posts may not have it
    if not doc.get("slug"):
        doc["slug"] = None  # Old posts without slug will return None
    if not doc.get("meta_title"):
        doc["meta_title"] = doc.get("title", "")
    if not doc.get("meta_description"):
        doc["meta_description"] = _extract_meta_description(doc.get("content", ""))
    if not doc.get("keywords"):
        doc["keywords"] = _extract_keywords(
            doc.get("title", ""), 
            doc.get("content", ""), 
            doc.get("categories", "")
        )
    
    return doc


def _validate_slug_uniqueness(slug: str, news_id: Optional[str], db_client: MongoClient) -> None:
    """Validate that slug is unique (excluding current news_id if updating)
    
    Args:
        slug: The slug to validate
        news_id: Current news ID (for updates) or None (for new posts)
        db_client: MongoDB client
    
    Raises:
        HTTPException: If slug already exists
    """
    coll = db_client[db.db_name][NEWS_COLL]
    
    query = {"slug": slug}
    # Exclude current post when updating
    if news_id and ObjectId.is_valid(news_id):
        query["_id"] = {"$ne": ObjectId(news_id)}
    
    existing = coll.find_one(query, {"_id": 1})
    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"Slug '{slug}' already exists. Please choose a unique slug."
        )


# ------------------------- Create news -------------------------
@news_router.post("/news", response_model=NewsPost, tags=["News"])
async def create_news(
    request: Request,
    title: str = Form(...),
    content: str = Form(...),
    categories: str = Form(""),
    tags: List[str] = Form([]),
    published: bool = Form(True),
    custom_slug: str = Form(...),
    scheduled_publish: bool = Form(False),
    scheduled_at: Optional[str] = Form(None),
    author_username: Optional[str] = Form(None),  # Admin can override author
    # NEW SEO fields (optional - for UI enhancement)
    focus_keyword: Optional[str] = Form(None),          # Primary SEO keyword
    meta_title_override: Optional[str] = Form(None),    # Custom meta title (max 60 chars)
    meta_description_override: Optional[str] = Form(None),  # Custom description (max 160 chars)
    image_alt: Optional[str] = Form(None),              # Alt text for featured image
    is_breaking_news: bool = Form(False),               # Breaking news flag
    is_opinion: bool = Form(False),                     # Opinion/Editorial flag
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = None,
    current_user: User = Depends(get_current_author_or_admin_user),
    db_client: MongoClient = Depends(db.get_client),
):
    # Parse form data manually to handle multiple files with same name
    form = await request.form()
    
    # Extract multiple content_images files
    files: List[UploadFile] = []
    captions_list: List[str] = []
    
    # Get all fields from form (form.getlist doesn't exist, so iterate)
    for key, value in form.multi_items():
        if key == "content_images" and hasattr(value, "file"):
            files.append(value)
        elif key == "content_image_captions":
            captions_list.append(str(value) if value else "")
    
    # Debug logging for incoming multipart payload
    try:
        logger.info(
            "[create_news] Incoming request: title=%r categories=%r tags=%r published=%r "
            "file_name=%r content_images_count=%s content_image_captions_count=%s custom_slug=%r",
            title,
            categories,
            tags,
            published,
            getattr(file, "filename", None),
            len(files),
            len(captions_list),
            custom_slug,
        )
    except Exception as log_exc:
        logger.warning("[create_news] Failed to log request metadata: %s", log_exc)
    
    # Validate and require custom slug
    if not custom_slug or not custom_slug.strip():
        raise HTTPException(
            status_code=400,
            detail="custom_slug is required. Please provide a URL-friendly slug."
        )
    
    custom_slug = custom_slug.strip()
    # Basic slug validation
    if not re.match(r'^[a-z0-9]+(?:-[a-z0-9]+)*$', custom_slug):
        raise HTTPException(
            status_code=400,
            detail="Slug must contain only lowercase letters, numbers, and hyphens (no spaces or special characters)"
        )
    # Check uniqueness
    _validate_slug_uniqueness(custom_slug, None, db_client)

    # Validate scheduling logic
    scheduled_at_utc = None
    if scheduled_publish:
        if not scheduled_at:
            raise HTTPException(
                status_code=400,
                detail="scheduled_at is required when scheduled_publish is true. Provide datetime in format: YYYY-MM-DDTHH:MM (IST)"
            )
        
        # Parse IST datetime and convert to UTC
        scheduled_at_utc = _parse_ist_datetime(scheduled_at)
        
        # Validate: scheduled time must be in the future
        current_utc = datetime.utcnow()
        if scheduled_at_utc <= current_utc:
            # Convert back to IST for user-friendly error message
            current_ist = _utc_to_ist(current_utc)
            raise HTTPException(
                status_code=400,
                detail=f"Scheduled time must be in the future. Current IST time: {current_ist.strftime('%Y-%m-%d %H:%M')}"
            )
        
        # When scheduling, auto-set published=False (will be auto-published at scheduled time)
        published = False
        logger.info(f"[create_news] Scheduling post for {scheduled_at} IST (UTC: {scheduled_at_utc})")
    
    # If not scheduling but scheduled_at provided, ignore it
    if not scheduled_publish and scheduled_at:
        logger.warning("[create_news] scheduled_at provided but scheduled_publish=False, ignoring scheduled_at")
        scheduled_at_utc = None

    file_extension = (file.filename or "image").split(".")[-1]
    unique_filename = f"news/{uuid.uuid4()}.{file_extension}"

    try:
        s3_client.upload_fileobj(
            file.file,
            AWS_BUCKET_NAME,
            unique_filename,
            ExtraArgs={"ContentType": file.content_type},
        )
        # Use CDN URL instead of direct S3 URL
        image_url = get_s3_url(unique_filename)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Image upload failed: {str(e)}")

    # Process gallery entries (files and captions_list already extracted from form above)
    gallery_entries: List[Dict[str, Optional[str]]] = []

    if files:
        for idx, gallery_file in enumerate(files):
            if not gallery_file or not getattr(gallery_file, "file", None):
                continue
            file_extension = (gallery_file.filename or "image").split(".")[-1]
            gallery_key = f"news/content/{uuid.uuid4()}.{file_extension}"
            content_type = gallery_file.content_type or "application/octet-stream"
            try:
                s3_client.upload_fileobj(
                    gallery_file.file,
                    AWS_BUCKET_NAME,
                    gallery_key,
                    ExtraArgs={"ContentType": content_type},
                )
            except Exception as exc:
                raise HTTPException(status_code=500, detail=f"Content image upload failed: {str(exc)}")

            # Use CDN URL instead of direct S3 URL
            gallery_url = get_s3_url(gallery_key)
            caption = None
            if idx < len(captions_list):
                candidate_caption = captions_list[idx]
                if candidate_caption is not None:
                    stripped_caption = candidate_caption.strip()
                    caption = stripped_caption if stripped_caption else None
            gallery_entries.append({"url": gallery_url, "caption": caption})

    # Determine the author (admin can override)
    selected_author = current_user.username
    
    if author_username and author_username.strip():
        # Admin or moderator can assign to different author
        if current_user.role in ["admin", "moderator"]:
            # Verify the selected author exists and is an author/admin
            users_collection = db_client[db.db_name]["user"]
            target_author = users_collection.find_one({"username": author_username.strip()})
            
            if not target_author:
                raise HTTPException(
                    status_code=404,
                    detail=f"Author '{author_username}' not found"
                )
            
            if target_author["role"] not in ["author", "admin"]:
                raise HTTPException(
                    status_code=400,
                    detail=f"User '{author_username}' is not an author. Current role: {target_author['role']}"
                )
            
            selected_author = author_username.strip()
            logger.info(f"[create_news] Admin/Moderator {current_user.username} assigned article to author: {selected_author}")
        else:
            # Non-admin cannot override author
            logger.warning(f"[create_news] User {current_user.username} attempted to override author (not allowed)")
    
    # Fetch author details to embed in the news post
    author_details = _get_author_details(selected_author, db_client)
    
    news_data = {
        "title": title,
        "image_url": image_url,
        "content": content,
        "author_username": selected_author,
        "author_details": author_details,  # Embed full author profile
        "categories": categories,
        "tags": tags,
        "published": published,
        "scheduled_publish": scheduled_publish,
        "scheduled_at": scheduled_at_utc,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
        "views": 0,
        "viewed_ips": [],
        "likes": 0,
        "liked_ips": [],
        "content_images": gallery_entries,
    }

    inserted = db_client[db.db_name][NEWS_COLL].insert_one(news_data)
    news_id = str(inserted.inserted_id)
    news_data["_id"] = news_id

    # Calculate word count and reading time
    word_count = _calculate_word_count(content)
    reading_time = _calculate_reading_time(word_count)

    # Add SEO data after insertion (custom slug is required)
    seo_updates = {
        "slug": custom_slug,
        # Use override if provided, else auto-generate
        "meta_title": (meta_title_override.strip()[:60] if meta_title_override else title[:60]) if len(title) > 60 else (meta_title_override.strip() if meta_title_override else title),
        "meta_description": meta_description_override.strip()[:160] if meta_description_override else _extract_meta_description(content),
        "keywords": _extract_keywords(title, content, categories),
        # NEW SEO fields
        "focus_keyword": focus_keyword.strip() if focus_keyword else None,
        "image_alt": image_alt.strip() if image_alt else title,  # Default to title for accessibility
        "word_count": word_count,
        "reading_time_minutes": reading_time,
        "is_breaking_news": is_breaking_news,
        "is_opinion": is_opinion,
    }
    
    # Update the document with SEO data
    db_client[db.db_name][NEWS_COLL].update_one(
        {"_id": ObjectId(news_id)},
        {"$set": seo_updates}
    )
    
    # Add SEO data to response
    news_data.update(seo_updates)
    
    # Update author's article count if published
    if published:
        db_client[db.db_name]["user"].update_one(
            {"username": selected_author},
            {"$inc": {"articles_count": 1}}
        )

    # 🔔 Notify subscribers only if published
    if published and background_tasks is not None:
        # Old notification system (blogs/FCM)
        slug = _slugify(title)
        canonical_url = f"{NEWS_BASE_URL}/n/{news_id}-{slug}"
        background_tasks.add_task(_notify_new_blog_async, title, canonical_url, image_url)
        
        # Fresh news push notification system
        if broadcast_to_all_news_subscribers:
            news_url = f"{NEWS_BASE_URL}/news/{custom_slug}"
            summary_text = _extract_meta_description(content, max_length=120)
            background_tasks.add_task(
                broadcast_to_all_news_subscribers,
                title=title,
                body=summary_text,
                url=news_url,
                image=image_url,
                news_id=news_id,
            )
            logger.info(f"[news-push] Queued notification for news: {news_id}")

    return news_data


# ====================================================================================
# IMPORTANT: All static /news/* endpoints come BEFORE the dynamic /news/{news_id}
# ====================================================================================

# ------------------------- Read/list (PUBLIC) -------------------------
@news_router.get("/news", response_model=List[NewsPost], tags=["News"])
async def get_news(
    request: Request,
    published: Optional[bool] = Query(default=None),
    author_username: Optional[str] = Query(default=None),
    db_client: MongoClient = Depends(db.get_client),
):
    # Process scheduled posts before listing
    _process_scheduled_posts(db_client)
    
    query: Dict[str, Any] = {}
    if _should_force_published_only(request, published):
        query["published"] = True
    elif published is not None:
        query["published"] = published
    
    # Filter by author username
    if author_username:
        query["author_username"] = author_username

    docs = list(db_client[db.db_name][NEWS_COLL].find(query).sort("created_at", DESCENDING))
    return [_normalize_news(d, db_client) for d in docs]


@news_router.get("/news/scheduled", response_model=List[NewsPost], tags=["News"])
async def get_scheduled_news(
    current_user: User = Depends(get_current_user),
    db_client: MongoClient = Depends(db.get_client),
):
    """
    Get all scheduled posts (admin/author only).
    Returns posts with scheduled_publish=True, sorted by scheduled_at.
    """
    if current_user.role not in ["admin", "author"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    # Process scheduled posts first
    _process_scheduled_posts(db_client)
    
    query = {
        "scheduled_publish": True,
        "published": False
    }
    
    docs = list(db_client[db.db_name][NEWS_COLL].find(query).sort("scheduled_at", ASCENDING))
    return [_normalize_news(d, db_client) for d in docs]


@news_router.get("/news/stats", tags=["News"])
async def news_stats(db_client: MongoClient = Depends(db.get_client)):
    coll = db_client[db.db_name][NEWS_COLL]
    total = coll.count_documents({})
    published = coll.count_documents({"published": True})
    drafts = total - published

    agg = list(
        coll.aggregate(
            [{"$group": {"_id": None, "views": {"$sum": {"$ifNull": ["$views", 0]}},
                                   "likes": {"$sum": {"$ifNull": ["$likes", 0]}}}}]
        )
    )
    views = (agg[0]["views"] if agg else 0) or 0
    likes = (agg[0]["likes"] if agg else 0) or 0

    top_viewed = list(coll.find({}, {"title": 1, "views": 1}).sort([("views", -1)]).limit(5))
    top_liked = list(coll.find({}, {"title": 1, "likes": 1}).sort([("likes", -1)]).limit(5))
    for d in top_viewed: d["_id"] = str(d["_id"])
    for d in top_liked: d["_id"] = str(d["_id"])

    return {
        "total": total, "published": published, "drafts": drafts,
        "views": views, "likes": likes,
        "top_viewed": top_viewed, "top_liked": top_liked,
    }


# ==================== SEO STATISTICS ENDPOINTS ====================

@news_router.get("/news/seo-stats", tags=["News SEO Analytics"])
async def get_seo_stats(
    current_user: User = Depends(get_current_author_or_admin_user),
    db_client: MongoClient = Depends(db.get_client)
):
    """
    Get comprehensive SEO statistics for the news portal.
    
    Returns:
    - Overall SEO health score
    - Field completion rates
    - Content quality metrics
    - Top performing articles by SEO
    """
    coll = db_client[db.db_name][NEWS_COLL]
    
    # Total counts
    total_articles = coll.count_documents({})
    published_articles = coll.count_documents({"published": True})
    
    if total_articles == 0:
        return {
            "overall_health_score": 0,
            "total_articles": 0,
            "published_articles": 0,
            "seo_field_coverage": {},
            "content_quality": {},
            "article_types": {},
            "recommendations": ["No articles found. Start creating content!"]
        }
    
    # SEO field coverage
    has_slug = coll.count_documents({"slug": {"$exists": True, "$ne": None, "$ne": ""}})
    has_meta_title = coll.count_documents({"meta_title": {"$exists": True, "$ne": None, "$ne": ""}})
    has_meta_description = coll.count_documents({"meta_description": {"$exists": True, "$ne": None, "$ne": ""}})
    has_focus_keyword = coll.count_documents({"focus_keyword": {"$exists": True, "$ne": None, "$ne": ""}})
    has_image_alt = coll.count_documents({"image_alt": {"$exists": True, "$ne": None, "$ne": ""}})
    has_keywords = coll.count_documents({"keywords": {"$exists": True, "$ne": [], "$type": "array"}})
    
    # Article types
    breaking_news_count = coll.count_documents({"is_breaking_news": True})
    opinion_count = coll.count_documents({"is_opinion": True})
    
    # Content quality aggregation
    content_agg = list(coll.aggregate([
        {"$match": {"published": True}},
        {"$group": {
            "_id": None,
            "avg_word_count": {"$avg": {"$ifNull": ["$word_count", 0]}},
            "avg_reading_time": {"$avg": {"$ifNull": ["$reading_time_minutes", 0]}},
            "total_views": {"$sum": {"$ifNull": ["$views", 0]}},
            "total_likes": {"$sum": {"$ifNull": ["$likes", 0]}},
            "articles_with_word_count": {"$sum": {"$cond": [{"$gt": [{"$ifNull": ["$word_count", 0]}, 0]}, 1, 0]}}
        }}
    ]))
    
    content_stats = content_agg[0] if content_agg else {
        "avg_word_count": 0, 
        "avg_reading_time": 0, 
        "total_views": 0, 
        "total_likes": 0,
        "articles_with_word_count": 0
    }
    
    # Calculate SEO health score (0-100)
    slug_score = (has_slug / total_articles) * 20 if total_articles > 0 else 0
    meta_title_score = (has_meta_title / total_articles) * 20 if total_articles > 0 else 0
    meta_desc_score = (has_meta_description / total_articles) * 20 if total_articles > 0 else 0
    focus_kw_score = (has_focus_keyword / total_articles) * 20 if total_articles > 0 else 0
    image_alt_score = (has_image_alt / total_articles) * 20 if total_articles > 0 else 0
    
    overall_health_score = round(slug_score + meta_title_score + meta_desc_score + focus_kw_score + image_alt_score)
    
    # Generate recommendations
    recommendations = []
    if has_slug < total_articles:
        recommendations.append(f"{total_articles - has_slug} articles missing SEO-friendly slugs")
    if has_meta_title < total_articles:
        recommendations.append(f"{total_articles - has_meta_title} articles missing custom meta titles")
    if has_meta_description < total_articles:
        recommendations.append(f"{total_articles - has_meta_description} articles missing meta descriptions")
    if has_focus_keyword < total_articles:
        recommendations.append(f"{total_articles - has_focus_keyword} articles missing focus keywords")
    if has_image_alt < total_articles:
        recommendations.append(f"{total_articles - has_image_alt} articles missing image alt text")
    
    return {
        "overall_health_score": overall_health_score,
        "total_articles": total_articles,
        "published_articles": published_articles,
        "draft_articles": total_articles - published_articles,
        "seo_field_coverage": {
            "slug": {"count": has_slug, "percentage": round((has_slug / total_articles) * 100, 1)},
            "meta_title": {"count": has_meta_title, "percentage": round((has_meta_title / total_articles) * 100, 1)},
            "meta_description": {"count": has_meta_description, "percentage": round((has_meta_description / total_articles) * 100, 1)},
            "focus_keyword": {"count": has_focus_keyword, "percentage": round((has_focus_keyword / total_articles) * 100, 1)},
            "image_alt": {"count": has_image_alt, "percentage": round((has_image_alt / total_articles) * 100, 1)},
            "keywords_array": {"count": has_keywords, "percentage": round((has_keywords / total_articles) * 100, 1)},
        },
        "content_quality": {
            "avg_word_count": round(content_stats.get("avg_word_count", 0)),
            "avg_reading_time_minutes": round(content_stats.get("avg_reading_time", 0), 1),
            "articles_with_word_count": content_stats.get("articles_with_word_count", 0),
            "total_views": content_stats.get("total_views", 0),
            "total_likes": content_stats.get("total_likes", 0),
        },
        "article_types": {
            "breaking_news": breaking_news_count,
            "opinion_editorial": opinion_count,
            "regular": total_articles - breaking_news_count - opinion_count
        },
        "recommendations": recommendations if recommendations else ["All SEO fields are complete! Great job!"]
    }


@news_router.get("/news/seo-stats/articles-missing-seo", tags=["News SEO Analytics"])
async def get_articles_missing_seo(
    field: str = Query(..., description="SEO field to check: slug, meta_title, meta_description, focus_keyword, image_alt"),
    limit: int = Query(50, ge=1, le=200),
    current_user: User = Depends(get_current_author_or_admin_user),
    db_client: MongoClient = Depends(db.get_client)
):
    """
    Get list of articles missing a specific SEO field.
    
    Useful for bulk SEO optimization tasks.
    """
    field_mapping = {
        "slug": "slug",
        "meta_title": "meta_title",
        "meta_description": "meta_description",
        "focus_keyword": "focus_keyword",
        "image_alt": "image_alt"
    }
    
    if field not in field_mapping:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid field. Must be one of: {', '.join(field_mapping.keys())}"
        )
    
    db_field = field_mapping[field]
    coll = db_client[db.db_name][NEWS_COLL]
    
    # Find articles where field is missing, null, or empty
    query = {
        "$or": [
            {db_field: {"$exists": False}},
            {db_field: None},
            {db_field: ""}
        ]
    }
    
    articles = list(coll.find(
        query,
        {"title": 1, "slug": 1, "author_username": 1, "published": 1, "created_at": 1, "views": 1}
    ).sort("created_at", DESCENDING).limit(limit))
    
    for a in articles:
        a["_id"] = str(a["_id"])
    
    return {
        "field": field,
        "total_missing": coll.count_documents(query),
        "articles": articles
    }


@news_router.get("/news/seo-stats/keyword-analysis", tags=["News SEO Analytics"])
async def get_keyword_analysis(
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_author_or_admin_user),
    db_client: MongoClient = Depends(db.get_client)
):
    """
    Analyze keyword usage across all articles.
    
    Returns:
    - Most used keywords
    - Focus keyword frequency
    - Keyword distribution
    """
    coll = db_client[db.db_name][NEWS_COLL]
    
    # Most used auto-extracted keywords
    keyword_pipeline = [
        {"$match": {"keywords": {"$exists": True, "$type": "array"}}},
        {"$unwind": "$keywords"},
        {"$group": {"_id": "$keywords", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": limit}
    ]
    top_keywords = list(coll.aggregate(keyword_pipeline))
    
    # Focus keyword analysis
    focus_keyword_pipeline = [
        {"$match": {"focus_keyword": {"$exists": True, "$ne": None, "$ne": ""}}},
        {"$group": {"_id": "$focus_keyword", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": limit}
    ]
    top_focus_keywords = list(coll.aggregate(focus_keyword_pipeline))
    
    # Category distribution
    category_pipeline = [
        {"$match": {"categories": {"$exists": True, "$ne": None, "$ne": ""}}},
        {"$group": {"_id": "$categories", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}}
    ]
    category_distribution = list(coll.aggregate(category_pipeline))
    
    return {
        "top_keywords": [{"keyword": k["_id"], "count": k["count"]} for k in top_keywords],
        "top_focus_keywords": [{"keyword": k["_id"], "count": k["count"]} for k in top_focus_keywords],
        "category_distribution": [{"category": c["_id"], "count": c["count"]} for c in category_distribution],
        "total_unique_keywords": len(list(coll.aggregate([
            {"$match": {"keywords": {"$exists": True, "$type": "array"}}},
            {"$unwind": "$keywords"},
            {"$group": {"_id": "$keywords"}}
        ]))),
        "articles_with_focus_keyword": coll.count_documents({"focus_keyword": {"$exists": True, "$ne": None, "$ne": ""}})
    }


@news_router.get("/news/seo-stats/content-length-distribution", tags=["News SEO Analytics"])
async def get_content_length_distribution(
    current_user: User = Depends(get_current_author_or_admin_user),
    db_client: MongoClient = Depends(db.get_client)
):
    """
    Analyze content length distribution for SEO optimization.
    
    Google typically favors articles with 1000+ words for comprehensive topics.
    """
    coll = db_client[db.db_name][NEWS_COLL]
    
    # Word count buckets
    very_short = coll.count_documents({"word_count": {"$lt": 300}})  # < 300 words
    short = coll.count_documents({"word_count": {"$gte": 300, "$lt": 600}})  # 300-599
    medium = coll.count_documents({"word_count": {"$gte": 600, "$lt": 1000}})  # 600-999
    long_form = coll.count_documents({"word_count": {"$gte": 1000, "$lt": 2000}})  # 1000-1999
    very_long = coll.count_documents({"word_count": {"$gte": 2000}})  # 2000+
    no_word_count = coll.count_documents({"$or": [{"word_count": {"$exists": False}}, {"word_count": None}, {"word_count": 0}]})
    
    # Reading time distribution
    quick_read = coll.count_documents({"reading_time_minutes": {"$lte": 2}})
    medium_read = coll.count_documents({"reading_time_minutes": {"$gt": 2, "$lte": 5}})
    long_read = coll.count_documents({"reading_time_minutes": {"$gt": 5, "$lte": 10}})
    very_long_read = coll.count_documents({"reading_time_minutes": {"$gt": 10}})
    
    # Top longest articles
    longest_articles = list(coll.find(
        {"word_count": {"$exists": True, "$gt": 0}},
        {"title": 1, "slug": 1, "word_count": 1, "reading_time_minutes": 1, "views": 1}
    ).sort("word_count", DESCENDING).limit(10))
    
    for a in longest_articles:
        a["_id"] = str(a["_id"])
    
    # Shortest published articles (need optimization)
    shortest_published = list(coll.find(
        {"published": True, "word_count": {"$exists": True, "$gt": 0, "$lt": 300}},
        {"title": 1, "slug": 1, "word_count": 1, "views": 1}
    ).sort("word_count", ASCENDING).limit(10))
    
    for a in shortest_published:
        a["_id"] = str(a["_id"])
    
    return {
        "word_count_distribution": {
            "very_short_under_300": {"count": very_short, "label": "< 300 words (needs improvement)"},
            "short_300_599": {"count": short, "label": "300-599 words (brief)"},
            "medium_600_999": {"count": medium, "label": "600-999 words (good)"},
            "long_1000_1999": {"count": long_form, "label": "1000-1999 words (excellent)"},
            "very_long_2000_plus": {"count": very_long, "label": "2000+ words (comprehensive)"},
            "no_word_count": {"count": no_word_count, "label": "Word count not calculated"}
        },
        "reading_time_distribution": {
            "quick_read_under_2min": quick_read,
            "medium_read_2_5min": medium_read,
            "long_read_5_10min": long_read,
            "very_long_read_over_10min": very_long_read
        },
        "longest_articles": longest_articles,
        "shortest_published_articles": shortest_published,
        "recommendation": "For SEO, aim for 600+ words per article. Long-form content (1000+) typically ranks better."
    }


@news_router.get("/news/seo-stats/performance-by-seo", tags=["News SEO Analytics"])
async def get_performance_by_seo(
    current_user: User = Depends(get_current_author_or_admin_user),
    db_client: MongoClient = Depends(db.get_client)
):
    """
    Compare performance (views, likes) between articles with complete SEO vs incomplete SEO.
    
    Helps demonstrate the value of SEO optimization.
    """
    coll = db_client[db.db_name][NEWS_COLL]
    
    # Define "complete SEO" as having all key fields
    complete_seo_query = {
        "published": True,
        "slug": {"$exists": True, "$ne": None, "$ne": ""},
        "meta_title": {"$exists": True, "$ne": None, "$ne": ""},
        "meta_description": {"$exists": True, "$ne": None, "$ne": ""},
        "focus_keyword": {"$exists": True, "$ne": None, "$ne": ""},
        "image_alt": {"$exists": True, "$ne": None, "$ne": ""}
    }
    
    incomplete_seo_query = {
        "published": True,
        "$or": [
            {"slug": {"$exists": False}},
            {"slug": None},
            {"slug": ""},
            {"meta_title": {"$exists": False}},
            {"meta_title": None},
            {"meta_description": {"$exists": False}},
            {"meta_description": None},
            {"focus_keyword": {"$exists": False}},
            {"focus_keyword": None},
            {"image_alt": {"$exists": False}},
            {"image_alt": None}
        ]
    }
    
    # Aggregate stats for complete SEO articles
    complete_stats = list(coll.aggregate([
        {"$match": complete_seo_query},
        {"$group": {
            "_id": None,
            "count": {"$sum": 1},
            "total_views": {"$sum": {"$ifNull": ["$views", 0]}},
            "total_likes": {"$sum": {"$ifNull": ["$likes", 0]}},
            "avg_views": {"$avg": {"$ifNull": ["$views", 0]}},
            "avg_likes": {"$avg": {"$ifNull": ["$likes", 0]}}
        }}
    ]))
    
    # Aggregate stats for incomplete SEO articles
    incomplete_stats = list(coll.aggregate([
        {"$match": incomplete_seo_query},
        {"$group": {
            "_id": None,
            "count": {"$sum": 1},
            "total_views": {"$sum": {"$ifNull": ["$views", 0]}},
            "total_likes": {"$sum": {"$ifNull": ["$likes", 0]}},
            "avg_views": {"$avg": {"$ifNull": ["$views", 0]}},
            "avg_likes": {"$avg": {"$ifNull": ["$likes", 0]}}
        }}
    ]))
    
    complete = complete_stats[0] if complete_stats else {"count": 0, "total_views": 0, "total_likes": 0, "avg_views": 0, "avg_likes": 0}
    incomplete = incomplete_stats[0] if incomplete_stats else {"count": 0, "total_views": 0, "total_likes": 0, "avg_views": 0, "avg_likes": 0}
    
    # Top performing articles with complete SEO
    top_seo_articles = list(coll.find(
        complete_seo_query,
        {"title": 1, "slug": 1, "views": 1, "likes": 1, "focus_keyword": 1}
    ).sort("views", DESCENDING).limit(10))
    
    for a in top_seo_articles:
        a["_id"] = str(a["_id"])
    
    return {
        "complete_seo_articles": {
            "count": complete.get("count", 0),
            "total_views": complete.get("total_views", 0),
            "total_likes": complete.get("total_likes", 0),
            "avg_views_per_article": round(complete.get("avg_views", 0), 1),
            "avg_likes_per_article": round(complete.get("avg_likes", 0), 1)
        },
        "incomplete_seo_articles": {
            "count": incomplete.get("count", 0),
            "total_views": incomplete.get("total_views", 0),
            "total_likes": incomplete.get("total_likes", 0),
            "avg_views_per_article": round(incomplete.get("avg_views", 0), 1),
            "avg_likes_per_article": round(incomplete.get("avg_likes", 0), 1)
        },
        "performance_difference": {
            "views_difference_percent": round(
                ((complete.get("avg_views", 0) - incomplete.get("avg_views", 0)) / max(incomplete.get("avg_views", 1), 1)) * 100, 1
            ) if incomplete.get("avg_views", 0) > 0 else 0,
            "likes_difference_percent": round(
                ((complete.get("avg_likes", 0) - incomplete.get("avg_likes", 0)) / max(incomplete.get("avg_likes", 1), 1)) * 100, 1
            ) if incomplete.get("avg_likes", 0) > 0 else 0
        },
        "top_performing_seo_articles": top_seo_articles,
        "insight": "Articles with complete SEO tend to perform better in search rankings and engagement."
    }


@news_router.get("/news/seo-stats/author-seo-scores", tags=["News SEO Analytics"])
async def get_author_seo_scores(
    current_user: User = Depends(get_current_author_or_admin_user),
    db_client: MongoClient = Depends(db.get_client)
):
    """
    Get SEO completion scores by author.
    
    Useful for identifying which authors need SEO training.
    """
    coll = db_client[db.db_name][NEWS_COLL]
    
    # Aggregate by author
    author_pipeline = [
        {"$group": {
            "_id": "$author_username",
            "total_articles": {"$sum": 1},
            "published": {"$sum": {"$cond": ["$published", 1, 0]}},
            "has_slug": {"$sum": {"$cond": [{"$and": [{"$ne": ["$slug", None]}, {"$ne": ["$slug", ""]}]}, 1, 0]}},
            "has_meta_title": {"$sum": {"$cond": [{"$and": [{"$ne": ["$meta_title", None]}, {"$ne": ["$meta_title", ""]}]}, 1, 0]}},
            "has_meta_desc": {"$sum": {"$cond": [{"$and": [{"$ne": ["$meta_description", None]}, {"$ne": ["$meta_description", ""]}]}, 1, 0]}},
            "has_focus_kw": {"$sum": {"$cond": [{"$and": [{"$ne": ["$focus_keyword", None]}, {"$ne": ["$focus_keyword", ""]}]}, 1, 0]}},
            "has_image_alt": {"$sum": {"$cond": [{"$and": [{"$ne": ["$image_alt", None]}, {"$ne": ["$image_alt", ""]}]}, 1, 0]}},
            "total_views": {"$sum": {"$ifNull": ["$views", 0]}},
            "total_likes": {"$sum": {"$ifNull": ["$likes", 0]}},
            "avg_word_count": {"$avg": {"$ifNull": ["$word_count", 0]}}
        }},
        {"$sort": {"total_articles": -1}}
    ]
    
    author_stats = list(coll.aggregate(author_pipeline))
    
    # Calculate SEO score for each author
    author_scores = []
    for author in author_stats:
        if not author["_id"]:
            continue
        
        total = author["total_articles"]
        if total == 0:
            continue
        
        # Calculate completion rate for each field (0-20 points each, total 100)
        slug_rate = (author["has_slug"] / total) * 20
        title_rate = (author["has_meta_title"] / total) * 20
        desc_rate = (author["has_meta_desc"] / total) * 20
        focus_rate = (author["has_focus_kw"] / total) * 20
        alt_rate = (author["has_image_alt"] / total) * 20
        
        seo_score = round(slug_rate + title_rate + desc_rate + focus_rate + alt_rate)
        
        author_scores.append({
            "author_username": author["_id"],
            "total_articles": total,
            "published_articles": author["published"],
            "seo_score": seo_score,
            "field_completion": {
                "slug": {"count": author["has_slug"], "percentage": round((author["has_slug"] / total) * 100, 1)},
                "meta_title": {"count": author["has_meta_title"], "percentage": round((author["has_meta_title"] / total) * 100, 1)},
                "meta_description": {"count": author["has_meta_desc"], "percentage": round((author["has_meta_desc"] / total) * 100, 1)},
                "focus_keyword": {"count": author["has_focus_kw"], "percentage": round((author["has_focus_kw"] / total) * 100, 1)},
                "image_alt": {"count": author["has_image_alt"], "percentage": round((author["has_image_alt"] / total) * 100, 1)}
            },
            "engagement": {
                "total_views": author["total_views"],
                "total_likes": author["total_likes"],
                "avg_word_count": round(author["avg_word_count"])
            }
        })
    
    # Sort by SEO score
    author_scores.sort(key=lambda x: x["seo_score"], reverse=True)
    
    return {
        "total_authors": len(author_scores),
        "author_seo_scores": author_scores,
        "top_seo_authors": author_scores[:5] if len(author_scores) >= 5 else author_scores,
        "needs_improvement": [a for a in author_scores if a["seo_score"] < 60]
    }


@news_router.get("/news/seo-stats/daily-trends", tags=["News SEO Analytics"])
async def get_seo_daily_trends(
    days: int = Query(30, ge=7, le=90, description="Number of days to analyze"),
    current_user: User = Depends(get_current_author_or_admin_user),
    db_client: MongoClient = Depends(db.get_client)
):
    """
    Get daily SEO trends over time.
    
    Tracks improvement in SEO adoption over the specified period.
    """
    coll = db_client[db.db_name][NEWS_COLL]
    
    from_date = datetime.utcnow() - timedelta(days=days)
    
    # Daily article creation with SEO fields
    daily_pipeline = [
        {"$match": {"created_at": {"$gte": from_date}}},
        {"$group": {
            "_id": {
                "$dateToString": {"format": "%Y-%m-%d", "date": "$created_at"}
            },
            "total": {"$sum": 1},
            "with_slug": {"$sum": {"$cond": [{"$and": [{"$ne": ["$slug", None]}, {"$ne": ["$slug", ""]}]}, 1, 0]}},
            "with_focus_keyword": {"$sum": {"$cond": [{"$and": [{"$ne": ["$focus_keyword", None]}, {"$ne": ["$focus_keyword", ""]}]}, 1, 0]}},
            "with_meta_title": {"$sum": {"$cond": [{"$and": [{"$ne": ["$meta_title", None]}, {"$ne": ["$meta_title", ""]}]}, 1, 0]}},
            "with_image_alt": {"$sum": {"$cond": [{"$and": [{"$ne": ["$image_alt", None]}, {"$ne": ["$image_alt", ""]}]}, 1, 0]}},
            "total_views": {"$sum": {"$ifNull": ["$views", 0]}},
            "avg_word_count": {"$avg": {"$ifNull": ["$word_count", 0]}}
        }},
        {"$sort": {"_id": 1}}
    ]
    
    daily_data = list(coll.aggregate(daily_pipeline))
    
    # Calculate trends
    trends = []
    for day in daily_data:
        total = day["total"]
        seo_completion = 0
        if total > 0:
            seo_completion = round(
                ((day["with_slug"] + day["with_focus_keyword"] + day["with_meta_title"] + day["with_image_alt"]) / (total * 4)) * 100, 1
            )
        
        trends.append({
            "date": day["_id"],
            "articles_created": total,
            "seo_completion_rate": seo_completion,
            "with_slug": day["with_slug"],
            "with_focus_keyword": day["with_focus_keyword"],
            "with_meta_title": day["with_meta_title"],
            "with_image_alt": day["with_image_alt"],
            "total_views": day["total_views"],
            "avg_word_count": round(day["avg_word_count"])
        })
    
    return {
        "period_days": days,
        "from_date": from_date.strftime("%Y-%m-%d"),
        "to_date": datetime.utcnow().strftime("%Y-%m-%d"),
        "total_articles_in_period": sum(d["articles_created"] for d in trends),
        "daily_trends": trends,
        "overall_trend": "improving" if len(trends) >= 2 and trends[-1]["seo_completion_rate"] > trends[0]["seo_completion_rate"] else "needs attention"
    }


# ------------------------- Filters (PUBLIC) -------------------------
@news_router.get("/news/filter", response_model=List[NewsPost], tags=["News"])
async def get_news_by_category_and_tags(
    request: Request,
    category: Optional[str] = None,
    tag: Optional[str] = None,
    published: Optional[bool] = Query(default=None),
    db_client: MongoClient = Depends(db.get_client),
):
    # Process scheduled posts before filtering
    _process_scheduled_posts(db_client)
    
    query: Dict[str, Any] = {}
    if category:
        query["categories"] = category
    if tag:
        query["tags"] = tag

    if _should_force_published_only(request, published):
        query["published"] = True
    elif published is not None:
        query["published"] = published

    docs = list(db_client[db.db_name][NEWS_COLL].find(query).sort("created_at", DESCENDING))
    return [_normalize_news(d, db_client) for d in docs]


@news_router.get("/news/tags", response_model=List[str], tags=["News"])
async def get_all_tags(db_client: MongoClient = Depends(db.get_client)):
    """
    Robust tag list: supports array or single-string 'tags' and ignores null/empty.
    """
    pipeline = [
        {"$addFields": {
            "tags": {
                "$cond": [
                    {"$isArray": "$tags"},
                    "$tags",
                    {"$cond": [
                        {"$and": [{"$ne": ["$tags", None]}, {"$ne": ["$tags", ""]}]},
                        ["$tags"],
                        []
                    ]}
                ]
            }
        }},
        {"$unwind": "$tags"},
        {"$group": {"_id": "$tags"}},
        {"$sort": {"_id": 1}},
    ]
    rows = db_client[db.db_name][NEWS_COLL].aggregate(pipeline)
    return [r["_id"] for r in rows]


@news_router.get("/news/category/{category_name}", response_model=List[NewsPost], tags=["News"])
async def get_news_by_category(
    request: Request,
    category_name: str,
    published: Optional[bool] = Query(default=None),
    db_client: MongoClient = Depends(db.get_client),
):
    query: Dict[str, Any] = {"categories": category_name}
    if _should_force_published_only(request, published):
        query["published"] = True
    elif published is not None:
        query["published"] = published

    docs = list(db_client[db.db_name][NEWS_COLL].find(query).sort("created_at", DESCENDING))
    if not docs:
        raise HTTPException(status_code=404, detail="No news found for this category")
    return [_normalize_news(d, db_client) for d in docs]


@news_router.get("/news/tags/{tag}", response_model=List[NewsPost], tags=["News"])
async def get_news_by_tag(
    request: Request,
    tag: str,
    published: Optional[bool] = Query(default=None),
    db_client: MongoClient = Depends(db.get_client),
):
    query: Dict[str, Any] = {"tags": tag}
    if _should_force_published_only(request, published):
        query["published"] = True
    elif published is not None:
        query["published"] = published

    docs = list(db_client[db.db_name][NEWS_COLL].find(query).sort("created_at", DESCENDING))
    return [_normalize_news(d, db_client) for d in docs]


# ------------------------- Search & Suggest (PUBLIC) -------------------------
_TEXT_INDEX_NAME = "news_text_idx"


def _ensure_text_index(db_client: MongoClient):
    coll = db_client[db.db_name][NEWS_COLL]
    try:
        coll.create_index(
            [
                ("title", "text"),
                ("content", "text"),
                ("tags", "text"),
                ("categories", "text"),
            ],
            name=_TEXT_INDEX_NAME,
            default_language="english",
        )
    except Exception as e:
        logger.debug(f"text index create skipped: {e}")


@news_router.get("/news/search", response_model=List[NewsPost], tags=["News"])
async def search_news(
    request: Request,
    q: str = Query(..., min_length=1),
    published: Optional[bool] = Query(default=None),
    limit: int = Query(20, ge=1, le=100),
    db_client: MongoClient = Depends(db.get_client),
):
    _ensure_text_index(db_client)

    base: Dict[str, Any] = {}
    if _should_force_published_only(request, published):
        base["published"] = True
    elif published is not None:
        base["published"] = published

    coll = db_client[db.db_name][NEWS_COLL]

    # Try text search first
    try:
        cursor = coll.find({"$text": {"$search": q}, **base}, {"score": {"$meta": "textScore"}})
        docs = list(cursor.sort([("score", {"$meta": "textScore"})]).limit(limit))
    except Exception:
        docs = []

    # Fallback: case-insensitive regex across fields (OR)
    if not docs:
        regex = re.compile(re.escape(q), re.IGNORECASE)
        docs = list(
            coll.find(
                {
                    **base,
                    "$or": [
                        {"title": regex},
                        {"content": regex},
                        {"tags": regex},
                        {"categories": regex},
                    ],
                }
            )
            .sort("created_at", DESCENDING)
            .limit(limit)
        )

    return [_normalize_news(d, db_client) for d in docs]


@news_router.get("/news/suggest", response_model=List[Dict[str, str]], tags=["News"])
async def suggest_news(
    request: Request,
    q: str = Query(..., min_length=1),
    limit: int = Query(8, ge=1, le=20),
    db_client: MongoClient = Depends(db.get_client),
):
    base: Dict[str, Any] = {}
    if _should_force_published_only(request, None):
        base["published"] = True

    regex = re.compile(re.escape(q), re.IGNORECASE)
    coll = db_client[db.db_name][NEWS_COLL]
    docs = list(
        coll.find(
            {
                **base,
                "$or": [
                    {"title": {"$regex": regex}},
                    {"tags": {"$regex": regex}},
                    {"categories": {"$regex": regex}},
                ],
            },
            {"title": 1},
        )
        .sort("created_at", DESCENDING)
        .limit(limit)
    )
    return [{"_id": str(d["_id"]), "title": d.get("title", "")} for d in docs]


# ------------------------- Related posts (PUBLIC) -------------------------
@news_router.get("/news/{news_id}/related", response_model=List[NewsPost], tags=["News"])
async def related_news(
    news_id: str,
    limit: int = Query(5, ge=1, le=10),
    db_client: MongoClient = Depends(db.get_client),
):
    if not ObjectId.is_valid(news_id):
        raise HTTPException(status_code=404, detail="News not found")
    me = db_client[db.db_name][NEWS_COLL].find_one({"_id": ObjectId(news_id)})
    if not me:
        raise HTTPException(status_code=404, detail="News not found")

    tags = me.get("tags", [])
    cat = me.get("categories")
    q: Dict[str, Any] = {"_id": {"$ne": me["_id"]}}
    ors = []
    if tags:
        ors.append({"tags": {"$in": tags}})
    if cat:
        ors.append({"categories": cat})
    if ors:
        q["$or"] = ors

    docs = list(
        db_client[db.db_name][NEWS_COLL]
        .find(q)
        .sort("created_at", DESCENDING)
        .limit(limit)
    )
    return [_normalize_news(d, db_client) for d in docs]


# ------------------------- Views & Likes (PUBLIC) -------------------------
@news_router.post("/news/{news_id}/views", response_model=dict, tags=["News"])
async def increment_news_views(
    news_id: str,
    request: Request,
    db_client: MongoClient = Depends(db.get_client),
):
    if not ObjectId.is_valid(news_id):
        raise HTTPException(status_code=404, detail="News not found")
    doc = db_client[db.db_name][NEWS_COLL].find_one({"_id": ObjectId(news_id)})
    if not doc:
        raise HTTPException(status_code=404, detail="News not found")

    client_ip = request.headers.get("X-Forwarded-For", request.client.host)
    if client_ip and "," in client_ip:
        client_ip = client_ip.split(",")[0].strip()
    if not client_ip:
        logger.warning("No valid client IP detected for views")
        client_ip = "unknown"

    viewed_ips = doc.get("viewed_ips", [])
    current_views = doc.get("views", 0)

    if client_ip not in viewed_ips:
        viewed_ips.append(client_ip)
        current_views += 1
        db_client[db.db_name][NEWS_COLL].update_one(
            {"_id": ObjectId(news_id)},
            {"$set": {"viewed_ips": viewed_ips, "views": current_views}},
        )

    return {"views": current_views}


@news_router.post("/news/{news_id}/likes", response_model=dict, tags=["News"])
async def increment_news_likes(
    news_id: str,
    request: Request,
    db_client: MongoClient = Depends(db.get_client),
):
    if not ObjectId.is_valid(news_id):
        raise HTTPException(status_code=404, detail="News not found")
    doc = db_client[db.db_name][NEWS_COLL].find_one({"_id": ObjectId(news_id)})
    if not doc:
        raise HTTPException(status_code=404, detail="News not found")

    client_ip = request.headers.get("X-Forwarded-For", request.client.host)
    if client_ip and "," in client_ip:
        client_ip = client_ip.split(",")[0].strip()
    if not client_ip:
        logger.warning("No valid client IP detected for likes")
        client_ip = "unknown"

    liked_ips = doc.get("liked_ips", [])
    current_likes = doc.get("likes", 0)

    if client_ip not in liked_ips:
        liked_ips.append(client_ip)
        current_likes += 1
        db_client[db.db_name][NEWS_COLL].update_one(
            {"_id": ObjectId(news_id)},
            {"$set": {"liked_ips": liked_ips, "likes": current_likes}},
        )

    return {"likes": current_likes}


# ------------------------- Comments (PUBLIC read, protected write) -------------------------
@news_router.get("/news/{news_id}/comments", response_model=List[Comment], tags=["News"])
async def list_comments_for_news(news_id: str, db_client: MongoClient = Depends(db.get_client)):
    comments = list(
        db_client[db.db_name][NEWS_COMMENTS_COLL]
        .find({"news_id": news_id})
        .sort("created_at", DESCENDING)
    )
    for c in comments:
        c["_id"] = str(c["_id"])
        if "phone" in c and c["phone"] is not None:
            try:
                c["phone"] = str(c["phone"]).strip()
            except Exception:
                c["phone"] = None
    return comments


class CommentCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=80)
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    content: str = Field(..., min_length=1, max_length=5000)

# ------------------------- Comments (PUBLIC create) -------------------------
# ------------------------- Comments (PUBLIC create) -------------------------
@news_router.post("/news/{news_id}/comments", response_model=Comment, tags=["News"])
async def create_comment_for_news(
    news_id: str,
    payload: CommentCreate = Body(...),
    db_client: MongoClient = Depends(db.get_client),
):
    # verify news exists (news collection uses ObjectId)
    if not ObjectId.is_valid(news_id):
        raise HTTPException(status_code=404, detail="News not found")
    if not db_client[db.db_name][NEWS_COLL].find_one({"_id": ObjectId(news_id)}):
        raise HTTPException(status_code=404, detail="News not found")

    # persist comment into the dedicated news comments collection
    doc = {
        "news_id": news_id,
        "name": payload.name.strip(),
        "email": (payload.email or None),
        # Store phone as string (some UIs may send numeric values)
        "phone": str(payload.phone).strip() if payload.phone is not None else None,
        "content": payload.content.strip(),
        "created_at": datetime.utcnow(),
    }

    res = db_client[db.db_name][NEWS_COMMENTS_COLL].insert_one(doc)
    doc["_id"] = str(res.inserted_id)
    return doc


@news_router.put("/news/comments/{comment_id}", response_model=Comment, tags=["News"])
async def update_comment(
    comment_id: str,
    payload: Comment,
    current_user: User = Depends(get_current_author_or_admin_user),
    db_client: MongoClient = Depends(db.get_client),
):
    if not ObjectId.is_valid(comment_id):
        raise HTTPException(status_code=404, detail="Comment not found")
    existing = db_client[db.db_name][NEWS_COMMENTS_COLL].find_one({"_id": ObjectId(comment_id)})
    if not existing:
        raise HTTPException(status_code=404, detail="Comment not found")

    # block changing identity/news linkage/created_at
    update_doc = payload.dict(by_alias=True, exclude={"id", "_id", "news_id", "created_at"})
    db_client[db.db_name][NEWS_COMMENTS_COLL].update_one(
        {"_id": ObjectId(comment_id)},
        {"$set": update_doc},
    )
    updated = db_client[db.db_name][NEWS_COMMENTS_COLL].find_one({"_id": ObjectId(comment_id)})
    updated["_id"] = str(updated["_id"])
    return updated


@news_router.delete("/news/comments/{comment_id}", tags=["News"])
async def delete_comment(
    comment_id: str,
    current_user: User = Depends(get_current_author_or_admin_user),
    db_client: MongoClient = Depends(db.get_client),
):
    if not ObjectId.is_valid(comment_id):
        raise HTTPException(status_code=404, detail="Comment not found")
    existing = db_client[db.db_name][NEWS_COMMENTS_COLL].find_one({"_id": ObjectId(comment_id)})
    if not existing:
        raise HTTPException(status_code=404, detail="Comment not found")
    db_client[db.db_name][NEWS_COMMENTS_COLL].delete_one({"_id": ObjectId(comment_id)})
    return {"message": "Comment deleted successfully"}


# ------------------------- SINGLE news (PUBLIC) -------------------------
@news_router.get("/news/{news_id}", response_model=NewsPost, tags=["News"])
async def get_news_item(news_id: str, db_client: MongoClient = Depends(db.get_client)):
    if not ObjectId.is_valid(news_id):
        raise HTTPException(status_code=404, detail="News not found")
    doc = db_client[db.db_name][NEWS_COLL].find_one({"_id": ObjectId(news_id)})
    if not doc:
        raise HTTPException(status_code=404, detail="News not found")
    return _normalize_news(doc, db_client)


class ExistingContentImage(BaseModel):
    """Represents an already-uploaded content image when editing a news post.

    This lets the UI keep or update captions for existing images without re-uploading files.
    """
    url: str
    caption: Optional[str] = None


@news_router.put("/news/{news_id}", response_model=NewsPost, tags=["News"])
async def update_news(
    request: Request,
    news_id: str,
    # core editable fields
    title: Optional[str] = Form(None),
    content: Optional[str] = Form(None),
    categories: Optional[str] = Form(None),
    published: Optional[bool] = Form(None),
    custom_slug: Optional[str] = Form(None),
    scheduled_publish: Optional[bool] = Form(None),
    scheduled_at: Optional[str] = Form(None),
    author_username: Optional[str] = Form(None),  # Admin can change author
    # existing gallery items coming back from UI as JSON string
    existing_content_images: Optional[str] = Form(None),
    # SEO fields (NEW - for editing existing posts)
    focus_keyword: Optional[str] = Form(None),          # Primary SEO keyword
    meta_title_override: Optional[str] = Form(None),    # Custom meta title (max 60 chars)
    meta_description_override: Optional[str] = Form(None),  # Custom description (max 160 chars)
    image_alt: Optional[str] = Form(None),              # Alt text for featured image
    is_breaking_news: Optional[bool] = Form(None),      # Breaking news flag
    is_opinion: Optional[bool] = Form(None),            # Opinion/Editorial flag
    current_user: User = Depends(get_current_author_or_admin_user),
    db_client: MongoClient = Depends(db.get_client),
):
    """Update a news post including optional gallery updates.

    - Feature image field (`file`) is intentionally NOT handled here to avoid
      breaking the existing, stable feature-image flow.
    - Supports keeping old gallery items (via `existing_content_images` JSON)
      and appending new uploads (`content_images` + `content_image_captions`).
    - All fields are optional; only provided values are updated.
    """

    # Parse form data manually to handle multiple files/tags with same name
    form = await request.form()
    
    # Extract tags as list
    tags: List[str] = []
    content_images_files: List[UploadFile] = []
    content_image_captions_list: List[str] = []
    
    for key, value in form.multi_items():
        if key == "tags":
            tags.append(str(value))
        elif key == "content_images" and hasattr(value, "file"):
            content_images_files.append(value)
        elif key == "content_image_captions":
            content_image_captions_list.append(str(value) if value else "")
    
    # Debug logging for incoming multipart payload
    try:
        logger.info(
            "[update_news] Incoming request: news_id=%s title=%r categories=%r tags=%r "
            "published=%r existing_content_images_len=%s new_content_images_count=%s custom_slug=%r",
            news_id,
            title,
            categories,
            tags,
            published,
            len(existing_content_images) if isinstance(existing_content_images, str) else None,
            len(content_images_files),
            custom_slug,
        )
    except Exception as log_exc:
        logger.warning("[update_news] Failed to log request metadata: %s", log_exc)

    if not ObjectId.is_valid(news_id):
        raise HTTPException(status_code=404, detail="News not found")
    
    # Validate custom slug if provided (optional in update)
    if custom_slug:
        custom_slug = custom_slug.strip()
        if not custom_slug:
            raise HTTPException(
                status_code=400,
                detail="custom_slug cannot be empty. Provide a valid slug or omit the field."
            )
        # Basic slug validation
        if not re.match(r'^[a-z0-9]+(?:-[a-z0-9]+)*$', custom_slug):
            raise HTTPException(
                status_code=400,
                detail="Slug must contain only lowercase letters, numbers, and hyphens (no spaces or special characters)"
            )
        # Check uniqueness (excluding current post)
        _validate_slug_uniqueness(custom_slug, news_id, db_client)

    coll = db_client[db.db_name][NEWS_COLL]
    existing = coll.find_one({"_id": ObjectId(news_id)})
    if not existing:
        raise HTTPException(status_code=404, detail="News not found")

    update_doc: Dict[str, Any] = {}

    if title is not None:
        update_doc["title"] = title
    if content is not None:
        update_doc["content"] = content
    if categories is not None:
        update_doc["categories"] = categories
    if tags is not None:
        update_doc["tags"] = tags
    if published is not None:
        update_doc["published"] = published
    if custom_slug is not None:
        update_doc["slug"] = custom_slug
    
    # Handle author change (admin/moderator only)
    if author_username and author_username.strip():
        if current_user.role in ["admin", "moderator"]:
            # Verify the selected author exists and has appropriate role
            users_collection = db_client[db.db_name]["user"]
            target_author = users_collection.find_one({"username": author_username.strip()})
            
            if not target_author:
                raise HTTPException(
                    status_code=404,
                    detail=f"Author '{author_username}' not found"
                )
            
            if target_author["role"] not in ["author", "admin"]:
                raise HTTPException(
                    status_code=400,
                    detail=f"User '{author_username}' is not an author. Current role: {target_author['role']}"
                )
            
            old_author = existing.get("author_username")
            new_author = author_username.strip()
            
            # Update author username and details
            update_doc["author_username"] = new_author
            author_details = _get_author_details(new_author, db_client)
            if author_details:
                update_doc["author_details"] = author_details
            
            # Update article counts if published
            if existing.get("published", False):
                # Decrement old author's count
                if old_author:
                    users_collection.update_one(
                        {"username": old_author},
                        {"$inc": {"articles_count": -1}}
                    )
                # Increment new author's count
                users_collection.update_one(
                    {"username": new_author},
                    {"$inc": {"articles_count": 1}}
                )
            
            logger.info(f"[update_news] Admin/Moderator {current_user.username} changed author from {old_author} to {new_author}")
        else:
            logger.warning(f"[update_news] User {current_user.username} attempted to change author (not allowed)")
    
    # Handle scheduling updates
    if scheduled_publish is not None:
        if scheduled_publish:
            # Enabling scheduling
            if not scheduled_at:
                raise HTTPException(
                    status_code=400,
                    detail="scheduled_at is required when enabling scheduled_publish. Format: YYYY-MM-DDTHH:MM (IST)"
                )
            
            # Parse and validate
            scheduled_at_utc = _parse_ist_datetime(scheduled_at)
            current_utc = datetime.utcnow()
            
            if scheduled_at_utc <= current_utc:
                current_ist = _utc_to_ist(current_utc)
                raise HTTPException(
                    status_code=400,
                    detail=f"Scheduled time must be in the future. Current IST: {current_ist.strftime('%Y-%m-%d %H:%M')}"
                )
            
            update_doc["scheduled_publish"] = True
            update_doc["scheduled_at"] = scheduled_at_utc
            # Auto-unpublish when scheduling
            update_doc["published"] = False
            logger.info(f"[update_news] Rescheduling post {news_id} for {scheduled_at} IST")
        else:
            # Disabling scheduling
            update_doc["scheduled_publish"] = False
            update_doc["scheduled_at"] = None
            logger.info(f"[update_news] Removed scheduling for post {news_id}")
    elif scheduled_at is not None:
        # Only scheduled_at provided, check if post is already in scheduled mode
        if existing.get("scheduled_publish", False):
            scheduled_at_utc = _parse_ist_datetime(scheduled_at)
            current_utc = datetime.utcnow()
            
            if scheduled_at_utc <= current_utc:
                current_ist = _utc_to_ist(current_utc)
                raise HTTPException(
                    status_code=400,
                    detail=f"Scheduled time must be in the future. Current IST: {current_ist.strftime('%Y-%m-%d %H:%M')}"
                )
            
            update_doc["scheduled_at"] = scheduled_at_utc
            logger.info(f"[update_news] Updated schedule time for post {news_id} to {scheduled_at} IST")

    # --- handle gallery: existing + new uploads ---
    merged_gallery: List[Dict[str, Optional[str]]] = []

    # 1) existing gallery from DB (fallback if UI doesn't send anything)
    if existing_content_images is None:
        raw_existing = existing.get("content_images") or []
        for entry in raw_existing:
            if isinstance(entry, dict):
                url = entry.get("url")
                caption = entry.get("caption")
            elif isinstance(entry, str):
                url = entry
                caption = None
            else:
                continue
            if not url:
                continue
            merged_gallery.append({"url": url, "caption": caption or None})
    else:
        # UI can send JSON string array of {url, caption}
        try:
            import json

            parsed = json.loads(existing_content_images) or []
            for entry in parsed:
                if not isinstance(entry, dict):
                    continue
                url = entry.get("url")
                if not url:
                    continue
                caption_val = entry.get("caption")
                if isinstance(caption_val, str):
                    caption_val = caption_val.strip() or None
                merged_gallery.append({"url": url, "caption": caption_val})
        except Exception:
            # If JSON parsing fails, fall back to stored DB gallery
            raw_existing = existing.get("content_images") or []
            for entry in raw_existing:
                if isinstance(entry, dict):
                    url = entry.get("url")
                    caption = entry.get("caption")
                elif isinstance(entry, str):
                    url = entry
                    caption = None
                else:
                    continue
                if not url:
                    continue
                merged_gallery.append({"url": url, "caption": caption or None})

    # 2) append newly uploaded images (if any)
    if content_images_files:
        for idx, gallery_file in enumerate(content_images_files):
            if not gallery_file or not getattr(gallery_file, "file", None):
                continue

            file_extension = (gallery_file.filename or "image").split(".")[-1]
            gallery_key = f"news/content/{uuid.uuid4()}.{file_extension}"
            content_type = gallery_file.content_type or "application/octet-stream"
            try:
                s3_client.upload_fileobj(
                    gallery_file.file,
                    AWS_BUCKET_NAME,
                    gallery_key,
                    ExtraArgs={"ContentType": content_type},
                )
            except Exception as exc:
                raise HTTPException(status_code=500, detail=f"Content image upload failed: {str(exc)}")

            # Use CDN URL instead of direct S3 URL
            gallery_url = get_s3_url(gallery_key)
            caption = None
            if idx < len(content_image_captions_list):
                candidate_caption = content_image_captions_list[idx]
                if candidate_caption is not None:
                    stripped_caption = candidate_caption.strip()
                    caption = stripped_caption if stripped_caption else None
            merged_gallery.append({"url": gallery_url, "caption": caption})

    update_doc["content_images"] = merged_gallery

    # --- SEO fields handling ---
    # Update SEO fields if provided
    if focus_keyword is not None:
        update_doc["focus_keyword"] = focus_keyword.strip() if focus_keyword else None
    
    if meta_title_override is not None:
        # Use custom meta title or regenerate from title
        if meta_title_override.strip():
            update_doc["meta_title"] = meta_title_override.strip()[:60]
        elif title:
            update_doc["meta_title"] = title[:60] if len(title) > 60 else title
    
    if meta_description_override is not None:
        # Use custom meta description or regenerate from content
        if meta_description_override.strip():
            update_doc["meta_description"] = meta_description_override.strip()[:160]
        elif content:
            update_doc["meta_description"] = _extract_meta_description(content)
    
    if image_alt is not None:
        update_doc["image_alt"] = image_alt.strip() if image_alt else None
    
    if is_breaking_news is not None:
        update_doc["is_breaking_news"] = is_breaking_news
    
    if is_opinion is not None:
        update_doc["is_opinion"] = is_opinion
    
    # Auto-recalculate word count and reading time if content changed
    if content is not None:
        word_count = _calculate_word_count(content)
        update_doc["word_count"] = word_count
        update_doc["reading_time_minutes"] = _calculate_reading_time(word_count)
    
    # Auto-regenerate keywords if title, content, or categories changed
    if any(k in update_doc for k in ["title", "content", "categories"]):
        final_title = update_doc.get("title") or existing.get("title", "")
        final_content = update_doc.get("content") or existing.get("content", "")
        final_categories = update_doc.get("categories") or existing.get("categories", "")
        update_doc["keywords"] = _extract_keywords(final_title, final_content, final_categories)

    # housekeeping fields
    update_doc["updated_at"] = datetime.utcnow()

    # apply update (do not touch immutable fields)
    coll.update_one({"_id": ObjectId(news_id)}, {"$set": update_doc})

    # return the freshly-updated, normalized document
    refreshed = coll.find_one({"_id": ObjectId(news_id)})
    return _normalize_news(refreshed, db_client)


@news_router.delete("/news/{news_id}", tags=["News"])
async def delete_news(
    news_id: str,
    current_user: User = Depends(get_current_author_or_admin_user),
    db_client: MongoClient = Depends(db.get_client),
):
    if not ObjectId.is_valid(news_id):
        raise HTTPException(status_code=404, detail="News not found")
    existing = db_client[db.db_name][NEWS_COLL].find_one({"_id": ObjectId(news_id)})
    if not existing:
        raise HTTPException(status_code=404, detail="News not found")
    db_client[db.db_name][NEWS_COLL].delete_one({"_id": ObjectId(news_id)})
    # (optional) cascade delete comments for this news_id if you want:
    # db_client[db.db_name][NEWS_COMMENTS_COLL].delete_many({"news_id": str(news_id)})
    return {"message": "News deleted successfully"}


# ------------------------- News <-> Tags per news (PROTECTED for write) -------------------------
class TagsPayload(BaseModel):
    tags: Optional[List[str]] = None
    tag: Optional[str] = None  # accept either shape


def _extract_tags(payload: TagsPayload) -> List[str]:
    if payload.tags and isinstance(payload.tags, list):
        return [str(t).strip() for t in payload.tags if str(t).strip()]
    if payload.tag and isinstance(payload.tag, str) and payload.tag.strip():
        return [payload.tag.strip()]
    return []


@news_router.post("/news/{news_id}/tags", tags=["News"])
async def add_tags_to_news(
    news_id: str,
    payload: TagsPayload = Body(...),
    current_user: User = Depends(get_current_author_or_admin_user),
    db_client: MongoClient = Depends(db.get_client),
):
    if not ObjectId.is_valid(news_id):
        raise HTTPException(status_code=404, detail="News not found")
    tags = _extract_tags(payload)
    if not tags:
        raise HTTPException(status_code=400, detail="No tags provided")
    res = db_client[db.db_name][NEWS_COLL].update_one(
        {"_id": ObjectId(news_id)},
        {"$addToSet": {"tags": {"$each": tags}}},
    )
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="News not found")
    return {"added": tags}


@news_router.delete("/news/{news_id}/tags", tags=["News"])
async def remove_tags_from_news(
    news_id: str,
    payload: TagsPayload = Body(...),
    current_user: User = Depends(get_current_author_or_admin_user),
    db_client: MongoClient = Depends(db.get_client),
):
    if not ObjectId.is_valid(news_id):
        raise HTTPException(status_code=404, detail="News not found")
    tags = _extract_tags(payload)
    if not tags:
        raise HTTPException(status_code=400, detail="No tags provided")
    res = db_client[db.db_name][NEWS_COLL].update_one(
        {"_id": ObjectId(news_id)},
        {"$pull": {"tags": {"$in": tags}}},
    )
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="News not found")
    return {"removed": tags}


# (legacy single-tag delete equivalent retained)
@news_router.delete("/news/{news_id}/tags/{tag}", tags=["News"])
async def remove_single_tag_legacy(
    news_id: str,
    tag: str,
    current_user: User = Depends(get_current_author_or_admin_user),
    db_client: MongoClient = Depends(db.get_client),
):
    if not ObjectId.is_valid(news_id):
        raise HTTPException(status_code=404, detail="News not found")
    res = db_client[db.db_name][NEWS_COLL].update_one(
        {"_id": ObjectId(news_id)},
        {"$pull": {"tags": tag}},
    )
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="News not found")
    return {"removed": [tag]}


# ------------------------- Global tags admin (PUBLIC counts, admin writes) -------------------------
@news_router.get("/news-tags", tags=["News"])
async def list_news_tags_with_counts(db_client: MongoClient = Depends(db.get_client)):
    pipeline = [
        {"$addFields": {
            "tags": {
                "$cond": [
                    {"$isArray": "$tags"},
                    "$tags",
                    {"$cond": [
                        {"$and": [{"$ne": ["$tags", None]}, {"$ne": ["$tags", ""]}]},
                        ["$tags"],
                        []
                    ]}
                ]
            }
        }},
        {"$unwind": "$tags"},
        {"$group": {"_id": "$tags", "count": {"$sum": 1}}},
        {"$sort": {"count": -1, "_id": 1}},
    ]
    rows = db_client[db.db_name][NEWS_COLL].aggregate(pipeline)
    return [{"tag": r["_id"], "count": r["count"]} for r in rows]


@news_router.put("/news-tags/rename", tags=["News"])
async def rename_news_tag_globally(
    payload: Dict[str, str],
    current_admin: User = Depends(get_current_admin_user),
    db_client: MongoClient = Depends(db.get_client),
):
    old = (payload.get("old_tag") or payload.get("old") or "").strip()
    new = (payload.get("new_tag") or payload.get("new") or "").strip()
    if not old or not new:
        raise HTTPException(status_code=400, detail="old_tag/new_tag required")
    res = db_client[db.db_name][NEWS_COLL].update_many(
        {"tags": old},
        {"$set": {"tags.$[elem]": new}},
        array_filters=[{"elem": old}],
    )
    return {"matched": res.matched_count, "modified": res.modified_count}


@news_router.delete("/news-tags/{tag}", tags=["News"])
async def delete_news_tag_globally(
    tag: str,
    current_admin: User = Depends(get_current_admin_user),
    db_client: MongoClient = Depends(db.get_client),
):
    res = db_client[db.db_name][NEWS_COLL].update_many(
        {"tags": tag},
        {"$pull": {"tags": tag}},
    )
    return {"matched": res.matched_count, "modified": res.modified_count}


# ------------------------- Categories CRUD -------------------------
@news_router.post("/news-categories", response_model=Category, tags=["News"])
async def create_category(
    category: Category,
    current_admin: User = Depends(get_current_admin_user),
    db_client: MongoClient = Depends(db.get_client),
):
    category_dict = category.dict(by_alias=True, exclude={"id"})
    inserted_category = db_client[db.db_name]["news_categories"].insert_one(category_dict)
    category.id = str(inserted_category.inserted_id)
    return category


@news_router.get("/news-categories", response_model=List[Category], tags=["News"])
async def get_categories(db_client: MongoClient = Depends(db.get_client)):
    categories = list(db_client[db.db_name]["news_categories"].find({}).sort("name", 1))
    for c in categories:
        c["_id"] = str(c["_id"])
    return categories


@news_router.put("/news-categories/{category_id}", response_model=Category, tags=["News"])
async def update_category(
    category_id: str,
    category: Category,
    current_admin: User = Depends(get_current_admin_user),
    db_client: MongoClient = Depends(db.get_client),
):
    if not ObjectId.is_valid(category_id):
        raise HTTPException(status_code=404, detail="Category not found")
    existing = db_client[db.db_name]["news_categories"].find_one({"_id": ObjectId(category_id)})
    if not existing:
        raise HTTPException(status_code=404, detail="Category not found")

    update_doc = category.dict(by_alias=True, exclude={"id", "_id"})
    db_client[db.db_name]["news_categories"].update_one(
        {"_id": ObjectId(category_id)},
        {"$set": update_doc},
    )
    category.id = category_id
    return category


@news_router.delete("/news-categories/{category_id}", tags=["News"])
async def delete_category(
    category_id: str,
    current_admin: User = Depends(get_current_admin_user),
    db_client: MongoClient = Depends(db.get_client),
):
    if not ObjectId.is_valid(category_id):
        raise HTTPException(status_code=404, detail="Category not found")
    existing = db_client[db.db_name]["news_categories"].find_one({"_id": ObjectId(category_id)})
    if not existing:
        raise HTTPException(status_code=404, detail="Category not found")
    db_client[db.db_name]["news_categories"].delete_one({"_id": ObjectId(category_id)})
    return {"message": "Category deleted successfully"}


@news_router.post("/news-categories/bulk", response_model=List[Category], tags=["News"])
async def create_multiple_categories(
    categories: List[Category],
    current_admin: User = Depends(get_current_admin_user),
    db_client: MongoClient = Depends(db.get_client),
):
    category_dicts = [category.dict(by_alias=True, exclude={"id"}) for category in categories]
    inserted = db_client[db.db_name]["news_categories"].insert_many(category_dicts)
    for i, category in enumerate(categories):
        category.id = str(inserted.inserted_ids[i])
    return categories


# ------------------------- SEO-friendly endpoints (NEW - don't break existing) -------------------------

@news_router.get("/news/seo/{news_id}", response_class=HTMLResponse, tags=["News"])
async def get_news_seo_meta(news_id: str, db_client: MongoClient = Depends(db.get_client)):
    """Enhanced SEO meta tags endpoint - works with existing data"""
    if not ObjectId.is_valid(news_id):
        raise HTTPException(status_code=404, detail="News not found")
    
    doc = db_client[db.db_name][NEWS_COLL].find_one({"_id": ObjectId(news_id)})
    if not doc:
        raise HTTPException(status_code=404, detail="News not found")

    # Use existing data with SEO enhancements
    title = doc.get("title", "")
    meta_title = doc.get("meta_title") or title
    meta_description = doc.get("meta_description") or _extract_meta_description(doc.get("content", ""))
    keywords = ", ".join(doc.get("keywords", []))
    
    # Generate slug if not exists
    slug = doc.get("slug") or _generate_seo_slug(title, news_id)
    canonical_url = f"{NEWS_BASE_URL}/news/{slug}"
    
    html_content = f"""
    <!DOCTYPE html>
    <html lang="hi">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        
        <!-- Primary Meta Tags -->
        <title>{meta_title}</title>
        <meta name="description" content="{meta_description}">
        <meta name="keywords" content="{keywords}">
        <link rel="canonical" href="{canonical_url}">
        
        <!-- Open Graph / Facebook -->
        <meta property="og:type" content="article">
        <meta property="og:url" content="{canonical_url}">
        <meta property="og:title" content="{title}">
        <meta property="og:description" content="{meta_description}">
        <meta property="og:image" content="{doc.get('image_url', '')}">
        <meta property="og:locale" content="hi_IN">
        
        <!-- Twitter -->
        <meta property="twitter:card" content="summary_large_image">
        <meta property="twitter:url" content="{canonical_url}">
        <meta property="twitter:title" content="{title}">
        <meta property="twitter:description" content="{meta_description}">
        <meta property="twitter:image" content="{doc.get('image_url', '')}">
        
        <!-- Hindi font optimization -->
        <link rel="preconnect" href="https://fonts.googleapis.com">
        <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
        <link href="https://fonts.googleapis.com/css2?family=Noto+Sans+Devanagari:wght@300;400;500;700&display=swap" rel="stylesheet">
    </head>
    <body>
        <h1>{title}</h1>
        <p>समाचार पढ़ें: <a href="{canonical_url}">{title}</a></p>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

@news_router.get("/news/slug/{slug}", response_model=NewsPost, tags=["News"])
async def get_news_by_slug(
    slug: str,
    request: Request,
    db_client: MongoClient = Depends(db.get_client)
):
    """Get news by SEO-friendly slug - backward compatible with old Hindi slugs
    
    Handles multiple slug formats:
    1. New format: transliterated-title-shortid (e.g., bihar-election-2025-a1b2c3d4)
    2. Old format: hindi-title-fullid (with encoded Hindi chars)
    3. Direct ObjectId lookup
    
    Public users: Only published news
    Authenticated users (admin/author): Can see unpublished news too
    """
    # Check if user is authenticated (for preview of unpublished news)
    auth_header = request.headers.get("Authorization", "")
    is_authenticated = bool(auth_header.strip())
    
    # Try to find by slug first (exact match)
    query = {"slug": slug}
    if not is_authenticated:
        query["published"] = True
    
    doc = db_client[db.db_name][NEWS_COLL].find_one(query)
    
    # If not found by slug, try to extract ID from slug
    if not doc:
        # Try last segment as ID (new format with short ID)
        parts = slug.split('-')
        if parts:
            potential_id = parts[-1]
            
            # Try as short ID (last 8 chars) - search by matching suffix
            if len(potential_id) == 8:
                # Find all posts (published or unpublished based on auth)
                find_query = {} if is_authenticated else {"published": True}
                cursor = db_client[db.db_name][NEWS_COLL].find(
                    find_query,
                    {"_id": 1}
                )
                for candidate in cursor:
                    if str(candidate["_id"]).endswith(potential_id):
                        doc = db_client[db.db_name][NEWS_COLL].find_one({"_id": candidate["_id"]})
                        break
            
            # Try as full ObjectId (backward compatibility)
            elif ObjectId.is_valid(potential_id):
                doc = db_client[db.db_name][NEWS_COLL].find_one({"_id": ObjectId(potential_id)})
    
    if not doc:
        raise HTTPException(status_code=404, detail="News not found")
    
    # Additional check: if unpublished, ensure user is authenticated
    if not doc.get("published", False) and not is_authenticated:
        raise HTTPException(status_code=404, detail="News not found")
    
    return _normalize_news(doc, db_client)


@news_router.post("/news/preview-slug", tags=["News"])
async def preview_slug(payload: Dict[str, str] = Body(...)):
    """Preview what slug will be generated for a given title
    
    Useful for editors to see URL before publishing.
    """
    title = payload.get("title", "")
    if not title:
        raise HTTPException(status_code=400, detail="Title is required")
    
    # Generate sample slug with dummy ID
    sample_slug = _generate_seo_slug(title, "675e3a1b2c4d5e6f7a8b9c0d")
    
    return {
        "title": title,
        "slug": sample_slug,
        "url": f"{NEWS_BASE_URL}/news/{sample_slug}",
        "transliterated": _transliterate_hindi(title),
    }


@news_router.post("/news/regenerate-slugs-test", tags=["News"])
async def regenerate_slugs_test(
    limit: int = Query(1, ge=1, le=10),
    current_admin: User = Depends(get_current_admin_user),
    db_client: MongoClient = Depends(db.get_client),
):
    """Admin endpoint: TEST slug generation on a few posts (safe, read-only preview)
    
    Shows what slugs would be generated WITHOUT modifying the database.
    Use this to verify before running the actual migration.
    """
    coll = db_client[db.db_name][NEWS_COLL]
    
    # Find a few news posts without slug
    cursor = coll.find({}, {"_id": 1, "title": 1, "slug": 1}).limit(limit)
    
    preview = []
    for doc in cursor:
        news_id = str(doc["_id"])
        title = doc.get("title", "")
        current_slug = doc.get("slug")
        
        # Generate what the new slug would be
        new_slug = _generate_seo_slug(title, news_id)
        
        preview.append({
            "news_id": news_id,
            "title": title,
            "current_slug": current_slug or "(none)",
            "new_slug": new_slug,
            "old_url": f"{NEWS_BASE_URL}/news/{news_id}",
            "new_url": f"{NEWS_BASE_URL}/news/{new_slug}",
            "would_update": not current_slug or current_slug != new_slug,
        })
    
    return {
        "message": "Preview only - no changes made to database",
        "preview": preview,
    }


@news_router.post("/news/regenerate-one-slug/{news_id}", tags=["News"])
async def regenerate_one_slug(
    news_id: str,
    current_admin: User = Depends(get_current_admin_user),
    db_client: MongoClient = Depends(db.get_client),
):
    """Admin endpoint: Update slug for ONE specific news post (safe test)
    
    Test the migration on a single post before doing all posts.
    """
    if not ObjectId.is_valid(news_id):
        raise HTTPException(status_code=404, detail="Invalid news ID")
    
    coll = db_client[db.db_name][NEWS_COLL]
    doc = coll.find_one({"_id": ObjectId(news_id)})
    
    if not doc:
        raise HTTPException(status_code=404, detail="News not found")
    
    title = doc.get("title", "")
    old_slug = doc.get("slug")
    new_slug = _generate_seo_slug(title, news_id)
    
    # Update the slug
    coll.update_one(
        {"_id": ObjectId(news_id)},
        {"$set": {"slug": new_slug}}
    )
    
    return {
        "message": "Successfully updated slug for one news post",
        "news_id": news_id,
        "title": title,
        "old_slug": old_slug or "(none)",
        "new_slug": new_slug,
        "old_url": f"{NEWS_BASE_URL}/news/{news_id}",
        "new_url": f"{NEWS_BASE_URL}/news/{new_slug}",
        "test_old_url": f"Test this still works: {NEWS_BASE_URL}/news/slug/{news_id}",
        "test_new_url": f"Test new slug works: {NEWS_BASE_URL}/news/slug/{new_slug}",
    }


@news_router.post("/news/regenerate-all-slugs", tags=["News"])
async def regenerate_all_slugs(
    dry_run: bool = Query(True, description="Set to false to actually update database"),
    current_admin: User = Depends(get_current_admin_user),
    db_client: MongoClient = Depends(db.get_client),
):
    """Admin endpoint: Regenerate slugs for all existing news posts
    
    SAFE: Default is dry_run=true (preview only, no changes).
    Set dry_run=false to actually update the database.
    
    This migrates old news to the new SEO-friendly slug system.
    Safe to run multiple times - only updates posts without slugs or with old format.
    """
    coll = db_client[db.db_name][NEWS_COLL]
    
    # Find all news without slug or with old Hindi slug format
    cursor = coll.find({}, {"_id": 1, "title": 1, "slug": 1})
    
    updated_count = 0
    previews = []
    
    for doc in cursor:
        news_id = str(doc["_id"])
        title = doc.get("title", "")
        current_slug = doc.get("slug")
        
        # Generate new slug
        new_slug = _generate_seo_slug(title, news_id)
        
        # Check if update needed
        should_update = not current_slug or current_slug != new_slug
        
        if should_update:
            if dry_run:
                # Preview only
                if updated_count < 10:  # Show first 10 previews
                    previews.append({
                        "news_id": news_id,
                        "title": title[:50] + "..." if len(title) > 50 else title,
                        "old_slug": current_slug or "(none)",
                        "new_slug": new_slug,
                    })
            else:
                # Actually update
                coll.update_one(
                    {"_id": doc["_id"]},
                    {"$set": {"slug": new_slug}}
                )
            updated_count += 1
    
    if dry_run:
        return {
            "message": "DRY RUN - No changes made to database",
            "would_update_count": updated_count,
            "preview_sample": previews,
            "instruction": "Add ?dry_run=false to the URL to actually update the database",
        }
    else:
        return {
            "message": f"Successfully regenerated slugs for {updated_count} news posts",
            "updated_count": updated_count,
        }

@news_router.get("/rss", response_class=HTMLResponse, tags=["News"])
async def get_rss_feed(db_client: MongoClient = Depends(db.get_client)):
    """Generate RSS feed for news - works with existing data"""
    docs = list(db_client[db.db_name][NEWS_COLL]
               .find({"published": True})
               .sort("created_at", DESCENDING)
               .limit(50))
    
    rss_items = []
    for doc in docs:
        title = doc.get("title", "")
        content = doc.get("content", "")
        description = _extract_meta_description(content, 200)
        slug = doc.get("slug") or _generate_seo_slug(title, str(doc["_id"]))
        link = f"{NEWS_BASE_URL}/news/{slug}"
        pub_date = doc.get("created_at", datetime.utcnow()).strftime('%a, %d %b %Y %H:%M:%S GMT')
        
        rss_items.append(f"""
        <item>
            <title><![CDATA[{title}]]></title>
            <description><![CDATA[{description}]]></description>
            <link>{link}</link>
            <guid>{link}</guid>
            <pubDate>{pub_date}</pubDate>
        </item>
        """)
    
    rss_content = f"""<?xml version="1.0" encoding="UTF-8"?>
    <rss version="2.0">
        <channel>
            <title>GT News 18 - हिंदी समाचार</title>
            <description>Latest Hindi news and updates</description>
            <link>{NEWS_BASE_URL}</link>
            <language>hi</language>
            <lastBuildDate>{datetime.utcnow().strftime('%a, %d %b %Y %H:%M:%S GMT')}</lastBuildDate>
            {''.join(rss_items)}
        </channel>
    </rss>
    """
    
    return HTMLResponse(content=rss_content, media_type="application/rss+xml")

@news_router.get("/sitemap.xml", response_class=HTMLResponse, tags=["News"])
async def generate_sitemap(db_client: MongoClient = Depends(db.get_client)):
    """Generate XML sitemap for SEO - works with existing data"""
    docs = list(db_client[db.db_name][NEWS_COLL]
               .find({"published": True}, {"slug": 1, "title": 1, "updated_at": 1, "created_at": 1})
               .sort("created_at", DESCENDING))
    
    urls = [f"""
        <url>
            <loc>{NEWS_BASE_URL}</loc>
            <lastmod>{datetime.utcnow().strftime('%Y-%m-%d')}</lastmod>
            <changefreq>daily</changefreq>
            <priority>1.0</priority>
        </url>"""]
    
    for doc in docs:
        title = doc.get("title", "")
        slug = doc.get("slug") or _generate_seo_slug(title, str(doc["_id"]))
        lastmod = (doc.get("updated_at") or doc.get("created_at") or datetime.utcnow()).strftime('%Y-%m-%d')
        urls.append(f"""
        <url>
            <loc>{NEWS_BASE_URL}/news/{slug}</loc>
            <lastmod>{lastmod}</lastmod>
            <changefreq>weekly</changefreq>
            <priority>0.8</priority>
        </url>
        """)
    
    sitemap_content = f"""<?xml version="1.0" encoding="UTF-8"?>
    <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
        {''.join(urls)}
    </urlset>
    """
    
    return HTMLResponse(content=sitemap_content, media_type="application/xml")


# ==================== JSON-LD STRUCTURED DATA ENDPOINTS ====================

@news_router.get("/news/{news_id}/jsonld", tags=["News SEO"])
async def get_news_jsonld(news_id: str, db_client: MongoClient = Depends(db.get_client)):
    """
    Get JSON-LD structured data for a news article.
    
    This endpoint returns Google News compliant structured data that should be
    embedded in the <head> of your news article page.
    
    Usage in UI:
    ```html
    <script type="application/ld+json">
        {response data here}
    </script>
    ```
    
    Why this matters for SEO:
    - Required for Google News inclusion
    - Enables rich snippets in Google Search
    - Improves click-through rate by 20-30%
    - Better article visibility in Google Discover
    """
    if not ObjectId.is_valid(news_id):
        raise HTTPException(status_code=404, detail="News not found")
    
    doc = db_client[db.db_name][NEWS_COLL].find_one({"_id": ObjectId(news_id)})
    if not doc:
        raise HTTPException(status_code=404, detail="News not found")
    
    return _generate_news_article_jsonld(doc, db_client)


@news_router.get("/news/slug/{slug}/jsonld", tags=["News SEO"])
async def get_news_jsonld_by_slug(slug: str, db_client: MongoClient = Depends(db.get_client)):
    """
    Get JSON-LD structured data by slug (SEO-friendly URL).
    
    Same as /news/{news_id}/jsonld but uses slug for lookup.
    """
    doc = db_client[db.db_name][NEWS_COLL].find_one({"slug": slug, "published": True})
    
    if not doc:
        # Try to find by short ID suffix
        parts = slug.split('-')
        if parts:
            potential_id = parts[-1]
            if len(potential_id) == 8:
                cursor = db_client[db.db_name][NEWS_COLL].find({"published": True}, {"_id": 1})
                for candidate in cursor:
                    if str(candidate["_id"]).endswith(potential_id):
                        doc = db_client[db.db_name][NEWS_COLL].find_one({"_id": candidate["_id"]})
                        break
    
    if not doc:
        raise HTTPException(status_code=404, detail="News not found")
    
    return _generate_news_article_jsonld(doc, db_client)


@news_router.get("/news/{news_id}/breadcrumb-jsonld", tags=["News SEO"])
async def get_news_breadcrumb_jsonld(news_id: str, db_client: MongoClient = Depends(db.get_client)):
    """
    Get BreadcrumbList JSON-LD for a news article.
    
    Helps Google understand site structure and may show breadcrumbs in search results.
    
    Usage in UI:
    ```html
    <script type="application/ld+json">
        {response data here}
    </script>
    ```
    """
    if not ObjectId.is_valid(news_id):
        raise HTTPException(status_code=404, detail="News not found")
    
    doc = db_client[db.db_name][NEWS_COLL].find_one({"_id": ObjectId(news_id)})
    if not doc:
        raise HTTPException(status_code=404, detail="News not found")
    
    return _generate_breadcrumb_jsonld(doc)


@news_router.get("/news/{news_id}/full-seo", tags=["News SEO"])
async def get_news_full_seo(news_id: str, db_client: MongoClient = Depends(db.get_client)):
    """
    Get complete SEO package for a news article.
    
    Returns all SEO data needed by the frontend:
    - Meta tags (title, description, keywords)
    - Open Graph tags
    - Twitter Card tags
    - JSON-LD structured data (NewsArticle + BreadcrumbList)
    - Canonical URL
    
    This is the recommended endpoint for UI integration.
    """
    if not ObjectId.is_valid(news_id):
        raise HTTPException(status_code=404, detail="News not found")
    
    doc = db_client[db.db_name][NEWS_COLL].find_one({"_id": ObjectId(news_id)})
    if not doc:
        raise HTTPException(status_code=404, detail="News not found")
    
    title = doc.get("title", "")
    slug = doc.get("slug") or _generate_seo_slug(title, news_id)
    canonical_url = doc.get("canonical_url_override") or f"{NEWS_BASE_URL}/news/{slug}"
    description = doc.get("meta_description") or _extract_meta_description(doc.get("content", ""))
    image_url = doc.get("image_url", "")
    keywords = doc.get("keywords") or _extract_keywords(title, doc.get("content", ""), doc.get("categories", ""))
    
    return {
        "meta": {
            "title": doc.get("meta_title") or title,
            "description": description,
            "keywords": keywords,
            "canonical_url": canonical_url,
            "robots": "index, follow",
            "language": "hi"
        },
        "open_graph": {
            "og:type": "article",
            "og:title": title,
            "og:description": description,
            "og:image": image_url,
            "og:url": canonical_url,
            "og:locale": "hi_IN",
            "og:site_name": PUBLISHER_NAME,
            "article:published_time": doc.get("created_at", datetime.utcnow()).isoformat() if isinstance(doc.get("created_at"), datetime) else str(doc.get("created_at", "")),
            "article:modified_time": doc.get("updated_at", datetime.utcnow()).isoformat() if isinstance(doc.get("updated_at"), datetime) else str(doc.get("updated_at", "")),
            "article:section": doc.get("categories", "News"),
            "article:tag": keywords
        },
        "twitter": {
            "twitter:card": "summary_large_image",
            "twitter:title": title,
            "twitter:description": description,
            "twitter:image": image_url,
            "twitter:image:alt": doc.get("image_alt") or title
        },
        "jsonld": [
            _generate_news_article_jsonld(doc, db_client),
            _generate_breadcrumb_jsonld(doc)
        ],
        "additional_seo": {
            "word_count": doc.get("word_count") or _calculate_word_count(doc.get("content", "")),
            "reading_time_minutes": doc.get("reading_time_minutes") or _calculate_reading_time(_calculate_word_count(doc.get("content", ""))),
            "focus_keyword": doc.get("focus_keyword"),
            "is_breaking_news": doc.get("is_breaking_news", False),
            "is_opinion": doc.get("is_opinion", False)
        }
    }


@news_router.get("/news/{news_id}/meta", response_class=HTMLResponse, tags=["News"])
async def get_news_meta(news_id: str, db_client: MongoClient = Depends(db.get_client)):
    if not ObjectId.is_valid(news_id):
        raise HTTPException(status_code=404, detail="News not found")
    doc = db_client[db.db_name][NEWS_COLL].find_one({"_id": ObjectId(news_id)})
    if not doc:
        raise HTTPException(status_code=404, detail="News not found")

    title = doc["title"]
    description = BeautifulSoup(doc["content"], "html.parser").get_text()[:150] + "..."
    image_url = doc.get("image_url") or ""
    # Ensure image URL uses CDN
    if image_url and not image_url.startswith("http"):
        image_url = get_s3_url(image_url)
    elif image_url and ".s3." in image_url and ".amazonaws.com" in image_url:
        # Convert existing S3 URL to CDN URL
        image_url = get_s3_url(image_url)
    slug = _slugify(title)
    news_url = f"{NEWS_BASE_URL}/n/{news_id}-{slug}"

    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <meta property="og:title" content="{title}" />
        <meta property="og:description" content="{description}" />
        <meta property="og:image" content="{image_url}" />
        <meta property="og:url" content="{news_url}" />
        <meta property="og:type" content="article" />
        <meta name="twitter:card" content="summary_large_image" />
        <title>{title}</title>
    </head>
    <body>
        <p>Read the full story at <a href="{news_url}">{title}</a></p>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)


# ------------------------- Paginated -------------------------
class PageMeta(BaseModel):
    total: int
    page: int
    per_page: int
    pages: int
    has_next: bool
    has_prev: bool


class PagedCategories(BaseModel):
    items: List[Category]
    meta: PageMeta


@news_router.get("/news-categories/paginated", response_model=PagedCategories, tags=["News"])
async def get_categories_paginated(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db_client: MongoClient = Depends(db.get_client),
):
    coll = db_client[db.db_name]["news_categories"]

    total = coll.count_documents({})
    pages = max(1, math.ceil(total / per_page))
    skip = (page - 1) * per_page

    docs = list(coll.find({}).sort("name", 1).skip(skip).limit(per_page))
    for d in docs:
        d["_id"] = str(d["_id"])

    return {
        "items": docs,
        "meta": {
            "total": total,
            "page": page,
            "per_page": per_page,
            "pages": pages,
            "has_next": page < pages,
            "has_prev": page > 1,
        },
    }


class PagedNews(BaseModel):
    items: List[NewsPost]
    meta: PageMeta


@news_router.get("/news/paginated", response_model=PagedNews, tags=["News"])
async def get_news_paginated(
    published: Optional[bool] = Query(default=None),
    category: Optional[str] = Query(default=None),
    tag: Optional[str] = Query(default=None),
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=50),
    db_client: MongoClient = Depends(db.get_client),
):
    q: Dict[str, Any] = {}
    if published is not None:
        q["published"] = published
    if category:
        q["categories"] = category
    if tag:
        q["tags"] = tag

    coll = db_client[db.db_name][NEWS_COLL]
    total = coll.count_documents(q)
    pages = max(1, math.ceil(total / per_page))
    skip = (page - 1) * per_page

    items = list(coll.find(q).sort("created_at", DESCENDING).skip(skip).limit(per_page))
    items = [_normalize_news(it, db_client) for it in items]

    return {
        "items": items,
        "meta": {
            "total": total,
            "page": page,
            "per_page": per_page,
            "pages": pages,
            "has_next": page < pages,
            "has_prev": page > 1,
        },
    }



# ==================== HOROSCOPE ENDPOINTS ====================
# Daily horoscope system (राशि फल)

HOROSCOPE_COLL = "daily_horoscopes"

# ---------- IST Timezone & Scheduling Helpers for Horoscope ----------

def _parse_ist_datetime_horoscope(datetime_str: str) -> datetime:
    """Parse datetime string in IST and return UTC datetime for storage
    
    Expected format: YYYY-MM-DDTHH:MM (24-hour format)
    Example: 2025-12-05T14:30
    """
    try:
        # Parse the datetime string (assumes IST input)
        naive_dt = datetime.strptime(datetime_str, "%Y-%m-%dT%H:%M")
        
        # Localize to IST
        ist_dt = IST.localize(naive_dt)
        
        # Convert to UTC for storage
        utc_dt = ist_dt.astimezone(pytz.UTC).replace(tzinfo=None)
        
        logger.info(f"[Timezone Conversion] Input IST: {datetime_str} -> Parsed IST: {ist_dt} -> UTC: {utc_dt}")
        
        return utc_dt
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid datetime format. Expected: YYYY-MM-DDTHH:MM (24-hour IST). Error: {str(e)}"
        )


def _coerce_horoscope_scheduled_at_to_utc_naive(value: Any) -> Optional[datetime]:
    """Coerce various scheduled_at representations to a UTC-naive datetime.

    Accepts:
    - datetime (naive assumed UTC; aware converted to UTC)
    - str:
      - ISO-8601 (with or without timezone)
      - legacy IST local string: YYYY-MM-DDTHH:MM
    """
    if value is None:
        return None

    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=None)
        return value.astimezone(pytz.UTC).replace(tzinfo=None)

    if isinstance(value, str):
        raw = value.strip()
        if not raw:
            return None

        # Legacy format sent by UI as IST local time.
        # This is also the format used by CreateHoroscopeRequest.scheduled_at.
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}", raw):
            return _parse_ist_datetime_horoscope(raw)

        # ISO strings (may include timezone offset). Try to parse and normalize.
        try:
            parsed = datetime.fromisoformat(raw)
            if parsed.tzinfo is not None:
                return parsed.astimezone(pytz.UTC).replace(tzinfo=None)
            # If timezone missing, assume it's already UTC.
            return parsed.replace(tzinfo=None)
        except Exception:
            return None

    return None


def _utc_to_ist_horoscope(utc_dt: datetime) -> datetime:
    """Convert UTC datetime to IST for display"""
    if utc_dt is None:
        return None
    utc_dt = pytz.UTC.localize(utc_dt) if utc_dt.tzinfo is None else utc_dt
    return utc_dt.astimezone(IST).replace(tzinfo=None)


def _get_today_ist() -> date:
    """Get today's date in IST timezone
    
    CRITICAL: Always use this function to get 'today' for horoscope queries.
    Do NOT use date.today() as it uses server timezone (likely UTC).
    
    Example:
    - Server time (UTC): 2025-12-19 23:00:00
    - IST time: 2025-12-20 04:30:00
    - This function returns: 2025-12-20 ✅
    - date.today() returns: 2025-12-19 ❌
    """
    current_ist = _utc_to_ist_horoscope(datetime.utcnow())
    return current_ist.date()


def _is_scheduled_horoscope_ready(scheduled_at: datetime) -> bool:
    """Check if a scheduled horoscope should be published now (UTC comparison)"""
    if scheduled_at is None:
        return False
    current_utc = datetime.utcnow()
    return current_utc >= scheduled_at


def _process_scheduled_horoscopes(db_client: MongoClient):
    """Background task to auto-publish scheduled horoscopes that are due.
    
    Uses Mongo $lte comparison for reliable datetime checks (same as news scheduler).
    Requires scheduled_at to be stored as UTC datetime (not string).
    """
    try:
        coll = db_client[db.db_name][HOROSCOPE_COLL]
        current_utc = datetime.utcnow()

        # Use Mongo $lte for reliable datetime comparison
        # This requires scheduled_at to be stored as datetime, not string
        scheduled_horoscopes = coll.find({
            "scheduled_publish": True,
            "published": False,
            "scheduled_at": {"$lte": current_utc}
        })

        count = 0
        for h in scheduled_horoscopes:
            scheduled_time = h.get("scheduled_at") or current_utc

            coll.update_one(
                {"_id": h["_id"]},
                {"$set": {
                    "published": True,
                    "published_at": scheduled_time,
                    "created_at": scheduled_time,  # Match NEWS: appear at scheduled time
                    "updated_at": current_utc,
                    "scheduled_publish": False
                }}
            )
            count += 1

        if count:
            logger.info(f"✅ [Horoscope Scheduler] Auto-published {count} horoscopes")

    except Exception as e:
        logger.error(f"❌ [Horoscope Scheduler Error]: {e}")


def _normalize_horoscope(doc: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize horoscope document for API response"""
    if "_id" in doc:
        doc["_id"] = str(doc["_id"])
    
    # Convert date strings back to date objects
    if "date" in doc and isinstance(doc["date"], str):
        try:
            doc["date"] = datetime.fromisoformat(doc["date"]).date()
        except:
            pass
    
    # Normalize datetime fields
    # - Store/compare in UTC (naive) in DB
    # - Return timezone-aware UTC datetimes for UI safety (+00:00), plus explicit *_utc/*_ist strings
    for dt_field in ["created_at", "updated_at", "published_at", "scheduled_at"]:
        if dt_field not in doc or doc[dt_field] is None:
            continue

        raw_value = doc[dt_field]
        utc_naive: Optional[datetime] = None

        if isinstance(raw_value, datetime):
            # DB values should be UTC-naive datetimes
            utc_naive = raw_value.replace(tzinfo=None)
        elif isinstance(raw_value, str):
            # Backward compat: some records might have timestamps stored as strings
            try:
                parsed = datetime.fromisoformat(raw_value)
                if parsed.tzinfo is not None:
                    utc_naive = parsed.astimezone(pytz.UTC).replace(tzinfo=None)
                else:
                    # Assume naive strings are UTC
                    utc_naive = parsed
            except Exception:
                utc_naive = None

        if utc_naive is None:
            continue

        aware_utc = pytz.UTC.localize(utc_naive)
        aware_ist = aware_utc.astimezone(IST)

        # Primary field becomes timezone-aware UTC so JS Date parsing converts correctly to local time
        doc[dt_field] = aware_utc
        doc[f"{dt_field}_utc"] = aware_utc.isoformat()
        doc[f"{dt_field}_ist"] = aware_ist.isoformat()
    
    # Ensure author_details exists (fallback if missing)
    if not doc.get("author_details") and doc.get("author_username"):
        # Try to fetch from current session or set basic fallback
        doc["author_details"] = {
            "username": doc["author_username"],
            "full_name": doc["author_username"],  # Fallback to username
            "author_profile_image": None,
            "author_designation": None,
            "author_bio": None
        }
    
    return doc


def _serialize_horoscope(data: Dict[str, Any]) -> Dict[str, Any]:
    """Convert horoscope data to MongoDB-compatible format"""
    from enum import Enum
    
    def convert_value(value):
        if isinstance(value, Enum):
            return value.value
        elif isinstance(value, date):
            return value.isoformat()
        elif isinstance(value, datetime):
            return value
        elif isinstance(value, dict):
            return {k: convert_value(v) for k, v in value.items()}
        elif isinstance(value, list):
            return [convert_value(item) for item in value]
        else:
            return value
    
    return {k: convert_value(v) for k, v in data.items()}


# ==================== PUBLIC HOROSCOPE ENDPOINTS ====================

@news_router.get("/horoscope/today", response_model=DailyHoroscope, tags=["Horoscope"])
async def get_today_horoscope(
    db_client: MongoClient = Depends(db.get_client),
):
    """Get today's daily horoscope (आज का राशि फल)"""
    try:
        # Process scheduled horoscopes first
        _process_scheduled_horoscopes(db_client)
        
        # ✅ Use IST date helper
        today = _get_today_ist()
        today_str = today.isoformat()
        
        logger.info(f"🔍 [get_today_horoscope] Looking for date (IST): {today_str}")
        
        # Query with explicit date string
        horoscope = db_client[db.db_name][HOROSCOPE_COLL].find_one({
            "date": today_str,
            "published": True
        })
        
        if not horoscope:
            logger.warning(f"⚠️ [get_today_horoscope] No published horoscope found for {today_str}")
            
            # Check if unpublished exists
            unpublished = db_client[db.db_name][HOROSCOPE_COLL].find_one({
                "date": today_str,
                "published": False
            })
            
            if unpublished:
                logger.error(f"❌ [get_today_horoscope] Found unpublished horoscope for {today_str}. Scheduled: {unpublished.get('scheduled_publish')}, Time: {unpublished.get('scheduled_at')}")
            
            raise HTTPException(
                status_code=404, 
                detail=f"आज ({today}) के लिए राशिफल उपलब्ध नहीं है"
            )
        
        logger.info(f"✅ [get_today_horoscope] Found horoscope: {horoscope['_id']}")
        return _normalize_horoscope(horoscope)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to fetch today's horoscope: {str(e)}")
        raise HTTPException(status_code=500, detail="राशिफल लाने में त्रुटि")


@news_router.get("/horoscope/date/{target_date}", response_model=DailyHoroscope, tags=["Horoscope"])
async def get_horoscope_by_date(
    target_date: date,
    db_client: MongoClient = Depends(db.get_client),
):
    """Get horoscope for specific date"""
    try:
        # Process scheduled horoscopes (auto-publish if time reached)
        _process_scheduled_horoscopes(db_client)
        
        # Query by exact date string
        horoscope = db_client[db.db_name][HOROSCOPE_COLL].find_one({
            "date": target_date.isoformat(),
            "published": True
        })
        
        if not horoscope:
            raise HTTPException(
                status_code=404, 
                detail=f"{target_date} के लिए राशिफल उपलब्ध नहीं है"
            )
        
        return _normalize_horoscope(horoscope)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch horoscope by date: {str(e)}")
        raise HTTPException(status_code=500, detail="राशिफल लाने में त्रुटि")


@news_router.get("/horoscope/zodiac/{zodiac_sign}", response_model=ZodiacPrediction, tags=["Horoscope"])
async def get_today_zodiac_prediction(
    zodiac_sign: ZodiacSign,
    db_client: MongoClient = Depends(db.get_client),
):
    """Get today's prediction for specific zodiac sign"""
    try:
        # Process scheduled horoscopes (auto-publish if time reached)
        _process_scheduled_horoscopes(db_client)
        
        # ✅ Use IST date helper
        today = _get_today_ist()
        
        horoscope = db_client[db.db_name][HOROSCOPE_COLL].find_one({
            "date": today.isoformat(),
            "published": True
        })
        
        if not horoscope:
            raise HTTPException(
                status_code=404, 
                detail=f"आज के लिए राशिफल उपलब्ध नहीं है"
            )
        
        # Find specific zodiac prediction
        zodiac_predictions = horoscope.get("zodiac_predictions", [])
        for pred in zodiac_predictions:
            if pred.get("sign") == zodiac_sign.value:
                return pred
        
        raise HTTPException(
            status_code=404, 
            detail=f"{zodiac_sign.value} राशि के लिए भविष्यफल नहीं मिला"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch zodiac prediction: {str(e)}")
        raise HTTPException(status_code=500, detail="राशिफल लाने में त्रुटि")


@news_router.get("/horoscope/archive", response_model=List[DailyHoroscope], tags=["Horoscope"])
async def get_horoscope_archive(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=50),
    db_client: MongoClient = Depends(db.get_client),
):
    """Get horoscope archive (past horoscopes)"""
    try:
        # Process scheduled horoscopes (auto-publish if time reached)
        _process_scheduled_horoscopes(db_client)
        
        skip = (page - 1) * limit
        
        horoscopes = list(
            db_client[db.db_name][HOROSCOPE_COLL]
            .find({"published": True})
            .sort("date", DESCENDING)
            .skip(skip)
            .limit(limit)
        )
        
        return [_normalize_horoscope(h) for h in horoscopes]
        
    except Exception as e:
        logger.error(f"Failed to fetch horoscope archive: {str(e)}")
        raise HTTPException(status_code=500, detail="राशिफल संग्रह लाने में त्रुटि")


# ==================== HOROSCOPE ENGAGEMENT ====================

@news_router.post("/horoscope/{horoscope_id}/views", response_model=dict, tags=["Horoscope"])
async def increment_horoscope_views(
    horoscope_id: str,
    request: Request,
    db_client: MongoClient = Depends(db.get_client),
):
    """Increment horoscope view count"""
    if not ObjectId.is_valid(horoscope_id):
        raise HTTPException(status_code=404, detail="राशिफल नहीं मिला")
    
    try:
        horoscope = db_client[db.db_name][HOROSCOPE_COLL].find_one({"_id": ObjectId(horoscope_id)})
        if not horoscope:
            raise HTTPException(status_code=404, detail="राशिफल नहीं मिला")

        # Get client IP
        client_ip = request.headers.get("X-Forwarded-For", request.client.host)
        if client_ip and "," in client_ip:
            client_ip = client_ip.split(",")[0].strip()
        if not client_ip:
            client_ip = "unknown"

        viewed_ips = horoscope.get("viewed_ips", [])
        current_views = horoscope.get("views", 0)

        if client_ip not in viewed_ips:
            viewed_ips.append(client_ip)
            current_views += 1
            db_client[db.db_name][HOROSCOPE_COLL].update_one(
                {"_id": ObjectId(horoscope_id)},
                {"$set": {"viewed_ips": viewed_ips, "views": current_views}},
            )

        return {"views": current_views}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to increment horoscope views: {str(e)}")
        raise HTTPException(status_code=500, detail="व्यू काउंट अपडेट करने में त्रुटि")


@news_router.post("/horoscope/{horoscope_id}/likes", response_model=dict, tags=["Horoscope"])
async def increment_horoscope_likes(
    horoscope_id: str,
    request: Request,
    db_client: MongoClient = Depends(db.get_client),
):
    """Increment horoscope like count"""
    if not ObjectId.is_valid(horoscope_id):
        raise HTTPException(status_code=404, detail="राशिफल नहीं मिला")
    
    try:
        horoscope = db_client[db.db_name][HOROSCOPE_COLL].find_one({"_id": ObjectId(horoscope_id)})
        if not horoscope:
            raise HTTPException(status_code=404, detail="राशिफल नहीं मिला")

        # Get client IP
        client_ip = request.headers.get("X-Forwarded-For", request.client.host)
        if client_ip and "," in client_ip:
            client_ip = client_ip.split(",")[0].strip()
        if not client_ip:
            client_ip = "unknown"

        liked_ips = horoscope.get("liked_ips", [])
        current_likes = horoscope.get("likes", 0)

        if client_ip not in liked_ips:
            # Use atomic MongoDB operations
            result = db_client[db.db_name][HOROSCOPE_COLL].update_one(
                {"_id": ObjectId(horoscope_id)},
                {
                    "$addToSet": {"liked_ips": client_ip},
                    "$inc": {"likes": 1}
                }
            )
            
            # Fetch updated count
            updated_horoscope = db_client[db.db_name][HOROSCOPE_COLL].find_one(
                {"_id": ObjectId(horoscope_id)},
                {"likes": 1}
            )
            current_likes = updated_horoscope.get("likes", current_likes + 1)

        return {"likes": current_likes}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to increment horoscope likes: {str(e)}")
        raise HTTPException(status_code=500, detail="लाइक काउंट अपडेट करने में त्रुटि")


# ==================== ADMIN HOROSCOPE ENDPOINTS ====================

def get_admin_user_horoscope(current_user: User = Depends(get_current_user)):
    """Admin/Author only access for horoscope management"""
    if current_user.role not in ["admin", "author"]:
        raise HTTPException(status_code=403, detail="Admin or Author access required")
    return current_user


@news_router.post("/admin/horoscope", response_model=DailyHoroscope, tags=["Horoscope Admin"])
async def create_horoscope(
    horoscope_data: CreateHoroscopeRequest,
    current_user: User = Depends(get_admin_user_horoscope),
    db_client: MongoClient = Depends(db.get_client),
):
    """Create new daily horoscope (Admin/Author only)"""
    try:
        # Check if horoscope already exists for this date
        existing = db_client[db.db_name][HOROSCOPE_COLL].find_one({
            "date": horoscope_data.date.isoformat()
        })
        
        if existing:
            raise HTTPException(
                status_code=400,
                detail=f"इस तारीख ({horoscope_data.date}) के लिए राशिफल पहले से मौजूद है"
            )
        
        # Validate that all 12 zodiac signs are present
        if len(horoscope_data.zodiac_predictions) != 12:
            raise HTTPException(
                status_code=400,
                detail="सभी 12 राशियों के भविष्यफल जरूरी हैं"
            )
        
        # Handle scheduled publishing
        scheduled_at_utc = None
        if horoscope_data.scheduled_publish:
            if not horoscope_data.scheduled_at:
                raise HTTPException(
                    status_code=400,
                    detail="scheduled_at is required when scheduled_publish is true. Provide datetime in format: YYYY-MM-DDTHH:MM (IST)"
                )
            
            # Parse IST datetime and convert to UTC
            scheduled_at_utc = _parse_ist_datetime_horoscope(horoscope_data.scheduled_at)
            
            # Validate: scheduled time must be in the future
            current_utc = datetime.utcnow()
            if scheduled_at_utc <= current_utc:
                # Convert back to IST for user-friendly error message
                current_ist = _utc_to_ist_horoscope(current_utc)
                raise HTTPException(
                    status_code=400,
                    detail=f"Scheduled time must be in the future. Current IST time: {current_ist.strftime('%Y-%m-%d %H:%M')}"
                )
            
            # When scheduling, auto-set published=False (will be auto-published at scheduled time)
            logger.info(f"[create_horoscope] Scheduling horoscope for {horoscope_data.scheduled_at} IST (UTC: {scheduled_at_utc})")
        
        # If not scheduling but scheduled_at provided, ignore it
        if not horoscope_data.scheduled_publish and horoscope_data.scheduled_at:
            logger.warning("[create_horoscope] scheduled_at provided but scheduled_publish=False, ignoring scheduled_at")
            scheduled_at_utc = None
        
        # Build horoscope document (like news - don't rely on model_dump for datetime fields)
        horoscope_dict = {
            "title": horoscope_data.title,
            "date": horoscope_data.date.isoformat(),  # Store date as string for query
            "zodiac_predictions": [p.model_dump() for p in horoscope_data.zodiac_predictions],
            "closing_message": horoscope_data.closing_message,
            "contact_info": horoscope_data.contact_info,
            "author_username": current_user.username,
            "author_details": {
                "username": current_user.username,
                "full_name": getattr(current_user, 'full_name', current_user.username),
                "author_profile_image": getattr(current_user, 'author_profile_image', None),
                "author_designation": getattr(current_user, 'author_designation', None),
                "author_bio": getattr(current_user, 'author_bio', None)
            },
            "published": horoscope_data.published if not scheduled_at_utc else False,
            "scheduled_publish": True if scheduled_at_utc else False,
            "scheduled_at": scheduled_at_utc,  # datetime object or None
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "views": 0,
            "viewed_ips": [],
            "likes": 0,
            "liked_ips": [],
        }
        
        # Set published_at if immediately publishing
        if horoscope_dict["published"]:
            horoscope_dict["published_at"] = datetime.utcnow()
        
        # Insert into database
        result = db_client[db.db_name][HOROSCOPE_COLL].insert_one(horoscope_dict)
        horoscope_dict["_id"] = str(result.inserted_id)
        
        return _normalize_horoscope(horoscope_dict)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create horoscope: {str(e)}")
        raise HTTPException(status_code=500, detail="राशिफल बनाने में त्रुटि")


@news_router.get("/admin/horoscopes", response_model=List[DailyHoroscope], tags=["Horoscope Admin"])
async def get_all_horoscopes_admin(
    current_user: User = Depends(get_admin_user_horoscope),
    db_client: MongoClient = Depends(db.get_client),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    published: Optional[bool] = None,
):
    """Get all horoscopes (Admin view - includes unpublished)"""
    try:
        filter_query = {}
        if published is not None:
            filter_query["published"] = published
        
        skip = (page - 1) * limit
        horoscopes = list(
            db_client[db.db_name][HOROSCOPE_COLL]
            .find(filter_query)
            .sort("date", DESCENDING)
            .skip(skip)
            .limit(limit)
        )
        
        return [_normalize_horoscope(h) for h in horoscopes]
        
    except Exception as e:
        logger.error(f"Failed to fetch horoscopes (admin): {str(e)}")
        raise HTTPException(status_code=500, detail="राशिफल लाने में त्रुटि")


@news_router.get("/admin/horoscope/{horoscope_id}", response_model=DailyHoroscope, tags=["Horoscope Admin"])
async def get_horoscope_by_id_admin(
    horoscope_id: str,
    current_user: User = Depends(get_admin_user_horoscope),
    db_client: MongoClient = Depends(db.get_client),
):
    """Get horoscope by ID (Admin - includes unpublished)"""
    if not ObjectId.is_valid(horoscope_id):
        raise HTTPException(status_code=404, detail="राशिफल नहीं मिला")
    
    try:
        horoscope = db_client[db.db_name][HOROSCOPE_COLL].find_one({"_id": ObjectId(horoscope_id)})
        if not horoscope:
            raise HTTPException(status_code=404, detail="राशिफल नहीं मिला")
        
        return _normalize_horoscope(horoscope)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch horoscope by ID: {str(e)}")
        raise HTTPException(status_code=500, detail="राशिफल लाने में त्रुटि")


@news_router.put("/admin/horoscope/{horoscope_id}", response_model=DailyHoroscope, tags=["Horoscope Admin"])
async def update_horoscope(
    horoscope_id: str,
    horoscope_data: UpdateHoroscopeRequest,
    current_user: User = Depends(get_admin_user_horoscope),
    db_client: MongoClient = Depends(db.get_client),
):
    """Update horoscope (Admin/Author only)"""
    if not ObjectId.is_valid(horoscope_id):
        raise HTTPException(status_code=404, detail="राशिफल नहीं मिला")
    
    try:
        existing = db_client[db.db_name][HOROSCOPE_COLL].find_one({"_id": ObjectId(horoscope_id)})
        if not existing:
            raise HTTPException(status_code=404, detail="राशिफल नहीं मिला")

        # Prepare update data
        update_data = horoscope_data.model_dump(exclude_unset=True)
        update_data["updated_at"] = datetime.utcnow()
        
        # Handle scheduled publishing updates
        if horoscope_data.scheduled_publish is not None:
            if horoscope_data.scheduled_publish:
                if not horoscope_data.scheduled_at:
                    raise HTTPException(
                        status_code=400,
                        detail="scheduled_at is required when scheduled_publish is true. Provide datetime in format: YYYY-MM-DDTHH:MM (IST)"
                    )
                
                # Parse IST datetime and convert to UTC
                scheduled_at_utc = _parse_ist_datetime_horoscope(horoscope_data.scheduled_at)
                
                # Validate: scheduled time must be in the future
                current_utc = datetime.utcnow()
                if scheduled_at_utc <= current_utc:
                    # Convert back to IST for user-friendly error message
                    current_ist = _utc_to_ist_horoscope(current_utc)
                    raise HTTPException(
                        status_code=400,
                        detail=f"Scheduled time must be in the future. Current IST time: {current_ist.strftime('%Y-%m-%d %H:%M')}"
                    )
                
                update_data["scheduled_at"] = scheduled_at_utc  # UTC naive datetime
                update_data["scheduled_publish"] = True
                update_data["published"] = False  # Force unpublished until scheduled time
                logger.info(f"[update_horoscope] Updating schedule to {horoscope_data.scheduled_at} IST (UTC: {scheduled_at_utc})")
            else:
                # Disable scheduling
                update_data["scheduled_at"] = None
                update_data["scheduled_publish"] = False
                logger.info("[update_horoscope] Disabling scheduled publishing")
        
        # Set published_at if publishing for the first time
        if horoscope_data.published and not existing.get("published"):
            update_data["published_at"] = datetime.utcnow()
            # Clear scheduling when manually publishing
            update_data["scheduled_publish"] = False
            update_data["scheduled_at"] = None
        
        # Handle zodiac_predictions serialization if present
        if "zodiac_predictions" in update_data and update_data["zodiac_predictions"]:
            update_data["zodiac_predictions"] = [
                p.model_dump() if hasattr(p, 'model_dump') else p 
                for p in update_data["zodiac_predictions"]
            ]
        
        # Handle date serialization if present
        if "date" in update_data and update_data["date"] is not None:
            if isinstance(update_data["date"], date):
                update_data["date"] = update_data["date"].isoformat()
        
        # Update horoscope
        db_client[db.db_name][HOROSCOPE_COLL].update_one(
            {"_id": ObjectId(horoscope_id)},
            {"$set": update_data}
        )
        
        # Get updated horoscope
        updated = db_client[db.db_name][HOROSCOPE_COLL].find_one({"_id": ObjectId(horoscope_id)})
        return _normalize_horoscope(updated)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update horoscope: {str(e)}")
        raise HTTPException(status_code=500, detail="राशिफल अपडेट करने में त्रुटि")


@news_router.delete("/admin/horoscope/{horoscope_id}", tags=["Horoscope Admin"])
async def delete_horoscope(
    horoscope_id: str,
    current_user: User = Depends(get_admin_user_horoscope),
    db_client: MongoClient = Depends(db.get_client),
):
    """Delete horoscope (Admin/Author only)"""
    if not ObjectId.is_valid(horoscope_id):
        raise HTTPException(status_code=404, detail="राशिफल नहीं मिला")
    
    try:
        existing = db_client[db.db_name][HOROSCOPE_COLL].find_one({"_id": ObjectId(horoscope_id)})
        if not existing:
            raise HTTPException(status_code=404, detail="राशिफल नहीं मिला")
        
        # Delete horoscope
        db_client[db.db_name][HOROSCOPE_COLL].delete_one({"_id": ObjectId(horoscope_id)})
        
        return {"message": "राशिफल सफलतापूर्वक डिलीट कर दिया गया"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete horoscope: {str(e)}")
        raise HTTPException(status_code=500, detail="राशिफल डिलीट करने में त्रुटि")


# ==================== ADDITIONAL ADMIN/AUTHOR HOROSCOPE OPERATIONS ====================

@news_router.post("/admin/horoscope/{horoscope_id}/publish", response_model=DailyHoroscope, tags=["Horoscope Admin"])
async def publish_horoscope(
    horoscope_id: str,
    current_user: User = Depends(get_admin_user_horoscope),
    db_client: MongoClient = Depends(db.get_client),
):
    """Publish horoscope (Admin/Author only)"""
    if not ObjectId.is_valid(horoscope_id):
        raise HTTPException(status_code=404, detail="राशिफल नहीं मिला")
    
    try:
        existing = db_client[db.db_name][HOROSCOPE_COLL].find_one({"_id": ObjectId(horoscope_id)})
        if not existing:
            raise HTTPException(status_code=404, detail="राशिफल नहीं मिला")
        
        # Update to published
        db_client[db.db_name][HOROSCOPE_COLL].update_one(
            {"_id": ObjectId(horoscope_id)},
            {
                "$set": {
                    "published": True,
                    "published_at": datetime.utcnow(),
                    "updated_at": datetime.utcnow()
                }
            }
        )
        
        updated = db_client[db.db_name][HOROSCOPE_COLL].find_one({"_id": ObjectId(horoscope_id)})
        return _normalize_horoscope(updated)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to publish horoscope: {str(e)}")
        raise HTTPException(status_code=500, detail="राशिफल प्रकाशित करने में त्रुटि")


@news_router.post("/admin/horoscope/{horoscope_id}/unpublish", response_model=DailyHoroscope, tags=["Horoscope Admin"])
async def unpublish_horoscope(
    horoscope_id: str,
    current_user: User = Depends(get_admin_user_horoscope),
    db_client: MongoClient = Depends(db.get_client),
):
    """Unpublish horoscope (Admin/Author only)"""
    if not ObjectId.is_valid(horoscope_id):
        raise HTTPException(status_code=404, detail="राशिफल नहीं मिला")
    
    try:
        existing = db_client[db.db_name][HOROSCOPE_COLL].find_one({"_id": ObjectId(horoscope_id)})
        if not existing:
            raise HTTPException(status_code=404, detail="राशिफल नहीं मिला")
        
        # Update to unpublished
        db_client[db.db_name][HOROSCOPE_COLL].update_one(
            {"_id": ObjectId(horoscope_id)},
            {
                "$set": {
                    "published": False,
                    "updated_at": datetime.utcnow()
                }
            }
        )
        
        updated = db_client[db.db_name][HOROSCOPE_COLL].find_one({"_id": ObjectId(horoscope_id)})
        return _normalize_horoscope(updated)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to unpublish horoscope: {str(e)}")
        raise HTTPException(status_code=500, detail="राशिफल अप्रकाशित करने में त्रुटि")


@news_router.get("/admin/horoscope/date/{target_date}", response_model=DailyHoroscope, tags=["Horoscope Admin"])
async def get_horoscope_by_date_admin(
    target_date: date,
    current_user: User = Depends(get_admin_user_horoscope),
    db_client: MongoClient = Depends(db.get_client),
):
    """Get horoscope by date (Admin - includes unpublished)"""
    try:
        horoscope = db_client[db.db_name][HOROSCOPE_COLL].find_one({
            "date": target_date.isoformat()
        })
        
        if not horoscope:
            raise HTTPException(
                status_code=404, 
                detail=f"{target_date} के लिए राशिफल नहीं मिला"
            )
        
        return _normalize_horoscope(horoscope)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch horoscope by date (admin): {str(e)}")
        raise HTTPException(status_code=500, detail="राशिफल लाने में त्रुटि")


@news_router.get("/author/horoscopes", response_model=List[DailyHoroscope], tags=["Horoscope Author"])
async def get_author_horoscopes(
    current_user: User = Depends(get_admin_user_horoscope),
    db_client: MongoClient = Depends(db.get_client),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    published: Optional[bool] = None,
):
    """Get horoscopes created by current author"""
    try:
        filter_query = {"author_username": current_user.username}
        
        if published is not None:
            filter_query["published"] = published
        
        skip = (page - 1) * limit
        horoscopes = list(
            db_client[db.db_name][HOROSCOPE_COLL]
            .find(filter_query)
            .sort("date", DESCENDING)
            .skip(skip)
            .limit(limit)
        )
        
        return [_normalize_horoscope(h) for h in horoscopes]
        
    except Exception as e:
        logger.error(f"Failed to fetch author horoscopes: {str(e)}")
        raise HTTPException(status_code=500, detail="राशिफल लाने में त्रुटि")


@news_router.get("/admin/horoscope/stats", tags=["Horoscope Admin"])
async def get_horoscope_stats(
    current_user: User = Depends(get_admin_user_horoscope),
    db_client: MongoClient = Depends(db.get_client),
):
    """Get horoscope statistics (Admin/Author)"""
    try:
        total_horoscopes = db_client[db.db_name][HOROSCOPE_COLL].count_documents({})
        published_horoscopes = db_client[db.db_name][HOROSCOPE_COLL].count_documents({"published": True})
        draft_horoscopes = db_client[db.db_name][HOROSCOPE_COLL].count_documents({"published": False})
        
        # Total views and likes
        pipeline = [
            {"$group": {
                "_id": None,
                "total_views": {"$sum": "$views"},
                "total_likes": {"$sum": "$likes"}
            }}
        ]
        stats = list(db_client[db.db_name][HOROSCOPE_COLL].aggregate(pipeline))
        
        total_views = stats[0]["total_views"] if stats else 0
        total_likes = stats[0]["total_likes"] if stats else 0
        
        # Most viewed horoscope
        most_viewed = db_client[db.db_name][HOROSCOPE_COLL].find_one(
            {"published": True},
            sort=[("views", DESCENDING)]
        )
        
        # Most liked horoscope
        most_liked = db_client[db.db_name][HOROSCOPE_COLL].find_one(
            {"published": True},
            sort=[("likes", DESCENDING)]
        )
        
        return {
            "total_horoscopes": total_horoscopes,
            "published_horoscopes": published_horoscopes,
            "draft_horoscopes": draft_horoscopes,
            "total_views": total_views,
            "total_likes": total_likes,
            "most_viewed": _normalize_horoscope(most_viewed) if most_viewed else None,
            "most_liked": _normalize_horoscope(most_liked) if most_liked else None
        }
        
    except Exception as e:
        logger.error(f"Failed to fetch horoscope stats: {str(e)}")
        raise HTTPException(status_code=500, detail="आँकड़े लाने में त्रुटि")


@news_router.get("/author/horoscope/stats", tags=["Horoscope Author"])
async def get_author_horoscope_stats(
    current_user: User = Depends(get_admin_user_horoscope),
    db_client: MongoClient = Depends(db.get_client),
):
    """Get horoscope statistics for current author"""
    try:
        filter_query = {"author_username": current_user.username}
        
        total_horoscopes = db_client[db.db_name][HOROSCOPE_COLL].count_documents(filter_query)
        published_horoscopes = db_client[db.db_name][HOROSCOPE_COLL].count_documents({
            **filter_query,
            "published": True
        })
        draft_horoscopes = db_client[db.db_name][HOROSCOPE_COLL].count_documents({
            **filter_query,
            "published": False
        })
        
        # Total views and likes for author's horoscopes
        pipeline = [
            {"$match": filter_query},
            {"$group": {
                "_id": None,
                "total_views": {"$sum": "$views"},
                "total_likes": {"$sum": "$likes"}
            }}
        ]
        stats = list(db_client[db.db_name][HOROSCOPE_COLL].aggregate(pipeline))
        
        total_views = stats[0]["total_views"] if stats else 0
        total_likes = stats[0]["total_likes"] if stats else 0
        
        return {
            "author": current_user.username,
            "total_horoscopes": total_horoscopes,
            "published_horoscopes": published_horoscopes,
            "draft_horoscopes": draft_horoscopes,
            "total_views": total_views,
            "total_likes": total_likes
        }
        
    except Exception as e:
        logger.error(f"Failed to fetch author horoscope stats: {str(e)}")
        raise HTTPException(status_code=500, detail="आँकड़े लाने में त्रुटि")


@news_router.post("/admin/horoscope/bulk-delete", tags=["Horoscope Admin"])
async def bulk_delete_horoscopes(
    horoscope_ids: List[str] = Body(...),
    current_user: User = Depends(get_admin_user_horoscope),
    db_client: MongoClient = Depends(db.get_client),
):
    """Bulk delete horoscopes (Admin only)"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    try:
        # Validate all IDs
        object_ids = []
        for hid in horoscope_ids:
            if not ObjectId.is_valid(hid):
                raise HTTPException(status_code=400, detail=f"Invalid ID: {hid}")
            object_ids.append(ObjectId(hid))
        
        # Delete horoscopes
        result = db_client[db.db_name][HOROSCOPE_COLL].delete_many({
            "_id": {"$in": object_ids}
        })
        
        return {
            "message": f"{result.deleted_count} राशिफल सफलतापूर्वक डिलीट किए गए",
            "deleted_count": result.deleted_count
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to bulk delete horoscopes: {str(e)}")
        raise HTTPException(status_code=500, detail="राशिफल डिलीट करने में त्रुटि")


@news_router.get("/admin/horoscope/drafts", response_model=List[DailyHoroscope], tags=["Horoscope Admin"])
async def get_draft_horoscopes(
    current_user: User = Depends(get_admin_user_horoscope),
    db_client: MongoClient = Depends(db.get_client),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
):
    """Get all draft horoscopes (Admin/Author)"""
    try:
        filter_query = {"published": False}
        
        # If author (not admin), only show their drafts
        if current_user.role != "admin":
            filter_query["author_username"] = current_user.username
        
        skip = (page - 1) * limit
        horoscopes = list(
            db_client[db.db_name][HOROSCOPE_COLL]
            .find(filter_query)
            .sort("created_at", DESCENDING)
            .skip(skip)
            .limit(limit)
        )
        
        return [_normalize_horoscope(h) for h in horoscopes]
        
    except Exception as e:
        logger.error(f"Failed to fetch draft horoscopes: {str(e)}")
        raise HTTPException(status_code=500, detail="ड्राफ्ट राशिफल लाने में त्रुटि")


@news_router.get("/admin/horoscope/published", response_model=List[DailyHoroscope], tags=["Horoscope Admin"])
async def get_published_horoscopes_admin(
    current_user: User = Depends(get_admin_user_horoscope),
    db_client: MongoClient = Depends(db.get_client),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    author: Optional[str] = None,
):
    """Get all published horoscopes (Admin view)"""
    try:
        filter_query = {"published": True}
        
        if author:
            filter_query["author_username"] = author
        
        skip = (page - 1) * limit
        horoscopes = list(
            db_client[db.db_name][HOROSCOPE_COLL]
            .find(filter_query)
            .sort("date", DESCENDING)
            .skip(skip)
            .limit(limit)
        )
        
        return [_normalize_horoscope(h) for h in horoscopes]
        
    except Exception as e:
        logger.error(f"Failed to fetch published horoscopes: {str(e)}")
        raise HTTPException(status_code=500, detail="प्रकाशित राशिफल लाने में त्रुटि")


@news_router.get("/admin/horoscope/search", response_model=List[DailyHoroscope], tags=["Horoscope Admin"])
async def search_horoscopes_admin(
    current_user: User = Depends(get_admin_user_horoscope),
    db_client: MongoClient = Depends(db.get_client),
    query: str = Query(..., min_length=1),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
):
    """Search horoscopes by title or content (Admin/Author)"""
    try:
        # Build search filter
        filter_query = {
            "$or": [
                {"title": {"$regex": query, "$options": "i"}},
                {"zodiac_predictions.prediction": {"$regex": query, "$options": "i"}},
                {"closing_message": {"$regex": query, "$options": "i"}}
            ]
        }
        
        # If author (not admin), only search their horoscopes
        if current_user.role != "admin":
            filter_query["author_username"] = current_user.username
        
        skip = (page - 1) * limit
        horoscopes = list(
            db_client[db.db_name][HOROSCOPE_COLL]
            .find(filter_query)
            .sort("date", DESCENDING)
            .skip(skip)
            .limit(limit)
        )
        
        return [_normalize_horoscope(h) for h in horoscopes]
        
    except Exception as e:
        logger.error(f"Failed to search horoscopes: {str(e)}")
        raise HTTPException(status_code=500, detail="राशिफल खोजने में त्रुटि")


@news_router.get("/admin/horoscope/date-range", response_model=List[DailyHoroscope], tags=["Horoscope Admin"])
async def get_horoscopes_by_date_range(
    current_user: User = Depends(get_admin_user_horoscope),
    db_client: MongoClient = Depends(db.get_client),
    start_date: date = Query(...),
    end_date: date = Query(...),
    published: Optional[bool] = None,
):
    """Get horoscopes within a date range (Admin/Author)"""
    try:
        filter_query = {
            "date": {
                "$gte": start_date.isoformat(),
                "$lte": end_date.isoformat()
            }
        }
        
        if published is not None:
            filter_query["published"] = published
        
        # If author (not admin), only show their horoscopes
        if current_user.role != "admin":
            filter_query["author_username"] = current_user.username
        
        horoscopes = list(
            db_client[db.db_name][HOROSCOPE_COLL]
            .find(filter_query)
            .sort("date", DESCENDING)
        )
        
        return [_normalize_horoscope(h) for h in horoscopes]
        
    except Exception as e:
        logger.error(f"Failed to fetch horoscopes by date range: {str(e)}")
        raise HTTPException(status_code=500, detail="राशिफल लाने में त्रुटि")


# ==================== DEBUG & TROUBLESHOOTING ENDPOINTS ====================

@news_router.get("/admin/horoscope/debug/today", tags=["Horoscope Debug"])
async def debug_today_horoscope(
    current_user: User = Depends(get_admin_user_horoscope),
    db_client: MongoClient = Depends(db.get_client),
):
    """Debug endpoint to see what's stored for today"""
    # ✅ Use IST date helper
    today = _get_today_ist()
    today_str = today.isoformat()
    
    # Check all horoscopes for today (published and unpublished)
    all_today = list(db_client[db.db_name][HOROSCOPE_COLL].find({
        "date": today_str
    }))
    
    # Check system time
    current_utc = datetime.utcnow()
    current_ist = _utc_to_ist_horoscope(current_utc)
    
    return {
        "debug_info": {
            "today_date": today_str,
            "current_utc": current_utc.isoformat(),
            "current_ist": current_ist.isoformat(),
            "found_count": len(all_today),
        },
        "horoscopes": [_normalize_horoscope(h) for h in all_today]
    }


@news_router.post("/admin/horoscope/force-process-scheduled", tags=["Horoscope Debug"])
async def force_process_scheduled(
    db_client: MongoClient = Depends(db.get_client),
):
    """Trigger scheduled horoscope processing.
    
    Can be called by cron job:
    * * * * * curl -s -X POST https://api.projectdevops.in/admin/horoscope/force-process-scheduled > /dev/null
    """
    _process_scheduled_horoscopes(db_client)
    
    return {"message": "Scheduled horoscopes processed"}


@news_router.get("/admin/horoscope/debug/all-dates", tags=["Horoscope Debug"])
async def debug_all_dates(
    current_user: User = Depends(get_admin_user_horoscope),
    db_client: MongoClient = Depends(db.get_client),
):
    """See all horoscope dates in database"""
    all_horoscopes = list(db_client[db.db_name][HOROSCOPE_COLL].find(
        {},
        {"date": 1, "published": 1, "title": 1, "scheduled_publish": 1, "scheduled_at": 1}
    ).sort("date", -1).limit(50))
    
    return {
        "total_count": len(all_horoscopes),
        "horoscopes": [_normalize_horoscope(h) for h in all_horoscopes]
    }


@news_router.post("/admin/horoscope/publish-today", tags=["Horoscope Debug"])
async def publish_today_horoscope(
    current_user: User = Depends(get_admin_user_horoscope),
    db_client: MongoClient = Depends(db.get_client),
):
    """Quick fix: Manually publish today's horoscope if it exists"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    # ✅ Use IST date helper
    today = _get_today_ist()
    today_str = today.isoformat()
    
    # Find today's unpublished horoscope
    horoscope = db_client[db.db_name][HOROSCOPE_COLL].find_one({
        "date": today_str,
        "published": False
    })
    
    if not horoscope:
        raise HTTPException(
            status_code=404,
            detail=f"No unpublished horoscope found for {today_str}"
        )
    
    # Publish it
    db_client[db.db_name][HOROSCOPE_COLL].update_one(
        {"_id": horoscope["_id"]},
        {
            "$set": {
                "published": True,
                "published_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
                "scheduled_publish": False
            }
        }
    )
    
    updated = db_client[db.db_name][HOROSCOPE_COLL].find_one({"_id": horoscope["_id"]})
    logger.info(f"✅ [publish_today_horoscope] Manually published horoscope for {today_str}")
    
    return {
        "message": f"Successfully published today's horoscope ({today_str})",
        "horoscope": _normalize_horoscope(updated)
    }


@news_router.get("/admin/horoscope/debug/scheduled", tags=["Horoscope Debug"])
async def debug_scheduled_horoscopes(
    current_user: User = Depends(get_admin_user_horoscope),
    db_client: MongoClient = Depends(db.get_client),
):
    """See all scheduled horoscopes and their status"""
    current_utc = datetime.utcnow()
    current_ist = _utc_to_ist_horoscope(current_utc)
    
    # Find all scheduled horoscopes (published and unpublished)
    scheduled = list(db_client[db.db_name][HOROSCOPE_COLL].find({
        "scheduled_publish": True
    }).sort("scheduled_at", 1))
    
    result = {
        "debug_info": {
            "current_utc": current_utc.isoformat(),
            "current_ist": current_ist.isoformat(),
            "total_scheduled": len(scheduled)
        },
        "scheduled_horoscopes": []
    }
    
    for h in scheduled:
        scheduled_at_utc = _coerce_horoscope_scheduled_at_to_utc_naive(h.get("scheduled_at"))
        scheduled_at_ist = _utc_to_ist_horoscope(scheduled_at_utc) if scheduled_at_utc else None

        is_due = bool(scheduled_at_utc and current_utc >= scheduled_at_utc)
        
        result["scheduled_horoscopes"].append({
            "_id": str(h["_id"]),
            "date": h.get("date"),
            "published": h.get("published", False),
            "scheduled_at_utc": scheduled_at_utc.isoformat() if scheduled_at_utc else None,
            "scheduled_at_ist": scheduled_at_ist.isoformat() if scheduled_at_ist else None,
            "is_due": is_due,
            "should_be_published": is_due and not h.get("published", False)
        })
    
    return result


@news_router.get("/admin/horoscope/debug/time-check", tags=["Horoscope Debug"])
async def debug_time_check(
    current_user: User = Depends(get_admin_user_horoscope),
):
    """Check current time in different timezones - use this to debug date issues"""
    import platform
    from datetime import datetime as dt_check
    
    current_utc = datetime.utcnow()
    current_ist = _utc_to_ist_horoscope(current_utc)
    today_ist = _get_today_ist()
    server_date = date.today()
    
    return {
        "server_info": {
            "platform": platform.system(),
            "python_version": platform.python_version(),
            "server_timezone": "Likely UTC" if server_date != today_ist else "Matches IST"
        },
        "times": {
            "utc_datetime": current_utc.isoformat(),
            "utc_date": current_utc.date().isoformat(),
            "ist_datetime": current_ist.isoformat(),
            "ist_date": today_ist.isoformat(),
            "server_date_today": server_date.isoformat(),
        },
        "comparison": {
            "ist_vs_utc_hours_diff": "+5:30",
            "dates_match": current_utc.date() == today_ist,
            "issue_detected": current_utc.date() != today_ist,
            "explanation": "If issue_detected=true, UTC and IST are on different dates (e.g., UTC=19th, IST=20th)"
        },
        "recommendation": {
            "always_use_function": "_get_today_ist()",
            "never_use": "date.today() - uses server timezone",
            "for_queries": f"Use date: '{today_ist.isoformat()}' for today's horoscope"
        }
    }


# ==================== LIVE STREAM API ENDPOINTS ====================

@news_router.post("/live-streams", tags=["Live Streams"])
async def create_live_stream(
    stream_data: CreateLiveStreamRequest,
    db_client: MongoClient = Depends(db.get_client),
    current_user: User = Depends(get_current_user),
):
    """
    Create a new live stream entry (Admin/Author only).
    
    Use this to add YouTube, Facebook, or other platform live stream URLs
    that will be embedded in iframe on the website.
    
    **Embed URL Examples:**
    - YouTube: `https://www.youtube.com/embed/VIDEO_ID` or `https://www.youtube.com/embed/live_stream?channel=CHANNEL_ID`
    - Facebook: `https://www.facebook.com/plugins/video.php?href=VIDEO_URL`
    - Twitter/X: Use the video URL directly
    """
    # Only admin/author can create live streams
    if current_user.role not in ["admin", "author"]:
        raise HTTPException(status_code=403, detail="Only admin or author can manage live streams")
    
    collection = db_client[db.db_name]["live_streams"]
    
    stream_doc = {
        "title": stream_data.title,
        "platform": stream_data.platform.value,
        "stream_url": stream_data.stream_url,
        "description": stream_data.description,
        "thumbnail_url": stream_data.thumbnail_url,
        "is_active": stream_data.is_active,
        "is_live": stream_data.is_live,
        "display_order": stream_data.display_order,
        "created_by": current_user.username,
        "created_at": datetime.utcnow(),
        "updated_at": None,
    }
    
    result = collection.insert_one(stream_doc)
    stream_doc["id"] = str(result.inserted_id)
    if "_id" in stream_doc:
        del stream_doc["_id"]
    
    return {
        "message": "Live stream created successfully",
        "stream": stream_doc
    }


@news_router.get("/live-streams", tags=["Live Streams"])
async def get_live_streams(
    active_only: bool = Query(True, description="Return only active streams"),
    platform: Optional[str] = Query(None, description="Filter by platform: youtube, facebook, twitter, etc."),
    db_client: MongoClient = Depends(db.get_client),
):
    """
    Get all live streams for the website (Public endpoint).
    
    Returns streams ordered by display_order for frontend to embed in iframes.
    """
    collection = db_client[db.db_name]["live_streams"]
    
    query = {}
    if active_only:
        query["is_active"] = True
    if platform:
        query["platform"] = platform.lower()
    
    streams = list(collection.find(query).sort("display_order", ASCENDING))
    
    # Serialize ObjectId
    for stream in streams:
        stream["id"] = str(stream["_id"])
        del stream["_id"]
    
    return {
        "count": len(streams),
        "streams": streams
    }


@news_router.get("/live-streams/active", tags=["Live Streams"])
async def get_active_live_stream(
    db_client: MongoClient = Depends(db.get_client),
):
    """
    Get the primary active live stream for homepage display.
    
    Returns the first active stream marked as 'is_live=True' with lowest display_order.
    Use this endpoint for the main live TV embed on homepage.
    """
    collection = db_client[db.db_name]["live_streams"]
    
    # Get the primary live stream (active + is_live + lowest order)
    stream = collection.find_one(
        {"is_active": True, "is_live": True},
        sort=[("display_order", ASCENDING)]
    )
    
    if not stream:
        # Fallback: Get any active stream
        stream = collection.find_one(
            {"is_active": True},
            sort=[("display_order", ASCENDING)]
        )
    
    if not stream:
        return {
            "has_live_stream": False,
            "stream": None,
            "message": "No active live stream configured"
        }
    
    stream["id"] = str(stream["_id"])
    del stream["_id"]
    
    return {
        "has_live_stream": True,
        "stream": stream
    }


@news_router.get("/live-streams/{stream_id}", tags=["Live Streams"])
async def get_live_stream(
    stream_id: str,
    db_client: MongoClient = Depends(db.get_client),
):
    """Get a specific live stream by ID"""
    collection = db_client[db.db_name]["live_streams"]
    
    try:
        stream = collection.find_one({"_id": ObjectId(stream_id)})
    except:
        raise HTTPException(status_code=400, detail="Invalid stream ID format")
    
    if not stream:
        raise HTTPException(status_code=404, detail="Live stream not found")
    
    stream["id"] = str(stream["_id"])
    del stream["_id"]
    
    return stream


@news_router.put("/live-streams/{stream_id}", tags=["Live Streams"])
async def update_live_stream(
    stream_id: str,
    update_data: UpdateLiveStreamRequest,
    db_client: MongoClient = Depends(db.get_client),
    current_user: User = Depends(get_current_user),
):
    """
    Update a live stream (Admin/Author only).
    
    Use this to change the stream URL, toggle is_live status, or update platform.
    """
    if current_user.role not in ["admin", "author"]:
        raise HTTPException(status_code=403, detail="Only admin or author can manage live streams")
    
    collection = db_client[db.db_name]["live_streams"]
    
    try:
        existing = collection.find_one({"_id": ObjectId(stream_id)})
    except:
        raise HTTPException(status_code=400, detail="Invalid stream ID format")
    
    if not existing:
        raise HTTPException(status_code=404, detail="Live stream not found")
    
    # Build update document
    update_doc = {"updated_at": datetime.utcnow()}
    
    if update_data.title is not None:
        update_doc["title"] = update_data.title
    if update_data.platform is not None:
        update_doc["platform"] = update_data.platform.value
    if update_data.stream_url is not None:
        update_doc["stream_url"] = update_data.stream_url
    if update_data.description is not None:
        update_doc["description"] = update_data.description
    if update_data.thumbnail_url is not None:
        update_doc["thumbnail_url"] = update_data.thumbnail_url
    if update_data.is_active is not None:
        update_doc["is_active"] = update_data.is_active
    if update_data.is_live is not None:
        update_doc["is_live"] = update_data.is_live
    if update_data.display_order is not None:
        update_doc["display_order"] = update_data.display_order
    
    collection.update_one(
        {"_id": ObjectId(stream_id)},
        {"$set": update_doc}
    )
    
    # Return updated document
    updated = collection.find_one({"_id": ObjectId(stream_id)})
    updated["id"] = str(updated["_id"])
    del updated["_id"]
    
    return {
        "message": "Live stream updated successfully",
        "stream": updated
    }


@news_router.patch("/live-streams/{stream_id}/toggle-live", tags=["Live Streams"])
async def toggle_live_status(
    stream_id: str,
    is_live: bool = Query(..., description="Set live status"),
    db_client: MongoClient = Depends(db.get_client),
    current_user: User = Depends(get_current_user),
):
    """
    Quick toggle for is_live status (Admin/Author only).
    
    Use this for quickly marking a stream as live or not live from admin panel.
    """
    if current_user.role not in ["admin", "author"]:
        raise HTTPException(status_code=403, detail="Only admin or author can manage live streams")
    
    collection = db_client[db.db_name]["live_streams"]
    
    try:
        result = collection.update_one(
            {"_id": ObjectId(stream_id)},
            {"$set": {"is_live": is_live, "updated_at": datetime.utcnow()}}
        )
    except:
        raise HTTPException(status_code=400, detail="Invalid stream ID format")
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Live stream not found")
    
    return {
        "message": f"Stream is now {'LIVE' if is_live else 'not live'}",
        "is_live": is_live
    }


@news_router.delete("/live-streams/{stream_id}", tags=["Live Streams"])
async def delete_live_stream(
    stream_id: str,
    db_client: MongoClient = Depends(db.get_client),
    current_user: User = Depends(get_current_user),
):
    """Delete a live stream (Admin only)"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only admin can delete live streams")
    
    collection = db_client[db.db_name]["live_streams"]
    
    try:
        result = collection.delete_one({"_id": ObjectId(stream_id)})
    except:
        raise HTTPException(status_code=400, detail="Invalid stream ID format")
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Live stream not found")
    
    return {"message": "Live stream deleted successfully"}


@news_router.get("/live-streams/platforms/list", tags=["Live Streams"])
async def get_supported_platforms():
    """
    Get list of supported streaming platforms.
    
    Use this to populate dropdown in admin panel.
    """
    return {
        "platforms": [
            {"value": "youtube", "label": "YouTube", "embed_hint": "https://www.youtube.com/embed/VIDEO_ID"},
            {"value": "facebook", "label": "Facebook", "embed_hint": "https://www.facebook.com/plugins/video.php?href=VIDEO_URL"},
            {"value": "twitter", "label": "Twitter/X", "embed_hint": "Direct video URL"},
            {"value": "instagram", "label": "Instagram", "embed_hint": "Instagram embed URL"},
            {"value": "dailymotion", "label": "Dailymotion", "embed_hint": "https://www.dailymotion.com/embed/video/VIDEO_ID"},
            {"value": "vimeo", "label": "Vimeo", "embed_hint": "https://player.vimeo.com/video/VIDEO_ID"},
            {"value": "custom", "label": "Custom/Other", "embed_hint": "Any iframe-compatible URL"},
        ]
    }
