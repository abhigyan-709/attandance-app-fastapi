# models/tutorials.py
from __future__ import annotations

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime


# ---------- Core content models ----------
class TutorialLesson(BaseModel):
    id: Optional[str] = Field(default=None, alias="_id")
    title: str
    slug: Optional[str] = None
    content_html: Optional[str] = None
    code_blocks: Optional[List[Dict[str, Any]]] = Field(default_factory=list)
    resources: Optional[List[Dict[str, str]]] = Field(default_factory=list)
    duration_minutes: Optional[int] = 0
    order: int = 0
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None

    class Config:
        arbitrary_types_allowed = True
        json_encoders = {datetime: lambda v: v.isoformat(), "ObjectId": str}
        alias_generator = lambda x: "_id" if x == "id" else x


class Tutorial(BaseModel):
    id: Optional[str] = Field(default=None, alias="_id")
    title: str
    subtitle: Optional[str] = None
    cover_image_url: Optional[str] = None
    author_username: str
    difficulty: str = Field(default="Beginner")
    # NOTE: we continue storing categories as names (strings) for backwards compatibility.
    categories: List[str] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)
    prerequisites: Optional[List[str]] = Field(default_factory=list)
    objectives: Optional[List[str]] = Field(default_factory=list)
    overview_html: Optional[str] = None
    lessons: List[TutorialLesson] = Field(default_factory=list)
    published: bool = False
    version: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None
    views: int = 0
    viewed_ips: List[str] = Field(default_factory=list)
    likes: int = 0
    liked_ips: List[str] = Field(default_factory=list)
    ratings_count: int = 0
    ratings_sum: float = 0.0

    class Config:
        arbitrary_types_allowed = True
        json_encoders = {datetime: lambda v: v.isoformat(), "ObjectId": str}
        alias_generator = lambda x: "_id" if x == "id" else x


# ---------- Comments / Q&A ----------
class TutorialComment(BaseModel):
    id: Optional[str] = Field(default=None, alias="_id")
    tutorial_id: str
    lesson_id: Optional[str] = None
    parent_id: Optional[str] = None
    name: str
    email: str
    content: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None
    is_answer: bool = False

    class Config:
        arbitrary_types_allowed = True
        json_encoders = {datetime: lambda v: v.isoformat(), "ObjectId": str}
        alias_generator = lambda x: "_id" if x == "id" else x


# ---------- Categories (with optional parent) ----------
class TutorialCategory(BaseModel):
    id: Optional[str] = Field(default=None, alias="_id")
    name: str
    description: Optional[str] = None
    icon: Optional[str] = None  # can be SVG string or URL
    parent_id: Optional[str] = None  # None => root
    # Returned by API when building a tree; not stored in DB.
    children: List["TutorialCategory"] = Field(default_factory=list)

    class Config:
        arbitrary_types_allowed = True
        json_encoders = {"ObjectId": str}
        alias_generator = lambda x: "_id" if x == "id" else x


# ---------- Progress / Bookmarks ----------
class TutorialProgress(BaseModel):
    id: Optional[str] = Field(default=None, alias="_id")
    tutorial_id: str
    username: str
    completed_lesson_ids: List[str] = Field(default_factory=list)
    last_lesson_id: Optional[str] = None
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        arbitrary_types_allowed = True
        json_encoders = {datetime: lambda v: v.isoformat(), "ObjectId": str}
        alias_generator = lambda x: "_id" if x == "id" else x


class Bookmark(BaseModel):
    id: Optional[str] = Field(default=None, alias="_id")
    tutorial_id: str
    username: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        arbitrary_types_allowed = True
        json_encoders = {datetime: lambda v: v.isoformat(), "ObjectId": str}
        alias_generator = lambda x: "_id" if x == "id" else x
