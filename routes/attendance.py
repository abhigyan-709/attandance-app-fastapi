from fastapi import APIRouter, HTTPException
from models.attendance import Attendance
from database.db import db
from datetime import datetime
from fastapi.responses import JSONResponse

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
