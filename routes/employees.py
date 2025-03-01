import uuid
import boto3
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from pymongo import MongoClient
from datetime import datetime
from typing import Optional
from database.db import db
from models.employees import Employees
from models.user import User
from routes.config import AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_REGION
from routes.user import get_current_user

route5 = APIRouter()

# ✅ Initialize S3 Client
s3_client = boto3.client(
    "s3",
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    region_name=AWS_REGION,
)

EMPLOYEE_BUCKET = "projectdevops-employeed"

# ✅ Check if user is admin
async def is_admin(current_user: User = Depends(get_current_user)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only admins can perform this action")
    return current_user

# ✅ Upload file to S3
async def upload_to_s3(upload_file: Optional[UploadFile], prefix: str):
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

# ✅ API to add an employee with file uploads
@route5.post("/add-employee", tags=["Employees"])
async def add_employee(
    username: str = Form(...),
    password: str = Form(...),
    first_name: str = Form(...),
    last_name: str = Form(...),
    mobile_number: str = Form(...),
    personal_email: str = Form(...),
    official_email: Optional[str] = Form(None),
    designation: str = Form(...),
    department: str = Form(...),
    employment_type: str = Form(...),
    date_of_joining: datetime = Form(...),
    date_of_birth: datetime = Form(...),
    city: str = Form(...),
    state: str = Form(...),
    country: str = Form(...),
    aadhar_number: str = Form(...),
    pan_number: str = Form(...),
    current_ctc: float = Form(...),
    previous_ctc: Optional[float] = Form(None),
    previous_employer: Optional[str] = Form(None),
    experience_years: Optional[int] = Form(0),
    reporting_manager: Optional[str] = Form(None),
    emergency_contact: Optional[str] = Form(None),
    address: Optional[str] = Form(None),

    # ✅ File Uploads
    photo: Optional[UploadFile] = File(None),
    aadhar_upload: Optional[UploadFile] = File(None),
    pan_upload: Optional[UploadFile] = File(None),
    previous_payslip_upload: Optional[UploadFile] = File(None),
    cv_upload: Optional[UploadFile] = File(None),

    db_client: MongoClient = Depends(db.get_client),
    admin: User = Depends(is_admin)  # Admin-only access
):
    """Admin can add new employees with document uploads to S3"""

    employee_data = {
        "username": username,
        "password": password,
        "first_name": first_name,
        "last_name": last_name,
        "mobile_number": mobile_number,
        "personal_email": personal_email,
        "official_email": official_email,
        "designation": designation,
        "department": department,
        "employment_type": employment_type,
        "date_of_joining": date_of_joining,
        "date_of_birth": date_of_birth,
        "city": city,
        "state": state,
        "country": country,
        "aadhar_number": aadhar_number,
        "pan_number": pan_number,
        "current_ctc": current_ctc,
        "previous_ctc": previous_ctc,
        "previous_employer": previous_employer,
        "experience_years": experience_years,
        "reporting_manager": reporting_manager,
        "emergency_contact": emergency_contact,
        "address": address,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }

    # ✅ Upload documents to S3
    employee_data["photo_url"] = await upload_to_s3(photo, "photo")
    employee_data["aadhar_url"] = await upload_to_s3(aadhar_upload, "aadhar")
    employee_data["pan_url"] = await upload_to_s3(pan_upload, "pan")
    employee_data["previous_payslip_url"] = await upload_to_s3(previous_payslip_upload, "payslip")
    employee_data["cv_url"] = await upload_to_s3(cv_upload, "cv")

    # ✅ Insert into MongoDB
    db_client[db.db_name]["employees"].insert_one(employee_data)

    return {"message": "Employee added successfully", "employee": employee_data}
