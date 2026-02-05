# routes/tutorials.py
import math
import os
import re
import uuid
import logging
from datetime import datetime
from typing import List, Optional, Dict, Any

import boto3
from bs4 import BeautifulSoup
from bson import ObjectId
from fastapi import (
    APIRouter, Depends, HTTPException, Query, UploadFile, File, Form, Request, BackgroundTasks
)
from fastapi.responses import HTMLResponse
from pymongo import MongoClient, DESCENDING

from database.db import db
from models.tutorials import (
    Tutorial, TutorialLesson, TutorialComment, TutorialCategory, TutorialProgress, Bookmark
)
from models.user import User
from routes.user import get_current_user
from routes.config import (
    AWS_ACCESS_KEY_ID, 
    AWS_SECRET_ACCESS_KEY, 
    AWS_REGION,
    AWS_BUCKET_NAME,
    get_cdn_url
)

from pydantic import BaseModel

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

tutorial_router = APIRouter()

# S3 client for uploads (bucket remains private, served via CloudFront CDN)
s3_client = boto3.client(
    "s3",
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    region_name=AWS_REGION,
)

PUBLIC_API_BASE = os.getenv("PUBLIC_API_BASE", "http://localhost:8000")
ADMIN_API_TOKEN = os.getenv("ADMIN_API_TOKEN")
TUTORIAL_BASE_URL = os.getenv("TUTORIAL_BASE_URL", "https://blogs.projectdevops.in")  # front host


# ------------------------- Auth roles -------------------------
def get_current_author_or_admin_user(current_user: User = Depends(get_current_user)):
    if current_user.role not in ["admin", "author"]:
        raise HTTPException(status_code=403, detail="Not authorized (admin/author required)")
    return current_user

def get_current_admin_user(current_user: User = Depends(get_current_user)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized (admin only)")
    return current_user


# ------------------------- Helpers -------------------------
def _slugify(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", (s or "").lower()).strip("-")

def _clean_str_list(values: Optional[List[str]]) -> List[str]:
    """
    Normalize a possibly-empty list of strings:
    - Trim whitespace
    - Split accidental comma-separated entries
    - Drop empties
    - De-duplicate (preserving order)
    """
    if not values:
        return []
    out: List[str] = []
    for v in values:
        if v is None:
            continue
        if isinstance(v, str):
            parts = [p.strip() for p in v.split(",")] if "," in v else [v.strip()]
            for p in parts:
                if p:
                    out.append(p)
        else:
            s = str(v).strip()
            if s:
                out.append(s)
    seen = set()
    uniq: List[str] = []
    for x in out:
        if x not in seen:
            seen.add(x)
            uniq.append(x)
    return uniq


def _should_force_published_only(request: Request, published_param: Optional[bool]) -> bool:
    if published_param is not None:
        return False
    auth = (request.headers.get("Authorization") or "").strip()
    return not bool(auth)

def _normalize(doc: Dict[str, Any]) -> Dict[str, Any]:
    doc["_id"] = str(doc["_id"])
    # normalize defaults
    doc["views"] = doc.get("views", 0)
    doc["viewed_ips"] = doc.get("viewed_ips", [])
    doc["likes"] = doc.get("likes", 0)
    doc["liked_ips"] = doc.get("liked_ips", [])
    doc["ratings_count"] = doc.get("ratings_count", 0)
    doc["ratings_sum"] = doc.get("ratings_sum", 0.0)
    # lessons
    for ls in doc.get("lessons", []):
        if isinstance(ls.get("_id"), ObjectId):
            ls["_id"] = str(ls["_id"])
    return doc

_TEXT_INDEX_NAME = "tutorials_text_idx"
def _ensure_text_index(db_client: MongoClient):
    coll = db_client[db.db_name]["tutorials"]
    try:
        coll.create_index(
            [("title", "text"), ("subtitle", "text"), ("overview_html", "text"),
             ("tags", "text"), ("categories", "text"), ("lessons.title", "text"), ("lessons.content_html", "text")],
            name=_TEXT_INDEX_NAME,
            default_language="english",
        )
    except Exception as e:
        logger.debug(f"text index create skipped: {e}")


# ====================================================================================
# 1) STATIC /tutorials/* ROUTES FIRST (these must come before /tutorials/{tutorial_id})
# ====================================================================================

# ------------------------- Upload cover image -------------------------
@tutorial_router.post("/tutorials/upload-cover", tags=["Tutorials"])
async def upload_tutorial_cover(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_author_or_admin_user),
):
    ext = (file.filename or "image").split(".")[-1]
    key = f"tutorials/covers/{uuid.uuid4()}.{ext}"
    try:
        s3_client.upload_fileobj(
            file.file, AWS_BUCKET_NAME, key, ExtraArgs={"ContentType": file.content_type}
        )
        # Use CDN URL instead of direct S3 URL
        url = get_cdn_url(key)
        return {"url": url}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


# ------------------------- Create tutorial -------------------------
@tutorial_router.post("/tutorials", response_model=Tutorial, tags=["Tutorials"])
async def create_tutorial(
    title: str = Form(...),
    subtitle: Optional[str] = Form(None),
    cover_image_url: Optional[str] = Form(None),
    difficulty: str = Form("Beginner"),
    categories: List[str] = Form([]),
    tags: List[str] = Form([]),
    overview_html: Optional[str] = Form(None),
    version: Optional[str] = Form(None),
    published: bool = Form(False),
    prerequisites: List[str] = Form([]),
    objectives: List[str] = Form([]),
    background_tasks: BackgroundTasks = None,
    current_user: User = Depends(get_current_author_or_admin_user),
    db_client: MongoClient = Depends(db.get_client),
):
    tutorial = {
        "title": title,
        "subtitle": subtitle,
        "cover_image_url": cover_image_url,
        "author_username": current_user.username,
        "difficulty": difficulty,
        "categories": categories or [],
        "tags": tags or [],
        "prerequisites": _clean_str_list(prerequisites),
        "objectives": _clean_str_list(objectives),
        "overview_html": overview_html,
        "lessons": [],
        "version": version,
        "published": published,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
        "views": 0,
        "viewed_ips": [],
        "likes": 0,
        "liked_ips": [],
        "ratings_count": 0,
        "ratings_sum": 0.0,
    }
    res = db_client[db.db_name]["tutorials"].insert_one(tutorial)
    tutorial["_id"] = str(res.inserted_id)

    # Optionally notify subscribers (same pattern as blogs)
    if published and background_tasks is not None:
        try:
            headers = {"Content-Type": "application/json"}
            if ADMIN_API_TOKEN:
                headers["x-admin-token"] = ADMIN_API_TOKEN
            slug = _slugify(title)
            url = f"{TUTORIAL_BASE_URL}/t/{tutorial['_id']}-{slug}"
            payload = {
                "title": title,
                "body": "New tutorial is live! Tap to learn.",
                "url": url,
                "image": cover_image_url,
                "tag": "new-tutorial",
            }
            import requests
            background_tasks.add_task(
                requests.post, f"{PUBLIC_API_BASE}/push/notify-new-blog",  # reuse endpoint
                json=payload, headers=headers, timeout=5
            )
        except Exception as e:
            logger.warning(f"notify_new_tutorial failed: {e}")

    return _normalize(tutorial)


# ------------------------- Read/List/Search (STATIC) -------------------------
@tutorial_router.get("/tutorials", response_model=List[Tutorial], tags=["Tutorials"])
async def list_tutorials(
    request: Request,
    published: Optional[bool] = Query(default=None),
    difficulty: Optional[str] = Query(default=None),
    category: Optional[str] = Query(default=None),
    tag: Optional[str] = Query(default=None),
    db_client: MongoClient = Depends(db.get_client),
):
    q: Dict[str, Any] = {}
    if _should_force_published_only(request, published):
        q["published"] = True
    elif published is not None:
        q["published"] = published
    if difficulty:
        q["difficulty"] = difficulty
    if category:
        q["categories"] = category
    if tag:
        q["tags"] = tag

    docs = list(db_client[db.db_name]["tutorials"].find(q).sort("created_at", DESCENDING))
    return [_normalize(d) for d in docs]


class PageMeta(BaseModel):
    total: int
    page: int
    per_page: int
    pages: int
    has_next: bool
    has_prev: bool

class PagedTutorials(BaseModel):
    items: List[Tutorial]
    meta: PageMeta

@tutorial_router.get("/tutorials/paginated", response_model=PagedTutorials, tags=["Tutorials"])
async def list_tutorials_paginated(
    request: Request,
    published: Optional[bool] = Query(default=None),
    difficulty: Optional[str] = Query(default=None),
    category: Optional[str] = Query(default=None),
    tag: Optional[str] = Query(default=None),
    page: int = Query(1, ge=1),
    per_page: int = Query(12, ge=1, le=50),
    db_client: MongoClient = Depends(db.get_client),
):
    q: Dict[str, Any] = {}
    if _should_force_published_only(request, published):
        q["published"] = True
    elif published is not None:
        q["published"] = published
    if difficulty:
        q["difficulty"] = difficulty
    if category:
        q["categories"] = category
    if tag:
        q["tags"] = tag

    coll = db_client[db.db_name]["tutorials"]
    total = coll.count_documents(q)
    pages = max(1, math.ceil(total / per_page))
    skip = (page - 1) * per_page
    items = list(coll.find(q).sort("created_at", DESCENDING).skip(skip).limit(per_page))
    items = [_normalize(it) for it in items]
    return {
        "items": items,
        "meta": {
            "total": total, "page": page, "per_page": per_page, "pages": pages,
            "has_next": page < pages, "has_prev": page > 1
        },
    }


@tutorial_router.get("/tutorials/search", response_model=List[Tutorial], tags=["Tutorials"])
async def search_tutorials(
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

    coll = db_client[db.db_name]["tutorials"]
    try:
        cursor = coll.find({"$text": {"$search": q}, **base}, {"score": {"$meta": "textScore"}})
        docs = list(cursor.sort([("score", {"$meta": "textScore"})]).limit(limit))
    except Exception:
        docs = []

    if not docs:
        regex = re.compile(re.escape(q), re.IGNORECASE)
        docs = list(
            coll.find(
                {
                    **base,
                    "$or": [
                        {"title": regex}, {"subtitle": regex}, {"overview_html": regex},
                        {"tags": regex}, {"categories": regex}, {"lessons.title": regex},
                    ],
                }
            )
            .sort("created_at", DESCENDING)
            .limit(limit)
        )
    return [_normalize(d) for d in docs]


@tutorial_router.get("/tutorials/suggest", response_model=List[Dict[str, str]], tags=["Tutorials"])
async def suggest_tutorials(
    request: Request,
    q: str = Query(..., min_length=1),
    limit: int = Query(8, ge=1, le=20),
    db_client: MongoClient = Depends(db.get_client),
):
    base: Dict[str, Any] = {}
    if _should_force_published_only(request, None):
        base["published"] = True
    regex = re.compile(re.escape(q), re.IGNORECASE)
    coll = db_client[db.db_name]["tutorials"]
    docs = list(
        coll.find({**base, "title": {"$regex": regex}}, {"title": 1})
            .sort("created_at", DESCENDING).limit(limit)
    )
    return [{"_id": str(d["_id"]), "title": d.get("title", "")} for d in docs]


@tutorial_router.get("/tutorials/stats", tags=["Tutorials"])
async def tutorials_stats(db_client: MongoClient = Depends(db.get_client)):
    coll = db_client[db.db_name]["tutorials"]
    total = coll.count_documents({})
    published = coll.count_documents({"published": True})
    drafts = total - published

    agg = list(coll.aggregate(
        [{"$group": {"_id": None,
                     "views": {"$sum": {"$ifNull": ["$views", 0]}},
                     "likes": {"$sum": {"$ifNull": ["$likes", 0]}},
                     "ratings_sum": {"$sum": {"$ifNull": ["$ratings_sum", 0]}},
                     "ratings_count": {"$sum": {"$ifNull": ["$ratings_count", 0]}}}}]
    ))
    views = (agg[0]["views"] if agg else 0) or 0
    likes = (agg[0]["likes"] if agg else 0) or 0
    ratings_sum = (agg[0]["ratings_sum"] if agg else 0.0) or 0.0
    ratings_count = (agg[0]["ratings_count"] if agg else 0) or 0
    avg_rating = round((ratings_sum / ratings_count), 2) if ratings_count else 0

    top_viewed = list(coll.find({}, {"title":1,"views":1}).sort([("views",-1)]).limit(5))
    top_liked = list(coll.find({}, {"title":1,"likes":1}).sort([("likes",-1)]).limit(5))
    for d in top_viewed: d["_id"] = str(d["_id"])
    for d in top_liked: d["_id"] = str(d["_id"])

    return {"total": total, "published": published, "drafts": drafts,
            "views": views, "likes": likes,
            "avg_rating": avg_rating,
            "top_viewed": top_viewed, "top_liked": top_liked}


# ------------------------- Categories & Tags (STATIC) -------------------------

def _normalize_cat(doc: Dict[str, Any]) -> Dict[str, Any]:
    # normalize _id and parent_id to strings for API responses
    if isinstance(doc.get("_id"), ObjectId):
        doc["_id"] = str(doc["_id"])
    if isinstance(doc.get("parent_id"), ObjectId):
        doc["parent_id"] = str(doc["parent_id"])
    # do NOT include children here; we add children only when building a tree
    return doc


def _build_category_tree(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Return hierarchical tree (roots first) from flat rows with parent_id."""
    nodes = {str(r["_id"]): {**_normalize_cat(r), "children": []} for r in rows}
    roots: List[Dict[str, Any]] = []
    for r in nodes.values():
        pid = r.get("parent_id")
        if pid and str(pid) in nodes:
            nodes[str(pid)]["children"].append(r)
        else:
            roots.append(r)
    # sort children by name (stable)
    def sort_rec(n):
        n["children"].sort(key=lambda x: x.get("name", "").lower())
        for c in n["children"]:
            sort_rec(c)
    for root in roots:
        sort_rec(root)
    roots.sort(key=lambda x: x.get("name", "").lower())
    return roots


@tutorial_router.post("/tutorials/categories", response_model=TutorialCategory, tags=["Tutorials"])
async def create_tutorial_category(
    category: TutorialCategory,
    current_admin: User = Depends(get_current_admin_user),
    db_client: MongoClient = Depends(db.get_client),
):
    doc = category.dict(by_alias=True, exclude={"id", "children"})
    # validate parent if provided
    pid = doc.get("parent_id")
    if pid:
        if not ObjectId.is_valid(pid):
            raise HTTPException(status_code=400, detail="Invalid parent_id")
        parent = db_client[db.db_name]["tutorial_categories"].find_one({"_id": ObjectId(pid)})
        if not parent:
            raise HTTPException(status_code=404, detail="Parent category not found")
        # store as ObjectId in DB
        doc["parent_id"] = ObjectId(pid)
    else:
        doc["parent_id"] = None

    ins = db_client[db.db_name]["tutorial_categories"].insert_one(doc)
    category.id = str(ins.inserted_id)
    category.children = []  # response consistency
    return category


@tutorial_router.get("/tutorials/categories", response_model=List[TutorialCategory], tags=["Tutorials"])
async def get_categories(
    flat: Optional[bool] = Query(default=False, description="Return flat list when true; default returns tree"),
    db_client: MongoClient = Depends(db.get_client),
):
    rows = list(db_client[db.db_name]["tutorial_categories"].find({}).sort("name", 1))
    if flat:
        return [_normalize_cat(r) for r in rows]
    return _build_category_tree(rows)


@tutorial_router.put("/tutorials/categories/{category_id}", response_model=TutorialCategory, tags=["Tutorials"])
async def update_tutorial_category(
    category_id: str,
    category: TutorialCategory,
    current_admin: User = Depends(get_current_admin_user),
    db_client: MongoClient = Depends(db.get_client),
):
    if not ObjectId.is_valid(category_id):
        raise HTTPException(status_code=404, detail="Category not found")
    existing = db_client[db.db_name]["tutorial_categories"].find_one({"_id": ObjectId(category_id)})
    if not existing:
        raise HTTPException(status_code=404, detail="Category not found")

    patch = category.dict(by_alias=True, exclude={"id", "_id", "children"})
    # Validate/normalize parent
    pid = patch.get("parent_id")
    if pid == "":
        pid = None
    if pid is not None:
        if pid == category_id:
            raise HTTPException(status_code=400, detail="A category cannot be its own parent")
        if pid and not ObjectId.is_valid(pid):
            raise HTTPException(status_code=400, detail="Invalid parent_id")
        if pid:
            parent = db_client[db.db_name]["tutorial_categories"].find_one({"_id": ObjectId(pid)})
            if not parent:
                raise HTTPException(status_code=404, detail="Parent category not found")
            patch["parent_id"] = ObjectId(pid)
        else:
            patch["parent_id"] = None

    db_client[db.db_name]["tutorial_categories"].update_one({"_id": ObjectId(category_id)}, {"$set": patch})
    updated = db_client[db.db_name]["tutorial_categories"].find_one({"_id": ObjectId(category_id)})
    # return as a single node (no children in this response)
    return {**_normalize_cat(updated), "children": []}  # type: ignore


@tutorial_router.delete("/tutorials/categories/{category_id}", tags=["Tutorials"])
async def delete_tutorial_category(
    category_id: str,
    current_admin: User = Depends(get_current_admin_user),
    db_client: MongoClient = Depends(db.get_client),
    force: Optional[bool] = Query(default=False, description="Set true to cascade-delete all subcategories"),
):
    if not ObjectId.is_valid(category_id):
        raise HTTPException(status_code=404, detail="Category not found")
    cat = db_client[db.db_name]["tutorial_categories"].find_one({"_id": ObjectId(category_id)})
    if not cat:
        raise HTTPException(status_code=404, detail="Category not found")

    # check for children
    children = list(db_client[db.db_name]["tutorial_categories"].find({"parent_id": ObjectId(category_id)}, {"_id": 1}))
    if children and not force:
        raise HTTPException(
            status_code=400,
            detail="Category has subcategories. Pass ?force=true to cascade delete."
        )

    # cascade delete if requested
    if children and force:
        # simple BFS cascade
        queue = [ObjectId(category_id)]
        to_delete = []
        while queue:
            cid = queue.pop(0)
            to_delete.append(cid)
            subs = db_client[db.db_name]["tutorial_categories"].find({"parent_id": cid}, {"_id": 1})
            queue.extend(s["_id"] for s in subs)
        db_client[db.db_name]["tutorial_categories"].delete_many({"_id": {"$in": to_delete}})
        return {"message": f"Deleted {len(to_delete)} categories (cascade)"}

    # plain delete
    db_client[db.db_name]["tutorial_categories"].delete_one({"_id": ObjectId(category_id)})
    return {"message": "Category deleted successfully"}


@tutorial_router.get("/tutorials/tags", response_model=List[str], tags=["Tutorials"])
async def list_all_tags(db_client: MongoClient = Depends(db.get_client)):
    pipeline = [
        {"$addFields": {
            "tags": {
                "$cond": [
                    {"$isArray": "$tags"}, "$tags",
                    {"$cond":[{"$and":[{"$ne":["$tags",None]},{"$ne":["$tags",""]}]}, ["$tags"], []]}
                ]
            }
        }},
        {"$unwind": "$tags"},
        {"$group": {"_id": "$tags"}},
        {"$sort": {"_id": 1}},
    ]
    rows = db_client[db.db_name]["tutorials"].aggregate(pipeline)
    return [r["_id"] for r in rows]


@tutorial_router.put("/tutorials/tags/rename", tags=["Tutorials"])
async def rename_tag_globally(
    payload: Dict[str, str],
    current_admin: User = Depends(get_current_admin_user),
    db_client: MongoClient = Depends(db.get_client),
):
    old = (payload.get("old_tag") or payload.get("old") or "").strip()
    new = (payload.get("new_tag") or payload.get("new") or "").strip()
    if not old or not new:
        raise HTTPException(status_code=400, detail="old_tag/new_tag required")
    res = db_client[db.db_name]["tutorials"].update_many(
        {"tags": old},
        {"$set": {"tags.$[elem]": new}},
        array_filters=[{"elem": old}],
    )
    return {"matched": res.matched_count, "modified": res.modified_count}


@tutorial_router.delete("/tutorials/tags/{tag}", tags=["Tutorials"])
async def delete_tag_globally(
    tag: str,
    current_admin: User = Depends(get_current_admin_user),
    db_client: MongoClient = Depends(db.get_client),
):
    res = db_client[db.db_name]["tutorials"].update_many({"tags": tag}, {"$pull": {"tags": tag}})
    return {"matched": res.matched_count, "modified": res.modified_count}



# ====================================================================================
# 2) DYNAMIC /tutorials/{tutorial_id} SUBROUTES (still BEFORE /tutorials/{tutorial_id})
# ====================================================================================

# ------------------------- Lessons (embedded array) -------------------------
class LessonUpdatePayload(BaseModel):
    title: Optional[str] = None
    content_html: Optional[str] = None
    code_blocks: Optional[List[Dict[str, Any]]] = None
    resources: Optional[List[Dict[str, str]]] = None
    duration_minutes: Optional[int] = None
    order: Optional[int] = None


@tutorial_router.post("/tutorials/{tutorial_id}/lessons", tags=["Tutorials"])
async def add_lesson(
    tutorial_id: str,
    payload: LessonUpdatePayload,
    current_user: User = Depends(get_current_author_or_admin_user),
    db_client: MongoClient = Depends(db.get_client),
):
    if not ObjectId.is_valid(tutorial_id):
        raise HTTPException(status_code=404, detail="Tutorial not found")
    lesson_id = str(ObjectId())
    doc = payload.dict()
    doc["_id"] = lesson_id
    doc["slug"] = _slugify(payload.title)
    doc["created_at"] = datetime.utcnow()
    doc["updated_at"] = None

    res = db_client[db.db_name]["tutorials"].update_one(
        {"_id": ObjectId(tutorial_id)},
        {"$push": {"lessons": doc}, "$set": {"updated_at": datetime.utcnow()}}
    )
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Tutorial not found")
    return {"lesson_id": lesson_id}

@tutorial_router.put("/tutorials/{tutorial_id}/lessons/{lesson_id}", tags=["Tutorials"])
async def update_lesson(
    tutorial_id: str,
    lesson_id: str,
    payload: LessonUpdatePayload,   # <-- accept partials
    current_user: User = Depends(get_current_author_or_admin_user),
    db_client: MongoClient = Depends(db.get_client),
):
    if not ObjectId.is_valid(tutorial_id):
        raise HTTPException(status_code=404, detail="Tutorial not found")

    patch = {k: v for k, v in payload.dict().items() if v is not None}
    if not patch:
        raise HTTPException(status_code=400, detail="No fields to update")

    update_set = {f"lessons.$[ls].{k}": v for k, v in patch.items()}

    # only update slug if title is provided
    if "title" in patch:
        update_set["lessons.$[ls].slug"] = _slugify(patch["title"])

    update_set["lessons.$[ls].updated_at"] = datetime.utcnow()

    res = db_client[db.db_name]["tutorials"].update_one(
        {"_id": ObjectId(tutorial_id)},
        {"$set": update_set},
        array_filters=[{"ls._id": lesson_id}],
    )

    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Tutorial or lesson not found")

    return {"updated": True}


@tutorial_router.delete("/tutorials/{tutorial_id}/lessons/{lesson_id}", tags=["Tutorials"])
async def delete_lesson(
    tutorial_id: str,
    lesson_id: str,
    current_user: User = Depends(get_current_author_or_admin_user),
    db_client: MongoClient = Depends(db.get_client),
):
    if not ObjectId.is_valid(tutorial_id):
        raise HTTPException(status_code=404, detail="Tutorial not found")
    res = db_client[db.db_name]["tutorials"].update_one(
        {"_id": ObjectId(tutorial_id)},
        {"$pull": {"lessons": {"_id": lesson_id}}, "$set": {"updated_at": datetime.utcnow()}}
    )
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Tutorial or lesson not found")
    # also remove lesson_id from users' progress
    db_client[db.db_name]["tutorial_progress"].update_many(
        {"tutorial_id": tutorial_id},
        {"$pull": {"completed_lesson_ids": lesson_id}}
    )
    return {"deleted": True}


# ------------------------- Views, Likes, Ratings -------------------------
@tutorial_router.post("/tutorials/{tutorial_id}/views", tags=["Tutorials"])
async def increment_views(tutorial_id: str, request: Request, db_client: MongoClient = Depends(db.get_client)):
    if not ObjectId.is_valid(tutorial_id):
        raise HTTPException(status_code=404, detail="Tutorial not found")
    tut = db_client[db.db_name]["tutorials"].find_one({"_id": ObjectId(tutorial_id)})
    if not tut:
        raise HTTPException(status_code=404, detail="Tutorial not found")

    client_ip = request.headers.get("X-Forwarded-For", request.client.host)
    if client_ip and "," in client_ip:
        client_ip = client_ip.split(",")[0].strip()
    client_ip = client_ip or "unknown"

    viewed_ips = tut.get("viewed_ips", [])
    views = tut.get("views", 0)
    if client_ip not in viewed_ips:
        viewed_ips.append(client_ip)
        views += 1
        db_client[db.db_name]["tutorials"].update_one(
            {"_id": ObjectId(tutorial_id)},
            {"$set": {"viewed_ips": viewed_ips, "views": views}}
        )
    return {"views": views}

@tutorial_router.post("/tutorials/{tutorial_id}/likes", tags=["Tutorials"])
async def increment_likes(tutorial_id: str, request: Request, db_client: MongoClient = Depends(db.get_client)):
    if not ObjectId.is_valid(tutorial_id):
        raise HTTPException(status_code=404, detail="Tutorial not found")
    tut = db_client[db.db_name]["tutorials"].find_one({"_id": ObjectId(tutorial_id)})
    if not tut:
        raise HTTPException(status_code=404, detail="Tutorial not found")

    client_ip = request.headers.get("X-Forwarded-For", request.client.host)
    if client_ip and "," in client_ip:
        client_ip = client_ip.split(",")[0].strip()
    client_ip = client_ip or "unknown"

    liked_ips = tut.get("liked_ips", [])
    likes = tut.get("likes", 0)
    if client_ip not in liked_ips:
        liked_ips.append(client_ip)
        likes += 1
        db_client[db.db_name]["tutorials"].update_one(
            {"_id": ObjectId(tutorial_id)},
            {"$set": {"liked_ips": liked_ips, "likes": likes}}
        )
    return {"likes": likes}

class RatingPayload(BaseModel):
    rating: float  # 1..5

@tutorial_router.post("/tutorials/{tutorial_id}/rating", tags=["Tutorials"])
async def rate_tutorial(
    tutorial_id: str,
    payload: RatingPayload,
    current_user: User = Depends(get_current_user),
    db_client: MongoClient = Depends(db.get_client)
):
    if not ObjectId.is_valid(tutorial_id):
        raise HTTPException(status_code=404, detail="Tutorial not found")
    if payload.rating < 1 or payload.rating > 5:
        raise HTTPException(status_code=400, detail="Rating must be between 1 and 5")
    res = db_client[db.db_name]["tutorials"].update_one(
        {"_id": ObjectId(tutorial_id)},
        {"$inc": {"ratings_count": 1, "ratings_sum": float(payload.rating)}}
    )
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Tutorial not found")
    doc = db_client[db.db_name]["tutorials"].find_one({"_id": ObjectId(tutorial_id)}, {"ratings_count":1,"ratings_sum":1})
    avg = (doc.get("ratings_sum", 0) / doc.get("ratings_count", 1)) if doc else 0
    return {"ratings_count": doc.get("ratings_count", 0), "average": round(avg, 2)}


# ------------------------- Comments / Q&A -------------------------
@tutorial_router.get("/tutorials/{tutorial_id}/comments", response_model=List[TutorialComment], tags=["Tutorials"])
async def list_comments(tutorial_id: str, db_client: MongoClient = Depends(db.get_client)):
    comments = list(db_client[db.db_name]["tutorial_comments"].find({"tutorial_id": tutorial_id}).sort("created_at", DESCENDING))
    for c in comments: c["_id"] = str(c["_id"])
    return comments

@tutorial_router.post("/tutorials/{tutorial_id}/comments", response_model=TutorialComment, tags=["Tutorials"])
async def add_comment(
    tutorial_id: str,
    payload: TutorialComment,
    db_client: MongoClient = Depends(db.get_client),
):
    if not ObjectId.is_valid(tutorial_id):
        raise HTTPException(status_code=404, detail="Tutorial not found")
    if not db_client[db.db_name]["tutorials"].find_one({"_id": ObjectId(tutorial_id)}):
        raise HTTPException(status_code=404, detail="Tutorial not found")

    doc = payload.dict(by_alias=True, exclude={"id", "_id"})
    doc["tutorial_id"] = tutorial_id
    doc["created_at"] = datetime.utcnow()
    ins = db_client[db.db_name]["tutorial_comments"].insert_one(doc)
    doc["_id"] = str(ins.inserted_id)
    return doc

@tutorial_router.put("/tutorials/comments/{comment_id}", response_model=TutorialComment, tags=["Tutorials"])
async def update_comment(
    comment_id: str,
    payload: TutorialComment,
    current_user: User = Depends(get_current_author_or_admin_user),
    db_client: MongoClient = Depends(db.get_client),
):
    if not ObjectId.is_valid(comment_id):
        raise HTTPException(status_code=404, detail="Comment not found")
    existing = db_client[db.db_name]["tutorial_comments"].find_one({"_id": ObjectId(comment_id)})
    if not existing:
        raise HTTPException(status_code=404, detail="Comment not found")

    update_doc = payload.dict(by_alias=True, exclude={"id","_id","tutorial_id","created_at"})
    update_doc["updated_at"] = datetime.utcnow()
    db_client[db.db_name]["tutorial_comments"].update_one({"_id": ObjectId(comment_id)}, {"$set": update_doc})
    updated = db_client[db.db_name]["tutorial_comments"].find_one({"_id": ObjectId(comment_id)})
    updated["_id"] = str(updated["_id"])
    return updated

@tutorial_router.delete("/tutorials/comments/{comment_id}", tags=["Tutorials"])
async def delete_comment(
    comment_id: str,
    current_user: User = Depends(get_current_author_or_admin_user),
    db_client: MongoClient = Depends(db.get_client),
):
    if not ObjectId.is_valid(comment_id):
        raise HTTPException(status_code=404, detail="Comment not found")
    db_client[db.db_name]["tutorial_comments"].delete_one({"_id": ObjectId(comment_id)})
    return {"message": "Comment deleted successfully"}

@tutorial_router.post("/tutorials/comments/{comment_id}/mark-answer", tags=["Tutorials"])
async def mark_comment_as_answer(
    comment_id: str,
    current_user: User = Depends(get_current_author_or_admin_user),
    db_client: MongoClient = Depends(db.get_client)
):
    if not ObjectId.is_valid(comment_id):
        raise HTTPException(status_code=404, detail="Comment not found")
    res = db_client[db.db_name]["tutorial_comments"].update_one(
        {"_id": ObjectId(comment_id)}, {"$set": {"is_answer": True}}
    )
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Comment not found")
    return {"marked": True}


# ------------------------- Progress & Bookmarks (per user) -------------------------
class ProgressPayload(BaseModel):
    lesson_id: str

@tutorial_router.get("/tutorials/{tutorial_id}/progress/me", response_model=TutorialProgress, tags=["Tutorials"])
async def get_my_progress(
    tutorial_id: str,
    current_user: User = Depends(get_current_user),
    db_client: MongoClient = Depends(db.get_client),
):
    doc = db_client[db.db_name]["tutorial_progress"].find_one(
        {"tutorial_id": tutorial_id, "username": current_user.username}
    )
    if not doc:
        # return an empty shell
        return {
            "_id": None,
            "tutorial_id": tutorial_id,
            "username": current_user.username,
            "completed_lesson_ids": [],
            "last_lesson_id": None,
            "updated_at": datetime.utcnow()
        }
    doc["_id"] = str(doc["_id"])
    return doc

@tutorial_router.post("/tutorials/{tutorial_id}/progress/me", tags=["Tutorials"])
async def mark_lesson_completed(
    tutorial_id: str,
    payload: ProgressPayload,
    current_user: User = Depends(get_current_user),
    db_client: MongoClient = Depends(db.get_client),
):
    res = db_client[db.db_name]["tutorial_progress"].find_one_and_update(
        {"tutorial_id": tutorial_id, "username": current_user.username},
        {"$addToSet": {"completed_lesson_ids": payload.lesson_id},
         "$set": {"last_lesson_id": payload.lesson_id, "updated_at": datetime.utcnow()}},
        upsert=True,
        return_document=True,
    )
    # PyMongo < v4: return_document is from bson; but here we just fetch again
    doc = db_client[db.db_name]["tutorial_progress"].find_one(
        {"tutorial_id": tutorial_id, "username": current_user.username}
    )
    doc["_id"] = str(doc["_id"])
    return doc

@tutorial_router.post("/tutorials/{tutorial_id}/bookmarks", tags=["Tutorials"])
async def bookmark_tutorial(
    tutorial_id: str,
    current_user: User = Depends(get_current_user),
    db_client: MongoClient = Depends(db.get_client),
):
    existing = db_client[db.db_name]["bookmarks"].find_one(
        {"tutorial_id": tutorial_id, "username": current_user.username}
    )
    if existing:
        return {"bookmarked": True}
    ins = db_client[db.db_name]["bookmarks"].insert_one({
        "tutorial_id": tutorial_id,
        "username": current_user.username,
        "created_at": datetime.utcnow(),
    })
    return {"bookmarked": True, "id": str(ins.inserted_id)}

@tutorial_router.delete("/tutorials/{tutorial_id}/bookmarks", tags=["Tutorials"])
async def unbookmark_tutorial(
    tutorial_id: str,
    current_user: User = Depends(get_current_user),
    db_client: MongoClient = Depends(db.get_client),
):
    db_client[db.db_name]["bookmarks"].delete_one(
        {"tutorial_id": tutorial_id, "username": current_user.username}
    )
    return {"bookmarked": False}


# ------------------------- Related & SEO Meta -------------------------
@tutorial_router.get("/tutorials/{tutorial_id}/related", response_model=List[Tutorial], tags=["Tutorials"])
async def related_tutorials(
    tutorial_id: str,
    limit: int = Query(5, ge=1, le=10),
    db_client: MongoClient = Depends(db.get_client),
):
    if not ObjectId.is_valid(tutorial_id):
        raise HTTPException(status_code=404, detail="Tutorial not found")
    me = db_client[db.db_name]["tutorials"].find_one({"_id": ObjectId(tutorial_id)})
    if not me:
        raise HTTPException(status_code=404, detail="Tutorial not found")

    tags = me.get("tags", [])
    cats = me.get("categories", [])
    q: Dict[str, Any] = {"_id": {"$ne": me["_id"]}}
    ors = []
    if tags: ors.append({"tags": {"$in": tags}})
    if cats: ors.append({"categories": {"$in": cats}})
    if ors: q["$or"] = ors

    docs = list(db_client[db.db_name]["tutorials"].find(q).sort("created_at", DESCENDING).limit(limit))
    return [_normalize(d) for d in docs]

@tutorial_router.get(
    "/tutorials/{tutorial_id}",
    response_model=Tutorial,
    response_model_exclude_none=False,  # ensure none fields aren't silently dropped
    tags=["Tutorials"],
)
async def get_tutorial(tutorial_id: str, db_client: MongoClient = Depends(db.get_client)):
    if not ObjectId.is_valid(tutorial_id):
        raise HTTPException(status_code=404, detail="Tutorial not found")
    doc = db_client[db.db_name]["tutorials"].find_one({"_id": ObjectId(tutorial_id)})
    if not doc:
        raise HTTPException(status_code=404, detail="Tutorial not found")
    return _normalize(doc)


# ============================ Partial update model ============================
class TutorialUpdate(BaseModel):
    title: Optional[str] = None
    subtitle: Optional[str] = None
    cover_image_url: Optional[str] = None
    difficulty: Optional[str] = None
    categories: Optional[List[str]] = None
    tags: Optional[List[str]] = None
    prerequisites: Optional[List[str]] = None
    objectives: Optional[List[str]] = None
    overview_html: Optional[str] = None
    version: Optional[str] = None
    published: Optional[bool] = None
    lessons: Optional[List[Dict[str, Any]]] = None  # usually edited via subroutes


@tutorial_router.put("/tutorials/{tutorial_id}", response_model=Tutorial, tags=["Tutorials"])
async def update_tutorial(
    tutorial_id: str,
    payload: TutorialUpdate,
    current_user: User = Depends(get_current_author_or_admin_user),
    db_client: MongoClient = Depends(db.get_client),
):
    if not ObjectId.is_valid(tutorial_id):
        raise HTTPException(status_code=404, detail="Tutorial not found")

    existing = db_client[db.db_name]["tutorials"].find_one({"_id": ObjectId(tutorial_id)})
    if not existing:
        raise HTTPException(status_code=404, detail="Tutorial not found")

    patch = payload.dict(exclude_unset=True)
    if not patch:
        return _normalize(existing)

    # never allow these to be overwritten from the client
    for k in ("author_username", "views", "viewed_ips", "likes", "liked_ips",
              "ratings_count", "ratings_sum", "created_at", "_id", "id"):
        patch.pop(k, None)

    patch["updated_at"] = datetime.utcnow()

    db_client[db.db_name]["tutorials"].update_one(
        {"_id": ObjectId(tutorial_id)},
        {"$set": patch}
    )
    updated = db_client[db.db_name]["tutorials"].find_one({"_id": ObjectId(tutorial_id)})
    return _normalize(updated)


@tutorial_router.delete("/tutorials/{tutorial_id}", tags=["Tutorials"])
async def delete_tutorial(
    tutorial_id: str,
    current_user: User = Depends(get_current_author_or_admin_user),
    db_client: MongoClient = Depends(db.get_client),
):
    if not ObjectId.is_valid(tutorial_id):
        raise HTTPException(status_code=404, detail="Tutorial not found")
    existing = db_client[db.db_name]["tutorials"].find_one({"_id": ObjectId(tutorial_id)})
    if not existing:
        raise HTTPException(status_code=404, detail="Tutorial not found")
    db_client[db.db_name]["tutorials"].delete_one({"_id": ObjectId(tutorial_id)})
    # cleanup per-user progress & bookmarks & comments
    db_client[db.db_name]["tutorial_progress"].delete_many({"tutorial_id": tutorial_id})
    db_client[db.db_name]["bookmarks"].delete_many({"tutorial_id": tutorial_id})
    db_client[db.db_name]["tutorial_comments"].delete_many({"tutorial_id": tutorial_id})
    return {"message": "Tutorial deleted successfully"}
