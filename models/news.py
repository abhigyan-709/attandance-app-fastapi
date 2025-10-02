from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime


class Comment(BaseModel):
    id: Optional[str] = Field(default=None, alias="_id")
    news_id: str  # Reference to newsPost
    name: str     # commenter's name
    email: str    # commenter's email
    phone: str    # commenter's phone
    content: str  # Comment text
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        arbitrary_types_allowed = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            "ObjectId": str,
        }
        alias_generator = lambda x: "_id" if x == "id" else x


class NewsPost(BaseModel):
    id: Optional[str] = Field(default=None, alias="_id")
    title: str
    image_url: Optional[str] = None
    content: str
    author_username: str
    categories: str
    tags: List[str] = Field(default_factory=list)          # ✅ safe default
    published: bool = False                                # ✅ draft/publish flag
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None
    comments: Optional[List[Comment]] = Field(default_factory=list)
    views: Optional[int] = 0
    viewed_ips: Optional[List[str]] = Field(default_factory=list)
    likes: int = 0
    liked_ips: List[str] = Field(default_factory=list)
    
    # SEO Enhancement Fields (Optional - won't break existing UI)
    slug: Optional[str] = None                              # Auto-generated if not provided
    meta_title: Optional[str] = None                        # Defaults to title
    meta_description: Optional[str] = None                  # Auto-extracted from content
    language: Optional[str] = Field(default="hi")          # Default language
    keywords: Optional[List[str]] = Field(default_factory=list)  # SEO keywords


class Category(BaseModel):
    id: Optional[str] = Field(default=None, alias="_id")
    name: str
    description: Optional[str] = None
