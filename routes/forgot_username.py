from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from database.db import db
from pymongo import MongoClient
from routes.send_email import send_username_recovery_email

router = APIRouter()

class ForgotUsernameRequest(BaseModel):
    email: str

# @router.post("/forgot-username", tags=["Forgot Username"])
# async def forgot_username(request: ForgotUsernameRequest, db_client: MongoClient = Depends(db.get_client)):
#     print(f"Checking email: {request.email}")  # Debugging statement
#     user_collection = db_client[db.db_name]["user"]
#     user = user_collection.find_one({"email": {"$regex": f"^{request.email}$", "$options": "i"}})

#     if not user:
#         print("User not found in the database")  # Debugging statement
#         raise HTTPException(status_code=404, detail="Email not found")

#     username = user.get("username")
#     print(f"Found username: {username}")  # Debugging statement

#     # Send email with the username
#     await send_username_recovery_email(request.email, username)

#     return {"message": "Your username has been sent to your email."}

@router.post("/forgot-username", tags=["Forgot Username"])
async def forgot_username(request: ForgotUsernameRequest, db_client: MongoClient = Depends(db.get_client)):
    user_collection = db_client[db.db_name]["user"]

    # Find user by email (case-insensitive)
    user = user_collection.find_one({"email": {"$regex": f"^{request.email.strip()}$", "$options": "i"}})

    if not user:
        raise HTTPException(status_code=404, detail="Email not found")

    username = user.get("username", "").rstrip()  # Get exact username and remove only trailing spaces

    # Send email with the formatted username (include trailing space if it exists)
    await send_username_recovery_email(request.email, username)

    return {"message": "Your username has been sent to your email."}



