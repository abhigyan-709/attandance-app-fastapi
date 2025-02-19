from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from database.db import db
from bson import ObjectId
from models.quiz import QuizCreate, UserResponse
from models.user import User
from routes.user import get_current_user
from typing import List
import datetime
import json

router17 = APIRouter()

# Store active WebSocket connections
active_connections: List[WebSocket] = []

# WebSocket for real-time quiz notifications
@router17.websocket("/quiz-notifications")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    active_connections.append(websocket)
    print(f"New WebSocket connection: {websocket}")

    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        active_connections.remove(websocket)
        print("WebSocket disconnected")



# Admin creates a new quiz & notifies users
@router17.post("/create-quiz", tags=["Quiz"])
async def create_quiz(quiz_data: QuizCreate, current_user: User = Depends(get_current_user)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only admins can create quizzes.")

    db_client = db.get_client()
    
    quiz_doc = {
        "question": quiz_data.question,
        "options": quiz_data.options,
        "correct_answer": quiz_data.correct_answer,
        "time_limit": quiz_data.time_limit,
        "created_by": current_user.username,
        "created_at": datetime.datetime.utcnow(),
    }

    result = db_client[db.db_name]["quizzes"].insert_one(quiz_doc)
    quiz_id = str(result.inserted_id)

    # Send WebSocket notification to all users
    quiz_notification = {
        "type": "new_quiz",
        "quiz_id": quiz_id,
        "question": quiz_data.question,
        "options": quiz_data.options,
        "time_limit": quiz_data.time_limit
    }
    
    for connection in active_connections:
        await connection.send_json(quiz_notification)

    return {"message": "Quiz created successfully", "quiz_id": quiz_id}



# # User submits a quiz response
# @router17.post("/submit-quiz/{quiz_id}", tags=["Quiz"])
# async def submit_quiz(quiz_id: str, user_response: UserResponse, current_user: User = Depends(get_current_user)):
#     db_client = db.get_client()
    
#     # Validate quiz existence
#     quiz = db_client[db.db_name]["quizzes"].find_one({"_id": ObjectId(quiz_id)})
#     if not quiz:
#         raise HTTPException(status_code=404, detail="Quiz not found.")

#     # Ensure submitted_at is a valid datetime
#     submitted_time = user_response.submitted_at or datetime.utcnow()

#     # Store response in MongoDB
#     response_doc = {
#         "quiz_id": quiz_id,
#         "username": current_user.username,
#         "selected_option": user_response.selected_option,
#         "submitted_at": submitted_time  # Ensure it's stored as datetime
#     }
    
#     db_client[db.db_name]["quiz_responses"].insert_one(response_doc)

#     return {"message": "Quiz submitted successfully"}

import uuid
from database.db import cache  # Import the cache instance

@router17.post("/submit-quiz/{quiz_id}", tags=["Quiz"])
async def submit_quiz(quiz_id: str, user_response: UserResponse, current_user: User = Depends(get_current_user)):
    db_client = db.get_client()
    
    # Validate quiz existence
    quiz = db_client[db.db_name]["quizzes"].find_one({"_id": ObjectId(quiz_id)})
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found.")

    submitted_time = user_response.submitted_at or datetime.datetime.utcnow()

    # Generate a unique key for Redis caching
    response_key = f"quiz_response:{quiz_id}:{current_user.username}:{uuid.uuid4()}"

    response_data = {
        "quiz_id": quiz_id,
        "username": current_user.username,
        "selected_option": user_response.selected_option,
        "submitted_at": submitted_time.isoformat()  # Store as string in Redis
    }

    # ✅ Store response in MongoDB immediately
    db_client[db.db_name]["quiz_responses"].insert_one({
        "quiz_id": quiz_id,
        "username": current_user.username,
        "selected_option": user_response.selected_option,
        "submitted_at": submitted_time
    })

    # ✅ Also cache response in Redis (expires in 5 mins)
    cache.set(response_key, json.dumps(response_data), expire=300)

    return {"message": "Quiz response stored in MongoDB and cached in Redis."}




from fastapi import Query

from fastapi import Query
import pytz

@router17.get("/quiz-attempts/count", tags=["Quiz"])
async def get_quiz_attempt_count(
    date: str = Query(..., description="Date in YYYY-MM-DD format"),
    current_user: User = Depends(get_current_user),
):
    db_client = db.get_client()

    try:
        # Convert date string to UTC datetime range
        local_timezone = pytz.utc  # Change this if your timestamps are in another timezone
        start_date = datetime.datetime.strptime(date, "%Y-%m-%d").replace(tzinfo=local_timezone)
        end_date = start_date + datetime.timedelta(days=1)

        # Debugging: Print date range
        print(f"Querying from {start_date} to {end_date}")

        # Count quiz responses for the user on the given date
        count = db_client[db.db_name]["quiz_responses"].count_documents({
            "username": current_user.username,
            "submitted_at": {"$gte": start_date, "$lt": end_date}
        })

        return {"date": date, "username": current_user.username, "quiz_attempt_count": count}
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD.")

    

@router17.get("/quiz-attempts/correct-count", tags=["Quiz"])
async def get_correct_quiz_attempt_count(
    date: str = Query(..., description="Date in YYYY-MM-DD format"),
    current_user: User = Depends(get_current_user),
):
    db_client = db.get_client()

    try:
        # Convert date string to UTC datetime range
        local_timezone = pytz.utc  
        start_date = datetime.datetime.strptime(date, "%Y-%m-%d").replace(tzinfo=local_timezone)
        end_date = start_date + datetime.timedelta(days=1)

        # Fetch all quizzes created on this date
        quizzes = list(db_client[db.db_name]["quizzes"].find({
            "created_at": {"$gte": start_date, "$lt": end_date}
        }))

        # Fetch all user's responses for this date
        responses = list(db_client[db.db_name]["quiz_responses"].find({
            "username": current_user.username,
            "submitted_at": {"$gte": start_date, "$lt": end_date}
        }))

        if not responses:
            return {"message": "No quiz attempts found for this date.", "correct_answers": 0}

        correct_count = 0

        # Compare user responses with correct answers
        for response in responses:
            for quiz in quizzes:
                if str(quiz["_id"]) == response["quiz_id"]:  # Match quiz ID
                    if response["selected_option"] == quiz["correct_answer"]:
                        correct_count += 1

        return {
            "date": date,
            "username": current_user.username,
            "correct_answers": correct_count,
            "total_quizzes": len(quizzes)
        }
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD.")

