from fastapi import APIRouter, HTTPException, Depends
from models.attendance import Attendance
from database.db import db
from datetime import datetime
from fastapi.responses import JSONResponse
from routes.user import get_current_user
from models.user import User
from pymongo import MongoClient
from datetime import datetime

router7 = APIRouter()

# Route to mark attendance
@router7.post("/mark-attendance")
async def mark_attendance(attendance: Attendance):
    db_client = db.get_client()
    user_collection = db_client[db.db_name]["user"]  # Ensure correct collection name
    attendance_collection = db_client[db.db_name]["attendance"]

    # 🔍 Check if the user exists in the "user" collection
    user = user_collection.find_one({"username": attendance.username})
    
    if not user:
        raise HTTPException(status_code=404, detail="User does not exist. Please register.")

    # 🔍 Check if attendance is already marked for today
    today_date = datetime.utcnow().strftime("%Y-%m-%d")
    existing_attendance = attendance_collection.find_one({
        "username": attendance.username,
        "date": today_date
    })

    if existing_attendance:
        raise HTTPException(status_code=400, detail="Attendance already marked for today")

    # ✅ Insert attendance record
    attendance_record = {
        "username": attendance.username,
        "date": today_date,
        "timestamp": datetime.utcnow()
    }
    attendance_collection.insert_one(attendance_record)

    return JSONResponse(content={"message": "Attendance marked successfully"}, status_code=201)

# Route to check if attendance is marked for today
@router7.get("/check-attendance/{username}")
async def check_attendance(username: str):
    db_client = db.get_client()
    user_collection = db_client[db.db_name]["user"]  # Ensure correct collection name
    attendance_collection = db_client[db.db_name]["attendance"]

    # 🔍 Check if user exists
    user = user_collection.find_one({"username": username})
    
    if not user:
        raise HTTPException(status_code=404, detail="User does not exist. Please register.")

    # 🔍 Check if attendance is already marked for today
    today_date = datetime.utcnow().strftime("%Y-%m-%d")
    existing_attendance = attendance_collection.find_one({
        "username": username,
        "date": today_date
    })

    if existing_attendance:
        return JSONResponse(content={"marked": True, "message": "Attendance already marked"})
    
    return JSONResponse(content={"marked": False, "message": "Attendance not marked yet"})

@router7.get("/attendance")
async def get_all_attendance(current_user: User = Depends(get_current_user), db_client: MongoClient = Depends(db.get_client)):
    # Check if the current user is an admin
    if current_user.role != "admin":
        raise HTTPException(
            status_code=403,
            detail="You do not have permission to access this resource"
        )

    # Fetch all attendance records from the database
    attendance_from_db = db_client[db.db_name]["attendance"].find()

    # Convert attendance records from the database into a list and handle datetime serialization
    attendance_list = []
    for attendance_data in attendance_from_db:
        attendance_data["_id"] = str(attendance_data["_id"])  # Convert ObjectId to string
        # Convert datetime fields to string (ISO format)
        if "timestamp" in attendance_data:
            attendance_data["timestamp"] = attendance_data["timestamp"].isoformat()  # or str(attendance_data["timestamp"])
        attendance_list.append(attendance_data)

    return JSONResponse(content=attendance_list, status_code=200)





