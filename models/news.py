from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime, date
from enum import Enum


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


class NewsContentImage(BaseModel):
    url: str
    caption: Optional[str] = None


class AuthorDetails(BaseModel):
    """Embedded author information in news posts"""
    username: str
    full_name: str
    author_profile_image: Optional[str] = None
    author_designation: Optional[str] = None
    author_bio: Optional[str] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "username": "rahul_kumar",
                "full_name": "Rahul Kumar",
                "author_profile_image": "https://example.com/profile.jpg",
                "author_designation": "Senior Editor",
                "author_bio": "Senior journalist with 10 years of experience"
            }
        }


class NewsPost(BaseModel):
    id: Optional[str] = Field(default=None, alias="_id")
    title: str
    image_url: Optional[str] = None
    content: str
    author_username: str  # Primary author username (for backward compatibility)
    
    # Enhanced author information
    author_details: Optional[AuthorDetails] = None  # Full author profile
    
    categories: str
    tags: List[str] = Field(default_factory=list)          # ✅ safe default
    content_images: List[NewsContentImage] = Field(default_factory=list)
    published: bool = False                                # ✅ draft/publish flag
    scheduled_publish: bool = False                        # ✅ is this a scheduled post
    scheduled_at: Optional[datetime] = None                # ✅ IST scheduled publish time
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
    keywords: Optional[List[str]] = Field(default_factory=list)  # SEO keywords
    
    # NEW SEO Fields for better Google ranking
    focus_keyword: Optional[str] = None                     # Primary SEO keyword (e.g., "Bihar Election 2026")
    image_alt: Optional[str] = None                         # Alt text for featured image (for accessibility & SEO)
    reading_time_minutes: Optional[int] = None              # Estimated reading time (auto-calculated)
    is_breaking_news: Optional[bool] = False                # Breaking news flag (for schema.org)
    is_opinion: Optional[bool] = False                      # Opinion/Editorial piece (for schema.org)
    word_count: Optional[int] = None                        # Word count (auto-calculated)
    canonical_url_override: Optional[str] = None            # Custom canonical URL if different from default


class Category(BaseModel):
    id: Optional[str] = Field(default=None, alias="_id")
    name: str
    description: Optional[str] = None
    hindi_keywords: Optional[List[str]] = None


# ==================== HOROSCOPE MODELS ====================

class ZodiacSign(str, Enum):
    """Hindi zodiac signs (राशि)"""
    mesh = "mesh"          # मेष (Aries)
    vrishabh = "vrishabh"  # वृषभ (Taurus)
    mithun = "mithun"      # मिथुन (Gemini)
    kark = "kark"          # कर्क (Cancer)
    simha = "simha"        # सिंह (Leo)
    kanya = "kanya"        # कन्या (Virgo)
    tula = "tula"          # तुला (Libra)
    vrishchik = "vrishchik" # वृश्चिक (Scorpio)
    dhanu = "dhanu"        # धनु (Sagittarius)
    makar = "makar"        # मकर (Capricorn)
    kumbh = "kumbh"        # कुम्भ (Aquarius)
    meen = "meen"          # मीन (Pisces)


class ZodiacPrediction(BaseModel):
    """Individual zodiac sign prediction"""
    sign: ZodiacSign
    hindi_name: str         # e.g., "मेष राशि"
    syllables: str          # e.g., "चू, चे, चो, ला, ली, लू, ले, लो, अ"
    prediction: str         # Full Hindi prediction text
    
    class Config:
        json_schema_extra = {
            "example": {
                "sign": "mesh",
                "hindi_name": "मेष राशि",
                "syllables": "चू, चे, चो, ला, ली, लू, ले, लो, अ",
                "prediction": "आज अपने काम के लिए दूसरों पर दबाव न डालें..."
            }
        }


class DailyHoroscope(BaseModel):
    """Daily horoscope post with all 12 zodiac predictions"""
    id: Optional[str] = Field(default=None, alias="_id")
    title: str = "राशि फल✡️🙏🏻"  # Default title
    date: date                      # Horoscope date
    zodiac_predictions: List[ZodiacPrediction]  # All 12 zodiac signs
    closing_message: str = "☘️आपका दिन मंगलमय हो।☘️"  # Default closing
    contact_info: Optional[str] = None  # Contact details for consultation
    
    # Metadata
    author_username: str
    author_details: Optional[AuthorDetails] = None  # Embedded author information
    published: bool = False
    
    # Scheduling (IST timezone)
    scheduled_publish: bool = False                        # ✅ is this a scheduled post
    scheduled_at: Optional[datetime] = None                # ✅ IST scheduled publish time (stored in UTC)
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None
    published_at: Optional[datetime] = None
    
    # Engagement
    views: int = 0
    viewed_ips: List[str] = Field(default_factory=list)
    likes: int = 0
    liked_ips: List[str] = Field(default_factory=list)
    
    class Config:
        arbitrary_types_allowed = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            date: lambda v: v.isoformat(),
            "ObjectId": str,
        }


class CreateHoroscopeRequest(BaseModel):
    """Request model for creating horoscope"""
    title: str = "राशि फल✡️🙏🏻"
    date: date
    zodiac_predictions: List[ZodiacPrediction]
    closing_message: str = "☘️आपका दिन मंगलमय हो।☘️"
    contact_info: Optional[str] = None
    published: bool = False
    scheduled_publish: bool = False                        # ✅ Enable scheduled publishing
    scheduled_at: Optional[str] = None                     # ✅ IST datetime string: "YYYY-MM-DDTHH:MM"


class UpdateHoroscopeRequest(BaseModel):
    """Request model for updating horoscope"""
    title: Optional[str] = None
    date: Optional[date] = None
    zodiac_predictions: Optional[List[ZodiacPrediction]] = None
    closing_message: Optional[str] = None
    contact_info: Optional[str] = None
    published: Optional[bool] = None
    scheduled_publish: Optional[bool] = None               # ✅ Toggle scheduled publishing
    scheduled_at: Optional[str] = None                     # ✅ Update scheduled time


# ==================== LIVE STREAM MODELS ====================

class StreamPlatform(str, Enum):
    """Supported live streaming platforms"""
    youtube = "youtube"
    facebook = "facebook"
    twitter = "twitter"          # X/Twitter
    instagram = "instagram"
    dailymotion = "dailymotion"
    vimeo = "vimeo"
    custom = "custom"            # Any other platform with iframe support


class LiveStream(BaseModel):
    """Live stream configuration for news website"""
    id: Optional[str] = Field(default=None, alias="_id")
    title: str                                              # Stream title (e.g., "Live News Coverage")
    platform: StreamPlatform                                # Platform type
    stream_url: str                                         # Full embed URL for iframe
    description: Optional[str] = None                       # Optional description
    thumbnail_url: Optional[str] = None                     # Thumbnail image URL
    is_active: bool = True                                  # Show/hide stream on website
    is_live: bool = False                                   # Currently live indicator
    display_order: int = 0                                  # For ordering multiple streams
    
    # Metadata
    created_by: str                                         # Admin username who created
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None
    
    class Config:
        arbitrary_types_allowed = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            "ObjectId": str,
        }


class CreateLiveStreamRequest(BaseModel):
    """Request model for creating a live stream"""
    title: str
    platform: StreamPlatform
    stream_url: str                                         # YouTube/Facebook embed URL
    description: Optional[str] = None
    thumbnail_url: Optional[str] = None
    is_active: bool = True
    is_live: bool = False
    display_order: int = 0
    
    class Config:
        json_schema_extra = {
            "example": {
                "title": "GTNews18 Live",
                "platform": "youtube",
                "stream_url": "https://www.youtube.com/embed/LIVE_VIDEO_ID",
                "description": "24/7 Live News Coverage",
                "is_active": True,
                "is_live": True,
                "display_order": 1
            }
        }


class UpdateLiveStreamRequest(BaseModel):
    """Request model for updating a live stream"""
    title: Optional[str] = None
    platform: Optional[StreamPlatform] = None
    stream_url: Optional[str] = None
    description: Optional[str] = None
    thumbnail_url: Optional[str] = None
    is_active: Optional[bool] = None
    is_live: Optional[bool] = None
    display_order: Optional[int] = None
