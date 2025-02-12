from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
import jwt
from datetime import datetime, timedelta
from passlib.context import CryptContext
from database.db import db
from models.user import User
from models.token import Token
from typing import Union, List
from pymongo import MongoClient
import secrets
from bson import ObjectId
from fastapi.responses import JSONResponse
from fastapi import HTTPException, APIRouter, Depends
from pymongo import MongoClient
from models.user import User
from database.db import db
from models.user_details import UserDetails


route2 = APIRouter()
SECRET_KEY = secrets.token_urlsafe(32)
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Create an instance of CryptContext for password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Union[timedelta, None] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire, "sub": data["username"]})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=401,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception

        # Fetch user details including the role from the database
        db_client = db.get_client()  # Use db.get_client directly
        user_from_db = db_client[db.db_name]["user"].find_one({"username": username})
        if user_from_db is None:
            raise credentials_exception

        user = User(**user_from_db)  # Convert database response to User model
        return user
    except jwt.ExpiredSignatureError:
        raise credentials_exception
    except jwt.PyJWTError:
        raise credentials_exception

@route2.get("/")
async def root():
    # Test MongoDB connection
    client = db.get_client()
    return {"message": "Connected to MongoDB successfully!"}

@route2.post("/token", response_model=Token, tags=["Login & Authentication"])
async def login_for_access_token(
        form_data: OAuth2PasswordRequestForm = Depends(),
        db_client: MongoClient = Depends(db.get_client)
):
    user_from_db = db_client[db.db_name]["user"].find_one({"username": form_data.username})
    
    if user_from_db and verify_password(form_data.password, user_from_db['password']):
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"username": form_data.username},
            expires_delta=access_token_expires
        )
        return {"access_token": access_token, "token_type": "bearer"}

    raise HTTPException(
        status_code=401,
        detail="Incorrect username or password",
        headers={"WWW-Authenticate": "Bearer"},
    )


@route2.post("/register/", tags=["User Registration"])
async def register(user: User, db_client: MongoClient = Depends(db.get_client)):
    # Check if the username is already taken
    existing_user_username = db_client[db.db_name]["user"].find_one({"username": user.username})
    if existing_user_username:
        raise HTTPException(status_code=400, detail="Username is already taken")

    # Check if the email is already taken
    existing_user_email = db_client[db.db_name]["user"].find_one({"email": user.email})
    if existing_user_email:
        raise HTTPException(status_code=400, detail="Email is already registered")

    # Hash the password before storing it in the database
    user_dict = user.dict()
    user_dict['password'] = get_password_hash(user.password)
    
    # Insert the user into the database
    result = db_client[db.db_name]["user"].insert_one(user_dict)
    
    # Convert ObjectId to string
    user_dict["_id"] = str(result.inserted_id)

    # Return response with the user data
    return JSONResponse(content=user_dict, status_code=201)


@route2.get("/users/me", response_model=User, tags=["Read User & Current User"])
async def read_current_user(current_user: User = Depends(get_current_user), db_client: MongoClient = Depends(db.get_client)):
    # Use the username from the current_user object to filter the database query
    user_from_db = db_client[db.db_name]["user"].find_one({"username": current_user.username})

    if user_from_db:
        return user_from_db

    raise HTTPException(status_code=404, detail="User not found")



@route2.get("/users", response_model=List[User], tags=["User Management"])
async def get_all_users(current_user: User = Depends(get_current_user), db_client: MongoClient = Depends(db.get_client)):
    # Check if the current user is an admin
    if current_user.role != "admin":
        raise HTTPException(
            status_code=403,
            detail="You do not have permission to access this resource"
        )

    # Fetch all users from the database
    users_from_db = db_client[db.db_name]["user"].find()

    # Convert users from the database into a list
    users_list = []
    for user_data in users_from_db:
        user_data["_id"] = str(user_data["_id"])  # Convert ObjectId to string
        users_list.append(user_data)

    return users_list


@route2.patch("/users/activate/{username}", response_model=User, tags=["User Management"])
async def activate_user(
    username: str,  # Get the username as a URL parameter
    current_user: User = Depends(get_current_user),  # Ensure the current user is authenticated
    db_client: MongoClient = Depends(db.get_client)  # Access the database client
):
    # Check if the current user is an admin
    if current_user.role != "admin":
        raise HTTPException(
            status_code=403,
            detail="You do not have permission to perform this action"
        )

    # Find the user by username
    user_from_db = db_client[db.db_name]["user"].find_one({"username": username})

    if user_from_db is None:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )

    # Update the is_active field to True
    update_result = db_client[db.db_name]["user"].update_one(
        {"username": username},  # Match the user by username
        {"$set": {"is_active": True}}  # Set the is_active field to True
    )

    if update_result.matched_count == 0:
        raise HTTPException(
            status_code=400,
            detail="Failed to update user status"
        )

    # Fetch the updated user data from database
    updated_user = db_client[db.db_name]["user"].find_one({"username": username})

    # Return the updated user details
    updated_user["_id"] = str(updated_user["_id"])  # Convert ObjectId to string for response
    return updated_user


@route2.put("/users/details", response_model=UserDetails, tags=["User Details"])
async def add_or_update_user_details(
    user_details: UserDetails, 
    current_user: User = Depends(get_current_user), 
    db_client: MongoClient = Depends(db.get_client)
):
    # Reference to the collection
    user_details_collection = db_client[db.db_name]["user_details"]

    # Convert user details to dictionary
    user_details_dict = user_details.dict()

    # Ensure username and other fixed fields remain unchanged
    user_details_dict["username"] = current_user.username
    user_details_dict["first_name"] = current_user.first_name
    user_details_dict["last_name"] = current_user.last_name
    user_details_dict["email"] = current_user.email
    user_details_dict["role"] = current_user.role
    user_details_dict["city"] = current_user.city

    # Update existing document if found, otherwise insert a new one
    result = user_details_collection.update_one(
        {"username": current_user.username},  # Filter criteria
        {"$set": user_details_dict},  # Data to update
        upsert=True  # Create new if not exists
    )

    # Retrieve the updated/inserted document
    updated_user_details = user_details_collection.find_one({"username": current_user.username})
    updated_user_details["_id"] = str(updated_user_details["_id"])  # Convert ObjectId to string

    return JSONResponse(content=updated_user_details, status_code=200)


@route2.get("/users/details", response_model=UserDetails, tags=["User Details"])
async def get_user_details(
    current_user: User = Depends(get_current_user),
    db_client: MongoClient = Depends(db.get_client)
):
    if current_user is None:
        raise HTTPException(status_code=401, detail="User is not logged in")
    
    # Fetch user details from the database
    user_details = db_client[db.db_name]["user_details"].find_one({"username": current_user.username})

    if not user_details:
        raise HTTPException(status_code=404, detail="User details not found")

    # Convert MongoDB ObjectId to string if needed
    user_details["_id"] = str(user_details["_id"]) if "_id" in user_details else None

    # Ensure all required fields are present
    required_fields = [
        "username", "father_name", "mother_name", "mobile_number", "college_name",
        "course", "branch", "year_of_passing", "date_of_birth", "first_name",
        "last_name", "email", "role", "city"
    ]
    
    # Fill missing fields with None (or default values)
    for field in required_fields:
        if field not in user_details:
            user_details[field] = None  

    return user_details

    

    