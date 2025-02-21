from fastapi import APIRouter, Depends, HTTPException
from database.db import db
from models.subscription import UserSubscription, Courses
from fastapi.responses import JSONResponse
from pymongo import MongoClient
from routes.send_email import send_registration_email ,send_password_reset_email
from passlib.context import CryptContext
from routes.user import get_current_user
from models.user import User

route21 = APIRouter()

# here we go for staging live
# Create an instance of CryptContext for password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

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
