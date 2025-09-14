# models/social.py
from pydantic import BaseModel, Field, field_validator
from typing import Optional, Literal

Platform = Literal["twitter", "instagram"]
Theme = Literal["light", "dark"]

class SocialRenderRequest(BaseModel):
    platform: Platform
    theme: Theme = "light"
    username: str = Field(..., min_length=1, max_length=30)
    display_name: Optional[str] = Field(None, max_length=40)
    verified: bool = False
    text: str = Field(..., min_length=1, max_length=2200)
    avatar_url: Optional[str] = None   # <— allow plain string or blank
    likes: Optional[int] = 0
    reposts: Optional[int] = 0
    comments: Optional[int] = 0
    minutes_ago: Optional[int] = 5
    location: Optional[str] = None

    @field_validator("avatar_url")
    @classmethod
    def _blank_to_none(cls, v: Optional[str]):
        if not v:
            return None
        v = v.strip()
        if v.lower().startswith(("http://", "https://")):
            return v
        # ignore non-URLs instead of erroring
        return None
