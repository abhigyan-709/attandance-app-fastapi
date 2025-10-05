from pydantic import BaseModel, Field
from typing import List, Optional, Union, Dict, Any
from datetime import datetime, date
from enum import Enum


# ------------------------- Religious Content Enums -------------------------

class ReligiousContentType(str, Enum):
    RASHIFAL = "rashifal"              # Daily horoscope
    EDITORIAL = "editorial"            # Religious editorials
    THIS_DAY_HISTORY = "this_day_history"  # Historical events
    PANCHANG = "panchang"              # Daily panchang
    FESTIVAL = "festival"              # Festival information
    MANTRA = "mantra"                  # Daily mantras
    AARTI = "aarti"                    # Aartis and prayers
    VRAT_KATHAS = "vrat_kathas"        # Fasting stories
    SPIRITUAL_GURU = "spiritual_guru"   # Guru quotes and teachings

class ScheduleStatus(str, Enum):
    SCHEDULED = "scheduled"            # Future publication
    PUBLISHED = "published"            # Currently published
    DRAFT = "draft"                   # Draft version
    EXPIRED = "expired"               # Past scheduled time but not published

class ZodiacSign(str, Enum):
    ARIES = "mesh"          # मेष
    TAURUS = "vrishabh"     # वृषभ
    GEMINI = "mithun"       # मिथुन
    CANCER = "kark"         # कर्क
    LEO = "singh"           # सिंह
    VIRGO = "kanya"         # कन्या
    LIBRA = "tula"          # तुला
    SCORPIO = "vrishchik"   # वृश्चिक
    SAGITTARIUS = "dhanu"   # धनु
    CAPRICORN = "makar"     # मकर
    AQUARIUS = "kumbh"      # कुम्भ
    PISCES = "meen"         # मीन

class HinduCalendarMonth(str, Enum):
    CHAITRA = "chaitra"         # चैत्र
    VAISHAKHA = "vaishakha"     # वैशाख
    JYAISTHA = "jyaistha"       # ज्येष्ठ
    ASHADHA = "ashadha"         # आषाढ़
    SHRAVANA = "shravana"       # श्रावण
    BHADRAPADA = "bhadrapada"   # भाद्रपद
    ASHVINA = "ashvina"         # आश्विन
    KARTIKA = "kartika"         # कार्तिक
    AGRAHAYANA = "agrahayana"   # अग्रहायण
    PAUSHA = "pausha"           # पौष
    MAGHA = "magha"             # माघ
    PHALGUNA = "phalguna"       # फाल्गुन


# ------------------------- Religious Content Models -------------------------

class RashifalContent(BaseModel):
    """Horoscope content for a specific zodiac sign"""
    rashi: ZodiacSign
    prediction: str                  # Main horoscope text
    lucky_number: Optional[int] = None
    lucky_color: Optional[str] = None
    lucky_time: Optional[str] = None
    advice: Optional[str] = None
    rating: Optional[int] = Field(None, ge=1, le=5)  # 1-5 star rating

class PanchangContent(BaseModel):
    """Daily panchang information"""
    tithi: str                      # तिथि
    nakshatra: str                  # नक्षत्र
    yoga: str                       # योग
    karana: str                     # करण
    sunrise: Optional[str] = None
    sunset: Optional[str] = None
    moonrise: Optional[str] = None
    moonset: Optional[str] = None
    auspicious_time: Optional[str] = None  # शुभ मुहूर्त
    inauspicious_time: Optional[str] = None  # अशुभ काल

class ThisDayHistoryContent(BaseModel):
    """Historical events that happened on this day"""
    event_year: int
    event_description: str
    historical_figure: Optional[str] = None
    location: Optional[str] = None
    significance: Optional[str] = None

class FestivalContent(BaseModel):
    """Festival and celebration information"""
    festival_name: str
    festival_date: date
    significance: str
    rituals: Optional[List[str]] = Field(default_factory=list)
    special_foods: Optional[List[str]] = Field(default_factory=list)
    regional_variations: Optional[str] = None

class ScheduledContent(BaseModel):
    """Base model for all scheduled religious content"""
    id: Optional[str] = Field(default=None, alias="_id")
    content_type: ReligiousContentType
    title: str
    content: str                    # Main article content
    schedule_date: datetime         # When to publish
    schedule_status: ScheduleStatus = ScheduleStatus.SCHEDULED
    
    # Religious specific content (based on type)
    rashifal_data: Optional[List[RashifalContent]] = Field(default_factory=list)
    panchang_data: Optional[PanchangContent] = None
    history_data: Optional[List[ThisDayHistoryContent]] = Field(default_factory=list)
    festival_data: Optional[FestivalContent] = None
    
    # Standard news fields
    author_username: str
    categories: str = Field(default="धर्म")  # Default to religion category
    tags: List[str] = Field(default_factory=list)
    image_url: Optional[str] = None
    
    # Scheduling metadata
    auto_publish: bool = True       # Automatically publish at scheduled time
    timezone: str = Field(default="Asia/Kolkata")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None
    published_at: Optional[datetime] = None
    
    # Recurring schedule (for daily content like rashifal)
    is_recurring: bool = False
    recurrence_pattern: Optional[str] = None  # "daily", "weekly", "monthly"
    next_schedule_date: Optional[datetime] = None
    
    # Template support for recurring content
    template_id: Optional[str] = None
    template_variables: Optional[Dict[str, Any]] = Field(default_factory=dict)

class ContentTemplate(BaseModel):
    """Template for recurring religious content"""
    id: Optional[str] = Field(default=None, alias="_id")
    name: str
    content_type: ReligiousContentType
    template_content: str           # Template with placeholders like {{date}}, {{rashi}}
    default_variables: Dict[str, Any] = Field(default_factory=dict)
    is_active: bool = True
    created_by: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None


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
    keywords: Optional[List[str]] = Field(default_factory=list)  # SEO keywords
    
    # Religious Content Integration
    content_type: Optional[ReligiousContentType] = None     # Optional religious type
    schedule_date: Optional[datetime] = None                # For scheduled posts
    schedule_status: Optional[ScheduleStatus] = None        # Scheduling status
    
    # Hindu Calendar Integration
    hindu_month: Optional[HinduCalendarMonth] = None
    festival_related: Optional[bool] = False
    auspicious_timing: Optional[str] = None
    
    class Config:
        arbitrary_types_allowed = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            date: lambda v: v.isoformat(),
            "ObjectId": str,
        }
        alias_generator = lambda x: "_id" if x == "id" else x


class Category(BaseModel):
    id: Optional[str] = Field(default=None, alias="_id")
    name: str
    description: Optional[str] = None
    
    class Config:
        arbitrary_types_allowed = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            "ObjectId": str,
        }
        alias_generator = lambda x: "_id" if x == "id" else x


# ------------------------- Scheduling and UI Models -------------------------

class ScheduleRequest(BaseModel):
    """Request model for scheduling religious content"""
    content_type: ReligiousContentType
    title: str
    content: str
    schedule_date: datetime
    tags: List[str] = Field(default_factory=list)
    auto_publish: bool = True
    is_recurring: bool = False
    recurrence_pattern: Optional[str] = None
    template_id: Optional[str] = None
    
    # Type-specific data
    rashifal_data: Optional[List[RashifalContent]] = Field(default_factory=list)
    panchang_data: Optional[PanchangContent] = None
    history_data: Optional[List[ThisDayHistoryContent]] = Field(default_factory=list)
    festival_data: Optional[FestivalContent] = None

class ScheduledContentResponse(BaseModel):
    """Response model for scheduled content listing"""
    id: str
    content_type: ReligiousContentType
    title: str
    schedule_date: datetime
    schedule_status: ScheduleStatus
    auto_publish: bool
    is_recurring: bool
    created_at: datetime
    author_username: str

class BulkScheduleRequest(BaseModel):
    """Bulk scheduling for multiple dates (e.g., daily rashifal for a week)"""
    content_type: ReligiousContentType
    template_id: Optional[str] = None
    start_date: date
    end_date: date
    schedule_time: str = Field(default="06:00")  # Default morning time
    tags: List[str] = Field(default_factory=list)
    
class DashboardStats(BaseModel):
    """Admin dashboard statistics for religious content"""
    total_scheduled: int
    published_today: int
    pending_approval: int
    failed_publications: int
    content_type_breakdown: Dict[str, int]
    upcoming_schedules: List[ScheduledContentResponse]
