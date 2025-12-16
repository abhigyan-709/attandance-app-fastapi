from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query
from fastapi.responses import StreamingResponse
from pymongo import MongoClient, DESCENDING
from bson import ObjectId
from typing import Optional, List
import uuid
import random
import string
from datetime import datetime, date
import logging
import json
import qrcode
from io import BytesIO

from database import db
from routes.user import get_current_user
from models.user import User
from models.employee_mgmt import (
    CreateEmployeeRequest,
    UpdateEmployeeRequest,
    EmployeeResponse,
    EmployeeListResponse,
    EquipmentType,
    EmploymentArea,
    QRCodeResponse
)
from routes.config import s3_client, AWS_BUCKET_NAME, AWS_REGION

router = APIRouter()
logger = logging.getLogger(__name__)

EMPLOYEE_COLL = "employees"


# ==================== HELPER FUNCTIONS ====================

def get_admin_or_moderator(current_user: User = Depends(get_current_user)):
    """Admin or Moderator access required"""
    if current_user.role not in ["admin", "moderator"]:
        raise HTTPException(status_code=403, detail="Admin or Moderator access required")
    return current_user


def get_admin_only(current_user: User = Depends(get_current_user)):
    """Admin only access required"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user


def generate_employee_id(db_client: MongoClient) -> str:
    """
    Generate unique employee ID in format: GTNE-YYYY-XXX
    GTNE = Gobarsahi Times News Employee
    YYYY = Current year
    XXX = Sequential number
    """
    current_year = datetime.now().year
    prefix = f"GTNE-{current_year}-"
    
    # Find the highest number for current year
    last_employee = db_client[db.db_name][EMPLOYEE_COLL].find_one(
        {"employee_id": {"$regex": f"^{prefix}"}},
        sort=[("employee_id", DESCENDING)]
    )
    
    if last_employee and "employee_id" in last_employee:
        try:
            last_number = int(last_employee["employee_id"].split("-")[-1])
            next_number = last_number + 1
        except (ValueError, IndexError):
            next_number = 1
    else:
        next_number = 1
    
    return f"{prefix}{next_number:03d}"


def upload_file_to_s3(file: UploadFile, folder: str) -> str:
    """Upload file to S3 and return URL"""
    file_extension = (file.filename or "file").split(".")[-1]
    unique_filename = f"employees/{folder}/{uuid.uuid4()}.{file_extension}"
    
    try:
        s3_client.upload_fileobj(
            file.file,
            AWS_BUCKET_NAME,
            unique_filename,
            ExtraArgs={"ContentType": file.content_type or "application/octet-stream"},
        )
        file_url = f"https://{AWS_BUCKET_NAME}.s3.{AWS_REGION}.amazonaws.com/{unique_filename}"
        return file_url
    except Exception as e:
        logger.error(f"S3 upload failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"File upload failed: {str(e)}")


def normalize_employee(doc: dict) -> dict:
    """Normalize employee document for response"""
    if "_id" in doc:
        doc["_id"] = str(doc["_id"])
    return doc


def check_unique_fields(db_client: MongoClient, email: str, phone: str, aadhar: str, exclude_id: Optional[str] = None):
    """Check if email, phone, or aadhar already exists"""
    query = {
        "$or": [
            {"email": email},
            {"phone_number": phone},
            {"aadhar_number": aadhar}
        ]
    }
    
    if exclude_id:
        query["_id"] = {"$ne": ObjectId(exclude_id)}
    
    existing = db_client[db.db_name][EMPLOYEE_COLL].find_one(query)
    
    if existing:
        if existing.get("email") == email:
            raise HTTPException(status_code=400, detail="Email already exists")
        if existing.get("phone_number") == phone:
            raise HTTPException(status_code=400, detail="Phone number already exists")
        if existing.get("aadhar_number") == aadhar:
            raise HTTPException(status_code=400, detail="Aadhar number already exists")


# ==================== EMPLOYEE CRUD ENDPOINTS ====================

@router.post("/employees", response_model=EmployeeResponse, tags=["Employee Management"])
async def create_employee(
    name: str = Form(...),
    fathers_name: str = Form(...),
    mothers_name: str = Form(...),
    email: str = Form(...),
    phone_number: str = Form(...),
    district: str = Form(...),
    village: str = Form(...),
    pincode: str = Form(...),
    address: str = Form(...),
    aadhar_number: str = Form(...),
    position: str = Form(...),
    employment_area_type: EmploymentArea = Form(...),
    employment_area_location: Optional[str] = Form(None),
    employment_date: date = Form(...),
    equipment_alloted: str = Form("[]"),  # JSON array of equipment
    resume_pdf: UploadFile = File(...),
    passport_photo: UploadFile = File(...),
    aadhar_front: UploadFile = File(...),
    aadhar_back: UploadFile = File(...),
    current_user: User = Depends(get_admin_or_moderator),
    db_client: MongoClient = Depends(db.get_client),
):
    """Create new employee (Admin/Moderator)"""
    try:
        # Validate aadhar number format
        if not aadhar_number.isdigit() or len(aadhar_number) != 12:
            raise HTTPException(status_code=400, detail="Aadhar number must be 12 digits")
        
        # Validate pincode format
        if not pincode.isdigit() or len(pincode) != 6:
            raise HTTPException(status_code=400, detail="Pincode must be 6 digits")
        
        # Check unique fields
        check_unique_fields(db_client, email, phone_number, aadhar_number)
        
        # Parse equipment
        try:
            equipment_list = json.loads(equipment_alloted)
        except:
            equipment_list = []
        
        # Validate ground deployment location
        if employment_area_type == EmploymentArea.GROUND and not employment_area_location:
            raise HTTPException(status_code=400, detail="Location is required for ground deployment")
        
        # Upload files to S3
        logger.info(f"Uploading files for employee: {name}")
        resume_url = upload_file_to_s3(resume_pdf, "resumes")
        passport_url = upload_file_to_s3(passport_photo, "photos")
        aadhar_front_url = upload_file_to_s3(aadhar_front, "aadhar")
        aadhar_back_url = upload_file_to_s3(aadhar_back, "aadhar")
        
        # Generate unique employee ID
        employee_id = generate_employee_id(db_client)
        
        # Create employee document
        employee_doc = {
            "employee_id": employee_id,
            "name": name,
            "fathers_name": fathers_name,
            "mothers_name": mothers_name,
            "email": email,
            "phone_number": phone_number,
            "district": district,
            "village": village,
            "pincode": pincode,
            "address": address,
            "aadhar_number": aadhar_number,
            "resume_url": resume_url,
            "passport_photo_url": passport_url,
            "aadhar_front_url": aadhar_front_url,
            "aadhar_back_url": aadhar_back_url,
            "position": position,
            "employment_area_type": employment_area_type.value,
            "employment_area_location": employment_area_location,
            "employment_date": employment_date.isoformat(),
            "date_of_leaving": None,
            "equipment_alloted": equipment_list,
            "qr_code_url": None,
            "is_active": True,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "created_by": current_user.username
        }
        
        # Insert into database
        result = db_client[db.db_name][EMPLOYEE_COLL].insert_one(employee_doc)
        employee_doc["_id"] = str(result.inserted_id)
        
        logger.info(f"Employee created: {employee_id} by {current_user.username}")
        return normalize_employee(employee_doc)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create employee: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to create employee: {str(e)}")


@router.get("/employees", response_model=EmployeeListResponse, tags=["Employee Management"])
async def get_all_employees(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    is_active: Optional[bool] = Query(None),
    district: Optional[str] = Query(None),
    position: Optional[str] = Query(None),
    employment_area_type: Optional[EmploymentArea] = Query(None),
    current_user: User = Depends(get_admin_or_moderator),
    db_client: MongoClient = Depends(db.get_client),
):
    """Get all employees with pagination and filters (Admin/Moderator)"""
    try:
        # Build filter query
        filter_query = {}
        if is_active is not None:
            filter_query["is_active"] = is_active
        if district:
            filter_query["district"] = {"$regex": district, "$options": "i"}
        if position:
            filter_query["position"] = {"$regex": position, "$options": "i"}
        if employment_area_type:
            filter_query["employment_area_type"] = employment_area_type.value
        
        # Get total count
        total = db_client[db.db_name][EMPLOYEE_COLL].count_documents(filter_query)
        
        # Get paginated results
        skip = (page - 1) * limit
        employees = list(
            db_client[db.db_name][EMPLOYEE_COLL]
            .find(filter_query)
            .sort("created_at", DESCENDING)
            .skip(skip)
            .limit(limit)
        )
        
        return {
            "employees": [normalize_employee(emp) for emp in employees],
            "total": total,
            "page": page,
            "limit": limit,
            "total_pages": (total + limit - 1) // limit
        }
        
    except Exception as e:
        logger.error(f"Failed to fetch employees: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch employees")


@router.get("/employees/{employee_id}", response_model=EmployeeResponse, tags=["Employee Management"])
async def get_employee_by_id(
    employee_id: str,
    current_user: User = Depends(get_admin_or_moderator),
    db_client: MongoClient = Depends(db.get_client),
):
    """Get employee by ID (Admin/Moderator)"""
    if not ObjectId.is_valid(employee_id):
        raise HTTPException(status_code=404, detail="Employee not found")
    
    try:
        employee = db_client[db.db_name][EMPLOYEE_COLL].find_one({"_id": ObjectId(employee_id)})
        
        if not employee:
            raise HTTPException(status_code=404, detail="Employee not found")
        
        return normalize_employee(employee)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch employee: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch employee")


@router.get("/employees/search/by-employee-id/{emp_id}", response_model=EmployeeResponse, tags=["Employee Management"])
async def get_employee_by_employee_id(
    emp_id: str,
    current_user: User = Depends(get_admin_or_moderator),
    db_client: MongoClient = Depends(db.get_client),
):
    """Get employee by employee ID (e.g., GTNE-2024-001)"""
    try:
        employee = db_client[db.db_name][EMPLOYEE_COLL].find_one({"employee_id": emp_id})
        
        if not employee:
            raise HTTPException(status_code=404, detail=f"Employee {emp_id} not found")
        
        return normalize_employee(employee)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch employee: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch employee")


@router.put("/employees/{employee_id}", response_model=EmployeeResponse, tags=["Employee Management"])
async def update_employee(
    employee_id: str,
    name: Optional[str] = Form(None),
    fathers_name: Optional[str] = Form(None),
    mothers_name: Optional[str] = Form(None),
    email: Optional[str] = Form(None),
    phone_number: Optional[str] = Form(None),
    district: Optional[str] = Form(None),
    village: Optional[str] = Form(None),
    pincode: Optional[str] = Form(None),
    address: Optional[str] = Form(None),
    aadhar_number: Optional[str] = Form(None),
    position: Optional[str] = Form(None),
    employment_area_type: Optional[EmploymentArea] = Form(None),
    employment_area_location: Optional[str] = Form(None),
    employment_date: Optional[date] = Form(None),
    date_of_leaving: Optional[date] = Form(None),
    equipment_alloted: Optional[str] = Form(None),
    resume_pdf: Optional[UploadFile] = File(None),
    passport_photo: Optional[UploadFile] = File(None),
    aadhar_front: Optional[UploadFile] = File(None),
    aadhar_back: Optional[UploadFile] = File(None),
    is_active: Optional[bool] = Form(None),
    current_user: User = Depends(get_admin_or_moderator),
    db_client: MongoClient = Depends(db.get_client),
):
    """Update employee (Admin/Moderator)"""
    if not ObjectId.is_valid(employee_id):
        raise HTTPException(status_code=404, detail="Employee not found")
    
    try:
        # Get existing employee
        existing = db_client[db.db_name][EMPLOYEE_COLL].find_one({"_id": ObjectId(employee_id)})
        if not existing:
            raise HTTPException(status_code=404, detail="Employee not found")
        
        # Build update document
        update_data = {}
        
        if name:
            update_data["name"] = name
        if fathers_name:
            update_data["fathers_name"] = fathers_name
        if mothers_name:
            update_data["mothers_name"] = mothers_name
        if email:
            check_unique_fields(db_client, email, existing["phone_number"], existing["aadhar_number"], employee_id)
            update_data["email"] = email
        if phone_number:
            check_unique_fields(db_client, existing["email"], phone_number, existing["aadhar_number"], employee_id)
            update_data["phone_number"] = phone_number
        if aadhar_number:
            if not aadhar_number.isdigit() or len(aadhar_number) != 12:
                raise HTTPException(status_code=400, detail="Aadhar number must be 12 digits")
            check_unique_fields(db_client, existing["email"], existing["phone_number"], aadhar_number, employee_id)
            update_data["aadhar_number"] = aadhar_number
        if district:
            update_data["district"] = district
        if village:
            update_data["village"] = village
        if pincode:
            if not pincode.isdigit() or len(pincode) != 6:
                raise HTTPException(status_code=400, detail="Pincode must be 6 digits")
            update_data["pincode"] = pincode
        if address:
            update_data["address"] = address
        if position:
            update_data["position"] = position
        if employment_area_type:
            update_data["employment_area_type"] = employment_area_type.value
        if employment_area_location:
            update_data["employment_area_location"] = employment_area_location
        if employment_date:
            update_data["employment_date"] = employment_date.isoformat()
        if date_of_leaving:
            update_data["date_of_leaving"] = date_of_leaving.isoformat()
            update_data["is_active"] = False  # Mark as inactive
        if equipment_alloted:
            try:
                equipment_list = json.loads(equipment_alloted)
                update_data["equipment_alloted"] = equipment_list
            except:
                pass
        if is_active is not None:
            update_data["is_active"] = is_active
        
        # Upload new files if provided
        if resume_pdf:
            update_data["resume_url"] = upload_file_to_s3(resume_pdf, "resumes")
        if passport_photo:
            update_data["passport_photo_url"] = upload_file_to_s3(passport_photo, "photos")
        if aadhar_front:
            update_data["aadhar_front_url"] = upload_file_to_s3(aadhar_front, "aadhar")
        if aadhar_back:
            update_data["aadhar_back_url"] = upload_file_to_s3(aadhar_back, "aadhar")
        
        update_data["updated_at"] = datetime.utcnow()
        
        # Update employee
        db_client[db.db_name][EMPLOYEE_COLL].update_one(
            {"_id": ObjectId(employee_id)},
            {"$set": update_data}
        )
        
        # Get updated employee
        updated = db_client[db.db_name][EMPLOYEE_COLL].find_one({"_id": ObjectId(employee_id)})
        
        logger.info(f"Employee {existing['employee_id']} updated by {current_user.username}")
        return normalize_employee(updated)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update employee: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to update employee: {str(e)}")


@router.delete("/employees/{employee_id}", tags=["Employee Management"])
async def delete_employee(
    employee_id: str,
    current_user: User = Depends(get_admin_only),  # Only admin can delete
    db_client: MongoClient = Depends(db.get_client),
):
    """Delete employee (Admin only)"""
    if not ObjectId.is_valid(employee_id):
        raise HTTPException(status_code=404, detail="Employee not found")
    
    try:
        employee = db_client[db.db_name][EMPLOYEE_COLL].find_one({"_id": ObjectId(employee_id)})
        
        if not employee:
            raise HTTPException(status_code=404, detail="Employee not found")
        
        # Delete employee
        db_client[db.db_name][EMPLOYEE_COLL].delete_one({"_id": ObjectId(employee_id)})
        
        logger.info(f"Employee {employee['employee_id']} deleted by {current_user.username}")
        return {"message": f"Employee {employee['employee_id']} deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete employee: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to delete employee")


# ==================== QR CODE GENERATION ====================

@router.post("/employees/{employee_id}/generate-qr", response_model=QRCodeResponse, tags=["Employee Management"])
async def generate_employee_qr_code(
    employee_id: str,
    current_user: User = Depends(get_admin_or_moderator),
    db_client: MongoClient = Depends(db.get_client),
):
    """Generate QR code for employee eyecard"""
    if not ObjectId.is_valid(employee_id):
        raise HTTPException(status_code=404, detail="Employee not found")
    
    try:
        employee = db_client[db.db_name][EMPLOYEE_COLL].find_one({"_id": ObjectId(employee_id)})
        
        if not employee:
            raise HTTPException(status_code=404, detail="Employee not found")
        
        # Prepare QR code data
        qr_data = {
            "employee_id": employee["employee_id"],
            "name": employee["name"],
            "position": employee["position"],
            "phone": employee["phone_number"],
            "email": employee["email"],
            "employment_area": employee["employment_area_type"],
            "photo_url": employee.get("passport_photo_url", "")
        }
        
        qr_data_json = json.dumps(qr_data)
        
        # Generate QR code
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(qr_data_json)
        qr.make(fit=True)
        
        # Create QR code image
        qr_image = qr.make_image(fill_color="black", back_color="white")
        
        # Save to BytesIO
        img_buffer = BytesIO()
        qr_image.save(img_buffer, format="PNG")
        img_buffer.seek(0)
        
        # Upload to S3
        qr_filename = f"employees/qrcodes/{employee['employee_id']}.png"
        s3_client.upload_fileobj(
            img_buffer,
            AWS_BUCKET_NAME,
            qr_filename,
            ExtraArgs={"ContentType": "image/png"},
        )
        
        qr_url = f"https://{AWS_BUCKET_NAME}.s3.{AWS_REGION}.amazonaws.com/{qr_filename}"
        
        # Update employee with QR code URL
        db_client[db.db_name][EMPLOYEE_COLL].update_one(
            {"_id": ObjectId(employee_id)},
            {"$set": {"qr_code_url": qr_url, "updated_at": datetime.utcnow()}}
        )
        
        logger.info(f"QR code generated for employee {employee['employee_id']}")
        
        return {
            "employee_id": employee["employee_id"],
            "qr_code_url": qr_url,
            "qr_code_data": qr_data_json,
            "generated_at": datetime.utcnow()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to generate QR code: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to generate QR code: {str(e)}")


@router.get("/employees/{employee_id}/qr-code", tags=["Employee Management"])
async def get_employee_qr_code(
    employee_id: str,
    current_user: User = Depends(get_admin_or_moderator),
    db_client: MongoClient = Depends(db.get_client),
):
    """Get QR code image for employee"""
    if not ObjectId.is_valid(employee_id):
        raise HTTPException(status_code=404, detail="Employee not found")
    
    try:
        employee = db_client[db.db_name][EMPLOYEE_COLL].find_one({"_id": ObjectId(employee_id)})
        
        if not employee:
            raise HTTPException(status_code=404, detail="Employee not found")
        
        if not employee.get("qr_code_url"):
            raise HTTPException(status_code=404, detail="QR code not generated yet. Please generate first.")
        
        return {"qr_code_url": employee["qr_code_url"]}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get QR code: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get QR code")


# ==================== STATISTICS & REPORTS ====================

@router.get("/employees/stats/overview", tags=["Employee Management"])
async def get_employee_statistics(
    current_user: User = Depends(get_admin_or_moderator),
    db_client: MongoClient = Depends(db.get_client),
):
    """Get employee statistics overview"""
    try:
        total = db_client[db.db_name][EMPLOYEE_COLL].count_documents({})
        active = db_client[db.db_name][EMPLOYEE_COLL].count_documents({"is_active": True})
        inactive = total - active
        
        # Count by employment area
        ground = db_client[db.db_name][EMPLOYEE_COLL].count_documents({"employment_area_type": "ground"})
        remote = db_client[db.db_name][EMPLOYEE_COLL].count_documents({"employment_area_type": "remote"})
        office = db_client[db.db_name][EMPLOYEE_COLL].count_documents({"employment_area_type": "office"})
        
        return {
            "total_employees": total,
            "active_employees": active,
            "inactive_employees": inactive,
            "by_area": {
                "ground": ground,
                "remote": remote,
                "office": office
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to get statistics: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get statistics")
