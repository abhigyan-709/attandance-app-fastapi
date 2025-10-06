# app/models/biodata.py
from __future__ import annotations
from typing import List, Optional, Dict, Any, Union
from datetime import date, datetime
from pydantic import BaseModel, Field, EmailStr, HttpUrl, field_serializer, field_validator
from enum import Enum

# ---------------- Enums (India-focused) ----------------
class Gender(str, Enum):
    male = "male"
    female = "female"
    other = "other"

class MaritalStatus(str, Enum):
    never_married = "never_married"
    divorced = "divorced"
    widowed = "widowed"
    annulled = "annulled"

class Religion(str, Enum):
    hindu = "hindu"
    muslim = "muslim"
    sikh = "sikh"
    christian = "christian"
    buddhist = "buddhist"
    jain = "jain"
    parsi = "parsi"
    other = "other"

class CasteCategory(str, Enum):
    general = "general"
    obc = "obc"
    sc = "sc"
    st = "st"
    ews = "ews"
    na = "na"

class Manglik(str, Enum):
    yes = "yes"
    no = "no"
    partial = "partial"
    dont_know = "dont_know"

class Diet(str, Enum):
    vegetarian = "vegetarian"
    non_vegetarian = "non_vegetarian"
    eggetarian = "eggetarian"
    vegan = "vegan"
    jain = "jain"

class Drinking(str, Enum):
    no = "no"
    occasionally = "occasionally"
    yes = "yes"

class Smoking(str, Enum):
    no = "no"
    occasionally = "occasionally"
    yes = "yes"

class BodyType(str, Enum):
    slim = "slim"
    athletic = "athletic"
    average = "average"
    heavy = "heavy"

class Complexion(str, Enum):
    very_fair = "very_fair"
    fair = "fair"
    wheatish = "wheatish"
    wheatish_brown = "wheatish_brown"
    dark = "dark"

class EducationLevel(str, Enum):
    high_school = "high_school"
    diploma = "diploma"
    bachelors = "bachelors"
    masters = "masters"
    doctorate = "doctorate"
    other = "other"

class EmploymentType(str, Enum):
    not_working = "not_working"
    private = "private"
    government = "government"
    business = "business"
    self_employed = "self_employed"
    defense = "defense"
    other = "other"

class Currency(str, Enum):
    INR = "INR"
    USD = "USD"
    EUR = "EUR"
    GBP = "GBP"
    AED = "AED"
    OTHER = "OTHER"

class LanguageProficiency(str, Enum):
    basic = "basic"
    conversational = "conversational"
    fluent = "fluent"
    native = "native"

# ============ ENHANCED HINDU MATRIMONIAL ENUMS ============

class Varna(str, Enum):
    brahmin = "brahmin"
    kshatriya = "kshatriya"
    vaishya = "vaishya"
    shudra = "shudra"
    other = "other"

class ReligiousSect(str, Enum):
    shaivism = "shaivism"
    vaishnavism = "vaishnavism"
    shaktism = "shaktism"
    smartism = "smartism"
    arya_samaj = "arya_samaj"
    brahmo_samaj = "brahmo_samaj"
    other = "other"

class Dosha(str, Enum):
    none = "none"
    mangal_dosha = "mangal_dosha"
    shani_dosha = "shani_dosha"
    rahu_ketu_dosha = "rahu_ketu_dosha"
    kaal_sarp_dosha = "kaal_sarp_dosha"
    pitra_dosha = "pitra_dosha"

class FamilyType(str, Enum):
    nuclear = "nuclear"
    joint = "joint"
    extended = "extended"

class FamilyValues(str, Enum):
    traditional = "traditional"
    moderate = "moderate"
    liberal = "liberal"

class EconomicStatus(str, Enum):
    lower_middle = "lower_middle"
    middle = "middle"
    upper_middle = "upper_middle"
    affluent = "affluent"
    wealthy = "wealthy"

class PhotoCategory(str, Enum):
    formal_portrait = "formal_portrait"
    family_photo = "family_photo"
    traditional_dress = "traditional_dress"
    religious_ceremony = "religious_ceremony"
    professional = "professional"
    candid = "candid"

class RegionalTradition(str, Enum):
    north_indian = "north_indian"
    south_indian = "south_indian"
    east_indian = "east_indian"
    west_indian = "west_indian"
    central_indian = "central_indian"

class BiodataType(str, Enum):
    basic = "basic"
    detailed = "detailed"

# ---------------- Sub-models ----------------
class Photo(BaseModel):
    url: HttpUrl
    caption: Optional[str] = None
    is_primary: bool = False
    category: Optional[PhotoCategory] = PhotoCategory.candid  # New field

# ============ ENHANCED HINDU MATRIMONIAL MODELS ============

class DetailedReligiousInfo(BaseModel):
    """Enhanced religious information for Hindu matrimonial"""
    varna: Optional[Varna] = None
    sub_caste: Optional[str] = None  # Specific community within caste
    religious_sect: Optional[ReligiousSect] = None
    temple_association: Optional[str] = None  # Regular temple visits
    religious_education: Optional[str] = None  # Sanskrit, Vedic studies
    spiritual_practices: List[str] = Field(default_factory=list)  # yoga, meditation, etc.
    festivals_observed: List[str] = Field(default_factory=list)  # major festivals
    religious_role: Optional[str] = None  # priest, community leader, etc.
    pilgrimage_history: List[str] = Field(default_factory=list)  # places visited
    daily_prayers: bool = False
    vegetarian_since: Optional[str] = None  # birth, childhood, recent

class DetailedAstrology(BaseModel):
    """Enhanced astrological information"""
    birth_time: Optional[str] = None  # Exact time HH:MM
    birth_place_coordinates: Optional[str] = None  # Latitude, Longitude
    rashi_detailed: Optional[str] = None  # Moon sign
    nakshatra_detailed: Optional[str] = None  # Birth star
    lagna: Optional[str] = None  # Ascendant
    navamsa: Optional[str] = None  # D9 chart
    dasha_period: Optional[str] = None  # Current planetary period
    doshas: List[Dosha] = Field(default_factory=list)
    kundli_pdf_url: Optional[HttpUrl] = None  # Uploaded kundli
    guna_milan_score: Optional[int] = None  # Out of 36
    auspicious_time_preference: Optional[str] = None  # Marriage muhurat
    astrologer_consultation: Optional[str] = None  # Astrologer details

class ExtendedFamilyMember(BaseModel):
    """Extended family member details"""
    relation: str  # Father, Mother, Brother, Sister, Uncle, Aunt, etc.
    name: Optional[str] = None
    age: Optional[int] = None
    occupation: Optional[str] = None
    education: Optional[str] = None
    is_married: Optional[bool] = None
    spouse_name: Optional[str] = None
    children_count: Optional[int] = None
    location: Optional[str] = None

class DetailedFamilyBackground(BaseModel):
    """Enhanced family information for Hindu matrimonial"""
    # Immediate family (existing fields enhanced)
    father_full_name: Optional[str] = None
    father_age: Optional[int] = None
    father_education: Optional[str] = None
    father_occupation_details: Optional[str] = None
    father_employer: Optional[str] = None
    
    mother_full_name: Optional[str] = None
    mother_age: Optional[int] = None
    mother_education: Optional[str] = None
    mother_occupation_details: Optional[str] = None
    
    # Extended family
    extended_family: List[ExtendedFamilyMember] = Field(default_factory=list)
    
    # Family background
    family_reputation: Optional[str] = None  # Social standing
    ancestral_village: Optional[str] = None  # Original native place
    family_tradition: Optional[str] = None  # Traditional occupation/business
    property_details: Optional[str] = None  # Ancestral property, land
    economic_status: Optional[EconomicStatus] = None
    
    # Family characteristics
    family_size: Optional[int] = None  # Total family members
    brothers_count: Optional[int] = None
    sisters_count: Optional[int] = None
    married_siblings: Optional[int] = None
    
    # Cultural aspects
    regional_tradition: Optional[RegionalTradition] = None
    family_language: Optional[str] = None  # Primary family language
    cultural_activities: List[str] = Field(default_factory=list)  # Music, dance, arts

class TraditionalPreferences(BaseModel):
    """Traditional Hindu marriage preferences"""
    same_caste_only: bool = True
    inter_caste_acceptable: List[str] = Field(default_factory=list)  # Acceptable castes
    gotra_restrictions: List[str] = Field(default_factory=list)  # Restricted gotras
    regional_preference: List[RegionalTradition] = Field(default_factory=list)
    
    # Traditional values
    joint_family_preference: bool = True
    traditional_gender_roles: bool = True
    religious_observance_required: bool = True
    vegetarian_requirement: bool = True
    
    # Economic expectations
    dowry_expectations: Optional[str] = None  # If applicable
    gift_expectations: Optional[str] = None  # Traditional gifts
    
    # Ceremony preferences
    wedding_type: Optional[str] = None  # Simple/Grand/Destination
    ceremony_traditions: List[str] = Field(default_factory=list)  # Specific rituals
    auspicious_months: List[str] = Field(default_factory=list)  # Preferred months

class MarriagePlanning(BaseModel):
    """Marriage ceremony planning details"""
    preferred_wedding_season: Optional[str] = None  # Spring, Winter, etc.
    guest_count_expectation: Optional[str] = None  # 50-100, 100-500, 500+
    venue_preference: Optional[str] = None  # Temple, Banquet, Destination
    budget_range: Optional[str] = None  # Conservative estimate
    rituals_to_include: List[str] = Field(default_factory=list)  # Specific ceremonies
    cultural_requirements: List[str] = Field(default_factory=list)  # Regional customs

class VerificationDocuments(BaseModel):
    """Document verification for traditional matrimonial"""
    birth_certificate_url: Optional[HttpUrl] = None
    caste_certificate_url: Optional[HttpUrl] = None
    education_certificates: List[HttpUrl] = Field(default_factory=list)
    income_proof_url: Optional[HttpUrl] = None
    id_proof_url: Optional[HttpUrl] = None
    address_proof_url: Optional[HttpUrl] = None
    character_references: List[str] = Field(default_factory=list)  # Reference contacts
    medical_reports: List[HttpUrl] = Field(default_factory=list)

class Address(BaseModel):
    address_line1: Optional[str] = None
    address_line2: Optional[str] = None
    city: Optional[str] = None
    district: Optional[str] = None
    state: Optional[str] = None  # e.g., Bihar
    country: str = "India"
    pincode: Optional[str] = None

class ContactInfo(BaseModel):
    email: Optional[EmailStr] = None
    phone_country_code: str = "+91"
    phone_number: Optional[str] = None
    alt_phone_number: Optional[str] = None
    whatsapp_number: Optional[str] = None
    address: Optional[Address] = None

class Education(BaseModel):
    level: Optional[EducationLevel] = None
    degree: Optional[str] = None       # e.g., B.Tech (CSE)
    institute: Optional[str] = None
    graduation_year: Optional[int] = None

    @field_validator('level', mode='before')
    @classmethod
    def handle_empty_level(cls, v):
        """Handle empty string for education level"""
        if v == "":
            return None
        return v

    @field_validator('graduation_year', mode='before')
    @classmethod
    def handle_empty_graduation_year(cls, v):
        """Handle empty string for graduation year"""
        if v == "" or v is None:
            return None
        return v

class Occupation(BaseModel):
    employment_type: Optional[EmploymentType] = None
    organization: Optional[str] = None
    designation: Optional[str] = None
    annual_income_value: Optional[float] = None
    annual_income_currency: Currency = Currency.INR

    @field_validator('employment_type', mode='before')
    @classmethod
    def handle_empty_employment_type(cls, v):
        """Handle empty string for employment type"""
        if v == "":
            return None
        return v

    @field_validator('annual_income_value', mode='before')
    @classmethod
    def handle_empty_income(cls, v):
        """Handle empty string for annual income"""
        if v == "" or v is None:
            return None
        return v

class FamilyMember(BaseModel):
    relation: str           # e.g., Father, Mother, Brother, Sister
    name: Optional[str] = None
    occupation: Optional[str] = None
    is_married: Optional[bool] = None

class FamilyDetails(BaseModel):
    father_name: Optional[str] = None
    father_occupation: Optional[str] = None
    mother_name: Optional[str] = None
    mother_occupation: Optional[str] = None
    siblings: List[FamilyMember] = Field(default_factory=list)
    family_type: Optional[str] = None      # Joint/Nuclear
    family_values: Optional[str] = None    # Traditional/Moderate/Liberal
    native_place: Optional[str] = None

class PhysicalAttributes(BaseModel):
    height_cm: Optional[float] = None      # store in cm
    weight_kg: Optional[float] = None
    body_type: Optional[BodyType] = None
    complexion: Optional[Complexion] = None
    blood_group: Optional[str] = None

    @field_validator('body_type', mode='before')
    @classmethod
    def handle_empty_body_type(cls, v):
        """Handle empty string for body type"""
        if v == "":
            return None
        return v

    @field_validator('complexion', mode='before')
    @classmethod
    def handle_empty_complexion(cls, v):
        """Handle empty string for complexion"""
        if v == "":
            return None
        return v

class Lifestyle(BaseModel):
    diet: Optional[Diet] = None
    drinking: Optional[Drinking] = None
    smoking: Optional[Smoking] = None

class Horoscope(BaseModel):
    date_of_birth: Optional[date] = None
    time_of_birth: Optional[str] = None    # "HH:MM"
    place_of_birth: Optional[str] = None
    manglik: Optional[Manglik] = None
    gotra: Optional[str] = None
    rashi: Optional[str] = None
    nakshatra: Optional[str] = None
    kundli_url: Optional[HttpUrl] = None   # if generated separately

    @field_validator('date_of_birth', mode='before')
    @classmethod
    def handle_empty_date_of_birth(cls, v):
        """Handle empty string for date of birth"""
        if v == "" or v is None:
            return None
        return v

    @field_validator('kundli_url', mode='before')
    @classmethod
    def handle_empty_kundli_url(cls, v):
        """Handle empty string for kundli URL"""
        if v == "" or v is None:
            return None
        return v

class Languages(BaseModel):
    known: Dict[str, LanguageProficiency] = Field(
        default_factory=lambda: {"Hindi": LanguageProficiency.fluent, "English": LanguageProficiency.conversational}
    )

class PartnerPreferences(BaseModel):
    min_age: Optional[int] = None
    max_age: Optional[int] = None
    min_height_cm: Optional[float] = None
    max_height_cm: Optional[float] = None
    marital_status: Optional[List[MaritalStatus]] = None
    religion: Optional[List[Religion]] = None
    caste: Optional[List[str]] = None
    gotra: Optional[List[str]] = None
    education_levels: Optional[List[EducationLevel]] = None
    occupations: Optional[List[EmploymentType]] = None
    mother_tongues: Optional[List[str]] = None
    preferred_locations: Optional[List[str]] = None
    diet: Optional[List[Diet]] = None

    @field_validator('marital_status', 'religion', 'education_levels', 'occupations', 'diet', mode='before')
    @classmethod
    def convert_boolean_to_none_for_lists(cls, v):
        """Convert boolean false to None for list fields"""
        if v is False or v == "":
            return None
        return v

    @field_validator('caste', 'gotra', 'mother_tongues', 'preferred_locations', mode='before')
    @classmethod
    def convert_string_to_list(cls, v):
        """Convert string values to lists, handling comma-separated values"""
        if v is None or v is False or v == "":
            return None
        if isinstance(v, str):
            if not v.strip():
                return []
            # Split by comma and strip whitespace, filter out empty strings
            return [item.strip() for item in v.split(',') if item.strip()]
        if isinstance(v, list):
            return v
        return v
        if isinstance(v, list):
            return v
        return v

# ---------------- Core candidate profile ----------------
class CandidateProfile(BaseModel):
    id: Optional[str] = Field(default=None, alias="_id")  # Mongo-friendly
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Profile type selection
    biodata_type: BiodataType = BiodataType.basic  # New field to determine profile type

    # Core identity (existing fields)
    first_name: str
    last_name: Optional[str] = None
    gender: Gender
    dob: date
    religion: Religion = Religion.hindu
    caste: Optional[str] = None              # e.g., Bhumihar, Kayastha, Yadav...
    caste_category: Optional[CasteCategory] = None
    gotra: Optional[str] = None
    mother_tongue: Optional[str] = "Hindi"
    marital_status: MaritalStatus = MaritalStatus.never_married
    about_me: Optional[str] = None
    profile_owner_relation: Optional[str] = None  # self/father/mother/brother/sister/guardian

    # Photos (S3/public URLs) - Enhanced
    photos: List[Photo] = Field(default_factory=list)

    # Basic sections (existing)
    contact: Optional[ContactInfo] = None
    education: Optional[Education] = None
    occupation: Optional[Occupation] = None
    family: Optional[FamilyDetails] = None
    physical: Optional[PhysicalAttributes] = None
    lifestyle: Optional[Lifestyle] = None
    horoscope: Optional[Horoscope] = None
    languages: Optional[Languages] = None
    partner_preferences: Optional[PartnerPreferences] = None

    # ============ ENHANCED DETAILED HINDU MATRIMONIAL SECTIONS ============
    # These fields are only populated when biodata_type = "detailed"
    
    # Enhanced religious information
    detailed_religious_info: Optional[DetailedReligiousInfo] = None
    
    # Enhanced astrology
    detailed_astrology: Optional[DetailedAstrology] = None
    
    # Enhanced family background
    detailed_family_background: Optional[DetailedFamilyBackground] = None
    
    # Traditional preferences
    traditional_preferences: Optional[TraditionalPreferences] = None
    
    # Marriage planning
    marriage_planning: Optional[MarriagePlanning] = None
    
    # Document verification
    verification_documents: Optional[VerificationDocuments] = None

    # Additional metadata for detailed profiles
    profile_completeness_score: Optional[float] = None  # Percentage 0-100
    last_activity: Optional[datetime] = None
    profile_views: int = 0
    interests_received: int = 0
    interests_sent: int = 0
    
    # Admin fields
    admin_notes: Optional[str] = None
    verification_status: Optional[str] = None  # pending/verified/rejected
    verified_by: Optional[str] = None  # Admin username
    verified_at: Optional[datetime] = None

    # Misc (existing)
    custom_fields: Dict[str, Any] = Field(default_factory=dict)
    is_active: bool = True
    is_verified: bool = False

    @field_serializer("created_at", "updated_at", "last_activity", "verified_at")
    def _ser_dt(self, v: Optional[datetime], _info):
        return v.isoformat() if v else None

    class Config:
        populate_by_name = True
        json_schema_extra = {
            "example_basic": {
                "biodata_type": "basic",
                "first_name": "Ananya",
                "last_name": "Kumar",
                "gender": "female",
                "dob": "1997-08-14",
                "religion": "hindu",
                "caste": "Kayastha",
                "gotra": "Kashyap",
                "mother_tongue": "Hindi",
                "marital_status": "never_married",
                "about_me": "Software engineer with a love for travel and books.",
                "photos": [
                    {"url": "https://s3.ap-south-1.amazonaws.com/bucket/ananya1.jpg", "is_primary": True, "category": "formal_portrait"},
                    {"url": "https://s3.../ananya2.jpg", "caption": "Candid", "category": "candid"}
                ],
                "contact": {
                    "email": "ananya@example.com",
                    "phone_country_code": "+91",
                    "phone_number": "9876543210",
                    "address": {"city": "Patna", "state": "Bihar", "country": "India", "pincode": "800001"}
                },
                "education": {"level": "masters", "degree": "MCA", "institute": "XYZ University", "graduation_year": 2020},
                "occupation": {"employment_type": "private", "organization": "ABC Tech", "designation": "SDE-2", "annual_income_value": 18.0},
                "physical": {"height_cm": 163, "weight_kg": 56, "body_type": "slim", "complexion": "wheatish"},
                "lifestyle": {"diet": "vegetarian", "drinking": "no", "smoking": "no"}
            },
            "example_detailed": {
                "biodata_type": "detailed",
                "first_name": "Priya",
                "last_name": "Sharma",
                "gender": "female",
                "dob": "1995-03-12",
                "religion": "hindu",
                "caste": "Brahmin",
                "gotra": "Bharadwaj",
                "mother_tongue": "Hindi",
                "marital_status": "never_married",
                "profile_owner_relation": "father",
                "about_me": "Traditional girl with modern education, believes in Hindu values and family traditions.",
                "detailed_religious_info": {
                    "varna": "brahmin",
                    "sub_caste": "Gaur Brahmin",
                    "religious_sect": "vaishnavism",
                    "temple_association": "Local Hanuman Temple",
                    "spiritual_practices": ["daily_prayers", "yoga", "meditation"],
                    "festivals_observed": ["Diwali", "Karva_Chauth", "Navratri", "Dussehra"],
                    "daily_prayers": True,
                    "vegetarian_since": "birth"
                },
                "detailed_astrology": {
                    "birth_time": "08:30",
                    "birth_place_coordinates": "25.5941° N, 85.1376° E",
                    "rashi_detailed": "Kanya (Virgo)",
                    "nakshatra_detailed": "Hasta",
                    "lagna": "Tula (Libra)",
                    "doshas": ["none"],
                    "guna_milan_score": 32,
                    "auspicious_time_preference": "Winter months (Dec-Feb)"
                },
                "detailed_family_background": {
                    "father_full_name": "Shri Rajesh Kumar Sharma",
                    "father_age": 55,
                    "father_education": "M.Com",
                    "father_occupation_details": "Senior Accountant in Government Office",
                    "mother_full_name": "Smt. Sunita Sharma",
                    "mother_age": 50,
                    "mother_education": "B.A.",
                    "mother_occupation_details": "Homemaker",
                    "brothers_count": 1,
                    "sisters_count": 0,
                    "married_siblings": 0,
                    "family_reputation": "Well respected in community",
                    "ancestral_village": "Gaya, Bihar",
                    "economic_status": "middle",
                    "regional_tradition": "north_indian"
                },
                "traditional_preferences": {
                    "same_caste_only": True,
                    "joint_family_preference": True,
                    "traditional_gender_roles": True,
                    "religious_observance_required": True,
                    "vegetarian_requirement": True,
                    "auspicious_months": ["November", "December", "January", "February"]
                },
                "marriage_planning": {
                    "preferred_wedding_season": "Winter",
                    "guest_count_expectation": "200-300",
                    "venue_preference": "Traditional Banquet Hall",
                    "rituals_to_include": ["Mehendi", "Sangam", "Pheras", "Vidaai"]
                }
            }
        }
