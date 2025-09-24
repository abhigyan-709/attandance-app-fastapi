# models/tutorials.py
from pydantic import BaseModel, Field, HttpUrl
from typing import List, Optional, Dict, Any
from datetime import datetime


# ---------- Core content models ----------
class TutorialLesson(BaseModel):
    id: Optional[str] = Field(default=None, alias="_id")
    title: str
    slug: Optional[str] = None
    content_html: Optional[str] = None             # full rich HTML (TipTap compatible)
    code_blocks: Optional[List[Dict[str, Any]]] = Field(default_factory=list)
    # e.g. [{ "language": "python", "filename": "app.py", "code": "<...>" }]
    resources: Optional[List[Dict[str, str]]] = Field(default_factory=list)
    # e.g. [{ "label": "Repo", "url": "https://..." }]
    duration_minutes: Optional[int] = 0
    order: int = 0
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None

    class Config:
        arbitrary_types_allowed = True
        json_encoders = { datetime: lambda v: v.isoformat(), "ObjectId": str }
        alias_generator = lambda x: "_id" if x == "id" else x


class Tutorial(BaseModel):
    id: Optional[str] = Field(default=None, alias="_id")
    # Meta
    title: str
    subtitle: Optional[str] = None
    cover_image_url: Optional[str] = None
    author_username: str
    difficulty: str = Field(default="Beginner")     # Beginner | Intermediate | Advanced
    categories: List[str] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)
    prerequisites: Optional[List[str]] = Field(default_factory=list)
    objectives: Optional[List[str]] = Field(default_factory=list)
    # Content shell
    overview_html: Optional[str] = None
    lessons: List[TutorialLesson] = Field(default_factory=list)
    # Publishing
    published: bool = False
    version: Optional[str] = None                   # e.g. "1.0.0"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None
    # Counters
    views: int = 0
    viewed_ips: List[str] = Field(default_factory=list)
    likes: int = 0
    liked_ips: List[str] = Field(default_factory=list)
    ratings_count: int = 0
    ratings_sum: float = 0.0                        # average = ratings_sum / ratings_count

    class Config:
        arbitrary_types_allowed = True
        json_encoders = { datetime: lambda v: v.isoformat(), "ObjectId": str }
        alias_generator = lambda x: "_id" if x == "id" else x


# ---------- Comments / Q&A ----------
class TutorialComment(BaseModel):
    id: Optional[str] = Field(default=None, alias="_id")
    tutorial_id: str
    lesson_id: Optional[str] = None                 # nullable to allow thread on tutorial level
    parent_id: Optional[str] = None                 # for threaded replies
    name: str
    email: str
    content: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None
    is_answer: bool = False                         # for Q&A marking

    class Config:
        arbitrary_types_allowed = True
        json_encoders = { datetime: lambda v: v.isoformat(), "ObjectId": str }
        alias_generator = lambda x: "_id" if x == "id" else x


# ---------- Categories ----------
class TutorialCategory(BaseModel):
    id: Optional[str] = Field(default=None, alias="_id")
    name: str
    description: Optional[str] = None
    icon: Optional[str] = None

    class Config:
        arbitrary_types_allowed = True
        json_encoders = { "ObjectId": str }
        alias_generator = lambda x: "_id" if x == "id" else x

# class TutorialCategory(BaseModel):
#     id: Optional[str] = Field(default=None, alias="_id")
#     name: str
#     description: Optional[str] = None
#     icon: Optional[str] = None


# ---------- Progress / Bookmarks (per-user) ----------
class TutorialProgress(BaseModel):
    id: Optional[str] = Field(default=None, alias="_id")
    tutorial_id: str
    username: str
    completed_lesson_ids: List[str] = Field(default_factory=list)
    last_lesson_id: Optional[str] = None
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        arbitrary_types_allowed = True
        json_encoders = { datetime: lambda v: v.isoformat(), "ObjectId": str }
        alias_generator = lambda x: "_id" if x == "id" else x


class Bookmark(BaseModel):
    id: Optional[str] = Field(default=None, alias="_id")
    tutorial_id: str
    username: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        arbitrary_types_allowed = True
        json_encoders = { datetime: lambda v: v.isoformat(), "ObjectId": str }
        alias_generator = lambda x: "_id" if x == "id" else x
