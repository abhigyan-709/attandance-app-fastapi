from fastapi import APIRouter, Depends, HTTPException
from database.db import db
from models.subscription import UserSubscription, Courses
from fastapi.responses import JSONResponse
from pymongo import MongoClient
from routes.send_email import send_registration_email ,send_password_reset_email
from passlib.context import CryptContext

route21 = APIRouter()

# here we go for staging live
# Create an instance of CryptContext for password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

@route21.post("/course-subscription/", tags = ["Paid User Subscription"])
async def course(course : Courses):
    db_client = db.get_client()
    db_client[db.db_name]["courses"].insert_one(course.dict())
    return JSONResponse(content={"message": "Course Inserted Successfully"}, status_code=201)


# @route21.post("/subscription/", tags = ["Paid User Subscription"])
# async def subscription(user: UserSubscription, db_client: MongoClient = Depends(db.get_client)):
#     # Check if the username is already taken
#     existing_user_username = db_client[db.db_name]["user_subscription"].find_one({"username": user.username})
#     if existing_user_username:
#         raise HTTPException(status_code=400, detail="Username is already taken")

#     # Check if the email is already taken
#     existing_user_email = db_client[db.db_name]["user_subscription"].find_one({"email": user.email})
#     if existing_user_email:
#         raise HTTPException(status_code=400, detail="Email is already registered")

#     # Hash the password before storing it in the database
#     user_dict = user.dict()
#     user_dict['password'] = get_password_hash(user.password)
    
#     # Insert the user into the database
#     result = db_client[db.db_name]["user_subscription"].insert_one(user_dict)
    
#     # Convert ObjectId to string
#     user_dict["_id"] = str(result.inserted_id)

#     await send_registration_email(user.email, user.first_name, user.last_name)

#     # Return response with the user data
#     return JSONResponse(content=user_dict, status_code=201)

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
