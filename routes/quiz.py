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
# @router17.post("/create-quiz", tags=["Quiz"])
# async def create_quiz(quiz_data: QuizCreate, current_user: User = Depends(get_current_user)):
#     if current_user.role != "admin":
#         raise HTTPException(status_code=403, detail="Only admins can create quizzes.")

#     db_client = db.get_client()
    
#     quiz_doc = {
#         "question": quiz_data.question,
#         "options": quiz_data.options,
#         "correct_answer": quiz_data.correct_answer,
#         "time_limit": quiz_data.time_limit,
#         "created_by": current_user.username,
#         "created_at": datetime.datetime.utcnow(),
#     }

#     result = db_client[db.db_name]["quizzes"].insert_one(quiz_doc)
#     quiz_id = str(result.inserted_id)

#     # Send WebSocket notification to all users
#     quiz_notification = {
#         "type": "new_quiz",
#         "quiz_id": quiz_id,
#         "question": quiz_data.question,
#         "options": quiz_data.options,
#         "time_limit": quiz_data.time_limit
#     }
    
#     for connection in active_connections:
#         await connection.send_json(quiz_notification)

#     return {"message": "Quiz created successfully", "quiz_id": quiz_id}

@router17.post("/create-quiz", tags=["Quiz"])
async def create_quiz(quiz_data: QuizCreate, current_user: User = Depends(get_current_user)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only admins can create quizzes.")

    db_client = db.get_client()
    redis_client = db.get_redis()

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

    # Cache the quiz in Redis (set expiration of 24 hours)
    redis_client.setex(f"quiz:{quiz_id}", 86400, json.dumps(quiz_doc))

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

@router17.post("/submit-quiz/{quiz_id}", tags=["Quiz"])
async def submit_quiz(quiz_id: str, user_response: UserResponse, current_user: User = Depends(get_current_user)):
    db_client = db.get_client()
    redis_client = db.get_redis()

    # Check Redis for quiz
    quiz_data = redis_client.get(f"quiz:{quiz_id}")

    if quiz_data:
        quiz = json.loads(quiz_data)
    else:
        # Fetch from MongoDB if not in Redis
        quiz = db_client[db.db_name]["quizzes"].find_one({"_id": ObjectId(quiz_id)})
        if not quiz:
            raise HTTPException(status_code=404, detail="Quiz not found.")
        redis_client.setex(f"quiz:{quiz_id}", 86400, json.dumps(quiz))  # Cache in Redis

    # Store response in MongoDB
    response_doc = {
        "quiz_id": quiz_id,
        "username": current_user.username,
        "selected_option": user_response.selected_option,
        "submitted_at": user_response.submitted_at or datetime.datetime.utcnow(),
    }
    
    db_client[db.db_name]["quiz_responses"].insert_one(response_doc)

    return {"message": "Quiz submitted successfully"}


from fastapi import Query

from fastapi import Query
import pytz

# @router17.get("/quiz-attempts/count", tags=["Quiz"])
# async def get_quiz_attempt_count(
#     date: str = Query(..., description="Date in YYYY-MM-DD format"),
#     current_user: User = Depends(get_current_user),
# ):
#     db_client = db.get_client()

#     try:
#         # Convert date string to UTC datetime range
#         local_timezone = pytz.utc  # Change this if your timestamps are in another timezone
#         start_date = datetime.datetime.strptime(date, "%Y-%m-%d").replace(tzinfo=local_timezone)
#         end_date = start_date + datetime.timedelta(days=1)

#         # Debugging: Print date range
#         print(f"Querying from {start_date} to {end_date}")

#         # Count quiz responses for the user on the given date
#         count = db_client[db.db_name]["quiz_responses"].count_documents({
#             "username": current_user.username,
#             "submitted_at": {"$gte": start_date, "$lt": end_date}
#         })

#         return {"date": date, "username": current_user.username, "quiz_attempt_count": count}
#     except ValueError:
#         raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD.")

@router17.get("/quiz-attempts/count", tags=["Quiz"])
async def get_quiz_attempt_count(
    date: str = Query(..., description="Date in YYYY-MM-DD format"),
    current_user: User = Depends(get_current_user),
):
    db_client = db.get_client()
    redis_client = db.get_redis()

    cache_key = f"quiz_attempts:{current_user.username}:{date}"
    cached_count = redis_client.get(cache_key)

    if cached_count:
        return {"date": date, "username": current_user.username, "quiz_attempt_count": int(cached_count)}

    # Convert date string to UTC datetime range
    start_date = datetime.datetime.strptime(date, "%Y-%m-%d").replace(tzinfo=pytz.utc)
    end_date = start_date + datetime.timedelta(days=1)

    count = db_client[db.db_name]["quiz_responses"].count_documents({
        "username": current_user.username,
        "submitted_at": {"$gte": start_date, "$lt": end_date}
    })

    # Cache result in Redis for 1 hour
    redis_client.setex(cache_key, 3600, count)

    return {"date": date, "username": current_user.username, "quiz_attempt_count": count}

    

# @router17.get("/quiz-attempts/correct-count", tags=["Quiz"])
# async def get_correct_quiz_attempt_count(
#     date: str = Query(..., description="Date in YYYY-MM-DD format"),
#     current_user: User = Depends(get_current_user),
# ):
#     db_client = db.get_client()

#     try:
#         # Convert date string to UTC datetime range
#         local_timezone = pytz.utc  
#         start_date = datetime.datetime.strptime(date, "%Y-%m-%d").replace(tzinfo=local_timezone)
#         end_date = start_date + datetime.timedelta(days=1)

#         # Fetch all quizzes created on this date
#         quizzes = list(db_client[db.db_name]["quizzes"].find({
#             "created_at": {"$gte": start_date, "$lt": end_date}
#         }))

#         # Fetch all user's responses for this date
#         responses = list(db_client[db.db_name]["quiz_responses"].find({
#             "username": current_user.username,
#             "submitted_at": {"$gte": start_date, "$lt": end_date}
#         }))

#         if not responses:
#             return {"message": "No quiz attempts found for this date.", "correct_answers": 0}

#         correct_count = 0

#         # Compare user responses with correct answers
#         for response in responses:
#             for quiz in quizzes:
#                 if str(quiz["_id"]) == response["quiz_id"]:  # Match quiz ID
#                     if response["selected_option"] == quiz["correct_answer"]:
#                         correct_count += 1

#         return {
#             "date": date,
#             "username": current_user.username,
#             "correct_answers": correct_count,
#             "total_quizzes": len(quizzes)
#         }
#     except ValueError:
#         raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD.")

@router17.get("/quiz-attempts/correct-count", tags=["Quiz"])
async def get_correct_quiz_attempt_count(
    date: str = Query(..., description="Date in YYYY-MM-DD format"),
    current_user: User = Depends(get_current_user),
):
    db_client = db.get_client()
    redis_client = db.get_redis()

    cache_key = f"correct_quiz_attempts:{current_user.username}:{date}"
    cached_count = redis_client.get(cache_key)

    if cached_count:
        return {"date": date, "username": current_user.username, "correct_answers": int(cached_count)}

    start_date = datetime.datetime.strptime(date, "%Y-%m-%d").replace(tzinfo=pytz.utc)
    end_date = start_date + datetime.timedelta(days=1)

    quizzes = list(db_client[db.db_name]["quizzes"].find({"created_at": {"$gte": start_date, "$lt": end_date}}))
    responses = list(db_client[db.db_name]["quiz_responses"].find({
        "username": current_user.username,
        "submitted_at": {"$gte": start_date, "$lt": end_date}
    }))

    correct_count = 0

    for response in responses:
        for quiz in quizzes:
            if str(quiz["_id"]) == response["quiz_id"] and response["selected_option"] == quiz["correct_answer"]:
                correct_count += 1

    # Cache result in Redis for 1 hour
    redis_client.setex(cache_key, 3600, correct_count)

    return {
        "date": date,
        "username": current_user.username,
        "correct_answers": correct_count,
        "total_quizzes": len(quizzes)
    }


@router17.get("/test-redis", tags=["Test"])
async def test_redis():
    try:
        # Get Redis client
        redis_client = db.get_redis()

        # Test setting a value in Redis
        redis_client.set("test_key", "Redis is working!")

        # Get the value from Redis
        value = redis_client.get("test_key")

        if value:
            return {"message": "Redis is working!", "value": value}  # No need for decode()
        else:
            return {"message": "Redis is not working. No value found."}
    except Exception as e:
        return {"message": "Error connecting to Redis", "error": str(e)}

