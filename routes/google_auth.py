from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from authentication.google_auth import verify_google_token
from database.db import Database

router = APIRouter()

# Initialize your custom DB connection (uses AWS Secrets Manager internally)
db = Database()
client = db.get_client()
db_name = db.db_name
collection = client[db_name]["google_users"]  # Use separate collection for Google users

class GoogleLoginRequest(BaseModel):
    id_token: str

@router.post("/auth/google")
async def google_login(payload: GoogleLoginRequest):
    user_info = verify_google_token(payload.id_token)
    if not user_info:
        raise HTTPException(status_code=401, detail="Invalid Google token")

    # Check if user already exists
    user = collection.find_one({"sub": user_info["sub"]})
    
    if not user:
        # Insert new Google user
        collection.insert_one(user_info)

    # Respond with the user info and a dummy token (later replace with JWT if needed)
    return {
        "access_token": user_info["sub"],
        "token_type": "bearer",
        "user": user_info
    }
