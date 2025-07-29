from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from authentication.google_auth import verify_google_token
from database.db import Database
from bson import ObjectId

router31 = APIRouter()

# Initialize your custom DB connection (uses AWS Secrets Manager internally)
db = Database()
client = db.get_client()
db_name = db.db_name
collection = client[db_name]["google_users"]  # Separate collection for Google users

class GoogleLoginRequest(BaseModel):
    id_token: str

def convert_objectid(obj):
    """Recursively convert ObjectId to str in nested dicts/lists."""
    if isinstance(obj, dict):
        return {k: convert_objectid(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_objectid(i) for i in obj]
    elif isinstance(obj, ObjectId):
        return str(obj)
    return obj

@router31.post("/auth/google")
async def google_login(payload: GoogleLoginRequest):
    user_info = verify_google_token(payload.id_token)
    if not user_info:
        raise HTTPException(status_code=401, detail="Invalid Google token")

    # Check if user already exists
    user = collection.find_one({"sub": user_info["sub"]})

    if not user:
        # Insert and re-fetch to get Mongo _id
        insert_result = collection.insert_one(user_info)
        user = collection.find_one({"_id": insert_result.inserted_id})

    # Convert ObjectId to string for response
    user_sanitized = convert_objectid(user)

    return {
        "access_token": user_info["sub"],  # You can replace this with a real JWT later
        "token_type": "bearer",
        "user": user_sanitized
    }
