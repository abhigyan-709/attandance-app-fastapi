# from fastapi import APIRouter, HTTPException
# from pydantic import BaseModel
# from authentication.google_auth import verify_google_token
# from database.db import Database
# from bson import ObjectId
# from authentication.google_jwt import create_google_access_token, create_google_refresh_token


# router31 = APIRouter()

# # Initialize your custom DB connection (uses AWS Secrets Manager internally)
# db = Database()
# client = db.get_client()
# db_name = db.db_name
# collection = client[db_name]["google_users"]  # Separate collection for Google users

# class GoogleLoginRequest(BaseModel):
#     id_token: str

# def convert_objectid(obj):
#     """Recursively convert ObjectId to str in nested dicts/lists."""
#     if isinstance(obj, dict):
#         return {k: convert_objectid(v) for k, v in obj.items()}
#     elif isinstance(obj, list):
#         return [convert_objectid(i) for i in obj]
#     elif isinstance(obj, ObjectId):
#         return str(obj)
#     return obj

# @router31.post("/auth/google")
# async def google_login(payload: GoogleLoginRequest):
#     user_info = verify_google_token(payload.id_token)
#     if not user_info:
#         raise HTTPException(status_code=401, detail="Invalid Google token")

#     # Check if user already exists
#     user = collection.find_one({"sub": user_info["sub"]})

#     if not user:
#         # Insert and re-fetch to get Mongo _id
#         insert_result = collection.insert_one(user_info)
#         user = collection.find_one({"_id": insert_result.inserted_id})

#     # Convert ObjectId to string for response
#     user_sanitized = convert_objectid(user)
#     access_token = create_google_access_token({"sub": user_info["sub"]})
#     refresh_token = create_google_refresh_token({"sub": user_info["sub"]})

#     return {
#         "access_token": access_token,
#         "refresh_token": refresh_token,
#         "token_type": "bearer",
#         "user": user_sanitized
#     }

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr
from typing import Optional, List
from authentication.google_auth import verify_google_token
from database.db import Database
from bson import ObjectId
from authentication.google_jwt import create_google_access_token, create_google_refresh_token


router31 = APIRouter()

# Initialize your custom DB connection (uses AWS Secrets Manager internally)
db = Database()
client = db.get_client()
db_name = db.db_name

google_users_collection = client[db_name]["google_users"]           # Raw Google data
google_users_details_collection = client[db_name]["google_users_details"]  # Extended user profile


# ---------- MODELS ----------
class GoogleLoginRequest(BaseModel):
    id_token: str

class Address(BaseModel):
    label: str                  # Home, Office, Other
    flat_no: Optional[str] = None
    address: str
    city: str
    location: Optional[str] = None  # could be lat,long or text

class UserDetails(BaseModel):
    full_name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[EmailStr] = None
    addresses: Optional[List[Address]] = []


# ---------- HELPERS ----------
def convert_objectid(obj):
    """Recursively convert ObjectId to str in nested dicts/lists."""
    if isinstance(obj, dict):
        return {k: convert_objectid(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_objectid(i) for i in obj]
    elif isinstance(obj, ObjectId):
        return str(obj)
    return obj


# ---------- GOOGLE LOGIN ----------
@router31.post("/auth/google")
async def google_login(payload: GoogleLoginRequest):
    user_info = verify_google_token(payload.id_token)
    if not user_info:
        raise HTTPException(status_code=401, detail="Invalid Google token")

    # Step 1: Check or insert into google_users
    user = google_users_collection.find_one({"sub": user_info["sub"]})
    if not user:
        insert_result = google_users_collection.insert_one(user_info)
        user = google_users_collection.find_one({"_id": insert_result.inserted_id})

    user_id = str(user["_id"])

    # Step 2: Check or insert into google_users_details
    user_details = google_users_details_collection.find_one({"user_id": user_id})
    if not user_details:
        google_users_details_collection.insert_one({
            "user_id": user_id,
            "full_name": user_info.get("name"),
            "email": user_info.get("email"),
            "phone": None,
            "addresses": []   # start empty, user will add later
        })
        user_details = google_users_details_collection.find_one({"user_id": user_id})

    # Step 3: Generate tokens
    access_token = create_google_access_token({"sub": user_info["sub"]})
    refresh_token = create_google_refresh_token({"sub": user_info["sub"]})

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "user": convert_objectid(user),
        "user_details": convert_objectid(user_details)
    }


# ---------- UPDATE USER DETAILS ----------
@router31.put("/users/google/details/{user_id}")
async def update_google_user_details(user_id: str, payload: UserDetails):
    update_data = {k: v for k, v in payload.dict(exclude_unset=True).items()}

    result = google_users_details_collection.update_one(
        {"user_id": user_id}, {"$set": update_data}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="User details not found")

    updated_user = google_users_details_collection.find_one({"user_id": user_id})
    return {"user_details": convert_objectid(updated_user)}


# ---------- ADD NEW ADDRESS ----------
@router31.post("/users/google/details/{user_id}/addresses")
async def add_address(user_id: str, address: Address):
    result = google_users_details_collection.update_one(
        {"user_id": user_id},
        {"$push": {"addresses": address.dict()}}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="User details not found")

    updated_user = google_users_details_collection.find_one({"user_id": user_id})
    return {"user_details": convert_objectid(updated_user)}


# ---------- DELETE ADDRESS ----------
@router31.delete("/users/google/details/{user_id}/addresses/{label}")
async def delete_address(user_id: str, label: str):
    result = google_users_details_collection.update_one(
        {"user_id": user_id},
        {"$pull": {"addresses": {"label": label}}}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="User details not found")

    updated_user = google_users_details_collection.find_one({"user_id": user_id})
    return {"user_details": convert_objectid(updated_user)}
