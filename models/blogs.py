from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

class BlogPost(BaseModel):
    id: Optional[str] = Field(default=None, alias="_id")
    title: str
    content: str
    author_id: str  # Reference to logged-in admin user
    categories: List[str] = []
    image_name: Optional[str] = None  # Name of the uploaded image
    image_url: Optional[str] = None   # URL of the image in S3
    published: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None

class Comment(BaseModel):
    id: Optional[str] = Field(default=None, alias="_id")
    post_id: str  # Reference to BlogPost
    user_id: str  # Reference to User model
    content: str
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Category(BaseModel):
    id: Optional[str] = Field(default=None, alias="_id")
    name: str
    description: Optional[str] = None

