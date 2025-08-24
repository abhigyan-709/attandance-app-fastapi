# routes/google_auth.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any
from bson import ObjectId
from datetime import datetime

from authentication.google_auth import verify_google_token
from authentication.google_jwt import create_google_access_token, create_google_refresh_token
from database.db import Database

router31 = APIRouter()

db = Database()
client = db.get_client()
db_name = db.db_name

google_users_collection = client[db_name]["google_users"]         # raw google payload
customer_details_collection = client[db_name]["customer_details"] # unified profile

class GoogleLoginRequest(BaseModel):
    id_token: str

def _now_iso() -> str:
    return datetime.utcnow().isoformat()

def _convert_id(x: Any):
    if isinstance(x, dict):
        return {k: _convert_id(v) for k, v in x.items()}
    if isinstance(x, list):
        return [_convert_id(i) for i in x]
    if isinstance(x, ObjectId):
        return str(x)
    return x

@router31.post("/auth/google")
async def google_login(payload: GoogleLoginRequest):
    user_info = verify_google_token(payload.id_token)
    if not user_info:
        raise HTTPException(status_code=401, detail="Invalid Google token")

    # 1) Upsert raw Google user
    user = google_users_collection.find_one({"sub": user_info["sub"]})
    if not user:
        insert = google_users_collection.insert_one(user_info)
        user = google_users_collection.find_one({"_id": insert.inserted_id})

    g_id = str(user["_id"])
    email = user.get("email")
    name = user.get("name")

    # 2) Ensure a customer_details doc exists and keyed by username=email
    username = email or f"google:{user['sub']}"
    selector = {"username": username}  # unified selector across local & google

    existing = customer_details_collection.find_one(selector)
    base_doc: Dict[str, Any] = {
        "username": username,        # for Google => email as username
        "email": email,
        "name": name,
        "phone_number": None,
        "addresses": [],
    }

    if not existing:
        base_doc.update({"created_at": _now_iso(), "updated_at": _now_iso()})
        customer_details_collection.update_one(selector, {"$set": base_doc}, upsert=True)
    else:
        updates: Dict[str, Any] = {"updated_at": _now_iso()}
        if email and existing.get("email") != email:
            updates["email"] = email
        if name and existing.get("name") != name:
            updates["name"] = name
        if updates:
            customer_details_collection.update_one(selector, {"$set": updates})

    # 3) Mint tokens
    access_token = create_google_access_token({"sub": user_info["sub"]})
    refresh_token = create_google_refresh_token({"sub": user_info["sub"]})

    user = _convert_id(user)
    profile = customer_details_collection.find_one(selector) or base_doc
    profile = _convert_id(profile)

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "google_user": user,
        "customer_details": profile,
    }
