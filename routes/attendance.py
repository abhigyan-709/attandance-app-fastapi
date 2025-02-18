from fastapi import APIRouter, HTTPException, Depends
from models.attendance import Attendance
from database.db import db
from datetime import datetime
from fastapi.responses import JSONResponse
from routes.user import get_current_user
from models.user import User
from pymongo import MongoClient

router7 = APIRouter()

# Route to mark attendance
@router7.post("/mark-attendance")
async def mark_attendance(attendance: Attendance, db_client: MongoClient = Depends(db.get_client)):
    user_collection = db_client[db.db_name]["user"]
    attendance_collection = db_client[db.db_name]["attendance"]

    # 🔍 Check if the user exists
    user = user_collection.find_one({"username": attendance.username})
    
    if not user:
        raise HTTPException(status_code=404, detail="User does not exist. Please register.")

    today_date = datetime.utcnow().strftime("%Y-%m-%d")

    # 🔍 Check if attendance is already marked for today
    existing_attendance = attendance_collection.find_one(
        {"username": attendance.username, "attendance_days.date": today_date}
    )

    if existing_attendance:
        raise HTTPException(status_code=400, detail="Attendance already marked for today")

    # ✅ Update or insert attendance record
    attendance_collection.update_one(
        {"username": attendance.username},
        {
            "$push": {"attendance_days": {"date": today_date, "timestamp": datetime.utcnow()}}
        },
        upsert=True  # Create document if not exists
    )

    return JSONResponse(content={"message": "Attendance marked successfully"}, status_code=201)


@router7.get("/attendance/{username}", tags=["Attendance for USER Dashboard"])
async def get_attendance(
    username: str,
    db_client: MongoClient = Depends(db.get_client),
    current_user: User = Depends(get_current_user)  # Ensure only logged-in users can access
):
    attendance_collection = db_client[db.db_name]["attendance"]

    # 🔒 Restrict access to only the logged-in user or admin
    if current_user.username != username and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Access denied")

    # 🔍 Fetch user's attendance record
    attendance_record = attendance_collection.find_one({"username": username})

    if not attendance_record:
        return JSONResponse(content={
            "attendanceData": [],
            "totalDays": 0,
            "presentDays": 0,
            "attendancePercentage": 0
        }, status_code=200)

    # 📅 Generate attendance data (Last 7 days)
    from datetime import datetime, timedelta

    today = datetime.utcnow()
    attendanceData = []
    presentDays = 0

    for i in range(7):
        day = today - timedelta(days=6 - i)
        day_str = day.strftime("%Y-%m-%d")

        attended = any(record["date"] == day_str for record in attendance_record.get("attendance_days", []))

        attendanceData.append({
            "day": f"Day {i+1}",
            "attended": attended
        })

        if attended:
            presentDays += 1

    totalDays = len(attendanceData)
    attendancePercentage = (presentDays / totalDays) * 100 if totalDays > 0 else 0

    return JSONResponse(content={
        "attendanceData": attendanceData,
        "totalDays": totalDays,
        "presentDays": presentDays,
        "attendancePercentage": round(attendancePercentage, 2)
    }, status_code=200)




# Route to get all attendance records (Admin Only)
@router7.get("/attendance")
async def get_all_attendance(current_user: User = Depends(get_current_user), db_client: MongoClient = Depends(db.get_client)):
    if current_user.role != "admin":
        raise HTTPException(
            status_code=403,
            detail="You do not have permission to access this resource"
        )

    attendance_collection = db_client[db.db_name]["attendance"]

    # Fetch all attendance records
    attendance_from_db = attendance_collection.find()

    # Convert records to list and format response
    attendance_list = []
    for attendance_data in attendance_from_db:
        attendance_data["_id"] = str(attendance_data["_id"])  # Convert ObjectId to string
        for record in attendance_data["attendance_days"]:
            record["timestamp"] = record["timestamp"].isoformat()  # Format timestamp
        attendance_list.append(attendance_data)

    return JSONResponse(content=attendance_list, status_code=200)
