from fastapi import APIRouter, Depends, HTTPException
from database.db import db
from models.subscription import UserSubscription, Courses
from fastapi.responses import JSONResponse
from pymongo import MongoClient
from routes.send_email import send_registration_email ,send_password_reset_email
from passlib.context import CryptContext
from routes.user import get_current_user
from models.user import User
from fastapi import APIRouter, Request, HTTPException, BackgroundTasks
import razorpay
import json
import hmac
import hashlib
from database.db import db
from routes.send_email import send_registration_email

route21 = APIRouter()


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def activate_user(email: str):
    db_client = db.get_client()
    db_client[db.db_name]["user_subscription"].update_one(
        {"email": email}, {"$set": {"is_active": True}}
    )
    print(f"✅ User {email} activated successfully!")

@route21.post("/course-subscription/", tags = ["Paid User Subscription"])
async def course(course : Courses, current_user = Depends(get_current_user)):
    # check is the user is admin or not
    if current_user.role != "admin":
        raise HTTPException(
            status_code=403,
            detail="You do not have permission to add a Google Meet Link"
        )
    
    db_client = db.get_client()
    db_client[db.db_name]["courses"].insert_one(course.dict())
    return JSONResponse(content={"message": "Course Inserted Successfully"}, status_code=201)

@route21.get("/get_course_details", tags = ["Paid User Subscription"])
async def get_course_details():
    db_client = db.get_client()
    courses = db_client[db.db_name]["courses"].find()
    courses_list = []
    for course in courses:
        course["_id"] = str(course["_id"])
        courses_list.append(course)

    return courses_list

@route21.post("/subscription/", tags=["Paid User Subscription"])
async def subscription(user: UserSubscription, db_client: MongoClient = Depends(db.get_client)):
    # Check if the email is already taken
    existing_user_email = db_client[db.db_name]["user_subscription"].find_one({"email": user.email})
    if existing_user_email:
        raise HTTPException(status_code=400, detail="Email is already registered")

    # Hash the password before storing it in the database
    user_dict = user.dict()
    user_dict['password'] = get_password_hash(user.password)
    
    # Insert the user into the database with inactive status
    user_dict["is_active"] = False  # User will be activated after successful payment
    result = db_client[db.db_name]["user_subscription"].insert_one(user_dict)
    
    # Convert ObjectId to string
    user_dict["_id"] = str(result.inserted_id)

    # Return response without sending an email
    return JSONResponse(content={"message": "User registered successfully. Redirect to payment."}, status_code=201)


@route21.post("/razorpay/webhook/", tags=["Payment Webhook"])
async def razorpay_webhook(background_tasks: BackgroundTasks, request: Request):
    try:
        payload = await request.json()
        print("🔔 Webhook Received:", payload)  # Log webhook data

        event = payload.get("event")
        payment_id = payload.get("payload", {}).get("payment", {}).get("entity", {}).get("id")
        email = payload.get("payload", {}).get("payment", {}).get("entity", {}).get("email")

        print(f"🔔 Event: {event}, Payment ID: {payment_id}, Email: {email}")

        # Simulate user activation for testing
        if event == "payment.captured":
            background_tasks.add_task(activate_user, email)
            return {"status": "success", "message": "Test Mode: User activated"}

        return {"status": "ignored", "message": "Unhandled event"}

    except Exception as e:
        print("⚠️ Webhook Error:", e)
        raise HTTPException(status_code=500, detail="Webhook processing failed")

