from fastapi import APIRouter, HTTPException, Depends
from database.db import db
from models.attendance import Attendance
from datetime import datetime
from routes.user_routes import get_current_user

router = APIRouter()

@router.post("/mark_attendance")
async def mark_attendance(username: str):
    user = db.users.find_one({"username": username})
    if not user or not user["activated"]:
        raise HTTPException(status_code=403, detail="User not activated")

    db.attendance.insert_one({"username": username, "timestamp": datetime.utcnow()})
    return {"message": "Attendance marked"}
