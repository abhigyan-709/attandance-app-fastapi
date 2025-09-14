# models/social.py
from pydantic import BaseModel, Field, HttpUrl
from typing import Optional, Literal

Platform = Literal["twitter", "instagram"]
Theme = Literal["light", "dark"]

class SocialRenderRequest(BaseModel):
    platform: Platform = Field(..., description="twitter | instagram")
    theme: Theme = "light"
    username: str = Field(..., min_length=1, max_length=30, description="@handle or username")
    display_name: Optional[str] = Field(None, max_length=40, description="Shown name for Twitter")
    verified: bool = False
    text: str = Field(..., min_length=1, max_length=280 if True else 2200, description="Post content")
    avatar_url: Optional[HttpUrl] = None
    likes: Optional[int] = 0
    reposts: Optional[int] = 0  # retweets/reposts for Twitter
    comments: Optional[int] = 0
    minutes_ago: Optional[int] = 5  # simple relative timestamp

    # Instagram-only (optional future extension)
    location: Optional[str] = None

class SocialRenderResponse(BaseModel):
    image_data_url: str  # "data:image/png;base64,...."

class ListResponse(BaseModel):
    items: list[str]
