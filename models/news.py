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


class Category(BaseModel):
    id: Optional[str] = Field(default=None, alias="_id")
    name: str
    description: Optional[str] = None


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


class HoroscopeType(str, Enum):
    daily = "daily"        # दैनिक
    weekly = "weekly"      # साप्ताहिक
    monthly = "monthly"    # मासिक
    yearly = "yearly"      # वार्षिक


class HindiZodiacDetails(BaseModel):
    """Hindi horoscope details for each zodiac sign"""
    sign: ZodiacSign
    hindi_name: str = ""           # राशि का हिंदी नाम (e.g., "मेष राशि")
    content: str                   # Hindi horoscope content
    lucky_number: Optional[int] = None        # भाग्यशाली संख्या
    lucky_color: Optional[str] = None         # भाग्यशाली रंग
    lucky_day: Optional[str] = None           # भाग्यशाली दिन
    lucky_gemstone: Optional[str] = None      # भाग्यशाली रत्न
    mood: Optional[str] = None                # मूड (खुश, चिंतित, ऊर्जावान)
    love_score: Optional[int] = Field(default=None, ge=1, le=10)      # प्रेम अंक (1-10)
    career_score: Optional[int] = Field(default=None, ge=1, le=10)    # करियर अंक (1-10)
    health_score: Optional[int] = Field(default=None, ge=1, le=10)    # स्वास्थ्य अंक (1-10)
    finance_score: Optional[int] = Field(default=None, ge=1, le=10)   # धन अंक (1-10)
    remedy: Optional[str] = None              # उपाय (Remedies)


class HoroscopePost(BaseModel):
    """Hindi horoscope post model"""
    id: Optional[str] = Field(default=None, alias="_id")
    title: str                    # e.g., "दैनिक राशिफल - 6 अक्टूबर 2025"
    horoscope_date: date         # राशिफल की तारीख
    horoscope_type: HoroscopeType = HoroscopeType.daily
    
    # General predictions in Hindi
    general_prediction: Optional[str] = None    # सामान्य भविष्यवाणी
    cosmic_overview: Optional[str] = None       # ग्रहों की स्थिति
    panchang_details: Optional[str] = None      # पंचांग विवरण
    
    # Individual zodiac predictions in Hindi
    zodiac_predictions: List[HindiZodiacDetails] = Field(default_factory=list)
    
    # Metadata
    author_username: str
    published: bool = False
    featured: bool = False       # विशेष राशिफल के लिए
    
    # Scheduling System (IST Timezone)
    scheduled_publish_at: Optional[datetime] = None  # IST scheduled publish time
    auto_publish_enabled: bool = False              # Enable/disable auto-publishing
    publish_status: str = "draft"                   # draft, scheduled, published, expired
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None
    published_at: Optional[datetime] = None
    scheduled_at: Optional[datetime] = None         # When scheduling was set
    
    # Engagement metrics
    views: int = 0
    viewed_ips: List[str] = Field(default_factory=list)
    likes: int = 0
    liked_ips: List[str] = Field(default_factory=list)
    shares: int = 0
    
    # Hindi SEO fields
    meta_title: Optional[str] = None           # Hindi meta title
    meta_description: Optional[str] = None     # Hindi meta description
    hindi_keywords: List[str] = Field(default_factory=list)  # Hindi keywords
    
    class Config:
        arbitrary_types_allowed = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            date: lambda v: v.isoformat(),
            "ObjectId": str,
        }


class HoroscopeComment(BaseModel):
    """Comments for horoscope posts"""
    id: Optional[str] = Field(default=None, alias="_id")
    horoscope_id: str           # Reference to HoroscopePost
    zodiac_sign: Optional[ZodiacSign] = None  # User's zodiac sign
    name: str                   # Commenter name
    email: str                  # Commenter email
    content: str                # Comment in Hindi/English
    rating: Optional[int] = Field(default=None, ge=1, le=5)  # 1-5 star rating
    created_at: datetime = Field(default_factory=datetime.utcnow)
    is_approved: bool = False   # Admin moderation
    
    class Config:
        arbitrary_types_allowed = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            "ObjectId": str,
        }


# Request/Response models for horoscope API
class CreateHoroscopeRequest(BaseModel):
    title: str
    horoscope_date: date
    horoscope_type: HoroscopeType = HoroscopeType.daily
    general_prediction: Optional[str] = None
    cosmic_overview: Optional[str] = None
    panchang_details: Optional[str] = None
    zodiac_predictions: List[HindiZodiacDetails] = Field(default_factory=list)
    published: bool = False
    featured: bool = False
    
    # Scheduling fields (IST Timezone)
    scheduled_publish_at: Optional[datetime] = None  # IST datetime for scheduling
    auto_publish_enabled: bool = False              # Enable auto-publishing
    
    meta_title: Optional[str] = None
    meta_description: Optional[str] = None
    hindi_keywords: List[str] = Field(default_factory=list)


class UpdateHoroscopeRequest(BaseModel):
    title: Optional[str] = None
    horoscope_date: Optional[date] = None
    horoscope_type: Optional[HoroscopeType] = None
    general_prediction: Optional[str] = None
    cosmic_overview: Optional[str] = None
    panchang_details: Optional[str] = None
    zodiac_predictions: Optional[List[HindiZodiacDetails]] = None
    published: Optional[bool] = None
    featured: Optional[bool] = None
    
    # Scheduling fields (IST Timezone)
    scheduled_publish_at: Optional[datetime] = None
    auto_publish_enabled: Optional[bool] = None
    
    meta_title: Optional[str] = None
    meta_description: Optional[str] = None
    hindi_keywords: Optional[List[str]] = None
