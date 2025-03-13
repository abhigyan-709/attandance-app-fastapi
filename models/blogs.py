from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime


class BlogPost(BaseModel):
    id: Optional[str] = Field(default=None, alias="_id")
    title: str
    content: str
    author_username: str  # Replacing author_id with username
    categories: List[str] = []
    published: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None


class Comment(BaseModel):
    id: Optional[str] = Field(default=None, alias="_id")
    blog_id: str  # Reference to BlogPost
    username: str  # Replacing user_id with username
    content: str
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Category(BaseModel):
    id: Optional[str] = Field(default=None, alias="_id")
    name: str
    description: Optional[str] = None
