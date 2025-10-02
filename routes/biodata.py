# routes/biodata.py
import uuid
import logging
from datetime import datetime, date
from typing import List, Optional, Dict, Any
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
    CasteCategory
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
    # Add user association
    profile_dict = profile.dict(by_alias=True, exclude={"id"})
    profile_dict["user_id"] = current_user.username  # Link to user
    profile_dict["created_by"] = current_user.username
    profile_dict["created_at"] = datetime.utcnow()
    profile_dict["updated_at"] = datetime.utcnow()
    
    # Convert date objects to strings for MongoDB storage
    if "dob" in profile_dict and isinstance(profile_dict["dob"], date):
        profile_dict["dob"] = profile_dict["dob"].isoformat()
    
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

# ------------------------- Get Single Biodata Profile -------------------------

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

# ------------------------- Get My Biodata Profile -------------------------

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
    update_data = updated_profile.dict(
        by_alias=True,
        exclude={"id", "created_at", "user_id", "created_by"}
    )
    update_data["updated_at"] = datetime.utcnow()
    
    # Convert date objects to strings for MongoDB storage
    if "dob" in update_data and isinstance(update_data["dob"], date):
        update_data["dob"] = update_data["dob"].isoformat()
    
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
                "contact": contact_info.dict(),
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
                "education": education.dict(),
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
                "occupation": occupation.dict(),
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
                "family": family.dict(),
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
                "partner_preferences": preferences.dict(),
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
                "physical": physical.dict(),
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
                "lifestyle": lifestyle.dict(),
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
    
    # Convert date objects to strings for MongoDB storage
    horoscope_data = horoscope.dict()
    if "date_of_birth" in horoscope_data and isinstance(horoscope_data["date_of_birth"], date):
        horoscope_data["date_of_birth"] = horoscope_data["date_of_birth"].isoformat()
    
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
                "languages": languages.dict(),
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