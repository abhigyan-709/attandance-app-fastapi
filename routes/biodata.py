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
    def convert_value(value):
        if isinstance(value, Enum):
            return value.value  # Convert enum to its string value
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
        file_extension = (file.filename or "image").split(".")[-1]
        unique_filename = f"{folder}/{uuid.uuid4()}.{file_extension}"
        
        s3_client.upload_fileobj(
            file.file,
            AWS_BUCKET_NAME,
            unique_filename,
            ExtraArgs={"ContentType": file.content_type or "image/jpeg"},
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
    if not ObjectId.is_valid(profile_id):
        raise HTTPException(status_code=404, detail="Profile not found")
    
    # Check if profile exists and user has permission
    profile = db_client[db.db_name][BIODATA_COLLECTION].find_one({"_id": ObjectId(profile_id)})
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
        db_client[db.db_name][BIODATA_COLLECTION].update_one(
            {"_id": ObjectId(profile_id)},
            {"$set": {"photos.$[].is_primary": False}}
        )
    
    # Add photo to profile
    db_client[db.db_name][BIODATA_COLLECTION].update_one(
        {"_id": ObjectId(profile_id)},
        {
            "$push": {"photos": photo_data},
            "$set": {"updated_at": datetime.utcnow()}
        }
    )
    
    return JSONResponse(content={
        "message": "Photo uploaded successfully",
        "photo": photo_data
    }, status_code=201)

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
                "languages": _serialize_for_mongodb(languages.model_dump()),
                "updated_at": datetime.utcnow()
            }
        }
    )
    
    return JSONResponse(content={"message": "Languages updated successfully"})

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
        db_client[db.db_name][BIODATA_COLLECTION].update_one(
            {"_id": ObjectId(profile_id)},
            {"$set": {"photos.$[].is_primary": False}}
        )
    
    # Replace photo in array
    db_client[db.db_name][BIODATA_COLLECTION].update_one(
        {"_id": ObjectId(profile_id)},
        {
            "$set": {
                f"photos.{photo_index}": new_photo_data,
                "updated_at": datetime.utcnow()
            }
        }
    )
    
    return JSONResponse(content={
        "message": "Photo replaced successfully",
        "photo": new_photo_data
    }, status_code=200)

@biodata_router.patch("/biodata/{profile_id}/photos/reorder", tags=["Biodata"])
async def reorder_biodata_photos(
    profile_id: str,
    photo_order: List[int] = Body(..., description="New order of photo indices"),
    current_user: User = Depends(get_current_user),
    db_client: MongoClient = Depends(db.get_client),
):
    """Reorder photos in the profile"""
    if not ObjectId.is_valid(profile_id):
        raise HTTPException(status_code=404, detail="Profile not found")
    
    profile = db_client[db.db_name][BIODATA_COLLECTION].find_one({"_id": ObjectId(profile_id)})
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
    
    db_client[db.db_name][BIODATA_COLLECTION].update_one(
        {"_id": ObjectId(profile_id)},
        {
            "$set": {
                "photos": reordered_photos,
                "updated_at": datetime.utcnow()
            }
        }
    )
    
    return JSONResponse(content={"message": "Photos reordered successfully"})

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
    if not ObjectId.is_valid(profile_id):
        raise HTTPException(status_code=404, detail="Profile not found")
    
    profile = db_client[db.db_name][BIODATA_COLLECTION].find_one(
        {"_id": ObjectId(profile_id)}, 
        {"languages": 1}
    )
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    
    languages_info = profile.get("languages")
    if not languages_info:
        raise HTTPException(status_code=404, detail="Languages information not found")
    
    return languages_info

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
            "$unset": {"contact": ""},
            "$set": {"updated_at": datetime.utcnow()}
        }
    )
    
    return JSONResponse(content={"message": "Contact information deleted successfully"})

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
    
    return JSONResponse(content={"message": "Education information deleted successfully"})

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
    
    return JSONResponse(content={"message": "Occupation information deleted successfully"})

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
    
    return JSONResponse(content={"message": "Physical attributes deleted successfully"})

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
    
    return JSONResponse(content={"message": "Lifestyle information deleted successfully"})

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
    
    return JSONResponse(content={"message": "Horoscope information deleted successfully"})

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
    
    return JSONResponse(content={"message": "Languages information deleted successfully"})

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
    
    return JSONResponse(content={"message": "Partner preferences deleted successfully"})

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
    
    return JSONResponse(content={"message": "Photo deleted successfully"})

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
    
    return JSONResponse(content={"message": "Profile deleted successfully"})

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

# ------------------------- Search Profiles -------------------------

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
    if not ObjectId.is_valid(profile_id):
        raise HTTPException(status_code=404, detail="Profile not found")
    
    # Check ownership
    profile = db_client[db.db_name][BIODATA_COLLECTION].find_one({"_id": ObjectId(profile_id)})
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    
    if profile.get("user_id") != current_user.username and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Validate file type
    if not kundli_file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed for Kundli")
    
    try:
        # Upload to S3
        file_key = f"kundli/{current_user.username}_{profile_id}_{int(datetime.utcnow().timestamp())}.pdf"
        
        s3_client.upload_fileobj(
            kundli_file.file,
            AWS_BUCKET_NAME,
            file_key,
            ExtraArgs={"ContentType": "application/pdf"}
        )
        
        kundli_url = f"https://{AWS_BUCKET_NAME}.s3.{AWS_REGION}.amazonaws.com/{file_key}"
        
        # Update profile with kundli URL
        db_client[db.db_name][BIODATA_COLLECTION].update_one(
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
        })
        
    except ClientError as e:
        logger.error(f"S3 upload error: {e}")
        raise HTTPException(status_code=500, detail="Failed to upload Kundli PDF")


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
    
    return JSONResponse(content={"message": "Extended family member added successfully"})


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
    
    return JSONResponse(content={"message": "Extended family member removed successfully"})


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
    if not ObjectId.is_valid(profile_id):
        raise HTTPException(status_code=404, detail="Profile not found")
    
    # Check ownership
    profile = db_client[db.db_name][BIODATA_COLLECTION].find_one({"_id": ObjectId(profile_id)})
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
    allowed_extensions = ['.pdf', '.jpg', '.jpeg', '.png']
    file_extension = '.' + document_file.filename.split('.')[-1].lower()
    
    if file_extension not in allowed_extensions:
        raise HTTPException(
            status_code=400, 
            detail="Only PDF, JPG, and PNG files are allowed"
        )
    
    try:
        # Upload to S3
        file_key = f"documents/{current_user.username}/{profile_id}/{document_type}_{int(datetime.utcnow().timestamp())}{file_extension}"
        
        content_type = "application/pdf" if file_extension == '.pdf' else f"image/{file_extension[1:]}"
        
        s3_client.upload_fileobj(
            document_file.file,
            AWS_BUCKET_NAME,
            file_key,
            ExtraArgs={"ContentType": content_type}
        )
        
        document_url = f"https://{AWS_BUCKET_NAME}.s3.{AWS_REGION}.amazonaws.com/{file_key}"
        
        # Update profile with document URL
        update_field = f"verification_documents.{document_type}_url"
        if document_type == "education_certificate":
            # Handle multiple education certificates
            db_client[db.db_name][BIODATA_COLLECTION].update_one(
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
            db_client[db.db_name][BIODATA_COLLECTION].update_one(
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
            db_client[db.db_name][BIODATA_COLLECTION].update_one(
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
        })
        
    except ClientError as e:
        logger.error(f"S3 upload error: {e}")
        raise HTTPException(status_code=500, detail="Failed to upload document")


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
    # Build filter
    filter_query = {"biodata_type": "detailed"}
    if verification_status:
        filter_query["verification_status"] = verification_status
    
    # Get profiles with pagination
    profiles = list(
        db_client[db.db_name][BIODATA_COLLECTION]
        .find(filter_query, {"verification_documents": 0})  # Exclude sensitive docs
        .sort("created_at", DESCENDING)
        .skip(skip)
        .limit(limit)
    )
    
    # Convert ObjectId to string
    for profile in profiles:
        profile["_id"] = str(profile["_id"])
    
    total_count = db_client[db.db_name][BIODATA_COLLECTION].count_documents(filter_query)
    
    return JSONResponse(content={
        "profiles": profiles,
        "total_count": total_count,
        "skip": skip,
        "limit": limit
    })


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