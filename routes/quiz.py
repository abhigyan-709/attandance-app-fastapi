from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from database.db import db
from bson import ObjectId
from models.quiz import QuizCreate, UserResponse
from models.user import User
from routes.user import get_current_user
from typing import List
import datetime

router17 = APIRouter()

# Store active WebSocket connections
active_connections: List[WebSocket] = []

# WebSocket for real-time quiz notifications
@router17.websocket("/quiz-notifications")
async def quiz_notifications(websocket: WebSocket):
    await websocket.accept()
    active_connections.append(websocket)
    try:
        while True:
            await websocket.receive_text()  # Keep connection alive
    except WebSocketDisconnect:
        active_connections.remove(websocket)

# Admin creates a new quiz & notifies users
@router17.post("/create-quiz")
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

# User submits a quiz response
@router17.post("/submit-quiz/{quiz_id}")
async def submit_quiz(quiz_id: str, user_response: UserResponse, current_user: User = Depends(get_current_user)):
    db_client = db.get_client()
    
    # Validate quiz existence
    quiz = db_client[db.db_name]["quizzes"].find_one({"_id": ObjectId(quiz_id)})
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found.")

    # Ensure submitted_at is a valid datetime
    submitted_time = user_response.submitted_at or datetime.utcnow()

    # Store response in MongoDB
    response_doc = {
        "quiz_id": quiz_id,
        "username": current_user.username,
        "selected_option": user_response.selected_option,
        "submitted_at": submitted_time  # Ensure it's stored as datetime
    }
    
    db_client[db.db_name]["quiz_responses"].insert_one(response_doc)

    return {"message": "Quiz submitted successfully"}