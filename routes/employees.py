import uuid
import boto3
import shutil
import os
import secrets
import jwt
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from typing import Optional
from pymongo import MongoClient
from datetime import datetime
from database.db import db
from models.employees import Employees
from models.user import User
from routes.config import AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_REGION

route3 = APIRouter()

# Secret Key for JWT
SECRET_KEY = secrets.token_urlsafe(32)
ALGORITHM = "HS256"

# Initialize S3 Client for Employee Documents
s3_client = boto3.client(
    "s3",
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    region_name=AWS_REGION,
)

EMPLOYEE_BUCKET = "projectdevops-employeed"

async def get_current_user(token: str = Depends()):
    """Validate JWT and get the current user."""
    credentials_exception = HTTPException(
        status_code=401,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception

        db_client = db.get_client()
        user_from_db = db_client[db.db_name]["user"].find_one({"username": username})
        if user_from_db is None:
            raise credentials_exception

        user = User(**user_from_db)
        return user
    except jwt.ExpiredSignatureError:
        raise credentials_exception
    except jwt.PyJWTError:
        raise credentials_exception

async def is_admin(current_user: User = Depends(get_current_user)):
    """Ensure only admin users can add employees."""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only admins can perform this action")
    return current_user

def upload_to_s3(upload_file: UploadFile, prefix: str):
    """Upload file to S3 and return the file URL"""
    if upload_file:
        unique_filename = f"{prefix}_{uuid.uuid4()}_{upload_file.filename}"
        try:
            s3_client.upload_fileobj(
                upload_file.file,
                EMPLOYEE_BUCKET,
                unique_filename,
                ExtraArgs={"ContentType": upload_file.content_type}
            )
            return f"https://{EMPLOYEE_BUCKET}.s3.{AWS_REGION}.amazonaws.com/{unique_filename}"
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"File upload failed: {str(e)}")
    return None

@route3.post("/add-employee", tags=["Employees"])
async def add_employee(
    employee: Employees,
    photo: Optional[UploadFile] = None,
    aadhar_upload: Optional[UploadFile] = None,
    pan_upload: Optional[UploadFile] = None,
    previous_payslip_upload: Optional[UploadFile] = None,
    cv_upload: Optional[UploadFile] = None,
    db_client: MongoClient = Depends(db.get_client),
    admin: User = Depends(is_admin)  # Admin-only access
):
    """Admin can add new employees with document uploads to S3"""

    employee_data = employee.dict()

    # Upload documents to S3 and store URLs
    employee_data["photo_url"] = upload_to_s3(photo, "photo")
    employee_data["aadhar_url"] = upload_to_s3(aadhar_upload, "aadhar")
    employee_data["pan_url"] = upload_to_s3(pan_upload, "pan")
    employee_data["previous_payslip_url"] = upload_to_s3(previous_payslip_upload, "payslip")
    employee_data["cv_url"] = upload_to_s3(cv_upload, "cv")

    # Insert into MongoDB
    employee_data["created_at"] = datetime.utcnow()
    employee_data["updated_at"] = datetime.utcnow()

    db_client[db.db_name]["employees"].insert_one(employee_data)
    
    return {"message": "Employee added successfully", "employee": employee_data}
