# from pydantic import BaseModel, Field
# from typing import List, Optional
# from datetime import datetime


# class Comment(BaseModel):
#     id: Optional[str] = Field(default=None, alias="_id")
#     blog_id: str  # Reference to BlogPost
#     name: str     # New field for commenter's name
#     email: str    # New field for commenter's email
#     phone: str    # New field for commenter's phone
#     content: str  # Comment text
#     created_at: datetime = Field(default_factory=datetime.utcnow)

#     class Config:
#         arbitrary_types_allowed = True
#         json_encoders = {
#             datetime: lambda v: v.isoformat(),
#             "ObjectId": str
#         }
#         alias_generator = lambda x: "_id" if x == "id" else x

# class BlogPost(BaseModel):
#     id: Optional[str] = Field(default=None, alias="_id")
#     title: str
#     image_url: Optional[str] = None
#     content: str
#     author_username: str  # Replacing author_id with username
#     categories: str
#     tags: List[str] = []  # 🔹 New Field for Tags
#     published: bool = False
#     created_at: datetime = Field(default_factory=datetime.utcnow)
#     updated_at: Optional[datetime] = None
#     comments: Optional[List[Comment]] = []  # Fetch comments while getting blogs
#     views: Optional[int] = 0  # New field for total view count
#     viewed_ips: Optional[List[str]] = []  # New field to track IPs
#     likes: int = 0           # Added
#     liked_ips: List[str] = [] # Added


# class Category(BaseModel):
#     id: Optional[str] = Field(default=None, alias="_id")
#     name: str
#     description: Optional[str] = None


from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime


class Comment(BaseModel):
    id: Optional[str] = Field(default=None, alias="_id")
    blog_id: str  # Reference to BlogPost
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


class BlogPost(BaseModel):
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


class Category(BaseModel):
    id: Optional[str] = Field(default=None, alias="_id")
    name: str
    description: Optional[str] = None
