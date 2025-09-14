from pydantic import BaseModel, Field, field_validator
from typing import Optional, Literal, List

Platform = Literal["twitter", "instagram"]
Theme = Literal["light", "dark"]

class SocialRenderRequest(BaseModel):
    platform: Platform
    theme: Theme = "light"

    # common
    username: str = Field(..., min_length=1, max_length=30)
    text: str = Field(..., min_length=1, max_length=2200)

    # twitter-only (ignored for IG)
    display_name: Optional[str] = Field(None, max_length=40)
    verified: bool = False
    reposts: Optional[int] = 0
    comments: Optional[int] = 0

    # shared counters/meta
    likes: Optional[int] = 0
    minutes_ago: Optional[int] = 5

    # optional images/extra meta
    avatar_url: Optional[str] = None
    photo_url: Optional[str] = None     # IG photo (optional)
    location: Optional[str] = None      # IG optional location
    width: Optional[int] = 900          # overall width (scales layout)

    @field_validator("avatar_url", "photo_url")
    @classmethod
    def _blank_to_http_url_or_none(cls, v: Optional[str]):
        if not v:
            return None
        v = v.strip()
        if v.lower().startswith(("http://", "https://")):
            return v
        # ignore non-urls (don't raise)
        return None

class SocialRenderResponse(BaseModel):
    image_data_url: str  # "data:image/png;base64,...."

class ListResponse(BaseModel):
    items: List[str]
