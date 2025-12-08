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
    # Horoscope models
    HoroscopePost, HoroscopeComment, CreateHoroscopeRequest, 
    UpdateHoroscopeRequest, ZodiacSign, HoroscopeType, HindiZodiacDetails
)
from models.user import User
from routes.config import AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_REGION
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

AWS_BUCKET_NAME = "projectdevops-blogs-new"
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
                        "created_at": scheduled_time,  # Update to scheduled time
                        "updated_at": datetime.utcnow()
                    }
                }
            )
            updated_count += 1
            auto_published_posts.append(post)
            logger.info(f"Auto-published scheduled post: {post['_id']} at scheduled time: {scheduled_time}")
        
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
        
        # Build author details object
        author_details = {
            "username": username,
            "full_name": f"{author.get('first_name', '')} {author.get('last_name', '')}".strip(),
            "author_profile_image": author.get("author_profile_image"),
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
        image_url = f"https://{AWS_BUCKET_NAME}.s3.{AWS_REGION}.amazonaws.com/{unique_filename}"
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

            gallery_url = f"https://{AWS_BUCKET_NAME}.s3.{AWS_REGION}.amazonaws.com/{gallery_key}"
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

    # Add SEO data after insertion (custom slug is required)
    seo_updates = {
        "slug": custom_slug,
        "meta_title": title[:60] if len(title) > 60 else title,  # SEO optimal length
        "meta_description": _extract_meta_description(content),
        "keywords": _extract_keywords(title, content, categories)
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
    db_client: MongoClient = Depends(db.get_client),
):
    # Process scheduled posts before listing
    _process_scheduled_posts(db_client)
    
    query: Dict[str, Any] = {}
    if _should_force_published_only(request, published):
        query["published"] = True
    elif published is not None:
        query["published"] = published

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

            gallery_url = f"https://{AWS_BUCKET_NAME}.s3.{AWS_REGION}.amazonaws.com/{gallery_key}"
            caption = None
            if idx < len(content_image_captions_list):
                candidate_caption = content_image_captions_list[idx]
                if candidate_caption is not None:
                    stripped_caption = candidate_caption.strip()
                    caption = stripped_caption if stripped_caption else None
            merged_gallery.append({"url": gallery_url, "caption": caption})

    update_doc["content_images"] = merged_gallery

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
    if image_url and not image_url.startswith("http"):
        image_url = f"https://{AWS_BUCKET_NAME}.s3.{AWS_REGION}.amazonaws.com/{image_url}"
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
# Hindi horoscope system 

HOROSCOPE_COLL = "horoscopes"
HOROSCOPE_COMMENTS_COLL = "horoscope_comments"

# ==================== IST TIMEZONE UTILITIES ====================
import pytz
from datetime import timezone, timedelta

def get_ist_timezone():
    """Get IST timezone object"""
    return pytz.timezone('Asia/Kolkata')

def convert_utc_to_ist(utc_dt: datetime) -> datetime:
    """Convert UTC datetime to IST"""
    if utc_dt.tzinfo is None:
        utc_dt = utc_dt.replace(tzinfo=pytz.UTC)
    ist_tz = get_ist_timezone()
    return utc_dt.astimezone(ist_tz)

def convert_ist_to_utc(ist_dt: datetime) -> datetime:
    """Convert IST datetime to UTC for database storage"""
    ist_tz = get_ist_timezone()
    if ist_dt.tzinfo is None:
        ist_dt = ist_tz.localize(ist_dt)
    return ist_dt.astimezone(pytz.UTC).replace(tzinfo=None)

def normalize_ist_datetime_input(dt: datetime) -> datetime:
    """Ensure incoming datetime is timezone-aware in IST."""
    ist_tz = get_ist_timezone()
    if dt.tzinfo is None:
        return ist_tz.localize(dt)
    return dt.astimezone(ist_tz)

def get_current_ist_time() -> datetime:
    """Get current time in IST"""
    utc_now = datetime.utcnow()
    return convert_utc_to_ist(utc_now)

def _parse_scheduled_datetime(value: Union[datetime, str]) -> Optional[datetime]:
    """Convert stored datetime values (string or datetime) into naive UTC datetime."""
    if isinstance(value, datetime):
        scheduled_dt = value
    elif isinstance(value, str):
        try:
            # Support both naive and Z-suffixed ISO strings
            normalized = value.replace("Z", "+00:00") if value.endswith("Z") else value
            scheduled_dt = datetime.fromisoformat(normalized)
        except ValueError:
            logger.warning(f"Unable to parse scheduled_publish_at value: {value}")
            return None
    else:
        return None

    # Normalize to naive UTC for comparison
    if scheduled_dt.tzinfo is not None:
        return scheduled_dt.astimezone(pytz.UTC).replace(tzinfo=None)
    return scheduled_dt


def is_scheduled_publish_time_reached(scheduled_utc: Union[datetime, str]) -> bool:
    """Check if scheduled publish time has been reached (IST comparison)"""
    if not scheduled_utc:
        return False

    parsed_datetime = _parse_scheduled_datetime(scheduled_utc)
    if parsed_datetime is None:
        return False

    current_utc = datetime.utcnow()
    return current_utc >= parsed_datetime

def determine_publish_status(horoscope_data: dict) -> str:
    """Determine publish status using normalized datetime comparisons"""
    if horoscope_data.get("published", False):
        return "published"

    if not horoscope_data.get("auto_publish_enabled", False):
        return "draft"

    scheduled_value = horoscope_data.get("scheduled_publish_at")
    if not scheduled_value:
        return "draft"

    scheduled_dt = _parse_scheduled_datetime(scheduled_value)
    if scheduled_dt is None:
        return "draft"

    return "published" if is_scheduled_publish_time_reached(scheduled_dt) else "scheduled"

def get_current_admin_user_horoscope(current_user: User = Depends(get_current_user)):
    """Admin/Author only access for horoscope management"""
    if current_user.role not in ["admin", "author"]:
        raise HTTPException(status_code=403, detail="Admin or Author access required")
    return current_user

def _serialize_horoscope_for_mongodb(data: Dict[str, Any]) -> Dict[str, Any]:
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

def _normalize_horoscope(doc: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize horoscope document for response with IST timezone conversion"""
    if "_id" in doc:
        doc["_id"] = str(doc["_id"])
    
    # Convert date strings back to date objects
    if "horoscope_date" in doc and isinstance(doc["horoscope_date"], str):
        try:
            doc["horoscope_date"] = datetime.fromisoformat(doc["horoscope_date"]).date()
        except:
            pass
    
    # Convert datetime objects to ISO strings with IST conversion for display
    for dt_field in ["created_at", "updated_at", "published_at", "scheduled_at"]:
        if dt_field in doc and isinstance(doc[dt_field], datetime):
            doc[dt_field] = doc[dt_field].isoformat()
    
    # Handle scheduled_publish_at - convert from UTC to IST for display
    if "scheduled_publish_at" in doc and doc["scheduled_publish_at"]:
        if isinstance(doc["scheduled_publish_at"], datetime):
            # Convert UTC to IST for frontend display
            ist_time = convert_utc_to_ist(doc["scheduled_publish_at"])
            doc["scheduled_publish_at_ist"] = ist_time.isoformat()
            doc["scheduled_publish_at"] = doc["scheduled_publish_at"].isoformat()
        elif isinstance(doc["scheduled_publish_at"], str):
            try:
                utc_dt = datetime.fromisoformat(doc["scheduled_publish_at"])
                ist_time = convert_utc_to_ist(utc_dt)
                doc["scheduled_publish_at_ist"] = ist_time.isoformat()
            except:
                pass
    
    # Update publish status if needed
    if doc.get("auto_publish_enabled") and doc.get("scheduled_publish_at"):
        doc["publish_status"] = determine_publish_status(doc)
    
    return doc

# ==================== ADMIN HOROSCOPE ENDPOINTS ====================

@news_router.post("/horoscopes", response_model=HoroscopePost, tags=["Horoscope Admin"])
async def create_horoscope(
    horoscope_data: CreateHoroscopeRequest,
    current_user: User = Depends(get_current_admin_user_horoscope),
    db_client: MongoClient = Depends(db.get_client),
):
    """Create a new Hindi horoscope post with IST scheduling support (Admin/Author only)"""
    try:
        # Check if horoscope already exists for this date and type
        existing = db_client[db.db_name][HOROSCOPE_COLL].find_one({
            "horoscope_date": horoscope_data.horoscope_date.isoformat(),
            "horoscope_type": horoscope_data.horoscope_type.value
        })
        
        if existing:
            raise HTTPException(
                status_code=400,
                detail=f"इस तारीख ({horoscope_data.horoscope_date}) के लिए राशिफल पहले से मौजूद है"
            )
        
        # Create horoscope document
        horoscope_dict = horoscope_data.model_dump()
        horoscope_dict["author_username"] = current_user.username
        horoscope_dict["created_at"] = datetime.utcnow()
        horoscope_dict["updated_at"] = datetime.utcnow()
        
        # Handle IST scheduling
        if horoscope_data.scheduled_publish_at and horoscope_data.auto_publish_enabled:
            # Convert IST scheduled time to UTC for storage
            scheduled_utc = convert_ist_to_utc(horoscope_data.scheduled_publish_at)
            horoscope_dict["scheduled_publish_at"] = scheduled_utc
            horoscope_dict["scheduled_at"] = datetime.utcnow()
            
            # Check if scheduled time has already passed
            if is_scheduled_publish_time_reached(scheduled_utc):
                horoscope_dict["published"] = True
                horoscope_dict["published_at"] = datetime.utcnow()
                horoscope_dict["publish_status"] = "published"
            else:
                horoscope_dict["published"] = False
                horoscope_dict["publish_status"] = "scheduled"
        else:
            # Regular publishing logic
            if horoscope_dict["published"]:
                horoscope_dict["published_at"] = datetime.utcnow()
                horoscope_dict["publish_status"] = "published"
            else:
                horoscope_dict["publish_status"] = "draft"
        
        # Serialize for MongoDB
        horoscope_dict = _serialize_horoscope_for_mongodb(horoscope_dict)
        
        # Insert into database
        result = db_client[db.db_name][HOROSCOPE_COLL].insert_one(horoscope_dict)
        horoscope_dict["_id"] = str(result.inserted_id)
        
        return _normalize_horoscope(horoscope_dict)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create horoscope: {str(e)}")
        raise HTTPException(status_code=500, detail="राशिफल बनाने में त्रुटि")

@news_router.get("/admin/horoscopes", response_model=List[HoroscopePost], tags=["Horoscope Admin"])
async def get_all_horoscopes_admin(
    current_user: User = Depends(get_current_admin_user_horoscope),
    db_client: MongoClient = Depends(db.get_client),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    horoscope_type: Optional[HoroscopeType] = None,
    published: Optional[bool] = None,
    author: Optional[str] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
):
    """Get all horoscopes with admin filters"""
    try:
        # Build filter query
        filter_query = {}
        
        if horoscope_type:
            filter_query["horoscope_type"] = horoscope_type.value
        if published is not None:
            filter_query["published"] = published
        if author:
            filter_query["author_username"] = author
        if date_from:
            filter_query["horoscope_date"] = {"$gte": date_from.isoformat()}
        if date_to:
            if "horoscope_date" in filter_query:
                filter_query["horoscope_date"]["$lte"] = date_to.isoformat()
            else:
                filter_query["horoscope_date"] = {"$lte": date_to.isoformat()}
        
        # Get paginated results
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
        logger.error(f"Failed to fetch horoscopes: {str(e)}")
        raise HTTPException(status_code=500, detail="राशिफल लाने में त्रुटि")

@news_router.get("/horoscopes/daily", response_model=HoroscopePost, tags=["Horoscope Public"])
async def get_daily_horoscope(
    target_date: Optional[date] = Query(None, description="राशिफल की तारीख (डिफ़ॉल्ट: आज)"),
    zodiac_sign: Optional[ZodiacSign] = Query(None, description="विशिष्ट राशि के लिए फ़िल्टर"),
    db_client: MongoClient = Depends(db.get_client),
):
    """आज का दैनिक राशिफल प्राप्त करें"""
    if not target_date:
        target_date = date.today()
    
    try:
        horoscope = db_client[db.db_name][HOROSCOPE_COLL].find_one({
            "horoscope_date": target_date.isoformat(),
            "horoscope_type": "daily",
            "published": True
        })
        
        if not horoscope:
            raise HTTPException(status_code=404, detail=f"{target_date} के लिए राशिफल उपलब्ध नहीं है")
        
        # Filter by zodiac sign if requested
        if zodiac_sign:
            zodiac_predictions = [
                pred for pred in horoscope.get("zodiac_predictions", [])
                if pred.get("sign") == zodiac_sign.value
            ]
            horoscope["zodiac_predictions"] = zodiac_predictions
        
        return _normalize_horoscope(horoscope)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch daily horoscope: {str(e)}")
        raise HTTPException(status_code=500, detail="दैनिक राशिफल लाने में त्रुटि")

@news_router.get("/horoscopes/archive", response_model=List[HoroscopePost], tags=["Horoscope Public"])
async def get_horoscope_archive(
    db_client: MongoClient = Depends(db.get_client),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=50),
    horoscope_type: HoroscopeType = Query(HoroscopeType.daily),
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
):
    """राशिफल का संग्रह (Archive) - Users can toggle dates to view old horoscopes"""
    try:
        # Build filter
        filter_query = {
            "horoscope_type": horoscope_type.value,
            "published": True
        }
        
        if date_from:
            filter_query["horoscope_date"] = {"$gte": date_from.isoformat()}
        if date_to:
            if "horoscope_date" in filter_query:
                filter_query["horoscope_date"]["$lte"] = date_to.isoformat()
            else:
                filter_query["horoscope_date"] = {"$lte": date_to.isoformat()}
        
        # Get paginated results
        skip = (page - 1) * limit
        horoscopes = list(
            db_client[db.db_name][HOROSCOPE_COLL]
            .find(filter_query)
            .sort("horoscope_date", DESCENDING)
            .skip(skip)
            .limit(limit)
        )
        
        return [_normalize_horoscope(h) for h in horoscopes]
        
    except Exception as e:
        logger.error(f"Failed to fetch horoscope archive: {str(e)}")
        raise HTTPException(status_code=500, detail="राशिफल संग्रह लाने में त्रुटि")

# ==================== SINGLE HOROSCOPE BY ID (PUBLIC) ====================

@news_router.get("/horoscopes/{horoscope_id}", response_model=HoroscopePost, tags=["Horoscope Public"])
async def get_horoscope_by_id(
    horoscope_id: str,
    db_client: MongoClient = Depends(db.get_client),
):
    """Get specific horoscope by ID (Public)"""
    if not ObjectId.is_valid(horoscope_id):
        raise HTTPException(status_code=404, detail="राशिफल नहीं मिला")
    
    try:
        horoscope = db_client[db.db_name][HOROSCOPE_COLL].find_one({
            "_id": ObjectId(horoscope_id),
            "published": True  # Only published horoscopes for public access
        })
        
        if not horoscope:
            raise HTTPException(status_code=404, detail="राशिफल नहीं मिला")
        
        return _normalize_horoscope(horoscope)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch horoscope by ID: {str(e)}")
        raise HTTPException(status_code=500, detail="राशिफल लाने में त्रुटि")

# ==================== HOROSCOPE ENGAGEMENT (PUBLIC) ====================

@news_router.post("/horoscopes/{horoscope_id}/views", response_model=dict, tags=["Horoscope Public"])
async def increment_horoscope_views(
    horoscope_id: str,
    request: Request,
    db_client: MongoClient = Depends(db.get_client),
):
    """Increment horoscope view count (Public)"""
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
            logger.warning("No valid client IP detected for horoscope views")
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

@news_router.post("/horoscopes/{horoscope_id}/likes", response_model=dict, tags=["Horoscope Public"])
async def increment_horoscope_likes(
    horoscope_id: str,
    request: Request,
    db_client: MongoClient = Depends(db.get_client),
):
    """Increment horoscope like count (Public)"""
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
            logger.warning("No valid client IP detected for horoscope likes")
            client_ip = "unknown"

        liked_ips = horoscope.get("liked_ips", [])
        current_likes = horoscope.get("likes", 0)

        if client_ip not in liked_ips:
            liked_ips.append(client_ip)
            current_likes += 1
            db_client[db.db_name][HOROSCOPE_COLL].update_one(
                {"_id": ObjectId(horoscope_id)},
                {"$set": {"liked_ips": liked_ips, "likes": current_likes}},
            )

        return {"likes": current_likes}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to increment horoscope likes: {str(e)}")
        raise HTTPException(status_code=500, detail="लाइक काउंट अपडेट करने में त्रुटि")

# ==================== RELATED HOROSCOPES (PUBLIC) ====================

@news_router.get("/horoscopes/{horoscope_id}/related", response_model=List[HoroscopePost], tags=["Horoscope Public"])
async def get_related_horoscopes(
    horoscope_id: str,
    limit: int = Query(5, ge=1, le=10),
    db_client: MongoClient = Depends(db.get_client),
):
    """Get related horoscopes based on type and recent dates"""
    if not ObjectId.is_valid(horoscope_id):
        raise HTTPException(status_code=404, detail="राशिफल नहीं मिला")
    
    try:
        horoscope = db_client[db.db_name][HOROSCOPE_COLL].find_one({"_id": ObjectId(horoscope_id)})
        if not horoscope:
            raise HTTPException(status_code=404, detail="राशिफल नहीं मिला")

        # Get related horoscopes of same type, excluding current one
        filter_query = {
            "_id": {"$ne": ObjectId(horoscope_id)},
            "horoscope_type": horoscope.get("horoscope_type", "daily"),
            "published": True
        }

        related_horoscopes = list(
            db_client[db.db_name][HOROSCOPE_COLL]
            .find(filter_query)
            .sort("horoscope_date", DESCENDING)
            .limit(limit)
        )

        return [_normalize_horoscope(h) for h in related_horoscopes]
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch related horoscopes: {str(e)}")
        raise HTTPException(status_code=500, detail="संबंधित राशिफल लाने में त्रुटि")

# ==================== ADMIN HOROSCOPE CRUD OPERATIONS ====================

@news_router.get("/horoscopes/{horoscope_id}/admin", response_model=HoroscopePost, tags=["Horoscope Admin"])
async def get_horoscope_by_id_admin(
    horoscope_id: str,
    current_user: User = Depends(get_current_admin_user_horoscope),
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
        logger.error(f"Failed to fetch horoscope by ID (admin): {str(e)}")
        raise HTTPException(status_code=500, detail="राशिफल लाने में त्रुटि")

@news_router.put("/horoscopes/{horoscope_id}", response_model=HoroscopePost, tags=["Horoscope Admin"])
async def update_horoscope(
    horoscope_id: str,
    horoscope_data: UpdateHoroscopeRequest,
    current_user: User = Depends(get_current_admin_user_horoscope),
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
        
        # Set published_at if publishing for the first time
        if horoscope_data.published and not existing.get("published"):
            update_data["published_at"] = datetime.utcnow()
        
        # Serialize for MongoDB
        update_data = _serialize_horoscope_for_mongodb(update_data)
        
        # Update horoscope
        db_client[db.db_name][HOROSCOPE_COLL].update_one(
            {"_id": ObjectId(horoscope_id)},
            {"$set": update_data}
        )
        
        # Get updated horoscope
        updated_horoscope = db_client[db.db_name][HOROSCOPE_COLL].find_one({"_id": ObjectId(horoscope_id)})
        return _normalize_horoscope(updated_horoscope)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update horoscope: {str(e)}")
        raise HTTPException(status_code=500, detail="राशिफल अपडेट करने में त्रुटि")

@news_router.delete("/horoscopes/{horoscope_id}", tags=["Horoscope Admin"])
async def delete_horoscope(
    horoscope_id: str,
    current_user: User = Depends(get_current_admin_user_horoscope),
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
        
        # Optionally delete related comments
        db_client[db.db_name][HOROSCOPE_COMMENTS_COLL].delete_many({"horoscope_id": horoscope_id})
        
        return {"message": "राशिफल सफलतापूर्वक डिलीट कर दिया गया"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete horoscope: {str(e)}")
        raise HTTPException(status_code=500, detail="राशिफल डिलीट करने में त्रुटि")

# ==================== HOROSCOPE SCHEDULING ENDPOINTS (IST) ====================

@news_router.post("/horoscopes/{horoscope_id}/schedule", response_model=HoroscopePost, tags=["Horoscope Admin"])
async def schedule_horoscope_publish(
    horoscope_id: str,
    scheduled_time: datetime = Body(..., description="IST timezone datetime for scheduling"),
    auto_publish: bool = Body(True, description="Enable auto-publishing"),
    current_user: User = Depends(get_current_admin_user_horoscope),
    db_client: MongoClient = Depends(db.get_client),
):
    """Schedule horoscope for future publishing (IST timezone)"""
    if not ObjectId.is_valid(horoscope_id):
        raise HTTPException(status_code=404, detail="राशिफल नहीं मिला")
    
    try:
        existing = db_client[db.db_name][HOROSCOPE_COLL].find_one({"_id": ObjectId(horoscope_id)})
        if not existing:
            raise HTTPException(status_code=404, detail="राशिफल नहीं मिला")
        
        # Normalize incoming datetime to IST-aware for comparison
        scheduled_ist = normalize_ist_datetime_input(scheduled_time)

        # Validate scheduled time (must be in future)
        current_ist = get_current_ist_time()
        if scheduled_ist <= current_ist:
            raise HTTPException(
                status_code=400, 
                detail="अनुसूचित समय भविष्य में होना चाहिए (IST timezone में)"
            )
        
        # Convert IST to UTC for storage
        scheduled_utc = convert_ist_to_utc(scheduled_ist)
        
        # Update scheduling fields
        update_data = {
            "scheduled_publish_at": scheduled_utc,
            "auto_publish_enabled": auto_publish,
            "scheduled_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "publish_status": "scheduled" if auto_publish else "draft"
        }
        
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
        logger.error(f"Failed to schedule horoscope: {str(e)}")
        raise HTTPException(status_code=500, detail="राशिफल को अनुसूचित करने में त्रुटि")

@news_router.delete("/horoscopes/{horoscope_id}/schedule", response_model=HoroscopePost, tags=["Horoscope Admin"])
async def cancel_horoscope_schedule(
    horoscope_id: str,
    current_user: User = Depends(get_current_admin_user_horoscope),
    db_client: MongoClient = Depends(db.get_client),
):
    """Cancel scheduled publishing for horoscope"""
    if not ObjectId.is_valid(horoscope_id):
        raise HTTPException(status_code=404, detail="राशिफल नहीं मिला")
    
    try:
        existing = db_client[db.db_name][HOROSCOPE_COLL].find_one({"_id": ObjectId(horoscope_id)})
        if not existing:
            raise HTTPException(status_code=404, detail="राशिफल नहीं मिला")
        
        # Cancel scheduling
        update_data = {
            "scheduled_publish_at": None,
            "auto_publish_enabled": False,
            "scheduled_at": None,
            "updated_at": datetime.utcnow(),
            "publish_status": "published" if existing.get("published") else "draft"
        }
        
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
        logger.error(f"Failed to cancel horoscope schedule: {str(e)}")
        raise HTTPException(status_code=500, detail="राशिफल शेड्यूल रद्द करने में त्रुटि")

@news_router.get("/admin/horoscopes/scheduled", response_model=List[HoroscopePost], tags=["Horoscope Admin"])
async def get_scheduled_horoscopes(
    current_user: User = Depends(get_current_admin_user_horoscope),
    db_client: MongoClient = Depends(db.get_client),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=50),
):
    """Get all scheduled horoscopes (Admin view)"""
    try:
        # Get horoscopes that are scheduled
        filter_query = {
            "publish_status": "scheduled",
            "auto_publish_enabled": True,
            "scheduled_publish_at": {"$ne": None}
        }
        
        skip = (page - 1) * limit
        scheduled_horoscopes = list(
            db_client[db.db_name][HOROSCOPE_COLL]
            .find(filter_query)
            .sort("scheduled_publish_at", 1)  # Earliest first
            .skip(skip)
            .limit(limit)
        )
        
        return [_normalize_horoscope(h) for h in scheduled_horoscopes]
        
    except Exception as e:
        logger.error(f"Failed to fetch scheduled horoscopes: {str(e)}")
        raise HTTPException(status_code=500, detail="अनुसूचित राशिफल लाने में त्रुटि")

@news_router.post("/admin/horoscopes/process-scheduled", response_model=dict, tags=["Horoscope Admin"])
async def process_scheduled_horoscopes(
    current_user: User = Depends(get_current_admin_user_horoscope),
    db_client: MongoClient = Depends(db.get_client),
):
    """Manually trigger processing of scheduled horoscopes (Admin only)"""
    try:
        current_utc = datetime.utcnow()
        
        # Find horoscopes that should be published now
        ready_to_publish = list(
            db_client[db.db_name][HOROSCOPE_COLL].find({
                "publish_status": "scheduled",
                "auto_publish_enabled": True,
                "scheduled_publish_at": {"$lte": current_utc}
            })
        )
        
        published_count = 0
        for horoscope in ready_to_publish:
            # Update to published status
            db_client[db.db_name][HOROSCOPE_COLL].update_one(
                {"_id": horoscope["_id"]},
                {
                    "$set": {
                        "published": True,
                        "published_at": current_utc,
                        "publish_status": "published",
                        "updated_at": current_utc
                    }
                }
            )
            published_count += 1
        
        return {
            "message": f"{published_count} राशिफल सफलतापूर्वक प्रकाशित किए गए",
            "published_count": published_count,
            "processed_at": current_utc.isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to process scheduled horoscopes: {str(e)}")
        raise HTTPException(status_code=500, detail="अनुसूचित राशिफल प्रोसेस करने में त्रुटि")

@news_router.get("/horoscopes/timezone-info", response_model=dict, tags=["Horoscope Public"])
async def get_timezone_info():
    """Get current IST time and timezone information for frontend"""
    try:
        current_ist = get_current_ist_time()
        current_utc = datetime.utcnow()
        
        return {
            "current_ist": current_ist.isoformat(),
            "current_utc": current_utc.isoformat(),
            "timezone": "Asia/Kolkata",
            "timezone_offset": "+05:30",
            "timezone_name": "Indian Standard Time (IST)"
        }
        
    except Exception as e:
        logger.error(f"Failed to get timezone info: {str(e)}")
        raise HTTPException(status_code=500, detail="समयक्षेत्र की जानकारी लाने में त्रुटि")
