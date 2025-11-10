# routes/biodata.py
import uuid
import logging
from datetime import datetime, date
from typing import List, Optional, Dict, Any
from enum import Enum
from bson import ObjectId
from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    Request,
    Response,
    UploadFile,
    BackgroundTasks,
    Body
)
from fastapi.responses import JSONResponse
from pymongo import MongoClient, DESCENDING
import boto3
from botocore.exceptions import ClientError

from database.db import db
from models.biodata import (
    CandidateProfile, 
    Photo, 
    ContactInfo, 
    Education, 
    Occupation,
    FamilyDetails,
    PhysicalAttributes,
    Lifestyle,
    Horoscope,
    Languages,
    PartnerPreferences,
    Gender,
    MaritalStatus,
    Religion,
    CasteCategory,
    # New enhanced models
    DetailedReligiousInfo,
    DetailedAstrology,
    DetailedFamilyBackground,
    TraditionalPreferences,
    MarriagePlanning,
    VerificationDocuments,
    ExtendedFamilyMember,
    BiodataType,
    Varna,
    ReligiousSect,
    Dosha,
    FamilyType,
    FamilyValues,
    EconomicStatus,
    PhotoCategory,
    RegionalTradition
)
from models.user import User
from routes.user import get_current_user
from routes.config import AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_REGION
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

biodata_router = APIRouter()

# Use the same S3 bucket as other routes
AWS_BUCKET_NAME = "projectdevops-blogs-new"
s3_client = boto3.client(
    "s3",
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    region_name=AWS_REGION,
)

BIODATA_COLLECTION = "biodata_profiles"

# ------------------------- Helper Functions -------------------------

def _serialize_for_mongodb(data: Dict[str, Any]) -> Dict[str, Any]:
    """Convert Pydantic model data to MongoDB-compatible format"""
    from pydantic import HttpUrl
    
    def convert_value(value):
        if isinstance(value, Enum):
            return value.value  # Convert enum to its string value
        elif isinstance(value, HttpUrl):
            return str(value)  # Convert HttpUrl to string
        elif isinstance(value, date):
            return value.isoformat()  # Convert date to ISO string
        elif isinstance(value, datetime):
            return value  # Keep datetime as-is (MongoDB supports it)
        elif isinstance(value, dict):
            return {k: convert_value(v) for k, v in value.items()}
        elif isinstance(value, list):
            return [convert_value(item) for item in value]
        else:
            return value
    
    return {k: convert_value(v) for k, v in data.items()}

def _normalize_biodata(doc: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize biodata document for response"""
    if "_id" in doc:
        doc["_id"] = str(doc["_id"])
    
    # Convert date strings back to date objects for proper serialization
    if "dob" in doc and isinstance(doc["dob"], str):
        try:
            doc["dob"] = datetime.fromisoformat(doc["dob"]).date()
        except:
            pass
    
    # Convert datetime objects to ISO strings for JSON response
    for key in ["created_at", "updated_at", "verified_at", "last_activity"]:
        if key in doc and isinstance(doc[key], datetime):
            doc[key] = doc[key].isoformat()
    
    return doc

def _upload_to_s3(file: UploadFile, folder: str = "biodata") -> str:
    """Upload file to S3 and return URL"""
    try:
        # Reset file pointer to beginning
        file.file.seek(0)
        
        file_extension = (file.filename or "image").split(".")[-1].lower()
        unique_filename = f"{folder}/{uuid.uuid4()}.{file_extension}"
        
        # Read file content
        file_content = file.file.read()
        
        # Reset file pointer again for potential reuse
        file.file.seek(0)
        
        # Upload to S3
        s3_client.put_object(
            Bucket=AWS_BUCKET_NAME,
            Key=unique_filename,
            Body=file_content,
            ContentType=file.content_type or "image/jpeg",
            ACL='public-read'
        )
        
        return f"https://{AWS_BUCKET_NAME}.s3.{AWS_REGION}.amazonaws.com/{unique_filename}"
    except Exception as e:
        logger.error(f"S3 upload failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Image upload failed: {str(e)}")

def _delete_from_s3(image_url: str) -> bool:
    """Delete file from S3"""
    try:
        # Extract key from URL
        if AWS_BUCKET_NAME in image_url:
            key = image_url.split(f"{AWS_BUCKET_NAME}.s3.{AWS_REGION}.amazonaws.com/")[1]
            s3_client.delete_object(Bucket=AWS_BUCKET_NAME, Key=key)
            return True
    except Exception as e:
        logger.warning(f"S3 delete failed: {str(e)}")
    return False

# ------------------------- PDF Service Class -------------------------

class BiodataPDFService:
    """Service for extracting complete biodata data for PDF generation"""
    
    def __init__(self, db_client: MongoClient, db_name: str = "testdb"):
        self.db_client = db_client
        self.db_name = db_name
        self.collection = db_client[db_name][BIODATA_COLLECTION]
    
    def get_complete_biodata_for_pdf(self, profile_id: str) -> Optional[Dict[str, Any]]:
        """
        Extract complete biodata data optimized for PDF generation
        Returns all data with S3 URLs and properly formatted content
        """
        try:
            if not ObjectId.is_valid(profile_id):
                logger.error(f"Invalid ObjectId format: {profile_id}")
                return None
                
            profile = self.collection.find_one({"_id": ObjectId(profile_id)})
            if not profile:
                logger.error(f"Profile not found: {profile_id}")
                return None
            
            # Transform data for PDF generation
            pdf_data = self._transform_for_pdf(profile)
            logger.info(f"Successfully generated PDF data for profile: {profile_id}")
            
            return pdf_data
            
        except Exception as e:
            logger.error(f"Error extracting PDF data for profile {profile_id}: {str(e)}")
            logger.error(f"Exception type: {type(e).__name__}")
            logger.error(f"Full traceback: {e.__class__.__module__}.{e.__class__.__name__}: {str(e)}")
            return None
    
    def get_user_biodata_for_pdf(self, username: str) -> Optional[Dict[str, Any]]:
        """Get user's biodata for PDF generation"""
        try:
            profile = self.collection.find_one({"user_id": username})
            if not profile:
                return None
            
            return self._transform_for_pdf(profile)
            
        except Exception as e:
            logger.error(f"Error extracting PDF data for user {username}: {str(e)}")
            return None
    
    def _safe_title(self, value: Any) -> str:
        """Safely convert a value to title case, handling None values"""
        return (value or "").title() if value is not None else ""
    
    def _safe_replace_title(self, value: Any, old: str, new: str) -> str:
        """Safely replace and title case a value, handling None values"""
        return (value or "").replace(old, new).title() if value is not None else ""
    
    def _transform_for_pdf(self, profile: Dict[str, Any]) -> Dict[str, Any]:
        """Transform MongoDB document to PDF-ready format"""
        try:
            logger.info(f"Starting PDF transform for profile with keys: {list(profile.keys())}")
            
            # Clean and organize data for PDF
            pdf_data = {
                # Basic Information
                "profile_id": str(profile.get("_id", "")),
                "created_at": self._format_datetime(profile.get("created_at")),
                "updated_at": self._format_datetime(profile.get("updated_at")),
                
                # Personal Details
                "personal": {
                    "full_name": f"{profile.get('first_name', '')} {profile.get('last_name', '')}".strip(),
                    "first_name": profile.get("first_name", ""),
                    "last_name": profile.get("last_name", ""),
                    "gender": self._safe_title(profile.get("gender")),
                    "date_of_birth": self._format_date(profile.get("dob")),
                    "age": self._calculate_age(profile.get("dob")),
                    "religion": self._safe_title(profile.get("religion")),
                    "caste": profile.get("caste", ""),
                    "caste_category": profile.get("caste_category", ""),
                    "gotra": profile.get("gotra", ""),
                    "mother_tongue": profile.get("mother_tongue", ""),
                    "marital_status": self._safe_replace_title(profile.get("marital_status"), "_", " "),
                    "about_me": profile.get("about_me", ""),
                    "profile_owner_relation": profile.get("profile_owner_relation", ""),
                    "biodata_type": self._safe_title(profile.get("biodata_type"))
                },
            
                # Photos with S3 URLs
                "photos": self._extract_photos(profile.get("photos", [])),
                
                # Contact Information
                "contact": self._extract_contact(profile.get("contact", {})),
                
                # Education
                "education": self._extract_education(profile.get("education", {})),
                
                # Occupation
                "occupation": self._extract_occupation(profile.get("occupation", {})),
                
                # Family Details
                "family": self._extract_family(profile.get("family", {})),
                
                # Physical Attributes
                "physical": self._extract_physical(profile.get("physical", {})),
                
                # Lifestyle
                "lifestyle": self._extract_lifestyle(profile.get("lifestyle", {})),
                
                # Horoscope
                "horoscope": self._extract_horoscope(profile.get("horoscope", {})),
                
                # Languages
                "languages": self._extract_languages(profile.get("languages", {})),
                
                # Partner Preferences
                "partner_preferences": self._extract_partner_preferences(profile.get("partner_preferences", {})),
                
                # Advanced Religious Information (for detailed profiles)
                "religious_details": self._extract_religious_details(profile.get("detailed_religious_info", {})),
                
                # Advanced Astrology (for detailed profiles)
                "astrology_details": self._extract_astrology_details(profile.get("detailed_astrology", {})),
                
                # Extended Family (for detailed profiles)
                "extended_family": self._extract_extended_family(profile.get("detailed_family_background", {})),
                
                # Traditional Preferences
                "traditional_preferences": self._extract_traditional_preferences(profile.get("traditional_preferences", {})),
                
                # Marriage Planning
                "marriage_planning": self._extract_marriage_planning(profile.get("marriage_planning", {})),
                
                # Metadata
                "metadata": {
                    "profile_completeness": profile.get("profile_completeness_score", 0),
                    "profile_views": profile.get("profile_views", 0),
                    "is_verified": profile.get("is_verified", False),
                    "verification_status": profile.get("verification_status", ""),
                    "last_activity": self._format_datetime(profile.get("last_activity"))
                }
            }
            
            logger.info(f"Successfully transformed PDF data with {len(pdf_data)} sections")
            return pdf_data
            
        except Exception as e:
            logger.error(f"Error in _transform_for_pdf: {str(e)}")
            logger.error(f"Profile keys available: {list(profile.keys()) if profile else 'None'}")
            import traceback
            logger.error(f"Full traceback: {traceback.format_exc()}")
            return None
    
    def _extract_photos(self, photos: List[Dict]) -> Dict[str, Any]:
        """Extract photo information with S3 URLs"""
        photo_data = {
            "primary_photo": "",
            "all_photos": [],
            "photo_count": len(photos)
        }
        
        for photo in photos:
            photo_info = {
                "url": photo.get("url", ""),
                "caption": photo.get("caption", ""),
                "is_primary": photo.get("is_primary", False),
                "category": photo.get("category", ""),
                "uploaded_at": self._format_datetime(photo.get("uploaded_at"))
            }
            photo_data["all_photos"].append(photo_info)
            
            if photo.get("is_primary"):
                photo_data["primary_photo"] = photo.get("url", "")
        
        # If no primary photo, use first photo
        if not photo_data["primary_photo"] and photos:
            photo_data["primary_photo"] = photos[0].get("url", "")
        
        return photo_data
    
    def _extract_contact(self, contact: Dict) -> Dict[str, Any]:
        """Extract contact information"""
        if not contact:
            return {}
            
        address = contact.get("address", {})
        # Handle case where address might be None
        if address is None:
            address = {}
            
        return {
            "email": contact.get("email", ""),
            "phone": f"{contact.get('phone_country_code', '')}{contact.get('phone_number', '')}".strip(),
            "alt_phone": contact.get("alt_phone_number", ""),
            "whatsapp": contact.get("whatsapp_number", ""),
            "address": {
                "full_address": f"{address.get('address_line1', '')} {address.get('address_line2', '')}".strip(),
                "city": address.get("city", ""),
                "district": address.get("district", ""),
                "state": address.get("state", ""),
                "country": address.get("country", ""),
                "pincode": address.get("pincode", "")
            }
        }
    
    def _extract_education(self, education: Dict) -> Dict[str, Any]:
        """Extract education information"""
        if not education:
            return {}
            
        return {
            "level": self._safe_title(education.get("level")),
            "degree": education.get("degree", ""),
            "institute": education.get("institute", ""),
            "graduation_year": education.get("graduation_year", ""),
            "specialization": education.get("specialization", ""),
            "grade": education.get("grade", "")
        }
    
    def _extract_occupation(self, occupation: Dict) -> Dict[str, Any]:
        """Extract occupation information"""
        if not occupation:
            return {}
            
        annual_income = occupation.get("annual_income_value", 0)
        currency = occupation.get("annual_income_currency", "INR")
        
        return {
            "employment_type": self._safe_title(occupation.get("employment_type")),
            "organization": occupation.get("organization", ""),
            "designation": occupation.get("designation", ""),
            "annual_income": f"{annual_income} {currency}" if annual_income else "",
            "work_location": occupation.get("work_location", ""),
            "experience_years": occupation.get("experience_years", "")
        }
    
    def _extract_family(self, family: Dict) -> Dict[str, Any]:
        """Extract family information"""
        if not family:
            return {}
            
        siblings_info = []
        for sibling in family.get("siblings", []):
            siblings_info.append({
                "relation": sibling.get("relation", ""),
                "name": sibling.get("name", ""),
                "occupation": sibling.get("occupation", ""),
                "is_married": sibling.get("is_married", False)
            })
        
        return {
            "father_name": family.get("father_name", ""),
            "father_occupation": family.get("father_occupation", ""),
            "mother_name": family.get("mother_name", ""),
            "mother_occupation": family.get("mother_occupation", ""),
            "siblings": siblings_info,
            "siblings_count": len(siblings_info),
            "family_type": family.get("family_type", ""),
            "family_values": family.get("family_values", ""),
            "native_place": family.get("native_place", "")
        }
    
    def _extract_physical(self, physical: Dict) -> Dict[str, Any]:
        """Extract physical attributes"""
        if not physical:
            return {}
            
        height_cm = physical.get("height_cm", 0)
        height_feet = ""
        if height_cm:
            feet = int(height_cm // 30.48)
            inches = int((height_cm % 30.48) / 2.54)
            height_feet = f"{feet}'{inches}\""
        
        return {
            "height_cm": height_cm,
            "height_feet": height_feet,
            "weight_kg": physical.get("weight_kg", ""),
            "body_type": (physical.get("body_type") or "").title(),
            "complexion": (physical.get("complexion") or "").title(),
            "blood_group": physical.get("blood_group", "")
        }
    
    def _extract_lifestyle(self, lifestyle: Dict) -> Dict[str, Any]:
        """Extract lifestyle information"""
        if not lifestyle:
            return {}
            
        return {
            "diet": self._safe_replace_title(lifestyle.get("diet"), "_", " "),
            "drinking": self._safe_title(lifestyle.get("drinking")),
            "smoking": self._safe_title(lifestyle.get("smoking"))
        }
    
    def _extract_horoscope(self, horoscope: Dict) -> Dict[str, Any]:
        """Extract horoscope information"""
        if not horoscope:
            return {}
            
        return {
            "birth_time": horoscope.get("time_of_birth", ""),
            "birth_place": horoscope.get("place_of_birth", ""),
            "manglik": self._safe_title(horoscope.get("manglik")),
            "gotra": horoscope.get("gotra", ""),
            "rashi": self._safe_title(horoscope.get("rashi")),
            "nakshatra": self._safe_title(horoscope.get("nakshatra")),
            "kundli_url": horoscope.get("kundli_url", "")
        }
    
    def _extract_languages(self, languages: Dict) -> Dict[str, Any]:
        """Extract languages information"""
        return {
            "known": languages.get("known", {}),
            "learning": languages.get("learning", []),
            "interested": languages.get("interested", [])
        }
    
    def _extract_partner_preferences(self, preferences: Dict) -> Dict[str, Any]:
        """Extract partner preferences"""
        if not preferences:
            return {}
            
        return {
            "age_range": f"{preferences.get('min_age', '')}-{preferences.get('max_age', '')} years",
            "height_range": f"{preferences.get('min_height_cm', '')}-{preferences.get('max_height_cm', '')} cm",
            "marital_status": ", ".join(preferences.get("marital_status", [])),
            "religion": ", ".join(preferences.get("religion", [])),
            "caste": ", ".join(preferences.get("caste", [])),
            "education": ", ".join(preferences.get("education_levels", [])),
            "occupation": ", ".join(preferences.get("occupations", [])),
            "locations": ", ".join(preferences.get("preferred_locations", [])),
            "diet": ", ".join(preferences.get("diet", []))
        }
    
    def _extract_religious_details(self, religious_info: Dict) -> Dict[str, Any]:
        """Extract detailed religious information"""
        if not religious_info:
            return {}
            
        return {
            "varna": self._safe_title(religious_info.get("varna")),
            "sub_caste": religious_info.get("sub_caste", ""),
            "religious_sect": self._safe_title(religious_info.get("religious_sect")),
            "temple_association": religious_info.get("temple_association", ""),
            "spiritual_practices": ", ".join(religious_info.get("spiritual_practices", [])),
            "festivals_observed": ", ".join(religious_info.get("festivals_observed", [])),
            "daily_prayers": religious_info.get("daily_prayers", False),
            "vegetarian_since": religious_info.get("vegetarian_since", "")
        }
    
    def _extract_astrology_details(self, astrology: Dict) -> Dict[str, Any]:
        """Extract detailed astrology information"""
        if not astrology:
            return {}
            
        return {
            "birth_time": astrology.get("birth_time", ""),
            "birth_coordinates": astrology.get("birth_place_coordinates", ""),
            "rashi_detailed": astrology.get("rashi_detailed", ""),
            "nakshatra_detailed": astrology.get("nakshatra_detailed", ""),
            "lagna": astrology.get("lagna", ""),
            "doshas": ", ".join(astrology.get("doshas", [])),
            "guna_milan_score": astrology.get("guna_milan_score", ""),
            "auspicious_time": astrology.get("auspicious_time_preference", "")
        }
    
    def _extract_extended_family(self, family_bg: Dict) -> Dict[str, Any]:
        """Extract extended family information"""
        if not family_bg:
            return {}
            
        extended_family = []
        for member in family_bg.get("extended_family", []):
            extended_family.append({
                "relation": member.get("relation", ""),
                "name": member.get("name", ""),
                "occupation": member.get("occupation", ""),
                "location": member.get("location", "")
            })
        
        return {
            "extended_family": extended_family,
            "family_traditions": family_bg.get("family_traditions", ""),
            "family_status": family_bg.get("family_status", "")
        }
    
    def _extract_traditional_preferences(self, traditional: Dict) -> Dict[str, Any]:
        """Extract traditional preferences"""
        if not traditional:
            return {}
            
        return {
            "wedding_type": traditional.get("wedding_type", ""),
            "ceremony_preferences": ", ".join(traditional.get("ceremony_preferences", [])),
            "cultural_values": traditional.get("cultural_values", ""),
            "lifestyle_expectations": traditional.get("lifestyle_expectations", "")
        }
    
    def _extract_marriage_planning(self, marriage: Dict) -> Dict[str, Any]:
        """Extract marriage planning information"""
        if not marriage:
            return {}
            
        return {
            "preferred_timeline": marriage.get("preferred_timeline", ""),
            "budget_range": marriage.get("budget_range", ""),
            "venue_preferences": ", ".join(marriage.get("venue_preferences", [])),
            "guest_count_estimate": marriage.get("guest_count_estimate", "")
        }
    
    def _format_datetime(self, dt) -> str:
        """Format datetime for PDF display"""
        if not dt:
            return ""
        if isinstance(dt, str):
            try:
                dt = datetime.fromisoformat(dt.replace('Z', '+00:00'))
            except:
                return dt
        if isinstance(dt, datetime):
            return dt.strftime("%B %d, %Y at %I:%M %p")
        return str(dt)
    
    def _format_date(self, date_val) -> str:
        """Format date for PDF display"""
        if not date_val:
            return ""
        if isinstance(date_val, str):
            try:
                date_obj = datetime.fromisoformat(date_val).date()
                return date_obj.strftime("%B %d, %Y")
            except:
                return date_val
        if isinstance(date_val, date):
            return date_val.strftime("%B %d, %Y")
        return str(date_val)
    
    def _calculate_age(self, dob) -> int:
        """Calculate age from date of birth"""
        if not dob:
            return 0
        try:
            if isinstance(dob, str):
                birth_date = datetime.fromisoformat(dob).date()
            else:
                birth_date = dob
            
            today = date.today()
            age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
            return age
        except:
            return 0
    
    async def validate_pdf_readiness(self, user_id: str) -> Dict[str, Any]:
        """
        Validate if biodata has sufficient data for PDF generation.
        Returns validation report with missing fields and recommendations.
        """
        profile = self.collection.find_one({"user_id": user_id})
        if not profile:
            return None
        
        validation_result = {
            "user_id": user_id,
            "is_pdf_ready": True,
            "readiness_score": 0,
            "missing_sections": [],
            "missing_fields": [],
            "recommendations": [],
            "photo_status": {},
            "critical_missing": [],
            "optional_missing": []
        }
        
        # Define critical fields for PDF generation
        critical_sections = {
            "basic_info": ["first_name", "last_name", "gender", "date_of_birth"],
            "contact_info": ["email", "phone"],
            "family_info": ["father_name", "mother_name"],
            "education_career": ["highest_education"],
            "physical_appearance": ["height", "complexion"]
        }
        
        optional_sections = {
            "lifestyle_preferences": ["diet", "smoking", "drinking"],
            "partner_preferences": ["min_age", "max_age", "preferred_education"],
            "additional_info": ["hobbies", "interests"]
        }
        
        total_score = 0
        max_score = 0
        
        # Check critical sections
        for section, required_fields in critical_sections.items():
            section_data = profile.get(section, {})
            max_score += len(required_fields) * 2  # Critical fields worth 2 points each
            
            if not section_data:
                validation_result["missing_sections"].append(section)
                validation_result["critical_missing"].extend([f"{section}.{field}" for field in required_fields])
            else:
                for field in required_fields:
                    if field in section_data and section_data[field]:
                        total_score += 2
                    else:
                        validation_result["critical_missing"].append(f"{section}.{field}")
        
        # Check optional sections
        for section, optional_fields in optional_sections.items():
            section_data = profile.get(section, {})
            max_score += len(optional_fields)  # Optional fields worth 1 point each
            
            if section_data:
                for field in optional_fields:
                    if field in section_data and section_data[field]:
                        total_score += 1
                    else:
                        validation_result["optional_missing"].append(f"{section}.{field}")
            else:
                validation_result["optional_missing"].extend([f"{section}.{field}" for field in optional_fields])
        
        # Check photos
        photos = profile.get("photos", [])
        validation_result["photo_status"] = {
            "total_photos": len(photos),
            "photos_with_s3": sum(1 for photo in photos if photo.get("s3_url")),
            "has_main_photo": any(photo.get("is_main", False) for photo in photos),
            "photo_quality_check": "passed" if len(photos) >= 1 else "failed"
        }
        
        if len(photos) == 0:
            validation_result["critical_missing"].append("photos.main_photo")
            max_score += 4  # Photos worth 4 points
        else:
            total_score += min(len(photos), 4)  # Max 4 points for photos
            max_score += 4
        
        # Calculate readiness score
        validation_result["readiness_score"] = round((total_score / max_score) * 100, 2) if max_score > 0 else 0
        
        # Determine if PDF ready (minimum 70% completion)
        validation_result["is_pdf_ready"] = (
            validation_result["readiness_score"] >= 70 and 
            len(validation_result["critical_missing"]) == 0 and
            validation_result["photo_status"]["total_photos"] > 0
        )
        
        # Generate recommendations
        if validation_result["critical_missing"]:
            validation_result["recommendations"].append(
                f"Critical fields missing: {', '.join(validation_result['critical_missing'][:5])}"
            )
        
        if validation_result["photo_status"]["total_photos"] == 0:
            validation_result["recommendations"].append("Add at least one profile photo")
        
        if validation_result["readiness_score"] < 70:
            validation_result["recommendations"].append(
                f"Complete more profile sections to improve readiness score (current: {validation_result['readiness_score']}%)"
            )
        
        if not validation_result["photo_status"]["has_main_photo"] and photos:
            validation_result["recommendations"].append("Set a main profile photo")
        
        return validation_result

# ------------------------- Auth Helpers -------------------------

def get_current_user_or_admin(current_user: User = Depends(get_current_user)):
    """Allow users to manage their own profiles or admins to manage any"""
    return current_user

def get_current_admin_user(current_user: User = Depends(get_current_user)):
    """Admin-only access"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user

# ------------------------- Create Biodata Profile -------------------------

@biodata_router.post("/biodata", response_model=CandidateProfile, tags=["Biodata"])
async def create_biodata_profile(
    profile: CandidateProfile,
    current_user: User = Depends(get_current_user),
    db_client: MongoClient = Depends(db.get_client),
):
    """Create a new biodata profile"""
    # Convert Pydantic model to dict and serialize for MongoDB
    profile_dict = profile.model_dump(by_alias=True, exclude={"id"})
    
    # Add user metadata
    profile_dict["user_id"] = current_user.username  # Link to user
    profile_dict["created_by"] = current_user.username
    profile_dict["created_at"] = datetime.utcnow()
    profile_dict["updated_at"] = datetime.utcnow()
    
    # 🔧 FIX: Serialize enums and dates for MongoDB compatibility
    profile_dict = _serialize_for_mongodb(profile_dict)
    
    try:
        result = db_client[db.db_name][BIODATA_COLLECTION].insert_one(profile_dict)
        profile_dict["_id"] = str(result.inserted_id)
        
        return _normalize_biodata(profile_dict)
    except Exception as e:
        logger.error(f"Failed to create biodata profile: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to create profile")

# ------------------------- Upload Photos -------------------------

@biodata_router.post("/biodata/{profile_id}/photos", tags=["Biodata"])
async def upload_biodata_photo(
    profile_id: str,
    file: UploadFile = File(...),
    caption: Optional[str] = Form(None),
    is_primary: bool = Form(False),
    current_user: User = Depends(get_current_user),
    db_client: MongoClient = Depends(db.get_client),
):
    """Upload a photo to biodata profile"""
    try:
        if not ObjectId.is_valid(profile_id):
            raise HTTPException(status_code=404, detail="Profile not found")
        
        # Check if profile exists and user has permission
        collection = db_client["testdb"][BIODATA_COLLECTION]
        profile = collection.find_one({"_id": ObjectId(profile_id)})
        if not profile:
            raise HTTPException(status_code=404, detail="Profile not found")
        
        # Check permission
        if profile.get("user_id") != current_user.username and current_user.role != "admin":
            raise HTTPException(status_code=403, detail="Permission denied")
        
        # Validate file type
        if not file.content_type or not file.content_type.startswith("image/"):
            raise HTTPException(status_code=400, detail="Only image files are allowed")
        
        # Upload to S3
        image_url = _upload_to_s3(file, f"biodata/{profile_id}")
        
        # Create photo object
        photo_data = {
            "url": image_url,
            "caption": caption,
            "is_primary": is_primary,
            "uploaded_at": datetime.utcnow()
        }
        
        # If this is primary, unset other primary photos
        if is_primary:
            collection.update_one(
                {"_id": ObjectId(profile_id)},
                {"$set": {"photos.$[].is_primary": False}}
            )
        
        # Add photo to profile
        collection.update_one(
            {"_id": ObjectId(profile_id)},
            {
                "$push": {"photos": photo_data},
                "$set": {"updated_at": datetime.utcnow()}
            }
        )
        
        # Convert datetime to string for JSON response
        photo_response = photo_data.copy()
        photo_response["uploaded_at"] = photo_data["uploaded_at"].isoformat()
        
        return JSONResponse(content={
            "message": "Photo uploaded successfully",
            "photo": photo_response
        }, status_code=201)
        
    except Exception as e:
        logger.error(f"Failed to upload photo: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to upload photo: {str(e)}")

# ------------------------- Get Biodata Profiles -------------------------

@biodata_router.get("/biodata", response_model=List[CandidateProfile], tags=["Biodata"])
async def get_biodata_profiles(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    gender: Optional[Gender] = None,
    religion: Optional[Religion] = None,
    marital_status: Optional[MaritalStatus] = None,
    min_age: Optional[int] = Query(None, ge=18, le=80),
    max_age: Optional[int] = Query(None, ge=18, le=80),
    caste_category: Optional[CasteCategory] = None,
    city: Optional[str] = None,
    state: Optional[str] = None,
    is_active: bool = Query(True),
    current_user: User = Depends(get_current_user),
    db_client: MongoClient = Depends(db.get_client),
):
    """Get biodata profiles with filtering options"""
    query = {"is_active": is_active}
    
    # Build filter query
    if gender:
        query["gender"] = gender
    if religion:
        query["religion"] = religion
    if marital_status:
        query["marital_status"] = marital_status
    if caste_category:
        query["caste_category"] = caste_category
    if city:
        query["contact.address.city"] = {"$regex": city, "$options": "i"}
    if state:
        query["contact.address.state"] = {"$regex": state, "$options": "i"}
    
    # Age filtering (calculate from DOB)
    if min_age or max_age:
        today = date.today()
        age_query = {}
        if max_age:
            min_dob = today.replace(year=today.year - max_age - 1)
            age_query["$gte"] = min_dob.isoformat()
        if min_age:
            max_dob = today.replace(year=today.year - min_age)
            age_query["$lte"] = max_dob.isoformat()
        if age_query:
            query["dob"] = age_query
    
    try:
        profiles = list(
            db_client[db.db_name][BIODATA_COLLECTION]
            .find(query)
            .sort("created_at", DESCENDING)
            .skip(skip)
            .limit(limit)
        )
        
        return [_normalize_biodata(profile) for profile in profiles]
    except Exception as e:
        logger.error(f"Failed to fetch profiles: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch profiles")

# ------------------------- Get My Biodata Profile (SPECIFIC ROUTE FIRST) -------------------------

@biodata_router.get("/biodata/my/profile", response_model=CandidateProfile, tags=["Biodata"])
async def get_my_biodata_profile(
    current_user: User = Depends(get_current_user),
    db_client: MongoClient = Depends(db.get_client),
):
    """Get current user's biodata profile"""
    profile = db_client[db.db_name][BIODATA_COLLECTION].find_one({"user_id": current_user.username})
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    
    return _normalize_biodata(profile)

# ------------------------- Search Profiles (SPECIFIC ROUTE BEFORE GENERIC) -------------------------

@biodata_router.get("/biodata/search", response_model=List[CandidateProfile], tags=["Biodata"])
async def search_biodata_profiles(
    q: str = Query(..., min_length=2, description="Search query"),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db_client: MongoClient = Depends(db.get_client),
):
    """Search biodata profiles by name, occupation, education, etc."""
    # Create text search query
    query = {
        "is_active": True,
        "$or": [
            {"first_name": {"$regex": q, "$options": "i"}},
            {"last_name": {"$regex": q, "$options": "i"}},
            {"occupation.organization": {"$regex": q, "$options": "i"}},
            {"occupation.designation": {"$regex": q, "$options": "i"}},
            {"education.degree": {"$regex": q, "$options": "i"}},
            {"education.institute": {"$regex": q, "$options": "i"}},
            {"contact.address.city": {"$regex": q, "$options": "i"}},
            {"contact.address.state": {"$regex": q, "$options": "i"}},
            {"caste": {"$regex": q, "$options": "i"}},
            {"mother_tongue": {"$regex": q, "$options": "i"}}
        ]
    }
    
    try:
        profiles = list(
            db_client[db.db_name][BIODATA_COLLECTION]
            .find(query)
            .sort("created_at", DESCENDING)
            .skip(skip)
            .limit(limit)
        )
        
        return [_normalize_biodata(profile) for profile in profiles]
    except Exception as e:
        logger.error(f"Search failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Search failed")


# ====== PDF DATA EXTRACTION ENDPOINTS (BEFORE GENERIC ROUTES) ======

@biodata_router.get("/biodata/{profile_id}/pdf-data", 
           tags=["PDF Generation"],
           response_model=Dict)
async def get_biodata_pdf_data(
    profile_id: str,
    current_user: User = Depends(get_current_user),
    db_client: MongoClient = Depends(db.get_client)
):
    """
    Get complete biodata data formatted for PDF generation.
    Includes all sections with S3 URLs for images.
    """
    try:
        if not ObjectId.is_valid(profile_id):
            raise HTTPException(status_code=404, detail="Invalid profile ID")
        
        collection = db_client["testdb"][BIODATA_COLLECTION]
        
        # Authorization check - admin can access all, users can access their own
        profile = collection.find_one({"_id": ObjectId(profile_id)})
        if not profile:
            raise HTTPException(status_code=404, detail="Biodata not found")
        
        # Check permissions
        if current_user.role not in ["admin"] and profile.get("user_id") != current_user.username:
            raise HTTPException(status_code=403, detail="Access denied")
        
        pdf_service = BiodataPDFService(db_client)
        pdf_data = pdf_service.get_complete_biodata_for_pdf(profile_id)
        
        if not pdf_data:
            raise HTTPException(status_code=404, detail="Failed to generate PDF data")
        
        return JSONResponse(content=pdf_data)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get PDF data: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get PDF data: {str(e)}")


@biodata_router.get("/biodata/{profile_id}/pdf-summary", 
           tags=["PDF Generation"],
           response_model=Dict)
async def get_biodata_pdf_summary(
    profile_id: str,
    current_user: User = Depends(get_current_user),
    db_client: MongoClient = Depends(db.get_client)
):
    """
    Get biodata summary optimized for PDF header/footer sections.
    """
    try:
        if not ObjectId.is_valid(profile_id):
            raise HTTPException(status_code=404, detail="Invalid profile ID")
        
        collection = db_client["testdb"][BIODATA_COLLECTION]
        
        # Authorization check
        profile = collection.find_one({"_id": ObjectId(profile_id)})
        if not profile:
            raise HTTPException(status_code=404, detail="Biodata not found")
        
        # Check permissions
        if current_user.role not in ["admin"] and profile.get("user_id") != current_user.username:
            raise HTTPException(status_code=403, detail="Access denied")
        
        pdf_service = BiodataPDFService(db_client)
        summary_data = pdf_service.get_complete_biodata_for_pdf(profile_id)
        
        if not summary_data:
            raise HTTPException(status_code=404, detail="Failed to generate PDF summary")
        
        # Extract summary fields for PDF header/footer
        summary = {
            "profile_id": profile_id,
            "full_name": f"{summary_data.get('first_name', '')} {summary_data.get('last_name', '')}".strip(),
            "age": summary_data.get('age', 0),
            "gender": summary_data.get('gender', ''),
            "religion": summary_data.get('religion', ''),
            "caste": summary_data.get('caste', ''),
            "education": summary_data.get('highest_education', ''),
            "occupation": summary_data.get('occupation', ''),
            "location": summary_data.get('current_location', ''),
            "main_photo_url": next((photo.get('s3_url') for photo in summary_data.get('photos', []) if photo.get('is_main')), '')
        }
        
        return JSONResponse(content=summary)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get PDF summary: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get PDF summary: {str(e)}")


@biodata_router.get("/biodata/{profile_id}/storage-status", 
           tags=["Data Management"],
           response_model=Dict)
async def check_biodata_storage_status(
    profile_id: str,
    current_user: User = Depends(get_current_user),
    db_client: MongoClient = Depends(db.get_client)
):
    """
    Check completeness of biodata storage in MongoDB.
    Validates all sections and data integrity for PDF generation.
    """
    try:
        if not ObjectId.is_valid(profile_id):
            raise HTTPException(status_code=404, detail="Invalid profile ID")
        
        collection = db_client["testdb"][BIODATA_COLLECTION]
        
        # Authorization check
        profile = collection.find_one({"_id": ObjectId(profile_id)})
        if not profile:
            raise HTTPException(status_code=404, detail="Biodata not found")
        
        # Check permissions
        if current_user.role not in ["admin"] and profile.get("user_id") != current_user.username:
            raise HTTPException(status_code=403, detail="Access denied")
        
        # Check data completeness
        storage_status = {
            "profile_id": profile_id,
            "profile_exists": True,
            "sections": {},
            "s3_urls": {},
            "data_completeness": 0
        }
        
        # Check each major section based on actual stored data
        sections_to_check = [
            "contact", "education", "occupation", "family", 
            "physical", "lifestyle", "horoscope", "partner_preferences"
        ]
        
        total_sections = len(sections_to_check)
        complete_sections = 0
        
        for section in sections_to_check:
            section_data = profile.get(section, {})
            is_complete = bool(section_data and len(section_data) > 0)
            storage_status["sections"][section] = {
                "exists": is_complete,
                "field_count": len(section_data) if isinstance(section_data, dict) else 1 if section_data else 0
            }
            if is_complete:
                complete_sections += 1
        
        # Check S3 URLs
        photos = profile.get("photos", [])
        storage_status["s3_urls"] = {
            "photo_count": len(photos),
            "photos_with_s3": sum(1 for photo in photos if photo.get("url")),
            "photos": [
                {
                    "photo_id": i,
                    "has_s3_url": bool(photo.get("url")),
                    "s3_url": photo.get("url", "")
                }
                for i, photo in enumerate(photos)
            ]
        }
        
        # Calculate completeness percentage
        storage_status["data_completeness"] = round((complete_sections / total_sections) * 100, 2)
        
        return JSONResponse(content=storage_status)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to check storage status: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to check storage status: {str(e)}")


@biodata_router.post("/biodata/{profile_id}/validate-pdf-readiness", 
            tags=["PDF Generation"],
            response_model=Dict)
async def validate_pdf_readiness(
    profile_id: str,
    current_user: User = Depends(get_current_user),
    db_client: MongoClient = Depends(db.get_client)
):
    """
    Validate if biodata has sufficient data for PDF generation.
    Returns validation report with missing fields and recommendations.
    """
    try:
        if not ObjectId.is_valid(profile_id):
            raise HTTPException(status_code=404, detail="Invalid profile ID")
        
        collection = db_client["testdb"][BIODATA_COLLECTION]
        
        # Authorization check
        profile = collection.find_one({"_id": ObjectId(profile_id)})
        if not profile:
            raise HTTPException(status_code=404, detail="Biodata not found")
        
        # Check permissions
        if current_user.role not in ["admin"] and profile.get("user_id") != current_user.username:
            raise HTTPException(status_code=403, detail="Access denied")
        
        pdf_service = BiodataPDFService(db_client)
        profile_data = pdf_service.get_complete_biodata_for_pdf(profile_id)
        
        if not profile_data:
            raise HTTPException(status_code=404, detail="Failed to process biodata for PDF")
        
        # Validate PDF readiness
        validation_result = {
            "profile_id": profile_id,
            "is_pdf_ready": True,
            "readiness_score": 0,
            "missing_sections": [],
            "recommendations": [],
            "photo_status": {},
            "critical_missing": []
        }
        
        # Check critical fields
        critical_fields = ["first_name", "last_name", "gender", "dob"]
        missing_critical = [field for field in critical_fields if not profile_data.get(field)]
        validation_result["critical_missing"] = missing_critical
        
        # Check photos
        photos = profile_data.get("photos", [])
        validation_result["photo_status"] = {
            "total_photos": len(photos),
            "photos_with_s3": sum(1 for photo in photos if photo.get("s3_url")),
            "has_main_photo": any(photo.get("is_main", False) for photo in photos)
        }
        
        # Calculate readiness score
        total_fields = len(critical_fields) + 1  # +1 for photos
        complete_fields = len(critical_fields) - len(missing_critical)
        if photos:
            complete_fields += 1
        
        validation_result["readiness_score"] = round((complete_fields / total_fields) * 100, 2)
        validation_result["is_pdf_ready"] = len(missing_critical) == 0 and len(photos) > 0
        
        # Generate recommendations
        if missing_critical:
            validation_result["recommendations"].append(f"Missing critical fields: {', '.join(missing_critical)}")
        if not photos:
            validation_result["recommendations"].append("Add at least one profile photo")
        
        return JSONResponse(content=validation_result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to validate PDF readiness: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to validate PDF readiness: {str(e)}")


# ------------------------- Get Single Biodata Profile (GENERIC ROUTE LAST) -------------------------

@biodata_router.get("/biodata/{profile_id}", response_model=CandidateProfile, tags=["Biodata"])
async def get_biodata_profile(
    profile_id: str,
    current_user: User = Depends(get_current_user),
    db_client: MongoClient = Depends(db.get_client),
):
    """Get a specific biodata profile"""
    if not ObjectId.is_valid(profile_id):
        raise HTTPException(status_code=404, detail="Profile not found")
    
    profile = db_client[db.db_name][BIODATA_COLLECTION].find_one({"_id": ObjectId(profile_id)})
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    
    return _normalize_biodata(profile)

# ------------------------- Update Biodata Profile -------------------------

@biodata_router.put("/biodata/{profile_id}", response_model=CandidateProfile, tags=["Biodata"])
async def update_biodata_profile(
    profile_id: str,
    updated_profile: CandidateProfile,
    current_user: User = Depends(get_current_user),
    db_client: MongoClient = Depends(db.get_client),
):
    """Update biodata profile"""
    if not ObjectId.is_valid(profile_id):
        raise HTTPException(status_code=404, detail="Profile not found")
    
    existing_profile = db_client[db.db_name][BIODATA_COLLECTION].find_one({"_id": ObjectId(profile_id)})
    if not existing_profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    
    # Check permission
    if existing_profile.get("user_id") != current_user.username and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Permission denied")
    
    # Prepare update data
    update_data = updated_profile.model_dump(
        by_alias=True,
        exclude={"id", "created_at", "user_id", "created_by"}
    )
    update_data["updated_at"] = datetime.utcnow()
    
    # 🔧 FIX: Serialize enums and dates for MongoDB compatibility
    update_data = _serialize_for_mongodb(update_data)
    
    try:
        db_client[db.db_name][BIODATA_COLLECTION].update_one(
            {"_id": ObjectId(profile_id)},
            {"$set": update_data}
        )
        
        updated = db_client[db.db_name][BIODATA_COLLECTION].find_one({"_id": ObjectId(profile_id)})
        return _normalize_biodata(updated)
    except Exception as e:
        logger.error(f"Failed to update profile: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to update profile")

# ------------------------- Update Profile Sections -------------------------

@biodata_router.patch("/biodata/{profile_id}/contact", tags=["Biodata"])
async def update_contact_info(
    profile_id: str,
    contact_info: ContactInfo,
    current_user: User = Depends(get_current_user),
    db_client: MongoClient = Depends(db.get_client),
):
    """Update contact information section"""
    if not ObjectId.is_valid(profile_id):
        raise HTTPException(status_code=404, detail="Profile not found")
    
    profile = db_client[db.db_name][BIODATA_COLLECTION].find_one({"_id": ObjectId(profile_id)})
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    
    # Check permission
    if profile.get("user_id") != current_user.username and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Permission denied")
    
    db_client[db.db_name][BIODATA_COLLECTION].update_one(
        {"_id": ObjectId(profile_id)},
        {
            "$set": {
                "contact": _serialize_for_mongodb(contact_info.model_dump()),
                "updated_at": datetime.utcnow()
            }
        }
    )
    
    return JSONResponse(content={"message": "Contact information updated successfully"})

@biodata_router.patch("/biodata/{profile_id}/education", tags=["Biodata"])
async def update_education_info(
    profile_id: str,
    education: Education,
    current_user: User = Depends(get_current_user),
    db_client: MongoClient = Depends(db.get_client),
):
    """Update education information section"""
    if not ObjectId.is_valid(profile_id):
        raise HTTPException(status_code=404, detail="Profile not found")
    
    profile = db_client[db.db_name][BIODATA_COLLECTION].find_one({"_id": ObjectId(profile_id)})
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    
    # Check permission
    if profile.get("user_id") != current_user.username and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Permission denied")
    
    db_client[db.db_name][BIODATA_COLLECTION].update_one(
        {"_id": ObjectId(profile_id)},
        {
            "$set": {
                "education": _serialize_for_mongodb(education.model_dump()),
                "updated_at": datetime.utcnow()
            }
        }
    )
    
    return JSONResponse(content={"message": "Education information updated successfully"})

@biodata_router.patch("/biodata/{profile_id}/occupation", tags=["Biodata"])
async def update_occupation_info(
    profile_id: str,
    occupation: Occupation,
    current_user: User = Depends(get_current_user),
    db_client: MongoClient = Depends(db.get_client),
):
    """Update occupation information section"""
    if not ObjectId.is_valid(profile_id):
        raise HTTPException(status_code=404, detail="Profile not found")
    
    profile = db_client[db.db_name][BIODATA_COLLECTION].find_one({"_id": ObjectId(profile_id)})
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    
    # Check permission
    if profile.get("user_id") != current_user.username and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Permission denied")
    
    db_client[db.db_name][BIODATA_COLLECTION].update_one(
        {"_id": ObjectId(profile_id)},
        {
            "$set": {
                "occupation": _serialize_for_mongodb(occupation.model_dump()),
                "updated_at": datetime.utcnow()
            }
        }
    )
    
    return JSONResponse(content={"message": "Occupation information updated successfully"})

@biodata_router.patch("/biodata/{profile_id}/family", tags=["Biodata"])
async def update_family_details(
    profile_id: str,
    family: FamilyDetails,
    current_user: User = Depends(get_current_user),
    db_client: MongoClient = Depends(db.get_client),
):
    """Update family details section"""
    if not ObjectId.is_valid(profile_id):
        raise HTTPException(status_code=404, detail="Profile not found")
    
    profile = db_client[db.db_name][BIODATA_COLLECTION].find_one({"_id": ObjectId(profile_id)})
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    
    # Check permission
    if profile.get("user_id") != current_user.username and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Permission denied")
    
    db_client[db.db_name][BIODATA_COLLECTION].update_one(
        {"_id": ObjectId(profile_id)},
        {
            "$set": {
                "family": _serialize_for_mongodb(family.model_dump()),
                "updated_at": datetime.utcnow()
            }
        }
    )
    
    return JSONResponse(content={"message": "Family details updated successfully"})

@biodata_router.patch("/biodata/{profile_id}/partner-preferences", tags=["Biodata"])
async def update_partner_preferences(
    profile_id: str,
    preferences: PartnerPreferences,
    current_user: User = Depends(get_current_user),
    db_client: MongoClient = Depends(db.get_client),
):
    """Update partner preferences section"""
    if not ObjectId.is_valid(profile_id):
        raise HTTPException(status_code=404, detail="Profile not found")
    
    profile = db_client[db.db_name][BIODATA_COLLECTION].find_one({"_id": ObjectId(profile_id)})
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    
    # Check permission
    if profile.get("user_id") != current_user.username and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Permission denied")
    
    db_client[db.db_name][BIODATA_COLLECTION].update_one(
        {"_id": ObjectId(profile_id)},
        {
            "$set": {
                "partner_preferences": _serialize_for_mongodb(preferences.model_dump()),
                "updated_at": datetime.utcnow()
            }
        }
    )
    
    return JSONResponse(content={"message": "Partner preferences updated successfully"})

@biodata_router.patch("/biodata/{profile_id}/physical", tags=["Biodata"])
async def update_physical_attributes(
    profile_id: str,
    physical: PhysicalAttributes,
    current_user: User = Depends(get_current_user),
    db_client: MongoClient = Depends(db.get_client),
):
    """Update physical attributes section"""
    if not ObjectId.is_valid(profile_id):
        raise HTTPException(status_code=404, detail="Profile not found")
    
    profile = db_client[db.db_name][BIODATA_COLLECTION].find_one({"_id": ObjectId(profile_id)})
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    
    # Check permission
    if profile.get("user_id") != current_user.username and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Permission denied")
    
    db_client[db.db_name][BIODATA_COLLECTION].update_one(
        {"_id": ObjectId(profile_id)},
        {
            "$set": {
                "physical": _serialize_for_mongodb(physical.model_dump()),
                "updated_at": datetime.utcnow()
            }
        }
    )
    
    return JSONResponse(content={"message": "Physical attributes updated successfully"})

@biodata_router.patch("/biodata/{profile_id}/lifestyle", tags=["Biodata"])
async def update_lifestyle(
    profile_id: str,
    lifestyle: Lifestyle,
    current_user: User = Depends(get_current_user),
    db_client: MongoClient = Depends(db.get_client),
):
    """Update lifestyle section"""
    if not ObjectId.is_valid(profile_id):
        raise HTTPException(status_code=404, detail="Profile not found")
    
    profile = db_client[db.db_name][BIODATA_COLLECTION].find_one({"_id": ObjectId(profile_id)})
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    
    # Check permission
    if profile.get("user_id") != current_user.username and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Permission denied")
    
    db_client[db.db_name][BIODATA_COLLECTION].update_one(
        {"_id": ObjectId(profile_id)},
        {
            "$set": {
                "lifestyle": _serialize_for_mongodb(lifestyle.model_dump()),
                "updated_at": datetime.utcnow()
            }
        }
    )
    
    return JSONResponse(content={"message": "Lifestyle updated successfully"})

@biodata_router.patch("/biodata/{profile_id}/horoscope", tags=["Biodata"])
async def update_horoscope(
    profile_id: str,
    horoscope: Horoscope,
    current_user: User = Depends(get_current_user),
    db_client: MongoClient = Depends(db.get_client),
):
    """Update horoscope section"""
    if not ObjectId.is_valid(profile_id):
        raise HTTPException(status_code=404, detail="Profile not found")
    
    profile = db_client[db.db_name][BIODATA_COLLECTION].find_one({"_id": ObjectId(profile_id)})
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    
    # Check permission
    if profile.get("user_id") != current_user.username and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Permission denied")
    
    # Update horoscope information
    horoscope_data = _serialize_for_mongodb(horoscope.model_dump())
    
    db_client[db.db_name][BIODATA_COLLECTION].update_one(
        {"_id": ObjectId(profile_id)},
        {
            "$set": {
                "horoscope": horoscope_data,
                "updated_at": datetime.utcnow()
            }
        }
    )
    
    return JSONResponse(content={"message": "Horoscope updated successfully"})

@biodata_router.patch("/biodata/{profile_id}/languages", tags=["Biodata"])
async def update_languages(
    profile_id: str,
    languages: Languages,
    current_user: User = Depends(get_current_user),
    db_client: MongoClient = Depends(db.get_client),
):
    """Update languages section"""
    try:
        if not ObjectId.is_valid(profile_id):
            raise HTTPException(status_code=404, detail="Profile not found")
        
        collection = db_client["testdb"][BIODATA_COLLECTION]
        profile = collection.find_one({"_id": ObjectId(profile_id)})
        if not profile:
            raise HTTPException(status_code=404, detail="Profile not found")
        
        # Check permission
        if profile.get("user_id") != current_user.username and current_user.role != "admin":
            raise HTTPException(status_code=403, detail="Permission denied")
        
        collection.update_one(
            {"_id": ObjectId(profile_id)},
            {
                "$set": {
                    "languages": _serialize_for_mongodb(languages.model_dump()),
                    "updated_at": datetime.utcnow()
                }
            }
        )
        
        return JSONResponse(content={"message": "Languages updated successfully"})
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update languages: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to update languages: {str(e)}")

# ------------------------- Enhanced Photo Management -------------------------

@biodata_router.get("/biodata/{profile_id}/photos", tags=["Biodata"])
async def get_biodata_photos(
    profile_id: str,
    current_user: User = Depends(get_current_user),
    db_client: MongoClient = Depends(db.get_client),
):
    """Get all photos for a biodata profile"""
    if not ObjectId.is_valid(profile_id):
        raise HTTPException(status_code=404, detail="Profile not found")
    
    profile = db_client[db.db_name][BIODATA_COLLECTION].find_one(
        {"_id": ObjectId(profile_id)}, 
        {"photos": 1}
    )
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    
    return {"photos": profile.get("photos", [])}

@biodata_router.patch("/biodata/{profile_id}/photos/reorder", tags=["Biodata"])
async def reorder_biodata_photos(
    profile_id: str,
    request: Dict[str, List[int]] = Body(...),
    current_user: User = Depends(get_current_user),
    db_client: MongoClient = Depends(db.get_client),
):
    """Reorder photos in the profile"""
    try:
        if not ObjectId.is_valid(profile_id):
            raise HTTPException(status_code=404, detail="Profile not found")
        
        photo_order = request.get("new_order", [])
        
        collection = db_client["testdb"][BIODATA_COLLECTION]
        profile = collection.find_one({"_id": ObjectId(profile_id)})
        if not profile:
            raise HTTPException(status_code=404, detail="Profile not found")
        
        # Check permission
        if profile.get("user_id") != current_user.username and current_user.role != "admin":
            raise HTTPException(status_code=403, detail="Permission denied")
        
        photos = profile.get("photos", [])
        
        # Validate photo_order
        if len(photo_order) != len(photos):
            raise HTTPException(status_code=400, detail="Photo order length must match current photos count")
        
        if set(photo_order) != set(range(len(photos))):
            raise HTTPException(status_code=400, detail="Invalid photo order indices")
        
        # Reorder photos
        reordered_photos = [photos[i] for i in photo_order]
        
        collection.update_one(
            {"_id": ObjectId(profile_id)},
            {
                "$set": {
                    "photos": reordered_photos,
                    "updated_at": datetime.utcnow()
                }
            }
        )
        
        return {"message": "Photos reordered successfully"}
    
    except Exception as e:
        logger.error(f"Failed to reorder photos: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to reorder photos: {str(e)}")

@biodata_router.patch("/biodata/{profile_id}/photos/{photo_index}", tags=["Biodata"])
async def update_biodata_photo(
    profile_id: str,
    photo_index: int,
    caption: Optional[str] = Form(None),
    is_primary: Optional[bool] = Form(None),
    current_user: User = Depends(get_current_user),
    db_client: MongoClient = Depends(db.get_client),
):
    """Update photo metadata (caption, primary status)"""
    if not ObjectId.is_valid(profile_id):
        raise HTTPException(status_code=404, detail="Profile not found")
    
    profile = db_client[db.db_name][BIODATA_COLLECTION].find_one({"_id": ObjectId(profile_id)})
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    
    # Check permission
    if profile.get("user_id") != current_user.username and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Permission denied")
    
    photos = profile.get("photos", [])
    if photo_index >= len(photos) or photo_index < 0:
        raise HTTPException(status_code=404, detail="Photo not found")
    
    update_fields = {}
    if caption is not None:
        update_fields[f"photos.{photo_index}.caption"] = caption
    
    if is_primary is not None:
        if is_primary:
            # First, unset all other primary photos
            db_client[db.db_name][BIODATA_COLLECTION].update_one(
                {"_id": ObjectId(profile_id)},
                {"$set": {"photos.$[].is_primary": False}}
            )
        update_fields[f"photos.{photo_index}.is_primary"] = is_primary
    
    if update_fields:
        update_fields["updated_at"] = datetime.utcnow()
        db_client[db.db_name][BIODATA_COLLECTION].update_one(
            {"_id": ObjectId(profile_id)},
            {"$set": update_fields}
        )
    
    return JSONResponse(content={"message": "Photo updated successfully"})

@biodata_router.post("/biodata/{profile_id}/photos/replace/{photo_index}", tags=["Biodata"])
async def replace_biodata_photo(
    profile_id: str,
    photo_index: int,
    file: UploadFile = File(...),
    caption: Optional[str] = Form(None),
    is_primary: Optional[bool] = Form(None),
    current_user: User = Depends(get_current_user),
    db_client: MongoClient = Depends(db.get_client),
):
    """Replace an existing photo with a new one"""
    try:
        if not ObjectId.is_valid(profile_id):
            raise HTTPException(status_code=404, detail="Profile not found")
        
        collection = db_client["testdb"][BIODATA_COLLECTION]
        profile = collection.find_one({"_id": ObjectId(profile_id)})
        if not profile:
            raise HTTPException(status_code=404, detail="Profile not found")
        
        # Check permission
        if profile.get("user_id") != current_user.username and current_user.role != "admin":
            raise HTTPException(status_code=403, detail="Permission denied")
        
        photos = profile.get("photos", [])
        if photo_index >= len(photos) or photo_index < 0:
            raise HTTPException(status_code=404, detail="Photo not found")
        
        # Validate file type
        if not file.content_type or not file.content_type.startswith("image/"):
            raise HTTPException(status_code=400, detail="Only image files are allowed")
        
        # Delete old photo from S3
        old_photo_url = photos[photo_index].get("url")
        if old_photo_url:
            _delete_from_s3(old_photo_url)
        
        # Upload new photo to S3
        new_image_url = _upload_to_s3(file, f"biodata/{profile_id}")
        
        # Update photo data
        new_photo_data = {
            "url": new_image_url,
            "caption": caption if caption is not None else photos[photo_index].get("caption"),
            "is_primary": is_primary if is_primary is not None else photos[photo_index].get("is_primary", False),
            "uploaded_at": datetime.utcnow()
        }
        
        # If this is primary, unset other primary photos
        if new_photo_data["is_primary"]:
            collection.update_one(
                {"_id": ObjectId(profile_id)},
                {"$set": {"photos.$[].is_primary": False}}
            )
        
        # Replace photo in array
        collection.update_one(
            {"_id": ObjectId(profile_id)},
            {
                "$set": {
                    f"photos.{photo_index}": new_photo_data,
                    "updated_at": datetime.utcnow()
                }
            }
        )
        
        # Convert datetime to string for JSON response
        photo_response = new_photo_data.copy()
        photo_response["uploaded_at"] = new_photo_data["uploaded_at"].isoformat()
        
        return JSONResponse(content={
            "message": "Photo replaced successfully",
            "photo": photo_response
        }, status_code=200)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to replace photo: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to replace photo: {str(e)}")

# ------------------------- Get Individual Sections -------------------------

@biodata_router.get("/biodata/{profile_id}/contact", response_model=ContactInfo, tags=["Biodata"])
async def get_contact_info(
    profile_id: str,
    current_user: User = Depends(get_current_user),
    db_client: MongoClient = Depends(db.get_client),
):
    """Get contact information section"""
    if not ObjectId.is_valid(profile_id):
        raise HTTPException(status_code=404, detail="Profile not found")
    
    profile = db_client[db.db_name][BIODATA_COLLECTION].find_one(
        {"_id": ObjectId(profile_id)}, 
        {"contact": 1}
    )
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    
    contact_info = profile.get("contact")
    if not contact_info:
        raise HTTPException(status_code=404, detail="Contact information not found")
    
    return contact_info

@biodata_router.get("/biodata/{profile_id}/education", response_model=Education, tags=["Biodata"])
async def get_education_info(
    profile_id: str,
    current_user: User = Depends(get_current_user),
    db_client: MongoClient = Depends(db.get_client),
):
    """Get education information section"""
    if not ObjectId.is_valid(profile_id):
        raise HTTPException(status_code=404, detail="Profile not found")
    
    profile = db_client[db.db_name][BIODATA_COLLECTION].find_one(
        {"_id": ObjectId(profile_id)}, 
        {"education": 1}
    )
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    
    education_info = profile.get("education")
    if not education_info:
        raise HTTPException(status_code=404, detail="Education information not found")
    
    return education_info

@biodata_router.get("/biodata/{profile_id}/occupation", response_model=Occupation, tags=["Biodata"])
async def get_occupation_info(
    profile_id: str,
    current_user: User = Depends(get_current_user),
    db_client: MongoClient = Depends(db.get_client),
):
    """Get occupation information section"""
    if not ObjectId.is_valid(profile_id):
        raise HTTPException(status_code=404, detail="Profile not found")
    
    profile = db_client[db.db_name][BIODATA_COLLECTION].find_one(
        {"_id": ObjectId(profile_id)}, 
        {"occupation": 1}
    )
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    
    occupation_info = profile.get("occupation")
    if not occupation_info:
        raise HTTPException(status_code=404, detail="Occupation information not found")
    
    return occupation_info

@biodata_router.get("/biodata/{profile_id}/family", response_model=FamilyDetails, tags=["Biodata"])
async def get_family_details(
    profile_id: str,
    current_user: User = Depends(get_current_user),
    db_client: MongoClient = Depends(db.get_client),
):
    """Get family details section"""
    if not ObjectId.is_valid(profile_id):
        raise HTTPException(status_code=404, detail="Profile not found")
    
    profile = db_client[db.db_name][BIODATA_COLLECTION].find_one(
        {"_id": ObjectId(profile_id)}, 
        {"family": 1}
    )
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    
    family_info = profile.get("family")
    if not family_info:
        raise HTTPException(status_code=404, detail="Family details not found")
    
    return family_info

@biodata_router.get("/biodata/{profile_id}/physical", response_model=PhysicalAttributes, tags=["Biodata"])
async def get_physical_attributes(
    profile_id: str,
    current_user: User = Depends(get_current_user),
    db_client: MongoClient = Depends(db.get_client),
):
    """Get physical attributes section"""
    if not ObjectId.is_valid(profile_id):
        raise HTTPException(status_code=404, detail="Profile not found")
    
    profile = db_client[db.db_name][BIODATA_COLLECTION].find_one(
        {"_id": ObjectId(profile_id)}, 
        {"physical": 1}
    )
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    
    physical_info = profile.get("physical")
    if not physical_info:
        raise HTTPException(status_code=404, detail="Physical attributes not found")
    
    return physical_info

@biodata_router.get("/biodata/{profile_id}/lifestyle", response_model=Lifestyle, tags=["Biodata"])
async def get_lifestyle(
    profile_id: str,
    current_user: User = Depends(get_current_user),
    db_client: MongoClient = Depends(db.get_client),
):
    """Get lifestyle section"""
    if not ObjectId.is_valid(profile_id):
        raise HTTPException(status_code=404, detail="Profile not found")
    
    profile = db_client[db.db_name][BIODATA_COLLECTION].find_one(
        {"_id": ObjectId(profile_id)}, 
        {"lifestyle": 1}
    )
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    
    lifestyle_info = profile.get("lifestyle")
    if not lifestyle_info:
        raise HTTPException(status_code=404, detail="Lifestyle information not found")
    
    return lifestyle_info

@biodata_router.get("/biodata/{profile_id}/horoscope", response_model=Horoscope, tags=["Biodata"])
async def get_horoscope(
    profile_id: str,
    current_user: User = Depends(get_current_user),
    db_client: MongoClient = Depends(db.get_client),
):
    """Get horoscope section"""
    if not ObjectId.is_valid(profile_id):
        raise HTTPException(status_code=404, detail="Profile not found")
    
    profile = db_client[db.db_name][BIODATA_COLLECTION].find_one(
        {"_id": ObjectId(profile_id)}, 
        {"horoscope": 1}
    )
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    
    horoscope_info = profile.get("horoscope")
    if not horoscope_info:
        raise HTTPException(status_code=404, detail="Horoscope information not found")
    
    # Convert date string back to date object if needed
    if "date_of_birth" in horoscope_info and isinstance(horoscope_info["date_of_birth"], str):
        try:
            horoscope_info["date_of_birth"] = datetime.fromisoformat(horoscope_info["date_of_birth"]).date()
        except:
            pass
    
    return horoscope_info

@biodata_router.get("/biodata/{profile_id}/languages", response_model=Languages, tags=["Biodata"])
async def get_languages(
    profile_id: str,
    current_user: User = Depends(get_current_user),
    db_client: MongoClient = Depends(db.get_client),
):
    """Get languages section"""
    try:
        if not ObjectId.is_valid(profile_id):
            raise HTTPException(status_code=404, detail="Profile not found")
        
        collection = db_client["testdb"][BIODATA_COLLECTION]
        profile = collection.find_one(
            {"_id": ObjectId(profile_id)}, 
            {"languages": 1}
        )
        if not profile:
            raise HTTPException(status_code=404, detail="Profile not found")
        
        languages_info = profile.get("languages")
        if not languages_info:
            # Return empty languages structure instead of 404
            return Languages(known={})
        
        return languages_info
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get languages: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get languages: {str(e)}")

@biodata_router.get("/biodata/{profile_id}/partner-preferences", response_model=PartnerPreferences, tags=["Biodata"])
async def get_partner_preferences(
    profile_id: str,
    current_user: User = Depends(get_current_user),
    db_client: MongoClient = Depends(db.get_client),
):
    """Get partner preferences section"""
    if not ObjectId.is_valid(profile_id):
        raise HTTPException(status_code=404, detail="Profile not found")
    
    profile = db_client[db.db_name][BIODATA_COLLECTION].find_one(
        {"_id": ObjectId(profile_id)}, 
        {"partner_preferences": 1}
    )
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    
    preferences_info = profile.get("partner_preferences")
    if not preferences_info:
        raise HTTPException(status_code=404, detail="Partner preferences not found")
    
    return preferences_info

# ------------------------- Delete Individual Sections -------------------------

@biodata_router.delete("/biodata/{profile_id}/contact", tags=["Biodata"])
async def delete_contact_info(
    profile_id: str,
    current_user: User = Depends(get_current_user),
    db_client: MongoClient = Depends(db.get_client),
):
    """Delete contact information section"""
    try:
        if not ObjectId.is_valid(profile_id):
            raise HTTPException(status_code=404, detail="Profile not found")
        
        collection = db_client["testdb"][BIODATA_COLLECTION]
        profile = collection.find_one({"_id": ObjectId(profile_id)})
        if not profile:
            raise HTTPException(status_code=404, detail="Profile not found")
        
        # Check permission
        if profile.get("user_id") != current_user.username and current_user.role != "admin":
            raise HTTPException(status_code=403, detail="Permission denied")
        
        collection.update_one(
            {"_id": ObjectId(profile_id)},
            {
                "$unset": {"contact": ""},
                "$set": {"updated_at": datetime.utcnow()}
            }
        )
        
        return Response(status_code=204)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete contact info: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to delete contact info: {str(e)}")

@biodata_router.delete("/biodata/{profile_id}/education", tags=["Biodata"])
async def delete_education_info(
    profile_id: str,
    current_user: User = Depends(get_current_user),
    db_client: MongoClient = Depends(db.get_client),
):
    """Delete education information section"""
    if not ObjectId.is_valid(profile_id):
        raise HTTPException(status_code=404, detail="Profile not found")
    
    profile = db_client[db.db_name][BIODATA_COLLECTION].find_one({"_id": ObjectId(profile_id)})
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    
    # Check permission
    if profile.get("user_id") != current_user.username and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Permission denied")
    
    db_client[db.db_name][BIODATA_COLLECTION].update_one(
        {"_id": ObjectId(profile_id)},
        {
            "$unset": {"education": ""},
            "$set": {"updated_at": datetime.utcnow()}
        }
    )
    
    return Response(status_code=204)

@biodata_router.delete("/biodata/{profile_id}/occupation", tags=["Biodata"])
async def delete_occupation_info(
    profile_id: str,
    current_user: User = Depends(get_current_user),
    db_client: MongoClient = Depends(db.get_client),
):
    """Delete occupation information section"""
    if not ObjectId.is_valid(profile_id):
        raise HTTPException(status_code=404, detail="Profile not found")
    
    profile = db_client[db.db_name][BIODATA_COLLECTION].find_one({"_id": ObjectId(profile_id)})
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    
    # Check permission
    if profile.get("user_id") != current_user.username and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Permission denied")
    
    db_client[db.db_name][BIODATA_COLLECTION].update_one(
        {"_id": ObjectId(profile_id)},
        {
            "$unset": {"occupation": ""},
            "$set": {"updated_at": datetime.utcnow()}
        }
    )
    
    return Response(status_code=204)

@biodata_router.delete("/biodata/{profile_id}/physical", tags=["Biodata"])
async def delete_physical_attributes(
    profile_id: str,
    current_user: User = Depends(get_current_user),
    db_client: MongoClient = Depends(db.get_client),
):
    """Delete physical attributes section"""
    if not ObjectId.is_valid(profile_id):
        raise HTTPException(status_code=404, detail="Profile not found")
    
    profile = db_client[db.db_name][BIODATA_COLLECTION].find_one({"_id": ObjectId(profile_id)})
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    
    # Check permission
    if profile.get("user_id") != current_user.username and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Permission denied")
    
    db_client[db.db_name][BIODATA_COLLECTION].update_one(
        {"_id": ObjectId(profile_id)},
        {
            "$unset": {"physical": ""},
            "$set": {"updated_at": datetime.utcnow()}
        }
    )
    
    return Response(status_code=204)

@biodata_router.delete("/biodata/{profile_id}/lifestyle", tags=["Biodata"])
async def delete_lifestyle(
    profile_id: str,
    current_user: User = Depends(get_current_user),
    db_client: MongoClient = Depends(db.get_client),
):
    """Delete lifestyle section"""
    if not ObjectId.is_valid(profile_id):
        raise HTTPException(status_code=404, detail="Profile not found")
    
    profile = db_client[db.db_name][BIODATA_COLLECTION].find_one({"_id": ObjectId(profile_id)})
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    
    # Check permission
    if profile.get("user_id") != current_user.username and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Permission denied")
    
    db_client[db.db_name][BIODATA_COLLECTION].update_one(
        {"_id": ObjectId(profile_id)},
        {
            "$unset": {"lifestyle": ""},
            "$set": {"updated_at": datetime.utcnow()}
        }
    )
    
    return Response(status_code=204)

@biodata_router.delete("/biodata/{profile_id}/horoscope", tags=["Biodata"])
async def delete_horoscope(
    profile_id: str,
    current_user: User = Depends(get_current_user),
    db_client: MongoClient = Depends(db.get_client),
):
    """Delete horoscope section"""
    if not ObjectId.is_valid(profile_id):
        raise HTTPException(status_code=404, detail="Profile not found")
    
    profile = db_client[db.db_name][BIODATA_COLLECTION].find_one({"_id": ObjectId(profile_id)})
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    
    # Check permission
    if profile.get("user_id") != current_user.username and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Permission denied")
    
    db_client[db.db_name][BIODATA_COLLECTION].update_one(
        {"_id": ObjectId(profile_id)},
        {
            "$unset": {"horoscope": ""},
            "$set": {"updated_at": datetime.utcnow()}
        }
    )
    
    return Response(status_code=204)

@biodata_router.delete("/biodata/{profile_id}/languages", tags=["Biodata"])
async def delete_languages(
    profile_id: str,
    current_user: User = Depends(get_current_user),
    db_client: MongoClient = Depends(db.get_client),
):
    """Delete languages section"""
    if not ObjectId.is_valid(profile_id):
        raise HTTPException(status_code=404, detail="Profile not found")
    
    profile = db_client[db.db_name][BIODATA_COLLECTION].find_one({"_id": ObjectId(profile_id)})
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    
    # Check permission
    if profile.get("user_id") != current_user.username and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Permission denied")
    
    db_client[db.db_name][BIODATA_COLLECTION].update_one(
        {"_id": ObjectId(profile_id)},
        {
            "$unset": {"languages": ""},
            "$set": {"updated_at": datetime.utcnow()}
        }
    )
    
    return Response(status_code=204)

@biodata_router.delete("/biodata/{profile_id}/partner-preferences", tags=["Biodata"])
async def delete_partner_preferences(
    profile_id: str,
    current_user: User = Depends(get_current_user),
    db_client: MongoClient = Depends(db.get_client),
):
    """Delete partner preferences section"""
    if not ObjectId.is_valid(profile_id):
        raise HTTPException(status_code=404, detail="Profile not found")
    
    profile = db_client[db.db_name][BIODATA_COLLECTION].find_one({"_id": ObjectId(profile_id)})
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    
    # Check permission
    if profile.get("user_id") != current_user.username and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Permission denied")
    
    db_client[db.db_name][BIODATA_COLLECTION].update_one(
        {"_id": ObjectId(profile_id)},
        {
            "$unset": {"partner_preferences": ""},
            "$set": {"updated_at": datetime.utcnow()}
        }
    )
    
    return Response(status_code=204)

# ------------------------- Delete Photo -------------------------

@biodata_router.delete("/biodata/{profile_id}/photos/{photo_index}", tags=["Biodata"])
async def delete_biodata_photo(
    profile_id: str,
    photo_index: int,
    current_user: User = Depends(get_current_user),
    db_client: MongoClient = Depends(db.get_client),
):
    """Delete a photo from biodata profile"""
    if not ObjectId.is_valid(profile_id):
        raise HTTPException(status_code=404, detail="Profile not found")
    
    profile = db_client[db.db_name][BIODATA_COLLECTION].find_one({"_id": ObjectId(profile_id)})
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    
    # Check permission
    if profile.get("user_id") != current_user.username and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Permission denied")
    
    photos = profile.get("photos", [])
    if photo_index >= len(photos) or photo_index < 0:
        raise HTTPException(status_code=404, detail="Photo not found")
    
    # Delete from S3
    photo_url = photos[photo_index].get("url")
    if photo_url:
        _delete_from_s3(photo_url)
    
    # Remove photo from array
    db_client[db.db_name][BIODATA_COLLECTION].update_one(
        {"_id": ObjectId(profile_id)},
        {
            "$unset": {f"photos.{photo_index}": 1},
            "$set": {"updated_at": datetime.utcnow()}
        }
    )
    
    # Remove null elements
    db_client[db.db_name][BIODATA_COLLECTION].update_one(
        {"_id": ObjectId(profile_id)},
        {"$pull": {"photos": None}}
    )
    
    return Response(status_code=204)

# ------------------------- Delete Biodata Profile -------------------------

@biodata_router.delete("/biodata/{profile_id}", tags=["Biodata"])
async def delete_biodata_profile(
    profile_id: str,
    current_user: User = Depends(get_current_user),
    db_client: MongoClient = Depends(db.get_client),
):
    """Delete biodata profile (soft delete by default)"""
    if not ObjectId.is_valid(profile_id):
        raise HTTPException(status_code=404, detail="Profile not found")
    
    profile = db_client[db.db_name][BIODATA_COLLECTION].find_one({"_id": ObjectId(profile_id)})
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    
    # Check permission
    if profile.get("user_id") != current_user.username and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Permission denied")
    
    # Soft delete (mark as inactive)
    db_client[db.db_name][BIODATA_COLLECTION].update_one(
        {"_id": ObjectId(profile_id)},
        {
            "$set": {
                "is_active": False,
                "deleted_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }
        }
    )
    
    return Response(status_code=204)

# ------------------------- Admin: Hard Delete Profile -------------------------

@biodata_router.delete("/biodata/{profile_id}/permanent", tags=["Biodata"])
async def permanently_delete_biodata_profile(
    profile_id: str,
    current_admin: User = Depends(get_current_admin_user),
    db_client: MongoClient = Depends(db.get_client),
):
    """Permanently delete biodata profile (admin only)"""
    if not ObjectId.is_valid(profile_id):
        raise HTTPException(status_code=404, detail="Profile not found")
    
    profile = db_client[db.db_name][BIODATA_COLLECTION].find_one({"_id": ObjectId(profile_id)})
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    
    # Delete all photos from S3
    photos = profile.get("photos", [])
    for photo in photos:
        if photo.get("url"):
            _delete_from_s3(photo["url"])
    
    # Delete from database
    db_client[db.db_name][BIODATA_COLLECTION].delete_one({"_id": ObjectId(profile_id)})
    
    return JSONResponse(content={"message": "Profile permanently deleted"})

# ------------------------- Statistics -------------------------

@biodata_router.get("/biodata/stats/overview", tags=["Biodata"])
async def get_biodata_stats(
    current_admin: User = Depends(get_current_admin_user),
    db_client: MongoClient = Depends(db.get_client),
):
    """Get biodata statistics (admin only)"""
    collection = db_client[db.db_name][BIODATA_COLLECTION]
    
    total_profiles = collection.count_documents({})
    active_profiles = collection.count_documents({"is_active": True})
    verified_profiles = collection.count_documents({"is_verified": True})
    
    # Gender distribution
    gender_stats = list(collection.aggregate([
        {"$match": {"is_active": True}},
        {"$group": {"_id": "$gender", "count": {"$sum": 1}}}
    ]))
    
    # Religion distribution
    religion_stats = list(collection.aggregate([
        {"$match": {"is_active": True}},
        {"$group": {"_id": "$religion", "count": {"$sum": 1}}}
    ]))
    
    # Marital status distribution
    marital_stats = list(collection.aggregate([
        {"$match": {"is_active": True}},
        {"$group": {"_id": "$marital_status", "count": {"$sum": 1}}}
    ]))
    
    return {
        "total_profiles": total_profiles,
        "active_profiles": active_profiles,
        "verified_profiles": verified_profiles,
        "gender_distribution": {stat["_id"]: stat["count"] for stat in gender_stats},
        "religion_distribution": {stat["_id"]: stat["count"] for stat in religion_stats},
        "marital_status_distribution": {stat["_id"]: stat["count"] for stat in marital_stats}
    }

# ------------------------- Verification -------------------------

@biodata_router.patch("/biodata/{profile_id}/verify", tags=["Biodata"])
async def verify_biodata_profile(
    profile_id: str,
    current_admin: User = Depends(get_current_admin_user),
    db_client: MongoClient = Depends(db.get_client),
):
    """Verify a biodata profile (admin only)"""
    if not ObjectId.is_valid(profile_id):
        raise HTTPException(status_code=404, detail="Profile not found")
    
    result = db_client[db.db_name][BIODATA_COLLECTION].update_one(
        {"_id": ObjectId(profile_id)},
        {
            "$set": {
                "is_verified": True,
                "verified_at": datetime.utcnow(),
                "verified_by": current_admin.username,
                "updated_at": datetime.utcnow()
            }
        }
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Profile not found")
    
    return JSONResponse(content={"message": "Profile verified successfully"})

@biodata_router.patch("/biodata/{profile_id}/unverify", tags=["Biodata"])
async def unverify_biodata_profile(
    profile_id: str,
    current_admin: User = Depends(get_current_admin_user),
    db_client: MongoClient = Depends(db.get_client),
):
    """Remove verification from a biodata profile (admin only)"""
    if not ObjectId.is_valid(profile_id):
        raise HTTPException(status_code=404, detail="Profile not found")
    
    result = db_client[db.db_name][BIODATA_COLLECTION].update_one(
        {"_id": ObjectId(profile_id)},
        {
            "$set": {
                "is_verified": False,
                "updated_at": datetime.utcnow()
            },
            "$unset": {
                "verified_at": "",
                "verified_by": ""
            }
        }
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Profile not found")
    
    return JSONResponse(content={"message": "Profile verification removed"})


# ============================================================================
# ENHANCED HINDU MATRIMONIAL FEATURES - DETAILED BIODATA CRUD OPERATIONS
# ============================================================================

# ==================== BIODATA TYPE MANAGEMENT ====================

@biodata_router.patch("/biodata/{profile_id}/upgrade-to-detailed", tags=["Enhanced Biodata"])
async def upgrade_to_detailed_biodata(
    profile_id: str,
    current_user: User = Depends(get_current_user),
    db_client: MongoClient = Depends(db.get_client),
):
    """Upgrade basic biodata to detailed Hindu matrimonial profile"""
    if not ObjectId.is_valid(profile_id):
        raise HTTPException(status_code=404, detail="Profile not found")
    
    # Check ownership
    profile = db_client[db.db_name][BIODATA_COLLECTION].find_one({"_id": ObjectId(profile_id)})
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    
    if profile.get("user_id") != current_user.username and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Upgrade to detailed
    result = db_client[db.db_name][BIODATA_COLLECTION].update_one(
        {"_id": ObjectId(profile_id)},
        {
            "$set": {
                "biodata_type": "detailed",
                "updated_at": datetime.utcnow(),
                "profile_completeness_score": 25.0  # Initial score for upgrade
            }
        }
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=400, detail="Failed to upgrade profile")
    
    return JSONResponse(content={"message": "Profile upgraded to detailed biodata successfully"})


# ==================== DETAILED RELIGIOUS INFO CRUD ====================

@biodata_router.patch("/biodata/{profile_id}/detailed-religious-info", tags=["Enhanced Biodata"])
async def update_detailed_religious_info(
    profile_id: str,
    religious_info: DetailedReligiousInfo,
    current_user: User = Depends(get_current_user),
    db_client: MongoClient = Depends(db.get_client),
):
    """Update detailed religious information (detailed biodata only)"""
    if not ObjectId.is_valid(profile_id):
        raise HTTPException(status_code=404, detail="Profile not found")
    
    # Check ownership and biodata type
    profile = db_client[db.db_name][BIODATA_COLLECTION].find_one({"_id": ObjectId(profile_id)})
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    
    if profile.get("user_id") != current_user.username and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Access denied")
    
    if profile.get("biodata_type") != "detailed":
        raise HTTPException(status_code=400, detail="This feature is only available for detailed biodata profiles")
    
    # Update religious information
    result = db_client[db.db_name][BIODATA_COLLECTION].update_one(
        {"_id": ObjectId(profile_id)},
        {
            "$set": {
                "detailed_religious_info": _serialize_for_mongodb(religious_info.model_dump()),
                "updated_at": datetime.utcnow()
            }
        }
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=400, detail="Failed to update religious information")
    
    return JSONResponse(content={"message": "Detailed religious information updated successfully"})


@biodata_router.get("/biodata/{profile_id}/detailed-religious-info", response_model=DetailedReligiousInfo, tags=["Enhanced Biodata"])
async def get_detailed_religious_info(
    profile_id: str,
    current_user: User = Depends(get_current_user),
    db_client: MongoClient = Depends(db.get_client),
):
    """Get detailed religious information"""
    if not ObjectId.is_valid(profile_id):
        raise HTTPException(status_code=404, detail="Profile not found")
    
    profile = db_client[db.db_name][BIODATA_COLLECTION].find_one({"_id": ObjectId(profile_id)})
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    
    # Check access permissions
    if profile.get("user_id") != current_user.username and current_user.role != "admin":
        if not profile.get("is_active", False):
            raise HTTPException(status_code=403, detail="Profile is not public")
    
    religious_info = profile.get("detailed_religious_info")
    if not religious_info:
        raise HTTPException(status_code=404, detail="Detailed religious information not found")
    
    return religious_info


# ==================== DETAILED ASTROLOGY CRUD ====================

@biodata_router.patch("/biodata/{profile_id}/detailed-astrology", tags=["Enhanced Biodata"])
async def update_detailed_astrology(
    profile_id: str,
    astrology_info: DetailedAstrology,
    current_user: User = Depends(get_current_user),
    db_client: MongoClient = Depends(db.get_client),
):
    """Update detailed astrological information"""
    if not ObjectId.is_valid(profile_id):
        raise HTTPException(status_code=404, detail="Profile not found")
    
    # Check ownership and biodata type
    profile = db_client[db.db_name][BIODATA_COLLECTION].find_one({"_id": ObjectId(profile_id)})
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    
    if profile.get("user_id") != current_user.username and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Access denied")
    
    if profile.get("biodata_type") != "detailed":
        raise HTTPException(status_code=400, detail="This feature is only available for detailed biodata profiles")
    
    # Update astrology information
    result = db_client[db.db_name][BIODATA_COLLECTION].update_one(
        {"_id": ObjectId(profile_id)},
        {
            "$set": {
                "detailed_astrology": _serialize_for_mongodb(astrology_info.model_dump()),
                "updated_at": datetime.utcnow()
            }
        }
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=400, detail="Failed to update astrology information")
    
    return JSONResponse(content={"message": "Detailed astrology information updated successfully"})


@biodata_router.get("/biodata/{profile_id}/detailed-astrology", response_model=DetailedAstrology, tags=["Enhanced Biodata"])
async def get_detailed_astrology(
    profile_id: str,
    current_user: User = Depends(get_current_user),
    db_client: MongoClient = Depends(db.get_client),
):
    """Get detailed astrological information"""
    if not ObjectId.is_valid(profile_id):
        raise HTTPException(status_code=404, detail="Profile not found")
    
    profile = db_client[db.db_name][BIODATA_COLLECTION].find_one({"_id": ObjectId(profile_id)})
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    
    # Check access permissions
    if profile.get("user_id") != current_user.username and current_user.role != "admin":
        if not profile.get("is_active", False):
            raise HTTPException(status_code=403, detail="Profile is not public")
    
    astrology_info = profile.get("detailed_astrology")
    if not astrology_info:
        raise HTTPException(status_code=404, detail="Detailed astrology information not found")
    
    return astrology_info


@biodata_router.post("/biodata/{profile_id}/upload-kundli", tags=["Enhanced Biodata"])
async def upload_kundli_pdf(
    profile_id: str,
    kundli_file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db_client: MongoClient = Depends(db.get_client),
):
    """Upload Kundli PDF file"""
    try:
        if not ObjectId.is_valid(profile_id):
            raise HTTPException(status_code=404, detail="Profile not found")
        
        # Check ownership
        collection = db_client["testdb"][BIODATA_COLLECTION]
        profile = collection.find_one({"_id": ObjectId(profile_id)})
        if not profile:
            raise HTTPException(status_code=404, detail="Profile not found")
        
        if profile.get("user_id") != current_user.username and current_user.role != "admin":
            raise HTTPException(status_code=403, detail="Access denied")
        
        # Validate file type
        if not kundli_file.filename or not kundli_file.filename.lower().endswith('.pdf'):
            raise HTTPException(status_code=400, detail="Only PDF files are allowed for Kundli")
        
        # Reset file pointer and read content
        kundli_file.file.seek(0)
        file_content = kundli_file.file.read()
        kundli_file.file.seek(0)
        
        # Upload to S3
        file_key = f"kundli/{current_user.username}_{profile_id}_{int(datetime.utcnow().timestamp())}.pdf"
        
        s3_client.put_object(
            Bucket=AWS_BUCKET_NAME,
            Key=file_key,
            Body=file_content,
            ContentType="application/pdf",
            ACL='public-read'
        )
        
        kundli_url = f"https://{AWS_BUCKET_NAME}.s3.{AWS_REGION}.amazonaws.com/{file_key}"
        
        # Update profile with kundli URL
        collection.update_one(
            {"_id": ObjectId(profile_id)},
            {
                "$set": {
                    "detailed_astrology.kundli_pdf_url": kundli_url,
                    "updated_at": datetime.utcnow()
                }
            }
        )
        
        return JSONResponse(content={
            "message": "Kundli PDF uploaded successfully",
            "kundli_url": kundli_url
        }, status_code=201)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to upload kundli: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to upload Kundli PDF: {str(e)}")


# ==================== DETAILED FAMILY BACKGROUND CRUD ====================

@biodata_router.patch("/biodata/{profile_id}/detailed-family-background", tags=["Enhanced Biodata"])
async def update_detailed_family_background(
    profile_id: str,
    family_background: DetailedFamilyBackground,
    current_user: User = Depends(get_current_user),
    db_client: MongoClient = Depends(db.get_client),
):
    """Update detailed family background information"""
    if not ObjectId.is_valid(profile_id):
        raise HTTPException(status_code=404, detail="Profile not found")
    
    # Check ownership and biodata type
    profile = db_client[db.db_name][BIODATA_COLLECTION].find_one({"_id": ObjectId(profile_id)})
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    
    if profile.get("user_id") != current_user.username and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Access denied")
    
    if profile.get("biodata_type") != "detailed":
        raise HTTPException(status_code=400, detail="This feature is only available for detailed biodata profiles")
    
    # Update family background
    result = db_client[db.db_name][BIODATA_COLLECTION].update_one(
        {"_id": ObjectId(profile_id)},
        {
            "$set": {
                "detailed_family_background": _serialize_for_mongodb(family_background.model_dump()),
                "updated_at": datetime.utcnow()
            }
        }
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=400, detail="Failed to update family background")
    
    return JSONResponse(content={"message": "Detailed family background updated successfully"})


@biodata_router.post("/biodata/{profile_id}/extended-family-member", tags=["Enhanced Biodata"])
async def add_extended_family_member(
    profile_id: str,
    family_member: ExtendedFamilyMember,
    current_user: User = Depends(get_current_user),
    db_client: MongoClient = Depends(db.get_client),
):
    """Add extended family member"""
    if not ObjectId.is_valid(profile_id):
        raise HTTPException(status_code=404, detail="Profile not found")
    
    # Check ownership
    profile = db_client[db.db_name][BIODATA_COLLECTION].find_one({"_id": ObjectId(profile_id)})
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    
    if profile.get("user_id") != current_user.username and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Add family member to extended family list
    result = db_client[db.db_name][BIODATA_COLLECTION].update_one(
        {"_id": ObjectId(profile_id)},
        {
            "$push": {
                "detailed_family_background.extended_family": _serialize_for_mongodb(family_member.model_dump())
            },
            "$set": {
                "updated_at": datetime.utcnow()
            }
        }
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=400, detail="Failed to add family member")
    
    return JSONResponse(content={"message": "Extended family member added successfully"}, status_code=201)


@biodata_router.delete("/biodata/{profile_id}/extended-family-member/{member_index}", tags=["Enhanced Biodata"])
async def remove_extended_family_member(
    profile_id: str,
    member_index: int,
    current_user: User = Depends(get_current_user),
    db_client: MongoClient = Depends(db.get_client),
):
    """Remove extended family member by index"""
    if not ObjectId.is_valid(profile_id):
        raise HTTPException(status_code=404, detail="Profile not found")
    
    # Check ownership
    profile = db_client[db.db_name][BIODATA_COLLECTION].find_one({"_id": ObjectId(profile_id)})
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    
    if profile.get("user_id") != current_user.username and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Get current extended family list
    family_background = profile.get("detailed_family_background", {})
    extended_family = family_background.get("extended_family", [])
    
    if member_index < 0 or member_index >= len(extended_family):
        raise HTTPException(status_code=400, detail="Invalid family member index")
    
    # Remove the family member
    extended_family.pop(member_index)
    
    result = db_client[db.db_name][BIODATA_COLLECTION].update_one(
        {"_id": ObjectId(profile_id)},
        {
            "$set": {
                "detailed_family_background.extended_family": extended_family,
                "updated_at": datetime.utcnow()
            }
        }
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=400, detail="Failed to remove family member")
    
    return Response(status_code=204)


@biodata_router.patch("/biodata/{profile_id}/extended-family", tags=["Enhanced Biodata"])
async def update_extended_family(
    profile_id: str,
    extended_family_data: dict,
    current_user: User = Depends(get_current_user),
    db_client: MongoClient = Depends(db.get_client),
):
    """Update extended family information in bulk"""
    if not ObjectId.is_valid(profile_id):
        raise HTTPException(status_code=404, detail="Profile not found")
    
    # Check ownership
    profile = db_client[db.db_name][BIODATA_COLLECTION].find_one({"_id": ObjectId(profile_id)})
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    
    if profile.get("user_id") != current_user.username and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Validate extended family data
    if "extended_family" not in extended_family_data:
        raise HTTPException(status_code=400, detail="extended_family field required")
    
    # Update extended family
    result = db_client[db.db_name][BIODATA_COLLECTION].update_one(
        {"_id": ObjectId(profile_id)},
        {
            "$set": {
                "detailed_family_background.extended_family": extended_family_data["extended_family"],
                "updated_at": datetime.utcnow()
            }
        }
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=400, detail="Failed to update extended family")
    
    return JSONResponse(content={"message": "Extended family updated successfully"})


# ==================== TRADITIONAL PREFERENCES CRUD ====================

@biodata_router.patch("/biodata/{profile_id}/traditional-preferences", tags=["Enhanced Biodata"])
async def update_traditional_preferences(
    profile_id: str,
    preferences: TraditionalPreferences,
    current_user: User = Depends(get_current_user),
    db_client: MongoClient = Depends(db.get_client),
):
    """Update traditional Hindu marriage preferences"""
    if not ObjectId.is_valid(profile_id):
        raise HTTPException(status_code=404, detail="Profile not found")
    
    # Check ownership and biodata type
    profile = db_client[db.db_name][BIODATA_COLLECTION].find_one({"_id": ObjectId(profile_id)})
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    
    if profile.get("user_id") != current_user.username and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Access denied")
    
    if profile.get("biodata_type") != "detailed":
        raise HTTPException(status_code=400, detail="This feature is only available for detailed biodata profiles")
    
    # Update traditional preferences
    result = db_client[db.db_name][BIODATA_COLLECTION].update_one(
        {"_id": ObjectId(profile_id)},
        {
            "$set": {
                "traditional_preferences": _serialize_for_mongodb(preferences.model_dump()),
                "updated_at": datetime.utcnow()
            }
        }
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=400, detail="Failed to update traditional preferences")
    
    return JSONResponse(content={"message": "Traditional preferences updated successfully"})


@biodata_router.get("/biodata/{profile_id}/traditional-preferences", response_model=TraditionalPreferences, tags=["Enhanced Biodata"])
async def get_traditional_preferences(
    profile_id: str,
    current_user: User = Depends(get_current_user),
    db_client: MongoClient = Depends(db.get_client),
):
    """Get traditional marriage preferences"""
    if not ObjectId.is_valid(profile_id):
        raise HTTPException(status_code=404, detail="Profile not found")
    
    profile = db_client[db.db_name][BIODATA_COLLECTION].find_one({"_id": ObjectId(profile_id)})
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    
    # Check access permissions
    if profile.get("user_id") != current_user.username and current_user.role != "admin":
        if not profile.get("is_active", False):
            raise HTTPException(status_code=403, detail="Profile is not public")
    
    preferences = profile.get("traditional_preferences")
    if not preferences:
        raise HTTPException(status_code=404, detail="Traditional preferences not found")
    
    return preferences


# ==================== MARRIAGE PLANNING CRUD ====================

@biodata_router.patch("/biodata/{profile_id}/marriage-planning", tags=["Enhanced Biodata"])
async def update_marriage_planning(
    profile_id: str,
    planning: MarriagePlanning,
    current_user: User = Depends(get_current_user),
    db_client: MongoClient = Depends(db.get_client),
):
    """Update marriage ceremony planning details"""
    if not ObjectId.is_valid(profile_id):
        raise HTTPException(status_code=404, detail="Profile not found")
    
    # Check ownership and biodata type
    profile = db_client[db.db_name][BIODATA_COLLECTION].find_one({"_id": ObjectId(profile_id)})
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    
    if profile.get("user_id") != current_user.username and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Access denied")
    
    if profile.get("biodata_type") != "detailed":
        raise HTTPException(status_code=400, detail="This feature is only available for detailed biodata profiles")
    
    # Update marriage planning
    result = db_client[db.db_name][BIODATA_COLLECTION].update_one(
        {"_id": ObjectId(profile_id)},
        {
            "$set": {
                "marriage_planning": _serialize_for_mongodb(planning.model_dump()),
                "updated_at": datetime.utcnow()
            }
        }
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=400, detail="Failed to update marriage planning")
    
    return JSONResponse(content={"message": "Marriage planning details updated successfully"})


@biodata_router.get("/biodata/{profile_id}/marriage-planning", response_model=MarriagePlanning, tags=["Enhanced Biodata"])
async def get_marriage_planning(
    profile_id: str,
    current_user: User = Depends(get_current_user),
    db_client: MongoClient = Depends(db.get_client),
):
    """Get marriage planning details"""
    if not ObjectId.is_valid(profile_id):
        raise HTTPException(status_code=404, detail="Profile not found")
    
    profile = db_client[db.db_name][BIODATA_COLLECTION].find_one({"_id": ObjectId(profile_id)})
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    
    # Check access permissions
    if profile.get("user_id") != current_user.username and current_user.role != "admin":
        if not profile.get("is_active", False):
            raise HTTPException(status_code=403, detail="Profile is not public")
    
    planning = profile.get("marriage_planning")
    if not planning:
        raise HTTPException(status_code=404, detail="Marriage planning details not found")
    
    return planning


# ==================== DOCUMENT VERIFICATION CRUD ====================

@biodata_router.patch("/biodata/{profile_id}/verification-documents", tags=["Enhanced Biodata"])
async def update_verification_documents(
    profile_id: str,
    documents: VerificationDocuments,
    current_user: User = Depends(get_current_user),
    db_client: MongoClient = Depends(db.get_client),
):
    """Update verification documents"""
    if not ObjectId.is_valid(profile_id):
        raise HTTPException(status_code=404, detail="Profile not found")
    
    # Check ownership
    profile = db_client[db.db_name][BIODATA_COLLECTION].find_one({"_id": ObjectId(profile_id)})
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    
    if profile.get("user_id") != current_user.username and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Update verification documents
    result = db_client[db.db_name][BIODATA_COLLECTION].update_one(
        {"_id": ObjectId(profile_id)},
        {
            "$set": {
                "verification_documents": _serialize_for_mongodb(documents.model_dump()),
                "updated_at": datetime.utcnow()
            }
        }
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=400, detail="Failed to update verification documents")
    
    return JSONResponse(content={"message": "Verification documents updated successfully"})


@biodata_router.post("/biodata/{profile_id}/upload-document", tags=["Enhanced Biodata"])
async def upload_verification_document(
    profile_id: str,
    document_type: str = Form(...),  # birth_certificate, caste_certificate, etc.
    document_file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db_client: MongoClient = Depends(db.get_client),
):
    """Upload verification document"""
    try:
        if not ObjectId.is_valid(profile_id):
            raise HTTPException(status_code=404, detail="Profile not found")
        
        # Check ownership
        collection = db_client["testdb"][BIODATA_COLLECTION]
        profile = collection.find_one({"_id": ObjectId(profile_id)})
        if not profile:
            raise HTTPException(status_code=404, detail="Profile not found")
        
        if profile.get("user_id") != current_user.username and current_user.role != "admin":
            raise HTTPException(status_code=403, detail="Access denied")
        
        # Validate document type
        valid_document_types = [
            "birth_certificate", "caste_certificate", "education_certificate",
            "income_proof", "id_proof", "address_proof", "medical_report"
        ]
        
        if document_type not in valid_document_types:
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid document type. Must be one of: {', '.join(valid_document_types)}"
            )
        
        # Validate file type (PDF, JPG, PNG)
        if not document_file.filename:
            raise HTTPException(status_code=400, detail="File name is required")
            
        allowed_extensions = ['.pdf', '.jpg', '.jpeg', '.png']
        file_extension = '.' + document_file.filename.split('.')[-1].lower()
        
        if file_extension not in allowed_extensions:
            raise HTTPException(
                status_code=400, 
                detail="Only PDF, JPG, and PNG files are allowed"
            )
        
        # Reset file pointer and read content
        document_file.file.seek(0)
        file_content = document_file.file.read()
        document_file.file.seek(0)
        
        # Upload to S3
        file_key = f"documents/{current_user.username}/{profile_id}/{document_type}_{int(datetime.utcnow().timestamp())}{file_extension}"
        
        content_type = "application/pdf" if file_extension == '.pdf' else f"image/{file_extension[1:]}"
        
        s3_client.put_object(
            Bucket=AWS_BUCKET_NAME,
            Key=file_key,
            Body=file_content,
            ContentType=content_type,
            ACL='public-read'
        )
        
        document_url = f"https://{AWS_BUCKET_NAME}.s3.{AWS_REGION}.amazonaws.com/{file_key}"
        
        # Update profile with document URL
        update_field = f"verification_documents.{document_type}_url"
        if document_type == "education_certificate":
            # Handle multiple education certificates
            collection.update_one(
                {"_id": ObjectId(profile_id)},
                {
                    "$push": {
                        "verification_documents.education_certificates": document_url
                    },
                    "$set": {
                        "updated_at": datetime.utcnow()
                    }
                }
            )
        elif document_type == "medical_report":
            # Handle multiple medical reports
            collection.update_one(
                {"_id": ObjectId(profile_id)},
                {
                    "$push": {
                        "verification_documents.medical_reports": document_url
                    },
                    "$set": {
                        "updated_at": datetime.utcnow()
                    }
                }
            )
        else:
            # Single document types
            collection.update_one(
                {"_id": ObjectId(profile_id)},
                {
                    "$set": {
                        update_field: document_url,
                        "updated_at": datetime.utcnow()
                    }
                }
            )
        
        return JSONResponse(content={
            "message": f"{document_type.replace('_', ' ').title()} uploaded successfully",
            "document_url": document_url
        }, status_code=201)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to upload document: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to upload document: {str(e)}")


@biodata_router.get("/biodata/{profile_id}/verification-documents", response_model=VerificationDocuments, tags=["Enhanced Biodata"])
async def get_verification_documents(
    profile_id: str,
    current_user: User = Depends(get_current_user),
    db_client: MongoClient = Depends(db.get_client),
):
    """Get verification documents (admin only or own profile)"""
    if not ObjectId.is_valid(profile_id):
        raise HTTPException(status_code=404, detail="Profile not found")
    
    profile = db_client[db.db_name][BIODATA_COLLECTION].find_one({"_id": ObjectId(profile_id)})
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    
    # Only owner or admin can access verification documents
    if profile.get("user_id") != current_user.username and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Access denied")
    
    documents = profile.get("verification_documents")
    if not documents:
        raise HTTPException(status_code=404, detail="Verification documents not found")
    
    return documents


# ==================== PROFILE ANALYTICS & MANAGEMENT ====================

@biodata_router.get("/biodata/{profile_id}/analytics", tags=["Enhanced Biodata"])
async def get_profile_analytics(
    profile_id: str,
    current_user: User = Depends(get_current_user),
    db_client: MongoClient = Depends(db.get_client),
):
    """Get profile analytics (views, interests, completeness)"""
    if not ObjectId.is_valid(profile_id):
        raise HTTPException(status_code=404, detail="Profile not found")
    
    profile = db_client[db.db_name][BIODATA_COLLECTION].find_one({"_id": ObjectId(profile_id)})
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    
    # Only owner can see analytics
    if profile.get("user_id") != current_user.username:
        raise HTTPException(status_code=403, detail="Access denied")
    
    analytics = {
        "profile_views": profile.get("profile_views", 0),
        "interests_received": profile.get("interests_received", 0),
        "interests_sent": profile.get("interests_sent", 0),
        "profile_completeness_score": profile.get("profile_completeness_score", 0),
        "last_activity": profile.get("last_activity"),
        "biodata_type": profile.get("biodata_type", "basic"),
        "is_verified": profile.get("is_verified", False),
        "verification_status": profile.get("verification_status", "pending")
    }
    
    return JSONResponse(content=analytics)


@biodata_router.patch("/biodata/{profile_id}/increment-view", tags=["Enhanced Biodata"])
async def increment_profile_view(
    profile_id: str,
    db_client: MongoClient = Depends(db.get_client),
):
    """Increment profile view count (public endpoint)"""
    if not ObjectId.is_valid(profile_id):
        raise HTTPException(status_code=404, detail="Profile not found")
    
    # Increment view count
    result = db_client[db.db_name][BIODATA_COLLECTION].update_one(
        {"_id": ObjectId(profile_id)},
        {
            "$inc": {"profile_views": 1},
            "$set": {"last_activity": datetime.utcnow()}
        }
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Profile not found")
    
    return JSONResponse(content={"message": "Profile view recorded"})


# ==================== ADMIN MANAGEMENT ====================

async def get_current_admin_user(current_user: User = Depends(get_current_user)):
    """Dependency to ensure current user is admin"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user


@biodata_router.get("/admin/biodata/detailed-profiles", tags=["Admin - Enhanced Biodata"])
async def get_all_detailed_profiles(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    verification_status: Optional[str] = Query(None),
    current_admin: User = Depends(get_current_admin_user),
    db_client: MongoClient = Depends(db.get_client),
):
    """Get all detailed biodata profiles (admin only)"""
    try:
        collection = db_client["testdb"][BIODATA_COLLECTION]
        
        # Build filter
        filter_query = {"biodata_type": "detailed"}
        if verification_status:
            filter_query["verification_status"] = verification_status
        
        # Get profiles with pagination
        profiles = list(
            collection
            .find(filter_query, {"verification_documents": 0})  # Exclude sensitive docs
            .sort("created_at", DESCENDING)
            .skip(skip)
            .limit(limit)
        )
        
        # Convert ObjectId to string and format all datetime fields
        for profile in profiles:
            profile["_id"] = str(profile["_id"])
            
            # Format all datetime fields recursively
            def format_datetimes(obj):
                if isinstance(obj, dict):
                    for key, value in obj.items():
                        if isinstance(value, datetime):
                            obj[key] = value.isoformat()
                        elif isinstance(value, (list, dict)):
                            format_datetimes(value)
                elif isinstance(obj, list):
                    for item in obj:
                        format_datetimes(item)
                        
            format_datetimes(profile)
        
        total_count = collection.count_documents(filter_query)
        
        return JSONResponse(content={
            "profiles": profiles,
            "total_count": total_count,
            "skip": skip,
            "limit": limit
        })
        
    except Exception as e:
        logger.error(f"Failed to get detailed profiles: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get detailed profiles: {str(e)}")


@biodata_router.patch("/admin/biodata/{profile_id}/verification-status", tags=["Admin - Enhanced Biodata"])
async def update_verification_status(
    profile_id: str,
    verification_status: str = Body(..., embed=True),
    admin_notes: Optional[str] = Body(None, embed=True),
    current_admin: User = Depends(get_current_admin_user),
    db_client: MongoClient = Depends(db.get_client),
):
    """Update profile verification status (admin only)"""
    if not ObjectId.is_valid(profile_id):
        raise HTTPException(status_code=404, detail="Profile not found")
    
    valid_statuses = ["pending", "verified", "rejected", "under_review"]
    if verification_status not in valid_statuses:
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid status. Must be one of: {', '.join(valid_statuses)}"
        )
    
    update_data = {
        "verification_status": verification_status,
        "updated_at": datetime.utcnow(),
        "verified_by": current_admin.username
    }
    
    if verification_status == "verified":
        update_data["is_verified"] = True
        update_data["verified_at"] = datetime.utcnow()
    else:
        update_data["is_verified"] = False
    
    if admin_notes:
        update_data["admin_notes"] = admin_notes
    
    result = db_client[db.db_name][BIODATA_COLLECTION].update_one(
        {"_id": ObjectId(profile_id)},
        {"$set": update_data}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Profile not found")
    
    return JSONResponse(content={
        "message": f"Verification status updated to '{verification_status}'",
        "verified_by": current_admin.username
    })

