# app/models/biodata.py
from __future__ import annotations
from typing import List, Optional, Dict, Any
from datetime import date, datetime
from pydantic import BaseModel, Field, EmailStr, HttpUrl, field_serializer
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

# ---------------- Sub-models ----------------
class Photo(BaseModel):
    url: HttpUrl
    caption: Optional[str] = None
    is_primary: bool = False

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

class Occupation(BaseModel):
    employment_type: Optional[EmploymentType] = None
    organization: Optional[str] = None
    designation: Optional[str] = None
    annual_income_value: Optional[float] = None
    annual_income_currency: Currency = Currency.INR

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

# ---------------- Core candidate profile ----------------
class CandidateProfile(BaseModel):
    id: Optional[str] = Field(default=None, alias="_id")  # Mongo-friendly
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Core identity
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

    # Photos (S3/public URLs)
    photos: List[Photo] = Field(default_factory=list)

    # Sections
    contact: Optional[ContactInfo] = None
    education: Optional[Education] = None
    occupation: Optional[Occupation] = None
    family: Optional[FamilyDetails] = None
    physical: Optional[PhysicalAttributes] = None
    lifestyle: Optional[Lifestyle] = None
    horoscope: Optional[Horoscope] = None
    languages: Optional[Languages] = None

    # Preferences (optional)
    partner_preferences: Optional[PartnerPreferences] = None

    # Misc
    custom_fields: Dict[str, Any] = Field(default_factory=dict)
    is_active: bool = True
    is_verified: bool = False

    @field_serializer("created_at", "updated_at")
    def _ser_dt(self, v: datetime, _info):
        return v.isoformat()

    class Config:
        populate_by_name = True
        json_schema_extra = {
            "example": {
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
                    {"url": "https://s3.ap-south-1.amazonaws.com/bucket/ananya1.jpg", "is_primary": True},
                    {"url": "https://s3.../ananya2.jpg", "caption": "Candid"}
                ],
                "contact": {
                    "email": "ananya@example.com",
                    "phone_country_code": "+91",
                    "phone_number": "9876543210",
                    "address": {"city": "Patna", "state": "Bihar", "country": "India", "pincode": "800001"}
                },
                "education": {"level": "masters", "degree": "MCA", "institute": "XYZ University", "graduation_year": 2020},
                "occupation": {"employment_type": "private", "organization": "ABC Tech", "designation": "SDE-2", "annual_income_value": 18.0, "annual_income_currency": "INR"},
                "family": {
                    "father_name": "Rajeev Kumar",
                    "father_occupation": "Business",
                    "mother_name": "Seema Devi",
                    "mother_occupation": "Homemaker",
                    "siblings": [{"relation": "Brother", "name": "Aman", "occupation": "Student", "is_married": False}],
                    "family_type": "Nuclear",
                    "family_values": "Moderate",
                    "native_place": "Muzaffarpur"
                },
                "physical": {"height_cm": 163, "weight_kg": 56, "body_type": "slim", "complexion": "wheatish"},
                "lifestyle": {"diet": "vegetarian", "drinking": "no", "smoking": "no"},
                "horoscope": {"manglik": "no", "gotra": "Kashyap"},
                "languages": {"known": {"Hindi": "native", "English": "fluent"}},
                "partner_preferences": {
                    "min_age": 25, "max_age": 32, "religion": ["hindu"], "caste": ["Kayastha"], "preferred_locations": ["Bihar", "Delhi NCR"]
                }
            }
        }
