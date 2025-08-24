# authentication/deps.py
from typing import Optional, Dict, Any
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from jose import jwt

from database.db import db

# Local JWT (your existing helper)
from authentication.auth import SECRET_KEY as LOCAL_SECRET, ALGORITHM as LOCAL_ALGO

# Google JWT (same secret/alg used when creating Google access tokens)
from authentication.secrets import get_google_access_secret
from authentication.google_jwt import ALGORITHM as GOOGLE_ALGO

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

client = db.get_client()
database = client[db.db_name]

users_col = database["user"]                # local users
google_users_col = database["google_users"] # raw google auth payloads

Principal = Dict[str, Any]  # { id, username, email, role, provider }

def _local_from_token(token: str) -> Optional[Principal]:
    try:
        payload = jwt.decode(token, LOCAL_SECRET, algorithms=[LOCAL_ALGO])
        # your local token may store username under 'sub' or directly as 'username'
        username = payload.get("sub") or payload.get("username")
        if not username:
            return None
        user = users_col.find_one({"username": username})
        if not user:
            return None
        return {
            "id": str(user.get("_id")),
            "username": user.get("username"),
            "email": user.get("email"),
            "role": user.get("role", "user"),
            "provider": "local",
        }
    except Exception:
        return None

def _google_from_token(token: str) -> Optional[Principal]:
    try:
        google_secret = get_google_access_secret()
        payload = jwt.decode(token, google_secret, algorithms=[GOOGLE_ALGO])
        sub = payload.get("sub")
        if not sub:
            return None

        guser = google_users_col.find_one({"sub": sub})
        if not guser:
            return None

        email = guser.get("email")
        # IMPORTANT: for Google users we treat username == email (your requirement)
        username = email or f"google:{sub}"

        return {
            "id": str(guser["_id"]),      # stable id from google_users
            "username": username,         # equals email if email present
            "email": email,
            "role": "user",
            "provider": "google",
        }
    except Exception:
        return None

async def get_current_principal(token: str = Depends(oauth2_scheme)) -> Principal:
    # try local first
    p = _local_from_token(token)
    if p:
        return p
    # then google
    p = _google_from_token(token)
    if p:
        return p
    raise HTTPException(status_code=401, detail="Could not validate credentials")
