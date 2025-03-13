from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

class Comment(BaseModel):
    id: Optional[str] = Field(default=None, alias="_id")
    blog_id: str  # Reference to BlogPost
    username: str  # Storing username instead of user ID
    content: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

class BlogPost(BaseModel):
    id: Optional[str] = Field(default=None, alias="_id")
    title: str
    image_url: Optional[str] = None
    content: str
    author_username: str  # Replacing author_id with username
    categories: List[str] = []
    published: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None
    comments: Optional[List[Comment]] = []  # Fetch comments while getting blogs

class Category(BaseModel):
    id: Optional[str] = Field(default=None, alias="_id")
    name: str
    description: Optional[str] = None
