# routes/user.py

from fastapi import APIRouter, Depends, HTTPException, Request, File, UploadFile, Form
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
# ✅ Use JOSE consistently (you already do elsewhere)
from jose import jwt
from datetime import datetime, timedelta
from passlib.context import CryptContext
from database.db import db
from models.user import User, UserProfileUpdate
from models.token import Token
from typing import Union, List, Optional
import secrets
from bson import ObjectId
from fastapi.responses import JSONResponse
from pymongo import MongoClient
from models.user import User
from models.user_details import UserDetails
from routes.send_email import send_registration_email ,send_password_reset_email
from datetime import datetime, timedelta
import pytz
import requests
import base64
import boto3
from botocore.exceptions import ClientError
import logging
import uuid

# ✅ import the shared values/functions
from authentication.auth import (
    SECRET_KEY,           # <- one shared secret
    ALGORITHM,            # "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES,
    get_password_hash,
    verify_password,
    create_access_token,  # reuse the same token creator
)

# S3 Configuration (same as biodata routes)
from routes.config import AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_REGION

# AWS S3 Configuration
AWS_BUCKET_NAME = "projectdevops-blogs-new"
s3_client = boto3.client(
    "s3",
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    region_name=AWS_REGION,
)

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

route2 = APIRouter()

RESET_TOKEN_EXPIRY_MINUTES = 15
RESET_SECRET_KEY = secrets.token_urlsafe(32)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=401,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        # 🔧 accept either "sub" or "username"
        username: str = payload.get("sub") or payload.get("username")
        if not username:
            raise credentials_exception

        db_client = db.get_client()
        user_from_db = db_client[db.db_name]["user"].find_one({"username": username})
        if not user_from_db:
            raise credentials_exception

        return User(**user_from_db)
    except Exception:
        # (Optional) you can import and catch jose.exceptions.ExpiredSignatureError/JWTError specifically,
        # but the root cause here was missing "sub".
        raise credentials_exception


@route2.post("/token", response_model=Token, tags=["Login & Authentication"])
async def login_for_access_token(
        form_data: OAuth2PasswordRequestForm = Depends(),
        db_client: MongoClient = Depends(db.get_client)
):
    user_from_db = db_client[db.db_name]["user"].find_one({"username": form_data.username})
    if user_from_db and verify_password(form_data.password, user_from_db['password']):
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        # ✅ reuse the same creator that uses SECRET_KEY/ALGO from authentication.auth
        access_token = create_access_token(
            data={"username": form_data.username},
            expires_delta=access_token_expires
        )
        db_client[db.db_name]["active_sessions"].insert_one({
            "username": form_data.username,
            "token": access_token,
            "login_time": datetime.utcnow()
        })
        return {"access_token": access_token, "token_type": "bearer"}

    raise HTTPException(
        status_code=401,
        detail="Incorrect username or password",
        headers={"WWW-Authenticate": "Bearer"},
    )


@route2.post("/verify-token", tags=["Login & Authentication"])
async def verify_token(request: Request, db_client: MongoClient = Depends(db.get_client)):
    """
    Verifies the JWT token from the request body and checks if the user exists.
    """
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Unauthorized")

    token = auth_header.split(" ")[1]  # Extract token from header

    try:
        # Decode the JWT token
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")

        if not username:
            raise HTTPException(status_code=401, detail="Invalid token")

        # Check if the user exists in the database
        user_from_db = db_client[db.db_name]["user"].find_one({"username": username})
        if not user_from_db:
            raise HTTPException(status_code=401, detail="User not found")

        return JSONResponse(content={"status": "authorized"}, status_code=200)

    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

    
LMS_AUTH_URL = "https://api.projectdevops.in/token"
@route2.get("/authenticate", tags=["Login & Authentication"])
async def authenticate(request: Request):
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Basic "):
        raise HTTPException(status_code=401, detail="Unauthorized")

    auth_decoded = base64.b64decode(auth_header.split(" ")[1]).decode("utf-8")
    username, password = auth_decoded.split(":", 1)

    response = requests.post(
        LMS_AUTH_URL,
        headers={"accept": "application/json", "Content-Type": "application/x-www-form-urlencoded"},
        data={"grant_type": "password", "username": username, "password": password}
    )

    if response.status_code == 200:
        return {}  # Authentication successful (Nginx allows access)

    raise HTTPException(status_code=401, detail="Invalid credentials")


@route2.post("/register/", tags=["User Registration"])
async def register(user: User, db_client: MongoClient = Depends(db.get_client)):
    # Check if the username is already taken
    existing_user_username = db_client[db.db_name]["user"].find_one({"username": user.username})
    if existing_user_username:
        raise HTTPException(status_code=400, detail="Username is already taken")

    # Check if the email is already taken
    existing_user_email = db_client[db.db_name]["user"].find_one({"email": user.email})
    if existing_user_email:
        raise HTTPException(status_code=400, detail="Email is already registered")

    # Hash the password before storing it in the database
    user_dict = user.dict()
    user_dict['password'] = get_password_hash(user.password)
    
    # Insert the user into the database
    result = db_client[db.db_name]["user"].insert_one(user_dict)
    
    # Convert ObjectId to string
    user_dict["_id"] = str(result.inserted_id)

    await send_registration_email(user.email, user.first_name, user.last_name)

    # Return response with the user data
    return JSONResponse(content=user_dict, status_code=201)


@route2.get("/users/me", response_model=User, tags=["Read User & Current User"])
async def read_current_user(current_user: User = Depends(get_current_user), db_client: MongoClient = Depends(db.get_client)):
    # Use the username from the current_user object to filter the database query
    user_from_db = db_client[db.db_name]["user"].find_one({"username": current_user.username})

    if user_from_db:
        return user_from_db

    raise HTTPException(status_code=404, detail="User not found")



@route2.get("/users", response_model=List[User], tags=["User Management"])
async def get_all_users(current_user: User = Depends(get_current_user), db_client: MongoClient = Depends(db.get_client)):
    # Check if the current user is an admin
    if current_user.role != "admin":
        raise HTTPException(
            status_code=403,
            detail="You do not have permission to access this resource"
        )

    # Fetch all users from the database
    users_from_db = db_client[db.db_name]["user"].find()

    # Convert users from the database into a list
    users_list = []
    for user_data in users_from_db:
        user_data["_id"] = str(user_data["_id"])  # Convert ObjectId to string
        users_list.append(user_data)

    return users_list


@route2.patch("/users/activate/{username}", response_model=User, tags=["User Management"])
async def activate_user(
    username: str,  # Get the username as a URL parameter
    current_user: User = Depends(get_current_user),  # Ensure the current user is authenticated
    db_client: MongoClient = Depends(db.get_client)  # Access the database client
):
    # Check if the current user is an admin
    if current_user.role != "admin":
        raise HTTPException(
            status_code=403,
            detail="You do not have permission to perform this action"
        )

    # Find the user by username
    user_from_db = db_client[db.db_name]["user"].find_one({"username": username})

    if user_from_db is None:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )

    # Update the is_active field to True
    update_result = db_client[db.db_name]["user"].update_one(
        {"username": username},  # Match the user by username
        {"$set": {"is_active": True}}  # Set the is_active field to True
    )

    if update_result.matched_count == 0:
        raise HTTPException(
            status_code=400,
            detail="Failed to update user status"
        )

    # Fetch the updated user data from database
    updated_user = db_client[db.db_name]["user"].find_one({"username": username})

    # Return the updated user details
    updated_user["_id"] = str(updated_user["_id"])  # Convert ObjectId to string for response
    return updated_user


@route2.patch("/users/deactivate/{username}", response_model=User, tags=["User Management"])
async def deactivate_user(
    username: str,
    current_user: User = Depends(get_current_user),
    db_client: MongoClient = Depends(db.get_client)
):
    # Check if the current user is an admin
    if current_user.role != "admin":
        raise HTTPException(
            status_code=403,
            detail="You do not have permission to perform this action"
        )

    # Find the user by username
    user_from_db = db_client[db.db_name]["user"].find_one({"username": username})

    if user_from_db is None:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )

    # Prevent admin from deactivating themselves
    if username == current_user.username:
        raise HTTPException(
            status_code=400,
            detail="You cannot deactivate your own account"
        )

    # Update the is_active field to False
    update_result = db_client[db.db_name]["user"].update_one(
        {"username": username},
        {"$set": {"is_active": False}}
    )

    if update_result.matched_count == 0:
        raise HTTPException(
            status_code=400,
            detail="Failed to update user status"
        )

    # Remove active sessions for deactivated user
    db_client[db.db_name]["active_sessions"].delete_many({"username": username})

    # Fetch the updated user data from database
    updated_user = db_client[db.db_name]["user"].find_one({"username": username})
    updated_user["_id"] = str(updated_user["_id"])

    return updated_user


@route2.put("/users/{username}", response_model=User, tags=["User Management"])
async def update_user(
    username: str,
    updated_user_data: dict,
    current_user: User = Depends(get_current_user),
    db_client: MongoClient = Depends(db.get_client)
):
    """Update user information (admin only or own profile)"""
    # Check permissions - admin can update any user, users can update their own profile
    if current_user.role != "admin" and current_user.username != username:
        raise HTTPException(
            status_code=403,
            detail="You do not have permission to update this user"
        )

    # Find the user to update
    user_from_db = db_client[db.db_name]["user"].find_one({"username": username})
    if not user_from_db:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )

    # Prepare update data
    # Only allow User model fields, NOT UserDetails fields (student info)
    allowed_fields = [
        "first_name", "last_name", "email", "city", "role", "is_active",
        # Author profile fields (optional, part of User model)
        "author_bio", "author_profile_image", "author_designation", "author_social_links"
    ]
    update_data = {}
    
    for field, value in updated_user_data.items():
        if field in allowed_fields:
            # Special handling for email uniqueness
            if field == "email" and value != user_from_db.get("email"):
                existing_email = db_client[db.db_name]["user"].find_one({"email": value})
                if existing_email:
                    raise HTTPException(
                        status_code=400,
                        detail="Email is already registered to another user"
                    )
            
            # Only admins can change role and is_active
            if field in ["role", "is_active"] and current_user.role != "admin":
                continue
                
            # Prevent admin from deactivating themselves
            if field == "is_active" and value is False and username == current_user.username:
                raise HTTPException(
                    status_code=400,
                    detail="You cannot deactivate your own account"
                )
                
            update_data[field] = value

    # Add updated timestamp
    update_data["updated_at"] = datetime.utcnow()

    # Perform the update
    if update_data:
        update_result = db_client[db.db_name]["user"].update_one(
            {"username": username},
            {"$set": update_data}
        )

        if update_result.matched_count == 0:
            raise HTTPException(
                status_code=400,
                detail="Failed to update user"
            )

    # Fetch and return updated user
    updated_user = db_client[db.db_name]["user"].find_one({"username": username})
    updated_user["_id"] = str(updated_user["_id"])
    
    return updated_user


@route2.patch("/users/{username}/role", tags=["User Management"])
async def update_user_role(
    username: str,
    new_role: str,
    current_user: User = Depends(get_current_user),
    db_client: MongoClient = Depends(db.get_client)
):
    """Update user role (admin only)"""
    # Only admin can change roles
    if current_user.role != "admin":
        raise HTTPException(
            status_code=403,
            detail="You do not have permission to change user roles"
        )

    # Validate role
    valid_roles = ["user", "admin", "author", "vendor", "moderator"]
    if new_role not in valid_roles:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid role. Must be one of: {', '.join(valid_roles)}"
        )

    # Find the user
    user_from_db = db_client[db.db_name]["user"].find_one({"username": username})
    if not user_from_db:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )

    # Prevent admin from changing their own role to non-admin
    if username == current_user.username and new_role != "admin":
        raise HTTPException(
            status_code=400,
            detail="You cannot change your own admin role"
        )

    # Update the role
    update_result = db_client[db.db_name]["user"].update_one(
        {"username": username},
        {
            "$set": {
                "role": new_role,
                "updated_at": datetime.utcnow()
            }
        }
    )

    if update_result.matched_count == 0:
        raise HTTPException(
            status_code=400,
            detail="Failed to update user role"
        )

    return JSONResponse(
        content={"message": f"User role updated to '{new_role}' successfully"},
        status_code=200
    )


@route2.patch("/users/change-password", tags=["User Management"])
async def change_password(
    current_password: str,
    new_password: str,
    current_user: User = Depends(get_current_user),
    db_client: MongoClient = Depends(db.get_client)
):
    """Change user's own password"""
    # Verify current password
    user_from_db = db_client[db.db_name]["user"].find_one({"username": current_user.username})
    if not user_from_db or not verify_password(current_password, user_from_db["password"]):
        raise HTTPException(
            status_code=400,
            detail="Current password is incorrect"
        )

    # Validate new password strength (basic validation)
    if len(new_password) < 6:
        raise HTTPException(
            status_code=400,
            detail="New password must be at least 6 characters long"
        )

    # Hash and update new password
    hashed_new_password = get_password_hash(new_password)
    update_result = db_client[db.db_name]["user"].update_one(
        {"username": current_user.username},
        {
            "$set": {
                "password": hashed_new_password,
                "updated_at": datetime.utcnow()
            }
        }
    )

    if update_result.matched_count == 0:
        raise HTTPException(
            status_code=400,
            detail="Failed to update password"
        )

    # Invalidate all active sessions for security
    db_client[db.db_name]["active_sessions"].delete_many({"username": current_user.username})

    return JSONResponse(
        content={"message": "Password changed successfully. Please log in again."},
        status_code=200
    )


@route2.delete("/users/{username}", tags=["User Management"])
async def delete_user(
    username: str,
    permanent: bool = False,
    current_user: User = Depends(get_current_user),
    db_client: MongoClient = Depends(db.get_client)
):
    """Delete user (soft delete by default, hard delete if permanent=True)"""
    # Only admin can delete users
    if current_user.role != "admin":
        raise HTTPException(
            status_code=403,
            detail="You do not have permission to delete users"
        )

    # Find the user to delete
    user_from_db = db_client[db.db_name]["user"].find_one({"username": username})
    if not user_from_db:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )

    # Prevent admin from deleting themselves
    if username == current_user.username:
        raise HTTPException(
            status_code=400,
            detail="You cannot delete your own account"
        )

    # Remove all active sessions
    db_client[db.db_name]["active_sessions"].delete_many({"username": username})

    if permanent:
        # Hard delete - remove from database completely
        delete_result = db_client[db.db_name]["user"].delete_one({"username": username})
        
        if delete_result.deleted_count == 0:
            raise HTTPException(
                status_code=400,
                detail="Failed to delete user"
            )

        # Also delete related data
        db_client[db.db_name]["user_details"].delete_many({"username": username})
        db_client[db.db_name]["biodata_profiles"].delete_many({"user_id": username})
        db_client[db.db_name]["password_resets"].delete_many({"email": user_from_db.get("email")})

        return JSONResponse(
            content={"message": f"User '{username}' permanently deleted"},
            status_code=200
        )
    else:
        # Soft delete - mark as inactive and add deletion timestamp
        update_result = db_client[db.db_name]["user"].update_one(
            {"username": username},
            {
                "$set": {
                    "is_active": False,
                    "deleted_at": datetime.utcnow(),
                    "deleted_by": current_user.username,
                    "updated_at": datetime.utcnow()
                }
            }
        )

        if update_result.matched_count == 0:
            raise HTTPException(
                status_code=400,
                detail="Failed to delete user"
            )

        return JSONResponse(
            content={"message": f"User '{username}' soft deleted (deactivated)"},
            status_code=200
        )


@route2.post("/users/{username}/restore", tags=["User Management"])
async def restore_user(
    username: str,
    current_user: User = Depends(get_current_user),
    db_client: MongoClient = Depends(db.get_client)
):
    """Restore soft-deleted user (admin only)"""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=403,
            detail="You do not have permission to restore users"
        )

    # Find the soft-deleted user
    user_from_db = db_client[db.db_name]["user"].find_one({
        "username": username,
        "deleted_at": {"$exists": True}
    })
    
    if not user_from_db:
        raise HTTPException(
            status_code=404,
            detail="Deleted user not found"
        )

    # Restore the user
    update_result = db_client[db.db_name]["user"].update_one(
        {"username": username},
        {
            "$set": {
                "is_active": True,
                "restored_at": datetime.utcnow(),
                "restored_by": current_user.username,
                "updated_at": datetime.utcnow()
            },
            "$unset": {
                "deleted_at": "",
                "deleted_by": ""
            }
        }
    )

    if update_result.matched_count == 0:
        raise HTTPException(
            status_code=400,
            detail="Failed to restore user"
        )

    return JSONResponse(
        content={"message": f"User '{username}' restored successfully"},
        status_code=200
    )


@route2.get("/users/deleted", response_model=List[User], tags=["User Management"])
async def get_deleted_users(
    current_user: User = Depends(get_current_user),
    db_client: MongoClient = Depends(db.get_client)
):
    """Get list of soft-deleted users (admin only)"""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=403,
            detail="You do not have permission to view deleted users"
        )

    # Find all soft-deleted users
    deleted_users = list(db_client[db.db_name]["user"].find(
        {"deleted_at": {"$exists": True}},
        {"password": 0}  # Exclude password field
    ))

    # Convert ObjectId to string
    for user in deleted_users:
        user["_id"] = str(user["_id"])

    return deleted_users


@route2.put("/users/details", response_model=UserDetails, tags=["User Details"])
async def add_or_update_user_details(
    user_details: UserDetails, 
    current_user: User = Depends(get_current_user), 
    db_client: MongoClient = Depends(db.get_client)
):
    # Reference to the collection
    user_details_collection = db_client[db.db_name]["user_details"]

    # Convert user details to dictionary
    user_details_dict = user_details.dict()

    # Ensure username and other fixed fields remain unchanged
    user_details_dict["username"] = current_user.username
    user_details_dict["first_name"] = current_user.first_name
    user_details_dict["last_name"] = current_user.last_name
    user_details_dict["email"] = current_user.email
    user_details_dict["role"] = current_user.role
    user_details_dict["city"] = current_user.city

    # Update existing document if found, otherwise insert a new one
    result = user_details_collection.update_one(
        {"username": current_user.username},  # Filter criteria
        {"$set": user_details_dict},  # Data to update
        upsert=True  # Create new if not exists
    )

    # Retrieve the updated/inserted document
    updated_user_details = user_details_collection.find_one({"username": current_user.username})
    updated_user_details["_id"] = str(updated_user_details["_id"])  # Convert ObjectId to string

    return JSONResponse(content=updated_user_details, status_code=200)


@route2.get("/users/details", response_model=UserDetails, tags=["User Details"])
async def get_user_details(
    current_user: User = Depends(get_current_user),
    db_client: MongoClient = Depends(db.get_client)
):
    if current_user is None:
        raise HTTPException(status_code=401, detail="User is not logged in")
    
    # Fetch user details from the database
    user_details = db_client[db.db_name]["user_details"].find_one({"username": current_user.username})

    if not user_details:
        raise HTTPException(status_code=404, detail="User details not found")

    # Convert MongoDB ObjectId to string if needed
    user_details["_id"] = str(user_details["_id"]) if "_id" in user_details else None

    # Ensure all required fields are present
    required_fields = [
        "username", "father_name", "mother_name", "mobile_number", "college_name",
        "course", "branch", "year_of_passing", "date_of_birth", "first_name",
        "last_name", "email", "role", "city"
    ]
    
    # Fill missing fields with None (or default values)
    for field in required_fields:
        if field not in user_details:
            user_details[field] = None  

    return user_details

    

@route2.get("/active-sessions", tags=["User Management"])
async def get_active_sessions(
    current_user: User = Depends(get_current_user),
    db_client: MongoClient = Depends(db.get_client)
):
    # Only admin can view active sessions
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Permission denied")

    active_sessions = list(db_client[db.db_name]["active_sessions"].find({}, {"_id": 0}))
    return {"active_users": active_sessions}


@route2.post("/logout", tags=["Login & Authentication"])
async def logout(
    token: str,
    db_client: MongoClient = Depends(db.get_client)
):
    session = db_client[db.db_name]["active_sessions"].find_one({"token": token})

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    db_client[db.db_name]["active_sessions"].delete_one({"token": token})

    return {"message": "Successfully logged out"}




@route2.post("/password-reset/request", tags=["Password Reset"])
async def request_password_reset(request: Request, db_client: MongoClient = Depends(db.get_client)):
    # Accept email from JSON body
    body = await request.json()
    email = body.get("email")
    
    if not email:
        raise HTTPException(status_code=400, detail="Email is required")
    
    user_from_db = db_client[db.db_name]["user"].find_one({"email": email})
    
    if not user_from_db:
        raise HTTPException(status_code=404, detail="User with this email not found")

    # Generate reset token
    reset_token = jwt.encode(
        {"email": email, "exp": datetime.utcnow() + timedelta(minutes=RESET_TOKEN_EXPIRY_MINUTES)},
        RESET_SECRET_KEY,
        algorithm="HS256"
    )

    # Store reset token in DB
    db_client[db.db_name]["password_resets"].insert_one(
        {"email": email, "token": reset_token, "expires_at": datetime.utcnow() + timedelta(minutes=RESET_TOKEN_EXPIRY_MINUTES)}
    )

    print(f"Generated Token: {reset_token}")

    # Send email with reset link
    reset_link = f"https://projectdevops.in/reset-password?token={reset_token}"
    await send_password_reset_email(email, reset_link)

    return JSONResponse(content={"message": "Password reset email sent"}, status_code=200)


from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

@route2.post("/password-reset/confirm", tags=["Password Reset"])
async def reset_password(token: str, new_password: str, db_client: MongoClient = Depends(db.get_client)):
    try:
        # Decode token
        payload = jwt.decode(token, RESET_SECRET_KEY, algorithms=["HS256"])
        email = payload.get("email")

        if not email:
            raise HTTPException(status_code=400, detail="Invalid token")

        # Check if token exists in DB
        token_entry = db_client[db.db_name]["password_resets"].find_one({"email": email, "token": token})
        if not token_entry:
            raise HTTPException(status_code=400, detail="Invalid or expired token")

        # Hash new password
        hashed_password = pwd_context.hash(new_password)

        # Update user password
        db_client[db.db_name]["user"].update_one({"email": email}, {"$set": {"password": hashed_password}})

        token_entry = db_client[db.db_name]["password_resets"].find_one({"email": email})
        print(f"Stored Token: {token_entry['token']}")


        # Delete the used token
        db_client[db.db_name]["password_resets"].delete_one({"email": email})

        return JSONResponse(content={"message": "Password reset successful"}, status_code=200)

    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=400, detail="Token has expired")
    except jwt.PyJWTError:
        raise HTTPException(status_code=400, detail="Invalid token")


@route2.patch("/users/profile", response_model=User, tags=["User Profile"])
async def update_user_profile(
    profile_update: UserProfileUpdate,
    current_user: User = Depends(get_current_user),
    db_client: MongoClient = Depends(db.get_client)
):
    """Update current user's profile information"""
    
    # Prepare update data - only include non-None fields
    update_data = {}
    
    for field, value in profile_update.model_dump(exclude_unset=True).items():
        if value is not None:
            # Special handling for email uniqueness
            if field == "email" and value != current_user.email:
                existing_user = db_client[db.db_name]["user"].find_one({"email": value})
                if existing_user and existing_user["username"] != current_user.username:
                    raise HTTPException(
                        status_code=400,
                        detail="Email is already registered to another user"
                    )
            
            update_data[field] = value
    
    # If no fields to update, return current user
    if not update_data:
        raise HTTPException(
            status_code=400,
            detail="No valid fields provided for update"
        )
    
    # Add updated timestamp
    update_data["updated_at"] = datetime.utcnow()
    
    # Perform the update
    update_result = db_client[db.db_name]["user"].update_one(
        {"username": current_user.username},
        {"$set": update_data}
    )
    
    if update_result.matched_count == 0:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )
    
    # Fetch and return updated user
    updated_user = db_client[db.db_name]["user"].find_one({"username": current_user.username})
    if not updated_user:
        raise HTTPException(status_code=404, detail="User not found after update")
    
    # Convert ObjectId to string and remove password from response
    updated_user["_id"] = str(updated_user["_id"])
    updated_user.pop("password", None)  # Remove password from response
    
    # 🔧 FIX: Convert datetime objects to ISO format strings for JSON serialization
    if "created_at" in updated_user and updated_user["created_at"]:
        updated_user["created_at"] = updated_user["created_at"].isoformat()
    if "updated_at" in updated_user and updated_user["updated_at"]:
        updated_user["updated_at"] = updated_user["updated_at"].isoformat()
    
    return JSONResponse(
        content={
            "message": "Profile updated successfully",
            "user": updated_user
        },
        status_code=200
    )


@route2.get("/users/profile", response_model=User, tags=["User Profile"])
async def get_user_profile(
    current_user: User = Depends(get_current_user),
    db_client: MongoClient = Depends(db.get_client)
):
    """Get current user's complete profile information"""
    
    # Fetch user from database to get latest data including new fields
    user_from_db = db_client[db.db_name]["user"].find_one({"username": current_user.username})
    
    if not user_from_db:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Convert ObjectId to string and remove password
    user_from_db["_id"] = str(user_from_db["_id"])
    user_from_db.pop("password", None)
    
    return user_from_db


@route2.post("/users/profile/upload-picture", tags=["User Profile"])
async def upload_profile_picture(
    profile_picture: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db_client: MongoClient = Depends(db.get_client)
):
    """Upload user profile picture to S3 and update user profile"""
    
    # Validate file type
    allowed_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp']
    file_extension = '.' + profile_picture.filename.split('.')[-1].lower()
    
    if file_extension not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail="Only JPG, JPEG, PNG, GIF, and WebP image files are allowed"
        )
    
    # Validate file size (max 5MB)
    max_file_size = 5 * 1024 * 1024  # 5MB in bytes
    file_content = await profile_picture.read()
    
    if len(file_content) > max_file_size:
        raise HTTPException(
            status_code=400,
            detail="File size too large. Maximum allowed size is 5MB"
        )
    
    try:
        # Generate unique filename
        unique_filename = f"profile-pictures/{current_user.username}_{uuid.uuid4()}{file_extension}"
        
        # Upload to S3
        s3_client.put_object(
            Bucket=AWS_BUCKET_NAME,
            Key=unique_filename,
            Body=file_content,
            ContentType=f"image/{file_extension[1:]}",
            CacheControl="max-age=31536000",  # Cache for 1 year
            ACL="public-read"  # Make image publicly accessible
        )
        
        # Generate S3 URL
        profile_picture_url = f"https://{AWS_BUCKET_NAME}.s3.{AWS_REGION}.amazonaws.com/{unique_filename}"
        
        # Get current user's old profile picture URL to delete later
        user_from_db = db_client[db.db_name]["user"].find_one({"username": current_user.username})
        old_profile_picture_url = user_from_db.get("profile_picture_url")
        
        # Update user profile with new picture URL
        update_result = db_client[db.db_name]["user"].update_one(
            {"username": current_user.username},
            {
                "$set": {
                    "profile_picture_url": profile_picture_url,
                    "updated_at": datetime.utcnow()
                }
            }
        )
        
        if update_result.matched_count == 0:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Delete old profile picture from S3 (if exists and not default)
        if old_profile_picture_url and "profile-pictures/" in old_profile_picture_url:
            try:
                old_key = old_profile_picture_url.split(f"{AWS_BUCKET_NAME}.s3.{AWS_REGION}.amazonaws.com/")[1]
                s3_client.delete_object(Bucket=AWS_BUCKET_NAME, Key=old_key)
                logger.info(f"Deleted old profile picture: {old_key}")
            except Exception as e:
                logger.warning(f"Failed to delete old profile picture: {e}")
        
        return JSONResponse(
            content={
                "message": "Profile picture uploaded successfully",
                "profile_picture_url": profile_picture_url
            },
            status_code=200
        )
        
    except ClientError as e:
        logger.error(f"S3 upload error: {e}")
        raise HTTPException(status_code=500, detail="Failed to upload profile picture")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise HTTPException(status_code=500, detail="An unexpected error occurred")


@route2.delete("/users/profile/delete-picture", tags=["User Profile"])
async def delete_profile_picture(
    current_user: User = Depends(get_current_user),
    db_client: MongoClient = Depends(db.get_client)
):
    """Delete user's profile picture from S3 and update profile"""
    
    # Get current user's profile picture URL
    user_from_db = db_client[db.db_name]["user"].find_one({"username": current_user.username})
    if not user_from_db:
        raise HTTPException(status_code=404, detail="User not found")
    
    profile_picture_url = user_from_db.get("profile_picture_url")
    
    if not profile_picture_url:
        raise HTTPException(status_code=400, detail="No profile picture to delete")
    
    # Only delete if it's stored in our S3 bucket
    if "profile-pictures/" not in profile_picture_url:
        raise HTTPException(status_code=400, detail="Cannot delete external profile picture")
    
    try:
        # Extract S3 key from URL
        s3_key = profile_picture_url.split(f"{AWS_BUCKET_NAME}.s3.{AWS_REGION}.amazonaws.com/")[1]
        
        # Delete from S3
        s3_client.delete_object(Bucket=AWS_BUCKET_NAME, Key=s3_key)
        
        # Remove profile picture URL from user document
        update_result = db_client[db.db_name]["user"].update_one(
            {"username": current_user.username},
            {
                "$unset": {"profile_picture_url": ""},
                "$set": {"updated_at": datetime.utcnow()}
            }
        )
        
        if update_result.matched_count == 0:
            raise HTTPException(status_code=404, detail="User not found")
        
        return JSONResponse(
            content={"message": "Profile picture deleted successfully"},
            status_code=200
        )
        
    except ClientError as e:
        logger.error(f"S3 delete error: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete profile picture")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise HTTPException(status_code=500, detail="An unexpected error occurred")


@route2.post("/migrate-users", tags=["User Management"])
async def migrate_users(current_user: User = Depends(get_current_user), db_client: MongoClient = Depends(db.get_client)):
    # Ensure only admins can perform this migration
    if current_user.role != "admin":
        raise HTTPException(
            status_code=403,
            detail="You do not have permission to perform this operation"
        )

    users_collection = db_client[db.db_name]["user"]
    new_collection = db_client[db.db_name]["user_migrated"]  # New collection for migrated users

    users_without_created_at = users_collection.find({"created_at": {"$exists": False}})
    migrated_count = 0

    ist_timezone = pytz.timezone("Asia/Kolkata")

    for user in users_without_created_at:
        # Convert ObjectId timestamp (UTC) to IST
        utc_time = user["_id"].generation_time  # UTC time from ObjectId
        ist_time = utc_time.astimezone(ist_timezone)  # Convert to IST

        # Store created_at as a string in ISO format with IST timezone
        user["created_at"] = ist_time.strftime("%Y-%m-%d %H:%M:%S %z")  # Explicitly store IST time

        user["_id"] = str(user["_id"])  # Convert ObjectId to string

        # Insert into the new collection
        new_collection.insert_one(user)
        migrated_count += 1

    return {"message": f"Migration completed. {migrated_count} users migrated successfully!"}


# ==================== AUTHOR & MODERATOR MANAGEMENT ====================

@route2.get("/authors", tags=["Author Management"])
async def get_all_authors(db_client: MongoClient = Depends(db.get_client)):
    """Get all users with author role (public endpoint)"""
    users_collection = db_client[db.db_name]["user"]
    
    authors = list(users_collection.find(
        {"role": "author", "is_active": True},
        {"password": 0}  # Exclude password from results
    ))
    
    # Format author information
    author_list = []
    for author in authors:
        author_info = {
            "username": author["username"],
            "full_name": f"{author.get('first_name', '')} {author.get('last_name', '')}".strip(),
            "author_bio": author.get("author_bio"),
            "author_profile_image": author.get("author_profile_image"),
            "author_designation": author.get("author_designation"),
            "author_social_links": author.get("author_social_links"),
            "articles_count": author.get("articles_count", 0)
        }
        author_list.append(author_info)
    
    return author_list


@route2.get("/authors/{username}", tags=["Author Management"])
async def get_author_profile(username: str, db_client: MongoClient = Depends(db.get_client)):
    """Get specific author profile (public endpoint)"""
    users_collection = db_client[db.db_name]["user"]
    
    author = users_collection.find_one(
        {"username": username, "role": "author", "is_active": True},
        {"password": 0}
    )
    
    if not author:
        raise HTTPException(
            status_code=404,
            detail="Author not found"
        )
    
    # Get article count from news collection
    news_collection = db_client[db.db_name]["news"]
    article_count = news_collection.count_documents({"author_username": username, "published": True})
    
    return {
        "username": author["username"],
        "full_name": f"{author.get('first_name', '')} {author.get('last_name', '')}".strip(),
        "email": author.get("email"),
        "city": author.get("city"),
        "author_bio": author.get("author_bio"),
        "author_profile_image": author.get("author_profile_image"),
        "author_designation": author.get("author_designation"),
        "author_social_links": author.get("author_social_links"),
        "articles_count": article_count,
        "created_at": author.get("created_at")
    }


@route2.patch("/authors/{username}/profile", tags=["Author Management"])
async def update_author_profile(
    username: str,
    author_bio: Optional[str] = None,
    author_designation: Optional[str] = None,
    author_social_links: Optional[dict] = None,
    current_user: User = Depends(get_current_user),
    db_client: MongoClient = Depends(db.get_client)
):
    """Update author profile information (author themselves or admin)"""
    # Check permissions: must be the author themselves or an admin
    if current_user.username != username and current_user.role != "admin":
        raise HTTPException(
            status_code=403,
            detail="You do not have permission to update this author profile"
        )
    
    users_collection = db_client[db.db_name]["user"]
    
    # Verify user is an author
    author = users_collection.find_one({"username": username})
    if not author:
        raise HTTPException(status_code=404, detail="User not found")
    
    if author["role"] != "author":
        raise HTTPException(
            status_code=400,
            detail="User is not an author"
        )
    
    # Build update dictionary
    update_data = {"updated_at": datetime.utcnow()}
    if author_bio is not None:
        update_data["author_bio"] = author_bio
    if author_designation is not None:
        update_data["author_designation"] = author_designation
    if author_social_links is not None:
        update_data["author_social_links"] = author_social_links
    
    # Update author profile
    result = users_collection.update_one(
        {"username": username},
        {"$set": update_data}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=400, detail="Failed to update author profile")
    
    return JSONResponse(
        content={"message": "Author profile updated successfully"},
        status_code=200
    )


@route2.post("/authors/{username}/upload-profile-image", tags=["Author Management"])
async def upload_author_profile_image(
    username: str,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db_client: MongoClient = Depends(db.get_client)
):
    """Upload author profile image (author themselves or admin)"""
    # Check permissions
    if current_user.username != username and current_user.role != "admin":
        raise HTTPException(
            status_code=403,
            detail="You do not have permission to update this author profile image"
        )
    
    users_collection = db_client[db.db_name]["user"]
    
    # Verify user is an author
    author = users_collection.find_one({"username": username})
    if not author or author["role"] != "author":
        raise HTTPException(
            status_code=404,
            detail="Author not found"
        )
    
    # Validate file type
    allowed_types = ["image/jpeg", "image/png", "image/jpg", "image/webp"]
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail="Invalid file type. Only JPEG, PNG, and WebP images are allowed"
        )
    
    try:
        # Read file content
        file_content = await file.read()
        
        # Generate unique filename
        file_extension = file.filename.split(".")[-1]
        unique_filename = f"authors/{username}_profile_{uuid.uuid4()}.{file_extension}"
        
        # Upload to S3
        s3_client.put_object(
            Bucket=AWS_BUCKET_NAME,
            Key=unique_filename,
            Body=file_content,
            ContentType=file.content_type
        )
        
        # Generate public URL
        image_url = f"https://{AWS_BUCKET_NAME}.s3.{AWS_REGION}.amazonaws.com/{unique_filename}"
        
        # Update user profile
        users_collection.update_one(
            {"username": username},
            {
                "$set": {
                    "author_profile_image": image_url,
                    "updated_at": datetime.utcnow()
                }
            }
        )
        
        return {
            "message": "Author profile image uploaded successfully",
            "image_url": image_url
        }
        
    except ClientError as e:
        logger.error(f"S3 upload error: {e}")
        raise HTTPException(status_code=500, detail="Failed to upload image")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise HTTPException(status_code=500, detail="An unexpected error occurred")


@route2.get("/moderators", tags=["Moderator Management"])
async def get_all_moderators(
    current_user: User = Depends(get_current_user),
    db_client: MongoClient = Depends(db.get_client)
):
    """Get all users with moderator role (admin only)"""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=403,
            detail="Only admins can view moderators"
        )
    
    users_collection = db_client[db.db_name]["user"]
    
    moderators = list(users_collection.find(
        {"role": "moderator"},
        {"password": 0}
    ))
    
    # Format moderator information
    moderator_list = []
    for mod in moderators:
        mod["_id"] = str(mod["_id"])
        moderator_list.append(mod)
    
    return moderator_list


@route2.get("/users/by-role/{role}", tags=["User Management"])
async def get_users_by_role(
    role: str,
    current_user: User = Depends(get_current_user),
    db_client: MongoClient = Depends(db.get_client)
):
    """Get all users with specific role (admin only)"""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=403,
            detail="Only admins can view users by role"
        )
    
    # Validate role
    valid_roles = ["user", "admin", "author", "vendor", "moderator"]
    if role not in valid_roles:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid role. Must be one of: {', '.join(valid_roles)}"
        )
    
    users_collection = db_client[db.db_name]["user"]
    
    users = list(users_collection.find(
        {"role": role},
        {"password": 0}
    ))
    
    # Format user information
    for user in users:
        user["_id"] = str(user["_id"])
    
    return {
        "role": role,
        "count": len(users),
        "users": users
    }