# routes/blogs.py — fixed ordering + public/admin split + robust tags + related
import math
import os
import re
import uuid
import logging
from datetime import datetime
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
from models.blogs import BlogPost, Comment, Category
from models.user import User
from routes.config import AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_REGION
from routes.user import get_current_user

from pydantic import BaseModel

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

blog_router = APIRouter()

AWS_BUCKET_NAME = "projectdevops-blogs-new"
s3_client = boto3.client(
    "s3",
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    region_name=AWS_REGION,
)

# --- web-push notify plumbing (uses your /push/notify-new-blog) ---
PUBLIC_API_BASE = os.getenv("PUBLIC_API_BASE", "http://localhost:8000")
ADMIN_API_TOKEN = os.getenv("ADMIN_API_TOKEN")
BLOG_BASE_URL = os.getenv("BLOG_BASE_URL", "https://blogs.projectdevops.in")


def _slugify(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def _notify_new_blog_async(title: str, url: str, image: Optional[str] = None):
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
    """
    If 'published' query is NOT provided:
      - Public (no Authorization header): return True => force published=True
      - Admin/author (Authorization present): return False => return all
    If 'published' query IS provided: never force; respect the explicit filter.
    """
    if published_param is not None:
        return False
    auth = (request.headers.get("Authorization") or "").strip()
    return not bool(auth)


def _normalize_blog(doc: Dict[str, Any], db_client: MongoClient) -> Dict[str, Any]:
    doc["_id"] = str(doc["_id"])
    # attach comments
    comments = list(db_client[db.db_name]["comments"].find({"blog_id": doc["_id"]}))
    for c in comments:
        c["_id"] = str(c["_id"])
    doc["comments"] = comments
    # normalize optional counters
    doc["views"] = doc.get("views", 0)
    doc["viewed_ips"] = doc.get("viewed_ips", [])
    doc["likes"] = doc.get("likes", 0)
    doc["liked_ips"] = doc.get("liked_ips", [])
    return doc


# ------------------------- Create blog -------------------------
@blog_router.post("/blogs", response_model=BlogPost, tags=["Blogs"])
async def create_blog(
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
    unique_filename = f"blogs/{uuid.uuid4()}.{file_extension}"

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

    blog_data = {
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

    inserted_blog = db_client[db.db_name]["blogs"].insert_one(blog_data)
    blog_id = str(inserted_blog.inserted_id)
    blog_data["_id"] = blog_id

    # 🔔 Notify subscribers (fire-and-forget) only if published
    if published and background_tasks is not None:
        slug = _slugify(title)
        canonical_url = f"{BLOG_BASE_URL}/b/{blog_id}-{slug}"
        background_tasks.add_task(_notify_new_blog_async, title, canonical_url, image_url)

    return blog_data


# ====================================================================================
# IMPORTANT: All static /blogs/* endpoints come BEFORE the dynamic /blogs/{blog_id}
# ====================================================================================

# ------------------------- Read/list (PUBLIC) -------------------------
@blog_router.get("/blogs", response_model=List[BlogPost], tags=["Blogs"])
async def get_blogs(
    request: Request,
    published: Optional[bool] = Query(default=None),
    db_client: MongoClient = Depends(db.get_client),
):
    query: Dict[str, Any] = {}
    if _should_force_published_only(request, published):
        query["published"] = True
    elif published is not None:
        query["published"] = published

    blogs = list(db_client[db.db_name]["blogs"].find(query).sort("created_at", DESCENDING))
    return [_normalize_blog(b, db_client) for b in blogs]


@blog_router.get("/blogs/stats", tags=["Blogs"])
async def blogs_stats(db_client: MongoClient = Depends(db.get_client)):
    coll = db_client[db.db_name]["blogs"]
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
@blog_router.get("/blogs/filter", response_model=List[BlogPost], tags=["Blogs"])
async def get_blogs_by_category_and_tags(
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

    blogs = list(db_client[db.db_name]["blogs"].find(query).sort("created_at", DESCENDING))
    return [_normalize_blog(b, db_client) for b in blogs]


@blog_router.get("/blogs/tags", response_model=List[str], tags=["Blogs"])
async def get_all_tags(db_client: MongoClient = Depends(db.get_client)):
    """
    Robust tag list:
    - works if 'tags' is an array
    - works if 'tags' is a single string
    - ignores null/empty
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
    rows = db_client[db.db_name]["blogs"].aggregate(pipeline)
    return [r["_id"] for r in rows]


@blog_router.get("/blogs/category/{category_name}", response_model=List[BlogPost], tags=["Blogs"])
async def get_blogs_by_category(
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

    blogs = list(db_client[db.db_name]["blogs"].find(query).sort("created_at", DESCENDING))
    if not blogs:
        raise HTTPException(status_code=404, detail="No blogs found for this category")
    return [_normalize_blog(b, db_client) for b in blogs]


@blog_router.get("/blogs/tags/{tag}", response_model=List[BlogPost], tags=["Blogs"])
async def get_blogs_by_tag(
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

    blogs = list(db_client[db.db_name]["blogs"].find(query).sort("created_at", DESCENDING))
    return [_normalize_blog(b, db_client) for b in blogs]


# ------------------------- Search & Suggest (PUBLIC) -------------------------
_TEXT_INDEX_NAME = "blogs_text_idx"


def _ensure_text_index(db_client: MongoClient):
    coll = db_client[db.db_name]["blogs"]
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


@blog_router.get("/blogs/search", response_model=List[BlogPost], tags=["Blogs"])
async def search_blogs(
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

    coll = db_client[db.db_name]["blogs"]

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

    return [_normalize_blog(d, db_client) for d in docs]


@blog_router.get("/blogs/suggest", response_model=List[Dict[str, str]], tags=["Blogs"])
async def suggest_blogs(
    request: Request,
    q: str = Query(..., min_length=1),
    limit: int = Query(8, ge=1, le=20),
    db_client: MongoClient = Depends(db.get_client),
):
    base: Dict[str, Any] = {}
    if _should_force_published_only(request, None):
        base["published"] = True

    regex = re.compile(re.escape(q), re.IGNORECASE)
    coll = db_client[db.db_name]["blogs"]
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
@blog_router.get("/blogs/{blog_id}/related", response_model=List[BlogPost], tags=["Blogs"])
async def related_blogs(
    blog_id: str,
    limit: int = Query(5, ge=1, le=10),
    db_client: MongoClient = Depends(db.get_client),
):
    if not ObjectId.is_valid(blog_id):
        raise HTTPException(status_code=404, detail="Blog not found")
    me = db_client[db.db_name]["blogs"].find_one({"_id": ObjectId(blog_id)})
    if not me:
        raise HTTPException(status_code=404, detail="Blog not found")

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
        db_client[db.db_name]["blogs"]
        .find(q)
        .sort("created_at", DESCENDING)
        .limit(limit)
    )
    return [_normalize_blog(d, db_client) for d in docs]


# ------------------------- Views & Likes (PUBLIC) -------------------------
@blog_router.post("/blogs/{blog_id}/views", response_model=dict, tags=["Blogs"])
async def increment_blog_views(
    blog_id: str,
    request: Request,
    db_client: MongoClient = Depends(db.get_client),
):
    if not ObjectId.is_valid(blog_id):
        raise HTTPException(status_code=404, detail="Blog not found")
    blog = db_client[db.db_name]["blogs"].find_one({"_id": ObjectId(blog_id)})
    if not blog:
        raise HTTPException(status_code=404, detail="Blog not found")

    client_ip = request.headers.get("X-Forwarded-For", request.client.host)
    if client_ip and "," in client_ip:
        client_ip = client_ip.split(",")[0].strip()
    if not client_ip:
        logger.warning("No valid client IP detected for views")
        client_ip = "unknown"

    viewed_ips = blog.get("viewed_ips", [])
    current_views = blog.get("views", 0)

    if client_ip not in viewed_ips:
        viewed_ips.append(client_ip)
        current_views += 1
        db_client[db.db_name]["blogs"].update_one(
            {"_id": ObjectId(blog_id)},
            {"$set": {"viewed_ips": viewed_ips, "views": current_views}},
        )

    return {"views": current_views}


@blog_router.post("/blogs/{blog_id}/likes", response_model=dict, tags=["Blogs"])
async def increment_blog_likes(
    blog_id: str,
    request: Request,
    db_client: MongoClient = Depends(db.get_client),
):
    if not ObjectId.is_valid(blog_id):
        raise HTTPException(status_code=404, detail="Blog not found")
    blog = db_client[db.db_name]["blogs"].find_one({"_id": ObjectId(blog_id)})
    if not blog:
        raise HTTPException(status_code=404, detail="Blog not found")

    client_ip = request.headers.get("X-Forwarded-For", request.client.host)
    if client_ip and "," in client_ip:
        client_ip = client_ip.split(",")[0].strip()
    if not client_ip:
        logger.warning("No valid client IP detected for likes")
        client_ip = "unknown"

    liked_ips = blog.get("liked_ips", [])
    current_likes = blog.get("likes", 0)

    if client_ip not in liked_ips:
        liked_ips.append(client_ip)
        current_likes += 1
        db_client[db.db_name]["blogs"].update_one(
            {"_id": ObjectId(blog_id)},
            {"$set": {"liked_ips": liked_ips, "likes": current_likes}},
        )

    return {"likes": current_likes}


# ------------------------- Comments (PUBLIC read, protected write) -------------------------
@blog_router.get("/blogs/{blog_id}/comments", response_model=List[Comment], tags=["Blogs"])
async def list_comments_for_blog(blog_id: str, db_client: MongoClient = Depends(db.get_client)):
    comments = list(db_client[db.db_name]["comments"].find({"blog_id": blog_id}).sort("created_at", DESCENDING))
    for c in comments:
        c["_id"] = str(c["_id"])
    return comments


class CommentCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=80)
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    content: str = Field(..., min_length=1, max_length=5000)

# ------------------------- Comments (PUBLIC create) -------------------------
@blog_router.post("/blogs/{blog_id}/comments", response_model=Comment, tags=["Blogs"])
async def create_comment_for_blog(
    blog_id: str,
    payload: CommentCreate = Body(...),
    db_client: MongoClient = Depends(db.get_client),
):
    # verify blog exists (blogs collection uses ObjectId)
    if not ObjectId.is_valid(blog_id):
        raise HTTPException(status_code=404, detail="Blog not found")
    if not db_client[db.db_name]["blogs"].find_one({"_id": ObjectId(blog_id)}):
        raise HTTPException(status_code=404, detail="Blog not found")

    # persist blog_id as STRING (your list uses {"blog_id": blog_id})
    doc = {
        "blog_id": blog_id,
        "name": payload.name.strip(),
        "email": (payload.email or None),
        "phone": (payload.phone or None),
        "content": payload.content.strip(),
        "created_at": datetime.utcnow(),
    }

    res = db_client[db.db_name]["comments"].insert_one(doc)
    doc["_id"] = str(res.inserted_id)
    return doc

@blog_router.put("/comments/{comment_id}", response_model=Comment, tags=["Blogs"])
async def update_comment(
    comment_id: str,
    payload: Comment,
    current_user: User = Depends(get_current_author_or_admin_user),
    db_client: MongoClient = Depends(db.get_client),
):
    if not ObjectId.is_valid(comment_id):
        raise HTTPException(status_code=404, detail="Comment not found")
    existing = db_client[db.db_name]["comments"].find_one({"_id": ObjectId(comment_id)})
    if not existing:
        raise HTTPException(status_code=404, detail="Comment not found")

    update_doc = payload.dict(by_alias=True, exclude={"id", "_id", "blog_id", "created_at"})
    db_client[db.db_name]["comments"].update_one(
        {"_id": ObjectId(comment_id)},
        {"$set": update_doc},
    )
    updated = db_client[db.db_name]["comments"].find_one({"_id": ObjectId(comment_id)})
    updated["_id"] = str(updated["_id"])
    return updated


@blog_router.delete("/comments/{comment_id}", tags=["Blogs"])
async def delete_comment(
    comment_id: str,
    current_user: User = Depends(get_current_author_or_admin_user),
    db_client: MongoClient = Depends(db.get_client),
):
    if not ObjectId.is_valid(comment_id):
        raise HTTPException(status_code=404, detail="Comment not found")
    existing = db_client[db.db_name]["comments"].find_one({"_id": ObjectId(comment_id)})
    if not existing:
        raise HTTPException(status_code=404, detail="Comment not found")
    db_client[db.db_name]["comments"].delete_one({"_id": ObjectId(comment_id)})
    return {"message": "Comment deleted successfully"}


# ------------------------- SINGLE blog (PUBLIC) -------------------------
@blog_router.get("/blogs/{blog_id}", response_model=BlogPost, tags=["Blogs"])
async def get_blog(blog_id: str, db_client: MongoClient = Depends(db.get_client)):
    if not ObjectId.is_valid(blog_id):
        raise HTTPException(status_code=404, detail="Blog not found")
    blog = db_client[db.db_name]["blogs"].find_one({"_id": ObjectId(blog_id)})
    if not blog:
        raise HTTPException(status_code=404, detail="Blog not found")
    return _normalize_blog(blog, db_client)


# ------------------------- Update & Delete blog (PROTECTED) -------------------------
@blog_router.put("/blogs/{blog_id}", response_model=BlogPost, tags=["Blogs"])
async def update_blog(
    blog_id: str,
    updated_blog: BlogPost,
    current_user: User = Depends(get_current_author_or_admin_user),
    db_client: MongoClient = Depends(db.get_client),
):
    if not ObjectId.is_valid(blog_id):
        raise HTTPException(status_code=404, detail="Blog not found")
    existing_blog = db_client[db.db_name]["blogs"].find_one({"_id": ObjectId(blog_id)})
    if not existing_blog:
        raise HTTPException(status_code=404, detail="Blog not found")

    updated_blog.updated_at = datetime.utcnow()
    db_client[db.db_name]["blogs"].update_one(
        {"_id": ObjectId(blog_id)},
        {
            "$set": updated_blog.dict(
                by_alias=True,
                exclude={
                    "id",
                    "author_username",
                    "created_at",
                    "views",
                    "viewed_ips",
                    "likes",
                    "liked_ips",
                },
            )
        },
    )
    updated_blog.id = blog_id
    return updated_blog


@blog_router.delete("/blogs/{blog_id}", tags=["Blogs"])
async def delete_blog(
    blog_id: str,
    current_user: User = Depends(get_current_author_or_admin_user),
    db_client: MongoClient = Depends(db.get_client),
):
    if not ObjectId.is_valid(blog_id):
        raise HTTPException(status_code=404, detail="Blog not found")
    existing_blog = db_client[db.db_name]["blogs"].find_one({"_id": ObjectId(blog_id)})
    if not existing_blog:
        raise HTTPException(status_code=404, detail="Blog not found")
    db_client[db.db_name]["blogs"].delete_one({"_id": ObjectId(blog_id)})
    return {"message": "Blog deleted successfully"}


# ------------------------- Blog <-> Tags per blog (PROTECTED for write) -------------------------
class TagsPayload(BaseModel):
    tags: Optional[List[str]] = None
    tag: Optional[str] = None  # accept either shape


def _extract_tags(payload: TagsPayload) -> List[str]:
    if payload.tags and isinstance(payload.tags, list):
        return [str(t).strip() for t in payload.tags if str(t).strip()]
    if payload.tag and isinstance(payload.tag, str) and payload.tag.strip():
        return [payload.tag.strip()]
    return []


@blog_router.post("/blogs/{blog_id}/tags", tags=["Blogs"])
async def add_tags_to_blog(
    blog_id: str,
    payload: TagsPayload = Body(...),
    current_user: User = Depends(get_current_author_or_admin_user),
    db_client: MongoClient = Depends(db.get_client),
):
    if not ObjectId.is_valid(blog_id):
        raise HTTPException(status_code=404, detail="Blog not found")
    tags = _extract_tags(payload)
    if not tags:
        raise HTTPException(status_code=400, detail="No tags provided")
    res = db_client[db.db_name]["blogs"].update_one(
        {"_id": ObjectId(blog_id)},
        {"$addToSet": {"tags": {"$each": tags}}},
    )
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Blog not found")
    return {"added": tags}


@blog_router.delete("/blogs/{blog_id}/tags", tags=["Blogs"])
async def remove_tags_from_blog(
    blog_id: str,
    payload: TagsPayload = Body(...),
    current_user: User = Depends(get_current_author_or_admin_user),
    db_client: MongoClient = Depends(db.get_client),
):
    if not ObjectId.is_valid(blog_id):
        raise HTTPException(status_code=404, detail="Blog not found")
    tags = _extract_tags(payload)
    if not tags:
        raise HTTPException(status_code=400, detail="No tags provided")
    res = db_client[db.db_name]["blogs"].update_one(
        {"_id": ObjectId(blog_id)},
        {"$pull": {"tags": {"$in": tags}}},
    )
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Blog not found")
    return {"removed": tags}


# (keep legacy single-tag delete for backwards compatibility)
@blog_router.delete("/blogs/{blog_id}/tags/{tag}", tags=["Blogs"])
async def remove_single_tag_legacy(
    blog_id: str,
    tag: str,
    current_user: User = Depends(get_current_author_or_admin_user),
    db_client: MongoClient = Depends(db.get_client),
):
    if not ObjectId.is_valid(blog_id):
        raise HTTPException(status_code=404, detail="Blog not found")
    res = db_client[db.db_name]["blogs"].update_one(
        {"_id": ObjectId(blog_id)},
        {"$pull": {"tags": tag}},
    )
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Blog not found")
    return {"removed": [tag]}


# ------------------------- Global tags admin (PUBLIC counts, admin writes) -------------------------
@blog_router.get("/tags", tags=["Blogs"])
async def list_tags_with_counts(db_client: MongoClient = Depends(db.get_client)):
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
    rows = db_client[db.db_name]["blogs"].aggregate(pipeline)
    return [{"tag": r["_id"], "count": r["count"]} for r in rows]


@blog_router.put("/tags/rename", tags=["Blogs"])
async def rename_tag_globally(
    payload: Dict[str, str],
    current_admin: User = Depends(get_current_admin_user),
    db_client: MongoClient = Depends(db.get_client),
):
    old = (payload.get("old_tag") or payload.get("old") or "").strip()
    new = (payload.get("new_tag") or payload.get("new") or "").strip()
    if not old or not new:
        raise HTTPException(status_code=400, detail="old_tag/new_tag required")
    res = db_client[db.db_name]["blogs"].update_many(
        {"tags": old},
        {"$set": {"tags.$[elem]": new}},
        array_filters=[{"elem": old}],
    )
    return {"matched": res.matched_count, "modified": res.modified_count}


@blog_router.delete("/tags/{tag}", tags=["Blogs"])
async def delete_tag_globally(
    tag: str,
    current_admin: User = Depends(get_current_admin_user),
    db_client: MongoClient = Depends(db.get_client),
):
    res = db_client[db.db_name]["blogs"].update_many(
        {"tags": tag},
        {"$pull": {"tags": tag}},
    )
    return {"matched": res.matched_count, "modified": res.modified_count}


# ------------------------- Categories CRUD -------------------------
@blog_router.post("/categories", response_model=Category, tags=["Blogs"])
async def create_category(
    category: Category,
    current_admin: User = Depends(get_current_admin_user),
    db_client: MongoClient = Depends(db.get_client),
):
    category_dict = category.dict(by_alias=True, exclude={"id"})
    inserted_category = db_client[db.db_name]["categories"].insert_one(category_dict)
    category.id = str(inserted_category.inserted_id)
    return category


@blog_router.get("/categories", response_model=List[Category], tags=["Blogs"])
async def get_categories(db_client: MongoClient = Depends(db.get_client)):
    categories = list(db_client[db.db_name]["categories"].find({}).sort("name", 1))
    for c in categories:
        c["_id"] = str(c["_id"])
    return categories


@blog_router.put("/categories/{category_id}", response_model=Category, tags=["Blogs"])
async def update_category(
    category_id: str,
    category: Category,
    current_admin: User = Depends(get_current_admin_user),
    db_client: MongoClient = Depends(db.get_client),
):
    if not ObjectId.is_valid(category_id):
        raise HTTPException(status_code=404, detail="Category not found")
    existing = db_client[db.db_name]["categories"].find_one({"_id": ObjectId(category_id)})
    if not existing:
        raise HTTPException(status_code=404, detail="Category not found")

    update_doc = category.dict(by_alias=True, exclude={"id", "_id"})
    db_client[db.db_name]["categories"].update_one(
        {"_id": ObjectId(category_id)},
        {"$set": update_doc},
    )
    category.id = category_id
    return category


@blog_router.delete("/categories/{category_id}", tags=["Blogs"])
async def delete_category(
    category_id: str,
    current_admin: User = Depends(get_current_admin_user),
    db_client: MongoClient = Depends(db.get_client),
):
    if not ObjectId.is_valid(category_id):
        raise HTTPException(status_code=404, detail="Category not found")
    existing = db_client[db.db_name]["categories"].find_one({"_id": ObjectId(category_id)})
    if not existing:
        raise HTTPException(status_code=404, detail="Category not found")
    db_client[db.db_name]["categories"].delete_one({"_id": ObjectId(category_id)})
    return {"message": "Category deleted successfully"}


@blog_router.post("/categories/bulk", response_model=List[Category], tags=["Blogs"])
async def create_multiple_categories(
    categories: List[Category],
    current_admin: User = Depends(get_current_admin_user),
    db_client: MongoClient = Depends(db.get_client),
):
    category_dicts = [category.dict(by_alias=True, exclude={"id"}) for category in categories]
    inserted = db_client[db.db_name]["categories"].insert_many(category_dicts)
    for i, category in enumerate(categories):
        category.id = str(inserted.inserted_ids[i])
    return categories


# ------------------------- SEO meta (PUBLIC) -------------------------
@blog_router.get("/blogs/{blog_id}/meta", response_class=HTMLResponse, tags=["Blogs"])
async def get_blog_meta(blog_id: str, db_client: MongoClient = Depends(db.get_client)):
    if not ObjectId.is_valid(blog_id):
        raise HTTPException(status_code=404, detail="Blog not found")
    blog = db_client[db.db_name]["blogs"].find_one({"_id": ObjectId(blog_id)})
    if not blog:
        raise HTTPException(status_code=404, detail="Blog not found")

    title = blog["title"]
    description = BeautifulSoup(blog["content"], "html.parser").get_text()[:150] + "..."
    image_url = blog["image_url"]
    if not image_url.startswith("http"):
        image_url = f"https://{AWS_BUCKET_NAME}.s3.{AWS_REGION}.amazonaws.com/{image_url}"
    blog_url = f"https://www.projectdevops.in/blog/{blog_id}/{title.replace(' ', '-').lower()}"

    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <meta property="og:title" content="{title}" />
        <meta property="og:description" content="{description}" />
        <meta property="og:image" content="{image_url}" />
        <meta property="og:url" content="{blog_url}" />
        <meta property="og:type" content="article" />
        <meta name="twitter:card" content="summary_large_image" />
        <title>{title}</title>
    </head>
    <body>
        <p>Visit the full blog post at <a href="{blog_url}">{title}</a></p>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)


# ------------------------- Paginated (compat; optional) -------------------------
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


@blog_router.get("/categories/paginated", response_model=PagedCategories, tags=["Blogs"])
async def get_categories_paginated(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db_client: MongoClient = Depends(db.get_client),
):
    coll = db_client[db.db_name]["categories"]

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


class PagedBlogs(BaseModel):
    items: List[BlogPost]
    meta: PageMeta


@blog_router.get("/blogs/paginated", response_model=PagedBlogs, tags=["Blogs"])
async def get_blogs_paginated(
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

    coll = db_client[db.db_name]["blogs"]
    total = coll.count_documents(q)
    pages = max(1, math.ceil(total / per_page))
    skip = (page - 1) * per_page

    items = list(coll.find(q).sort("created_at", DESCENDING).skip(skip).limit(per_page))
    items = [_normalize_blog(it, db_client) for it in items]

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
