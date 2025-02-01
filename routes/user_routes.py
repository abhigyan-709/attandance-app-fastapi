from fastapi import APIRouter, HTTPException, Depends
from database.db import db
from models.user import User
from authentication.auth import get_password_hash, verify_password, create_access_token
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt

SECRET_KEY = "2a57b0240652eabd4bfbbc1e11993ee620d8c4c8617ecf3ee26788a16afb08be"
ALGORITHM = "HS256"

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        user = db.users.find_one({"username": username})
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        return user
    except JWTError:
        raise HTTPException(status_code=401, detail="Could not validate credentials")
    
# User registration route
@router.post("/register")
async def register_user(user: User):
    if db.users.find_one({"username": user.username}):
        raise HTTPException(status_code=400, detail="User already exists")
    
    user_dict = user.dict()
    user_dict["password"] = get_password_hash(user_dict["password"])
    db.users.insert_one(user_dict)
    return {"message": "User registered. Awaiting activation."}

# User login route
@router.post("/login")
async def login(username: str, password: str):
    user = db.users.find_one({"username": username})
    if not user or not verify_password(password, user["password"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    if not user["activated"]:
        raise HTTPException(status_code=403, detail="User not activated")

    token = create_access_token({"sub": username})
    return {"access_token": token, "token_type": "bearer"}

@router.post("/activate_user")
async def activate_user(username: str, current_user: dict = Depends(get_current_user)):
    if current_user["user_type"] != "admin":
        raise HTTPException(status_code=403, detail="Only admins can activate users")

    result = db.users.update_one({"username": username}, {"$set": {"activated": True}})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    
    return {"message": f"User {username} activated successfully"}

