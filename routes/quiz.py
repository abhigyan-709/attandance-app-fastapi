import redis
import json
import datetime
import pytz
from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect, BackgroundTasks
from database.db import db
from bson import ObjectId
from models.quiz import QuizCreate, UserResponse
from models.user import User
from routes.user import get_current_user
from typing import List
from fastapi import Query

router17 = APIRouter()

REDIS_HOST = "172.31.38.238" 
REDIS_PORT = 6379 

redis_client = redis.StrictRedis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)

# Store active WebSocket connections
active_connections: List[WebSocket] = []

# WebSocket for real-time quiz notifications
@router17.websocket("/quiz-notifications")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    active_connections.append(websocket)

    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        active_connections.remove(websocket)


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


@router17.post("/submit-quiz/{quiz_id}", tags=["Quiz"])
async def submit_quiz(
    quiz_id: str,
    user_response: UserResponse,
    background_tasks: BackgroundTasks,  # Move this before default arguments
    current_user: User = Depends(get_current_user)  # Keep Depends() at the end
):

    db_client = db.get_client()
    
    # Validate quiz existence
    quiz = db_client[db.db_name]["quizzes"].find_one({"_id": ObjectId(quiz_id)})
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found.")

    submitted_time = user_response.submitted_at or datetime.datetime.utcnow()
    
    response_doc = {
        "quiz_id": quiz_id,
        "username": current_user.username,
        "selected_option": user_response.selected_option,
        "submitted_at": submitted_time.isoformat(),
    }

    # Store in Redis (List for batch processing)
    redis_client.rpush("quiz_responses", json.dumps(response_doc))

    # Update quiz attempt count in Redis
    redis_client.hincrby(f"user:{current_user.username}:quiz_attempts", quiz_id, 1)

    # Check if correct
    if user_response.selected_option == quiz["correct_answer"]:
        redis_client.hincrby(f"user:{current_user.username}:correct_quiz_attempts", quiz_id, 1)

    # Background task to process batch writes to MongoDB
    background_tasks.add_task(process_redis_quiz_responses)

    return {"message": "Quiz response received and stored in Redis"}


# Background task to process Redis responses and insert into MongoDB
def process_redis_quiz_responses():
    db_client = db.get_client()
    while redis_client.llen("quiz_responses") > 0:
        response_json = redis_client.lpop("quiz_responses")
        if response_json:
            response_doc = json.loads(response_json)
            response_doc["submitted_at"] = datetime.datetime.fromisoformat(response_doc["submitted_at"])
            db_client[db.db_name]["quiz_responses"].insert_one(response_doc)


# Get total quiz attempts from Redis
@router17.get("/quiz-attempts/count", tags=["Quiz"])
async def get_quiz_attempt_count(
    current_user: User = Depends(get_current_user)
):
    attempt_counts = redis_client.hgetall(f"user:{current_user.username}:quiz_attempts")
    total_attempts = sum(map(int, attempt_counts.values())) if attempt_counts else 0

    return {"username": current_user.username, "quiz_attempt_count": total_attempts}


# Get correct quiz attempts from Redis
@router17.get("/quiz-attempts/correct-count", tags=["Quiz"])
async def get_correct_quiz_attempt_count(
    current_user: User = Depends(get_current_user)
):
    correct_counts = redis_client.hgetall(f"user:{current_user.username}:correct_quiz_attempts")
    total_correct = sum(map(int, correct_counts.values())) if correct_counts else 0

    return {"username": current_user.username, "correct_answers": total_correct}