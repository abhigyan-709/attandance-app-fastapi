# routes/news.py — gtnews18 news API (blogs parity) + Religious Content Scheduling
import math
import os
import re
import uuid
import logging
import calendar
from datetime import datetime, date, timedelta
from typing import List, Optional, Dict, Any
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
from pymongo import MongoClient, DESCENDING

from database.db import db
from models.news import (
    NewsPost, Comment, Category, ScheduledContent, ContentTemplate,
    ReligiousContentType, ScheduleStatus, ZodiacSign, HinduCalendarMonth,
    ScheduleRequest, ScheduledContentResponse, BulkScheduleRequest, DashboardStats,
    RashifalContent, PanchangContent, ThisDayHistoryContent, FestivalContent
)
from models.user import User
from routes.config import AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_REGION
from routes.user import get_current_user
from services.hindu_calendar import hindu_calendar_service

from pydantic import BaseModel, Field

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
NEWS_BASE_URL = os.getenv("NEWS_BASE_URL", "https://gtnews18.in")


def _slugify(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")

def _generate_seo_slug(title: str, news_id: str) -> str:
    """Generate SEO-friendly slug from title and ID"""
    # Handle both Hindi and English text
    base_slug = re.sub(r'[^a-zA-Z0-9\u0900-\u097F]+', '-', title.lower()).strip('-')
    # Limit slug length and ensure it ends with ID for uniqueness
    slug_part = base_slug[:50] if len(base_slug) > 50 else base_slug
    return f"{slug_part}-{news_id}"

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


NEWS_COLL = "news"
NEWS_COMMENTS_COLL = "news_comments"  # separate from blogs "comments"
SCHEDULED_CONTENT_COLL = "scheduled_religious_content"
CONTENT_TEMPLATES_COLL = "religious_content_templates"


def _normalize_news(doc: Dict[str, Any], db_client: MongoClient) -> Dict[str, Any]:
    doc["_id"] = str(doc["_id"])
    # attach comments by news_id (string id)
    comments = list(
        db_client[db.db_name][NEWS_COMMENTS_COLL].find({"news_id": doc["_id"]}).sort("created_at", DESCENDING)
    )
    for c in comments:
        c["_id"] = str(c["_id"])
    doc["comments"] = comments
    # counters
    doc["views"] = doc.get("views", 0)
    doc["viewed_ips"] = doc.get("viewed_ips", [])
    doc["likes"] = doc.get("likes", 0)
    doc["liked_ips"] = doc.get("liked_ips", [])
    
    # SEO fields (backward compatible - add if missing)
    if not doc.get("slug"):
        doc["slug"] = _generate_seo_slug(doc.get("title", ""), doc["_id"])
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


# ------------------------- Create news -------------------------
@news_router.post("/news", response_model=NewsPost, tags=["News"])
async def create_news(
    title: str = Form(...),
    content: str = Form(...),
    categories: str = Form(""),
    tags: List[str] = Form([]),
    published: bool = Form(True),
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = None,
    current_user: User = Depends(get_current_author_or_admin_user),
    db_client: MongoClient = Depends(db.get_client),
):
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

    news_data = {
        "title": title,
        "image_url": image_url,
        "content": content,
        "author_username": current_user.username,
        "categories": categories,
        "tags": tags,
        "published": published,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
        "views": 0,
        "viewed_ips": [],
        "likes": 0,
        "liked_ips": [],
    }

    inserted = db_client[db.db_name][NEWS_COLL].insert_one(news_data)
    news_id = str(inserted.inserted_id)
    news_data["_id"] = news_id

    # Auto-generate SEO data after insertion (backward compatible)
    seo_updates = {
        "slug": _generate_seo_slug(title, news_id),
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

    # 🔔 Notify subscribers (same notifier) only if published
    if published and background_tasks is not None:
        slug = _slugify(title)
        canonical_url = f"{NEWS_BASE_URL}/n/{news_id}-{slug}"
        background_tasks.add_task(_notify_new_blog_async, title, canonical_url, image_url)

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
    query: Dict[str, Any] = {}
    if _should_force_published_only(request, published):
        query["published"] = True
    elif published is not None:
        query["published"] = published

    docs = list(db_client[db.db_name][NEWS_COLL].find(query).sort("created_at", DESCENDING))
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
        "phone": (payload.phone or None),
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


# ------------------------- Update & Delete news (PROTECTED) -------------------------
@news_router.put("/news/{news_id}", response_model=NewsPost, tags=["News"])
async def update_news(
    news_id: str,
    updated_news: NewsPost,
    current_user: User = Depends(get_current_author_or_admin_user),
    db_client: MongoClient = Depends(db.get_client),
):
    if not ObjectId.is_valid(news_id):
        raise HTTPException(status_code=404, detail="News not found")
    existing = db_client[db.db_name][NEWS_COLL].find_one({"_id": ObjectId(news_id)})
    if not existing:
        raise HTTPException(status_code=404, detail="News not found")

    updated_news.updated_at = datetime.utcnow()
    db_client[db.db_name][NEWS_COLL].update_one(
        {"_id": ObjectId(news_id)},
        {
            "$set": updated_news.dict(
                by_alias=True,
                exclude={
                    "id",
                    "author_username",
                    "created_at",
                    "views",
                    "viewed_ips",
                    "likes",
                    "liked_ips",
                    "comments",
                },
            )
        },
    )
    updated_news.id = news_id
    return updated_news


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
async def get_news_by_slug(slug: str, db_client: MongoClient = Depends(db.get_client)):
    """Get news by SEO-friendly slug - backward compatible"""
    # Try to find by slug first
    doc = db_client[db.db_name][NEWS_COLL].find_one({"slug": slug, "published": True})
    
    # If not found by slug, try to extract ID from slug (format: title-words-id)
    if not doc:
        parts = slug.split('-')
        if parts:
            potential_id = parts[-1]  # Last part should be the ID
            if ObjectId.is_valid(potential_id):
                doc = db_client[db.db_name][NEWS_COLL].find_one({"_id": ObjectId(potential_id)})
    
    if not doc:
        raise HTTPException(status_code=404, detail="News not found")
    
    return _normalize_news(doc, db_client)

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


# ========================================================================================
# RELIGIOUS CONTENT SCHEDULING SYSTEM
# ========================================================================================

def _serialize_for_scheduled_content(data: Dict[str, Any]) -> Dict[str, Any]:
    """Convert Pydantic models to MongoDB-compatible format for scheduled content"""
    if isinstance(data, dict):
        result = {}
        for key, value in data.items():
            if hasattr(value, '__dict__'):  # Pydantic model
                result[key] = _serialize_for_scheduled_content(value.dict())
            elif isinstance(value, list):
                result[key] = [_serialize_for_scheduled_content(item) if isinstance(item, dict) else 
                              item.dict() if hasattr(item, 'dict') else item for item in value]
            elif hasattr(value, 'value'):  # Enum
                result[key] = value.value
            elif isinstance(value, (datetime, date)):
                result[key] = value.isoformat()
            else:
                result[key] = value
        return result
    return data

def _normalize_scheduled_content(doc: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize scheduled content from MongoDB"""
    doc["_id"] = str(doc["_id"])
    return doc


# ------------------------- Content Templates Management -------------------------

@news_router.post("/religious-content/templates", response_model=ContentTemplate, tags=["Religious Content"])
async def create_content_template(
    template: ContentTemplate,
    current_user: User = Depends(get_current_author_or_admin_user),
    db_client: MongoClient = Depends(db.get_client),
):
    """Create a new content template for recurring religious content"""
    template_data = _serialize_for_scheduled_content(template.dict(exclude={"id"}))
    template_data["created_by"] = current_user.username
    template_data["created_at"] = datetime.utcnow()
    
    result = db_client[db.db_name][CONTENT_TEMPLATES_COLL].insert_one(template_data)
    template_data["_id"] = str(result.inserted_id)
    
    return template_data

@news_router.get("/religious-content/templates", response_model=List[ContentTemplate], tags=["Religious Content"])
async def get_content_templates(
    content_type: Optional[ReligiousContentType] = Query(None),
    active_only: bool = Query(True),
    current_user: User = Depends(get_current_author_or_admin_user),
    db_client: MongoClient = Depends(db.get_client),
):
    """Get all content templates, optionally filtered by type"""
    query = {}
    if content_type:
        query["content_type"] = content_type.value
    if active_only:
        query["is_active"] = True
    
    templates = list(db_client[db.db_name][CONTENT_TEMPLATES_COLL].find(query).sort("created_at", DESCENDING))
    return [_normalize_scheduled_content(t) for t in templates]


# ------------------------- Scheduled Content CRUD -------------------------

@news_router.post("/religious-content/schedule", response_model=ScheduledContent, tags=["Religious Content"])
async def schedule_religious_content(
    request: ScheduleRequest,
    current_user: User = Depends(get_current_author_or_admin_user),
    db_client: MongoClient = Depends(db.get_client),
):
    """Schedule religious content for future publication"""
    
    # Create scheduled content document
    scheduled_data = {
        "content_type": request.content_type.value,
        "title": request.title,
        "content": request.content,
        "schedule_date": request.schedule_date,
        "schedule_status": ScheduleStatus.SCHEDULED.value,
        "author_username": current_user.username,
        "categories": "धर्म",  # Default religion category
        "tags": request.tags,
        "auto_publish": request.auto_publish,
        "timezone": "Asia/Kolkata",
        "created_at": datetime.utcnow(),
        "is_recurring": request.is_recurring,
        "recurrence_pattern": request.recurrence_pattern,
        "template_id": request.template_id,
    }
    
    # Add type-specific data
    if request.rashifal_data:
        scheduled_data["rashifal_data"] = [_serialize_for_scheduled_content(r.dict()) for r in request.rashifal_data]
    if request.panchang_data:
        scheduled_data["panchang_data"] = _serialize_for_scheduled_content(request.panchang_data.dict())
    if request.history_data:
        scheduled_data["history_data"] = [_serialize_for_scheduled_content(h.dict()) for h in request.history_data]
    if request.festival_data:
        scheduled_data["festival_data"] = _serialize_for_scheduled_content(request.festival_data.dict())
    
    # Calculate next schedule date for recurring content
    if request.is_recurring and request.recurrence_pattern:
        if request.recurrence_pattern == "daily":
            scheduled_data["next_schedule_date"] = request.schedule_date + timedelta(days=1)
        elif request.recurrence_pattern == "weekly":
            scheduled_data["next_schedule_date"] = request.schedule_date + timedelta(weeks=1)
        elif request.recurrence_pattern == "monthly":
            scheduled_data["next_schedule_date"] = request.schedule_date + timedelta(days=30)
    
    result = db_client[db.db_name][SCHEDULED_CONTENT_COLL].insert_one(scheduled_data)
    scheduled_data["_id"] = str(result.inserted_id)
    
    return _normalize_scheduled_content(scheduled_data)

@news_router.get("/religious-content/scheduled", response_model=List[ScheduledContentResponse], tags=["Religious Content"])
async def get_scheduled_content(
    content_type: Optional[ReligiousContentType] = Query(None),
    status: Optional[ScheduleStatus] = Query(None),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_author_or_admin_user),
    db_client: MongoClient = Depends(db.get_client),
):
    """Get scheduled religious content with filtering"""
    query = {}
    
    if content_type:
        query["content_type"] = content_type.value
    if status:
        query["schedule_status"] = status.value
    if start_date:
        query["schedule_date"] = {"$gte": datetime.combine(start_date, datetime.min.time())}
    if end_date:
        if "schedule_date" in query:
            query["schedule_date"]["$lte"] = datetime.combine(end_date, datetime.max.time())
        else:
            query["schedule_date"] = {"$lte": datetime.combine(end_date, datetime.max.time())}
    
    skip = (page - 1) * limit
    
    scheduled_items = list(
        db_client[db.db_name][SCHEDULED_CONTENT_COLL]
        .find(query)
        .sort("schedule_date", 1)
        .skip(skip)
        .limit(limit)
    )
    
    return [_normalize_scheduled_content(item) for item in scheduled_items]

@news_router.put("/religious-content/scheduled/{content_id}", response_model=ScheduledContent, tags=["Religious Content"])
async def update_scheduled_content(
    content_id: str,
    request: ScheduleRequest,
    current_user: User = Depends(get_current_author_or_admin_user),
    db_client: MongoClient = Depends(db.get_client),
):
    """Update scheduled religious content"""
    if not ObjectId.is_valid(content_id):
        raise HTTPException(status_code=404, detail="Scheduled content not found")
    
    existing = db_client[db.db_name][SCHEDULED_CONTENT_COLL].find_one({"_id": ObjectId(content_id)})
    if not existing:
        raise HTTPException(status_code=404, detail="Scheduled content not found")
    
    # Check authorization (admin or content author)
    if current_user.role != "admin" and existing.get("author_username") != current_user.username:
        raise HTTPException(status_code=403, detail="Not authorized to update this content")
    
    update_data = _serialize_for_scheduled_content(request.dict())
    update_data["updated_at"] = datetime.utcnow()
    
    db_client[db.db_name][SCHEDULED_CONTENT_COLL].update_one(
        {"_id": ObjectId(content_id)},
        {"$set": update_data}
    )
    
    updated = db_client[db.db_name][SCHEDULED_CONTENT_COLL].find_one({"_id": ObjectId(content_id)})
    return _normalize_scheduled_content(updated)

@news_router.delete("/religious-content/scheduled/{content_id}", tags=["Religious Content"])
async def delete_scheduled_content(
    content_id: str,
    current_user: User = Depends(get_current_author_or_admin_user),
    db_client: MongoClient = Depends(db.get_client),
):
    """Delete scheduled religious content"""
    if not ObjectId.is_valid(content_id):
        raise HTTPException(status_code=404, detail="Scheduled content not found")
    
    existing = db_client[db.db_name][SCHEDULED_CONTENT_COLL].find_one({"_id": ObjectId(content_id)})
    if not existing:
        raise HTTPException(status_code=404, detail="Scheduled content not found")
    
    # Check authorization
    if current_user.role != "admin" and existing.get("author_username") != current_user.username:
        raise HTTPException(status_code=403, detail="Not authorized to delete this content")
    
    db_client[db.db_name][SCHEDULED_CONTENT_COLL].delete_one({"_id": ObjectId(content_id)})
    return {"message": "Scheduled content deleted successfully"}


# ------------------------- Bulk Scheduling -------------------------

@news_router.post("/religious-content/bulk-schedule", tags=["Religious Content"])
async def bulk_schedule_content(
    request: BulkScheduleRequest,
    current_user: User = Depends(get_current_author_or_admin_user),
    db_client: MongoClient = Depends(db.get_client),
):
    """Bulk schedule content for multiple dates (useful for daily rashifal, panchang)"""
    
    # Get template if provided
    template = None
    if request.template_id:
        if ObjectId.is_valid(request.template_id):
            template = db_client[db.db_name][CONTENT_TEMPLATES_COLL].find_one({"_id": ObjectId(request.template_id)})
    
    if request.template_id and not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    scheduled_items = []
    current_date = request.start_date
    
    while current_date <= request.end_date:
        # Create schedule datetime
        schedule_time_parts = request.schedule_time.split(":")
        schedule_datetime = datetime.combine(
            current_date,
            datetime.min.time().replace(
                hour=int(schedule_time_parts[0]),
                minute=int(schedule_time_parts[1]) if len(schedule_time_parts) > 1 else 0
            )
        )
        
        # Generate content from template or use default title
        if template:
            title = template["template_content"].replace("{{date}}", current_date.strftime("%d %B %Y"))
            content = template["template_content"]
        else:
            title = f"{request.content_type.value.title()} - {current_date.strftime('%d %B %Y')}"
            content = f"Content for {current_date.strftime('%d %B %Y')}"
        
        scheduled_data = {
            "content_type": request.content_type.value,
            "title": title,
            "content": content,
            "schedule_date": schedule_datetime,
            "schedule_status": ScheduleStatus.SCHEDULED.value,
            "author_username": current_user.username,
            "categories": "धर्म",
            "tags": request.tags,
            "auto_publish": True,
            "timezone": "Asia/Kolkata",
            "created_at": datetime.utcnow(),
            "is_recurring": False,
            "template_id": request.template_id,
        }
        
        scheduled_items.append(scheduled_data)
        current_date += timedelta(days=1)
    
    # Bulk insert
    if scheduled_items:
        result = db_client[db.db_name][SCHEDULED_CONTENT_COLL].insert_many(scheduled_items)
        return {
            "message": f"Successfully scheduled {len(scheduled_items)} items",
            "scheduled_count": len(scheduled_items),
            "scheduled_ids": [str(id) for id in result.inserted_ids]
        }
    
    return {"message": "No items to schedule", "scheduled_count": 0}


# ------------------------- Publishing System -------------------------

@news_router.post("/religious-content/publish/{content_id}", tags=["Religious Content"])
async def publish_scheduled_content(
    content_id: str,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_author_or_admin_user),
    db_client: MongoClient = Depends(db.get_client),
):
    """Manually publish scheduled religious content"""
    if not ObjectId.is_valid(content_id):
        raise HTTPException(status_code=404, detail="Scheduled content not found")
    
    scheduled = db_client[db.db_name][SCHEDULED_CONTENT_COLL].find_one({"_id": ObjectId(content_id)})
    if not scheduled:
        raise HTTPException(status_code=404, detail="Scheduled content not found")
    
    # Convert scheduled content to regular news post
    news_data = {
        "title": scheduled["title"],
        "content": scheduled["content"],
        "author_username": scheduled["author_username"],
        "categories": scheduled.get("categories", "धर्म"),
        "tags": scheduled.get("tags", []),
        "published": True,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
        "views": 0,
        "viewed_ips": [],
        "likes": 0,
        "liked_ips": [],
        "content_type": scheduled.get("content_type"),
        "schedule_date": scheduled.get("schedule_date"),
        "schedule_status": ScheduleStatus.PUBLISHED.value,
    }
    
    # Add religious-specific data
    if "rashifal_data" in scheduled:
        news_data["rashifal_data"] = scheduled["rashifal_data"]
    if "panchang_data" in scheduled:
        news_data["panchang_data"] = scheduled["panchang_data"]
    
    # Generate SEO data
    news_data["slug"] = _generate_seo_slug(scheduled["title"], "")
    news_data["meta_title"] = scheduled["title"]
    news_data["meta_description"] = _extract_meta_description(scheduled["content"])
    news_data["keywords"] = _extract_keywords(scheduled["title"], scheduled["content"], scheduled.get("categories", ""))
    
    # Insert into news collection
    result = db_client[db.db_name][NEWS_COLL].insert_one(news_data)
    news_id = str(result.inserted_id)
    
    # Update SEO slug with actual ID
    news_data["slug"] = _generate_seo_slug(scheduled["title"], news_id)
    db_client[db.db_name][NEWS_COLL].update_one(
        {"_id": ObjectId(news_id)},
        {"$set": {"slug": news_data["slug"]}}
    )
    
    # Update scheduled content status
    db_client[db.db_name][SCHEDULED_CONTENT_COLL].update_one(
        {"_id": ObjectId(content_id)},
        {"$set": {
            "schedule_status": ScheduleStatus.PUBLISHED.value,
            "published_at": datetime.utcnow(),
            "published_news_id": news_id
        }}
    )
    
    # Send notifications
    if background_tasks:
        canonical_url = f"{NEWS_BASE_URL}/news/{news_data['slug']}"
        background_tasks.add_task(_notify_new_blog_async, scheduled["title"], canonical_url)
    
    return {
        "message": "Content published successfully",
        "news_id": news_id,
        "url": f"{NEWS_BASE_URL}/news/{news_data['slug']}"
    }


# ------------------------- Admin Dashboard -------------------------

@news_router.get("/religious-content/dashboard", response_model=DashboardStats, tags=["Religious Content"])
async def get_religious_content_dashboard(
    current_user: User = Depends(get_current_admin_user),
    db_client: MongoClient = Depends(db.get_client),
):
    """Get dashboard statistics for religious content management"""
    
    # Basic counts
    total_scheduled = db_client[db.db_name][SCHEDULED_CONTENT_COLL].count_documents({})
    
    today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = today_start + timedelta(days=1)
    
    published_today = db_client[db.db_name][SCHEDULED_CONTENT_COLL].count_documents({
        "schedule_status": ScheduleStatus.PUBLISHED.value,
        "published_at": {"$gte": today_start, "$lt": today_end}
    })
    
    pending_approval = db_client[db.db_name][SCHEDULED_CONTENT_COLL].count_documents({
        "schedule_status": ScheduleStatus.SCHEDULED.value,
        "schedule_date": {"$lte": datetime.utcnow()}
    })
    
    failed_publications = db_client[db.db_name][SCHEDULED_CONTENT_COLL].count_documents({
        "schedule_status": ScheduleStatus.EXPIRED.value
    })
    
    # Content type breakdown
    pipeline = [
        {"$group": {"_id": "$content_type", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}}
    ]
    content_breakdown = list(db_client[db.db_name][SCHEDULED_CONTENT_COLL].aggregate(pipeline))
    content_type_breakdown = {item["_id"]: item["count"] for item in content_breakdown}
    
    # Upcoming schedules (next 7 days)
    next_week = datetime.utcnow() + timedelta(days=7)
    upcoming = list(
        db_client[db.db_name][SCHEDULED_CONTENT_COLL]
        .find({
            "schedule_status": ScheduleStatus.SCHEDULED.value,
            "schedule_date": {"$gte": datetime.utcnow(), "$lte": next_week}
        })
        .sort("schedule_date", 1)
        .limit(10)
    )
    
    upcoming_schedules = [_normalize_scheduled_content(item) for item in upcoming]
    
    return {
        "total_scheduled": total_scheduled,
        "published_today": published_today,
        "pending_approval": pending_approval,
        "failed_publications": failed_publications,
        "content_type_breakdown": content_type_breakdown,
        "upcoming_schedules": upcoming_schedules
    }


# ------------------------- Hindu Calendar Integration -------------------------

@news_router.get("/religious-content/calendar/festivals", tags=["Religious Content"])
async def get_hindu_festivals(
    month: Optional[int] = Query(None, ge=1, le=12),
    year: Optional[int] = Query(None, ge=2024, le=2030),
    current_user: User = Depends(get_current_author_or_admin_user),
):
    """Get Hindu festivals for scheduling content around important dates"""
    
    current_year = year or datetime.now().year
    
    if month:
        festivals = hindu_calendar_service.get_festivals_for_month(month, current_year)
        return {"month": month, "year": current_year, "festivals": festivals}
    else:
        all_festivals = hindu_calendar_service.get_festivals_for_year(current_year)
        return {"year": current_year, "festivals_by_month": all_festivals}

@news_router.get("/religious-content/calendar/panchang", tags=["Religious Content"])
async def get_daily_panchang(
    date_requested: Optional[date] = Query(None),
    current_user: User = Depends(get_current_author_or_admin_user),
):
    """Get panchang data for a specific date (for content scheduling)"""
    
    target_date = date_requested or date.today()
    panchang_data = hindu_calendar_service.generate_daily_panchang(target_date)
    
    return panchang_data

@news_router.get("/religious-content/calendar/auspicious-dates", tags=["Religious Content"])
async def get_auspicious_dates_for_scheduling(
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    days_ahead: int = Query(30, ge=1, le=90),
    current_user: User = Depends(get_current_author_or_admin_user),
):
    """Get auspicious dates for scheduling religious content"""
    
    if not start_date:
        start_date = date.today()
    if not end_date:
        end_date = start_date + timedelta(days=days_ahead)
    
    auspicious_dates = hindu_calendar_service.get_auspicious_dates_for_content_scheduling(
        start_date, end_date
    )
    
    return {
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "auspicious_dates": auspicious_dates,
        "total_count": len(auspicious_dates)
    }

@news_router.get("/religious-content/calendar/monthly-overview", tags=["Religious Content"])
async def get_monthly_calendar_overview(
    month: int = Query(..., ge=1, le=12),
    year: int = Query(..., ge=2024, le=2030),
    current_user: User = Depends(get_current_author_or_admin_user),
    db_client: MongoClient = Depends(db.get_client),
):
    """Get comprehensive monthly overview for content planning"""
    
    # Get festivals for the month
    festivals = hindu_calendar_service.get_festivals_for_month(month, year)
    
    # Get auspicious dates for the month
    start_date = date(year, month, 1)
    end_date = date(year, month, calendar.monthrange(year, month)[1])
    auspicious_dates = hindu_calendar_service.get_auspicious_dates_for_content_scheduling(
        start_date, end_date
    )
    
    # Generate daily panchang for the entire month
    daily_panchang = []
    current_date = start_date
    while current_date <= end_date:
        panchang = hindu_calendar_service.generate_daily_panchang(current_date)
        daily_panchang.append(panchang)
        current_date += timedelta(days=1)
    
    # Get existing scheduled content for the month
    scheduled_content = list(
        db_client[db.db_name][SCHEDULED_CONTENT_COLL].find({
            "schedule_date": {
                "$gte": datetime.combine(start_date, datetime.min.time()),
                "$lte": datetime.combine(end_date, datetime.max.time())
            }
        }).sort("schedule_date", 1)
    )
    
    return {
        "month": month,
        "year": year,
        "festivals": festivals,
        "auspicious_dates": auspicious_dates,
        "daily_panchang": daily_panchang,
        "scheduled_content": [_normalize_scheduled_content(item) for item in scheduled_content],
        "content_scheduling_suggestions": _generate_monthly_content_suggestions(
            month, year, festivals, auspicious_dates
        )
    }

def _generate_monthly_content_suggestions(month: int, year: int, festivals: List[Dict], 
                                        auspicious_dates: List[Dict]) -> List[Dict]:
    """Generate content scheduling suggestions for the month"""
    suggestions = []
    
    # Suggest content around major festivals
    for festival in festivals:
        if festival.get("is_major", False):
            festival_date = datetime.fromisoformat(festival["date"]).date()
            
            # Suggest content 3 days before festival
            pre_festival_date = festival_date - timedelta(days=3)
            suggestions.append({
                "date": pre_festival_date.isoformat(),
                "content_type": "festival_preparation",
                "title": f"{festival['hindi_name']} की तैयारी",
                "description": f"आने वाले {festival['hindi_name']} के लिए तैयारी और महत्व",
                "priority": "high"
            })
            
            # Suggest content on festival day
            suggestions.append({
                "date": festival["date"],
                "content_type": "festival_celebration",
                "title": f"{festival['hindi_name']} की शुभकामनाएं",
                "description": f"{festival['hindi_name']} के अवसर पर विशेष सामग्री",
                "priority": "high"
            })
    
    # Suggest weekly rashifal on Sundays
    start_date = date(year, month, 1)
    end_date = date(year, month, calendar.monthrange(year, month)[1])
    current_date = start_date
    
    while current_date <= end_date:
        if current_date.weekday() == 6:  # Sunday
            suggestions.append({
                "date": current_date.isoformat(),
                "content_type": "weekly_rashifal",
                "title": f"साप्ताहिक राशिफल - {current_date.strftime('%d %B %Y')}",
                "description": "आने वाले सप्ताह का विस्तृत राशिफल",
                "priority": "medium"
            })
        current_date += timedelta(days=1)
    
    # Suggest daily panchang content
    suggestions.append({
        "date": "daily",
        "content_type": "daily_panchang",
        "title": "दैनिक पंचांग",
        "description": "रोज सुबह 6 बजे दैनिक पंचांग प्रकाशित करें",
        "priority": "high",
        "recurring": True
    })
    
    return suggestions


# ------------------------- Admin UI Support Endpoints -------------------------

@news_router.get("/admin/religious-content/overview", tags=["Admin"])
async def admin_religious_content_overview(
    current_user: User = Depends(get_current_admin_user),
    db_client: MongoClient = Depends(db.get_client),
):
    """Admin overview of all religious content activities"""
    
    # Get counts by status
    status_counts = {}
    for status in ScheduleStatus:
        count = db_client[db.db_name][SCHEDULED_CONTENT_COLL].count_documents({
            "schedule_status": status.value
        })
        status_counts[status.value] = count
    
    # Get counts by content type
    type_counts = {}
    for content_type in ReligiousContentType:
        count = db_client[db.db_name][SCHEDULED_CONTENT_COLL].count_documents({
            "content_type": content_type.value
        })
        type_counts[content_type.value] = count
    
    # Recent activity (last 30 days)
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    recent_activity = list(
        db_client[db.db_name][SCHEDULED_CONTENT_COLL]
        .find({"created_at": {"$gte": thirty_days_ago}})
        .sort("created_at", -1)
        .limit(20)
    )
    
    # Failed publications that need attention
    failed_items = list(
        db_client[db.db_name][SCHEDULED_CONTENT_COLL]
        .find({"schedule_status": ScheduleStatus.EXPIRED.value})
        .sort("schedule_date", -1)
        .limit(10)
    )
    
    return {
        "status_counts": status_counts,
        "type_counts": type_counts,
        "recent_activity": [_normalize_scheduled_content(item) for item in recent_activity],
        "failed_items": [_normalize_scheduled_content(item) for item in failed_items],
        "total_templates": db_client[db.db_name][CONTENT_TEMPLATES_COLL].count_documents({}),
        "active_templates": db_client[db.db_name][CONTENT_TEMPLATES_COLL].count_documents({"is_active": True})
    }

@news_router.get("/admin/religious-content/authors", tags=["Admin"])
async def get_religious_content_authors_stats(
    current_user: User = Depends(get_current_admin_user),
    db_client: MongoClient = Depends(db.get_client),
):
    """Get statistics by author for religious content"""
    
    pipeline = [
        {"$group": {
            "_id": "$author_username",
            "total_content": {"$sum": 1},
            "published": {"$sum": {"$cond": [{"$eq": ["$schedule_status", "published"]}, 1, 0]}},
            "scheduled": {"$sum": {"$cond": [{"$eq": ["$schedule_status", "scheduled"]}, 1, 0]}},
            "failed": {"$sum": {"$cond": [{"$eq": ["$schedule_status", "expired"]}, 1, 0]}},
            "last_activity": {"$max": "$created_at"}
        }},
        {"$sort": {"total_content": -1}}
    ]
    
    author_stats = list(db_client[db.db_name][SCHEDULED_CONTENT_COLL].aggregate(pipeline))
    
    return {"author_statistics": author_stats}

@news_router.post("/admin/religious-content/bulk-actions", tags=["Admin"])
async def bulk_actions_on_scheduled_content(
    action: str = Body(...),  # "publish", "delete", "reschedule"
    content_ids: List[str] = Body(...),
    new_schedule_date: Optional[datetime] = Body(None),
    current_user: User = Depends(get_current_admin_user),
    db_client: MongoClient = Depends(db.get_client),
):
    """Perform bulk actions on scheduled religious content"""
    
    if not content_ids:
        raise HTTPException(status_code=400, detail="No content IDs provided")
    
    # Validate content IDs
    valid_ids = [ObjectId(id) for id in content_ids if ObjectId.is_valid(id)]
    if len(valid_ids) != len(content_ids):
        raise HTTPException(status_code=400, detail="Invalid content IDs provided")
    
    results = {"success_count": 0, "error_count": 0, "errors": []}
    
    if action == "delete":
        try:
            delete_result = db_client[db.db_name][SCHEDULED_CONTENT_COLL].delete_many({
                "_id": {"$in": valid_ids}
            })
            results["success_count"] = delete_result.deleted_count
        except Exception as e:
            results["error_count"] = len(content_ids)
            results["errors"].append(f"Bulk delete failed: {str(e)}")
    
    elif action == "reschedule":
        if not new_schedule_date:
            raise HTTPException(status_code=400, detail="New schedule date required for reschedule action")
        
        try:
            update_result = db_client[db.db_name][SCHEDULED_CONTENT_COLL].update_many(
                {"_id": {"$in": valid_ids}},
                {"$set": {
                    "schedule_date": new_schedule_date,
                    "schedule_status": ScheduleStatus.SCHEDULED.value,
                    "updated_at": datetime.utcnow()
                }}
            )
            results["success_count"] = update_result.modified_count
        except Exception as e:
            results["error_count"] = len(content_ids)
            results["errors"].append(f"Bulk reschedule failed: {str(e)}")
    
    elif action == "publish":
        # Publish each item individually to handle errors gracefully
        for content_id in valid_ids:
            try:
                # Get the scheduled content
                scheduled = db_client[db.db_name][SCHEDULED_CONTENT_COLL].find_one({"_id": content_id})
                if not scheduled:
                    results["error_count"] += 1
                    results["errors"].append(f"Content {content_id} not found")
                    continue
                
                # Publish the content (similar to individual publish endpoint)
                news_data = {
                    "title": scheduled["title"],
                    "content": scheduled["content"],
                    "author_username": scheduled["author_username"],
                    "categories": scheduled.get("categories", "धर्म"),
                    "tags": scheduled.get("tags", []),
                    "published": True,
                    "created_at": datetime.utcnow(),
                    "updated_at": datetime.utcnow(),
                    "views": 0,
                    "viewed_ips": [],
                    "likes": 0,
                    "liked_ips": [],
                    "content_type": scheduled.get("content_type"),
                    "schedule_date": scheduled.get("schedule_date"),
                    "schedule_status": ScheduleStatus.PUBLISHED.value,
                }
                
                # Add religious-specific data
                for field in ["rashifal_data", "panchang_data", "history_data", "festival_data"]:
                    if field in scheduled:
                        news_data[field] = scheduled[field]
                
                # Generate SEO data
                news_data["slug"] = _generate_seo_slug(scheduled["title"], "")
                news_data["meta_title"] = scheduled["title"]
                news_data["meta_description"] = _extract_meta_description(scheduled["content"])
                news_data["keywords"] = _extract_keywords(
                    scheduled["title"], 
                    scheduled["content"], 
                    scheduled.get("categories", "")
                )
                
                # Insert into news collection
                result = db_client[db.db_name][NEWS_COLL].insert_one(news_data)
                news_id = str(result.inserted_id)
                
                # Update SEO slug with actual ID
                news_data["slug"] = _generate_seo_slug(scheduled["title"], news_id)
                db_client[db.db_name][NEWS_COLL].update_one(
                    {"_id": ObjectId(news_id)},
                    {"$set": {"slug": news_data["slug"]}}
                )
                
                # Update scheduled content status
                db_client[db.db_name][SCHEDULED_CONTENT_COLL].update_one(
                    {"_id": content_id},
                    {"$set": {
                        "schedule_status": ScheduleStatus.PUBLISHED.value,
                        "published_at": datetime.utcnow(),
                        "published_news_id": news_id
                    }}
                )
                
                results["success_count"] += 1
                
            except Exception as e:
                results["error_count"] += 1
                results["errors"].append(f"Failed to publish {content_id}: {str(e)}")
    
    else:
        raise HTTPException(status_code=400, detail="Invalid action. Use 'publish', 'delete', or 'reschedule'")
    
    return results

@news_router.get("/admin/religious-content/performance", tags=["Admin"])
async def get_religious_content_performance(
    days: int = Query(30, ge=1, le=365),
    current_user: User = Depends(get_current_admin_user),
    db_client: MongoClient = Depends(db.get_client),
):
    """Get performance metrics for religious content"""
    
    start_date = datetime.utcnow() - timedelta(days=days)
    
    # Get published religious content from news collection
    published_religious = list(
        db_client[db.db_name][NEWS_COLL].find({
            "content_type": {"$exists": True},
            "created_at": {"$gte": start_date}
        })
    )
    
    # Calculate metrics
    total_views = sum(item.get("views", 0) for item in published_religious)
    total_likes = sum(item.get("likes", 0) for item in published_religious)
    avg_views = total_views / len(published_religious) if published_religious else 0
    avg_likes = total_likes / len(published_religious) if published_religious else 0
    
    # Performance by content type
    type_performance = {}
    for content_type in ReligiousContentType:
        type_items = [item for item in published_religious if item.get("content_type") == content_type.value]
        if type_items:
            type_performance[content_type.value] = {
                "count": len(type_items),
                "total_views": sum(item.get("views", 0) for item in type_items),
                "total_likes": sum(item.get("likes", 0) for item in type_items),
                "avg_views": sum(item.get("views", 0) for item in type_items) / len(type_items),
                "avg_likes": sum(item.get("likes", 0) for item in type_items) / len(type_items),
            }
    
    # Top performing content
    top_viewed = sorted(published_religious, key=lambda x: x.get("views", 0), reverse=True)[:10]
    top_liked = sorted(published_religious, key=lambda x: x.get("likes", 0), reverse=True)[:10]
    
    return {
        "period_days": days,
        "total_published": len(published_religious),
        "total_views": total_views,
        "total_likes": total_likes,
        "avg_views_per_content": round(avg_views, 2),
        "avg_likes_per_content": round(avg_likes, 2),
        "performance_by_type": type_performance,
        "top_viewed": [{"title": item["title"], "views": item.get("views", 0), "_id": str(item["_id"])} for item in top_viewed],
        "top_liked": [{"title": item["title"], "likes": item.get("likes", 0), "_id": str(item["_id"])} for item in top_liked]
    }

# ------------------------- Quick Actions for UI -------------------------

@news_router.post("/religious-content/quick-schedule", tags=["Religious Content"])
async def quick_schedule_daily_content(
    content_type: ReligiousContentType = Body(...),
    days_ahead: int = Body(7, ge=1, le=30),
    time_slot: str = Body("06:00"),  # Default morning time
    current_user: User = Depends(get_current_author_or_admin_user),
    db_client: MongoClient = Depends(db.get_client),
):
    """Quick schedule for daily content like rashifal, panchang for multiple days"""
    
    scheduled_items = []
    
    for day_offset in range(days_ahead):
        target_date = date.today() + timedelta(days=day_offset + 1)
        
        # Create schedule datetime
        time_parts = time_slot.split(":")
        schedule_datetime = datetime.combine(
            target_date,
            datetime.min.time().replace(
                hour=int(time_parts[0]),
                minute=int(time_parts[1]) if len(time_parts) > 1 else 0
            )
        )
        
        # Generate content based on type
        if content_type == ReligiousContentType.RASHIFAL:
            title = f"आज का राशिफल - {target_date.strftime('%d %B %Y')}"
            content = f"आज {target_date.strftime('%d %B %Y')} का राशिफल - सभी 12 राशियों के लिए विस्तृत भविष्यफल।"
        elif content_type == ReligiousContentType.PANCHANG:
            title = f"आज का पंचांग - {target_date.strftime('%d %B %Y')}"
            content = f"आज {target_date.strftime('%d %B %Y')} का संपूर्ण पंचांग - तिथि, नक्षत्र, योग, करण और शुभ मुहूर्त।"
        elif content_type == ReligiousContentType.THIS_DAY_HISTORY:
            title = f"आज का इतिहास - {target_date.strftime('%d %B %Y')}"
            content = f"इतिहास में आज {target_date.strftime('%d %B %Y')} के दिन क्या घटित हुआ था।"
        else:
            title = f"{content_type.value.title()} - {target_date.strftime('%d %B %Y')}"
            content = f"Content for {target_date.strftime('%d %B %Y')}"
        
        scheduled_data = {
            "content_type": content_type.value,
            "title": title,
            "content": content,
            "schedule_date": schedule_datetime,
            "schedule_status": ScheduleStatus.SCHEDULED.value,
            "author_username": current_user.username,
            "categories": "धर्म",
            "tags": [content_type.value, "daily"],
            "auto_publish": True,
            "timezone": "Asia/Kolkata",
            "created_at": datetime.utcnow(),
            "is_recurring": False,
        }
        
        scheduled_items.append(scheduled_data)
    
    # Bulk insert
    if scheduled_items:
        result = db_client[db.db_name][SCHEDULED_CONTENT_COLL].insert_many(scheduled_items)
        return {
            "message": f"Successfully scheduled {len(scheduled_items)} {content_type.value} items",
            "scheduled_count": len(scheduled_items),
            "scheduled_ids": [str(id) for id in result.inserted_ids]
        }
    
    return {"message": "No items to schedule", "scheduled_count": 0}

@news_router.get("/religious-content/template-suggestions", tags=["Religious Content"])
async def get_template_suggestions(
    content_type: ReligiousContentType = Query(...),
    current_user: User = Depends(get_current_author_or_admin_user),
):
    """Get template suggestions for different religious content types"""
    
    templates = {
        ReligiousContentType.RASHIFAL: {
            "title_template": "आज का राशिफल - {{date}}",
            "content_template": """
आज {{date}} का संपूर्ण राशिफल:

🌟 मेष राशि: {{mesh_prediction}}
🌟 वृषभ राशि: {{vrishabh_prediction}}
🌟 मिथुन राशि: {{mithun_prediction}}
... (अन्य राशियां)

आज का शुभ समय: {{auspicious_time}}
बचने योग्य समय: {{avoid_time}}
""",
            "variables": ["date", "mesh_prediction", "vrishabh_prediction", "auspicious_time", "avoid_time"]
        },
        ReligiousContentType.PANCHANG: {
            "title_template": "आज का पंचांग - {{date}}",
            "content_template": """
आज {{date}} का संपूर्ण पंचांग:

📅 तिथि: {{tithi}}
⭐ नक्षत्र: {{nakshatra}}
🕉️ योग: {{yoga}}
🌙 करण: {{karana}}

🌅 सूर्योदय: {{sunrise}}
🌇 सूर्यास्त: {{sunset}}

शुभ मुहूर्त: {{auspicious_time}}
अशुभ काल: {{inauspicious_time}}
""",
            "variables": ["date", "tithi", "nakshatra", "yoga", "karana", "sunrise", "sunset", "auspicious_time", "inauspicious_time"]
        },
        ReligiousContentType.THIS_DAY_HISTORY: {
            "title_template": "आज का इतिहास - {{date}}",
            "content_template": """
इतिहास में आज {{date}} के दिन:

📜 प्रमुख घटनाएं:
• {{event_1}}
• {{event_2}}
• {{event_3}}

🎭 जन्मदिन:
• {{birthday_1}}
• {{birthday_2}}

📖 महत्वपूर्ण तथ्य:
{{important_fact}}
""",
            "variables": ["date", "event_1", "event_2", "event_3", "birthday_1", "birthday_2", "important_fact"]
        }
    }
    
    return templates.get(content_type, {
        "title_template": f"{content_type.value.title()} - {{{{date}}}}",
        "content_template": f"Content for {content_type.value} on {{{{date}}}}",
        "variables": ["date"]
    })
