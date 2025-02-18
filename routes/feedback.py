from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from pymongo import MongoClient
from datetime import datetime
from pydantic import BaseModel, EmailStr
from typing import Optional
from models.feedback import Feedback
from database.db import db

# 🚀 FastAPI Router
router18 = APIRouter()

# 📌 Feedback Route
@router18.post("/submit-feedback", tags=["Feedback"])
async def submit_feedback(feedback: Feedback, db_client: MongoClient = Depends(db.get_client)):
    user_collection = db_client[db.db_name]["user"]
    feedback_collection = db_client[db.db_name]["feedback"]

    # 🔍 Check if the user exists
    user = user_collection.find_one({"username": feedback.username})
    if not user:
        raise HTTPException(status_code=404, detail="User does not exist. Please register.")

    today_date = datetime.utcnow().strftime("%Y-%m-%d")

    # 🔍 Check if feedback is already submitted for today
    existing_feedback = feedback_collection.find_one(
        {"username": feedback.username, "feedback_days.date": today_date}
    )

    if existing_feedback:
        raise HTTPException(status_code=400, detail="Feedback already submitted for today")

    # ✅ Insert feedback for today
    feedback_collection.update_one(
        {"username": feedback.username},
        {
            "$push": {
                "feedback_days": {
                    "date": today_date,
                    "message": feedback.message,
                    "rating": feedback.rating,
                    "timestamp": datetime.utcnow()
                }
            }
        },
        upsert=True  # Create document if not exists
    )

    return JSONResponse(content={"message": "Feedback submitted successfully"}, status_code=201)
