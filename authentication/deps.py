# # authentication/deps.py
# from typing import Optional, Dict, Any
# from fastapi import Depends, HTTPException
# from fastapi.security import OAuth2PasswordBearer
# from jose import jwt

# from database.db import db

# # Local JWT (your existing helper)
# from authentication.auth import SECRET_KEY as LOCAL_SECRET, ALGORITHM as LOCAL_ALGO

# # Google JWT (same secret/alg used when creating Google access tokens)
# from authentication.secrets import get_google_access_secret
# from authentication.google_jwt import ALGORITHM as GOOGLE_ALGO

# oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# client = db.get_client()
# database = client[db.db_name]

# users_col = database["user"]                # local users
# google_users_col = database["google_users"] # raw google auth payloads

# Principal = Dict[str, Any]  # { id, username, email, role, provider }

# def _local_from_token(token: str) -> Optional[Principal]:
#     try:
#         payload = jwt.decode(token, LOCAL_SECRET, algorithms=[LOCAL_ALGO])
#         # your local token may store username under 'sub' or directly as 'username'
#         username = payload.get("sub") or payload.get("username")
#         if not username:
#             return None
#         user = users_col.find_one({"username": username})
#         if not user:
#             return None
#         return {
#             "id": str(user.get("_id")),
#             "username": user.get("username"),
#             "email": user.get("email"),
#             "role": user.get("role", "user"),
#             "provider": "local",
#         }
#     except Exception:
#         return None

# def _google_from_token(token: str) -> Optional[Principal]:
#     try:
#         google_secret = get_google_access_secret()
#         payload = jwt.decode(token, google_secret, algorithms=[GOOGLE_ALGO])
#         sub = payload.get("sub")
#         if not sub:
#             return None

#         guser = google_users_col.find_one({"sub": sub})
#         if not guser:
#             return None

#         email = guser.get("email")
#         # IMPORTANT: for Google users we treat username == email (your requirement)
#         username = email or f"google:{sub}"

#         return {
#             "id": str(guser["_id"]),      # stable id from google_users
#             "username": username,         # equals email if email present
#             "email": email,
#             "role": "user",
#             "provider": "google",
#         }
#     except Exception:
#         return None

# async def get_current_principal(token: str = Depends(oauth2_scheme)) -> Principal:
#     # try local first
#     p = _local_from_token(token)
#     if p:
#         return p
#     # then google
#     p = _google_from_token(token)
#     if p:
#         return p
#     raise HTTPException(status_code=401, detail="Could not validate credentials")


# authentication/deps.py
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import jwt, JWTError
from typing import Dict, TypedDict, Optional

from authentication.secrets import (
    get_google_access_secret,
)
from authentication.auth import SECRET_KEY as LOCAL_SECRET, ALGORITHM as LOCAL_ALG

security = HTTPBearer(auto_error=False)

class Principal(TypedDict, total=False):
    user_id: str
    username: str
    email: Optional[str]
    role: str
    provider: str  # "google" | "local"

def _decode(token: str, secret: str, alg: str = "HS256") -> Dict:
    return jwt.decode(token, secret, algorithms=[alg])

def _unverified_claims(token: str) -> Dict:
    try:
        return jwt.get_unverified_claims(token)
    except Exception:
        return {}

def _as_principal(claims: Dict, provider: str) -> Principal:
    # Try common keys; adjust to what you set when issuing tokens.
    user_id = str(
        claims.get("user_id")
        or claims.get("id")
        or claims.get("sub")  # often a string id/username for local; google 'sub' is fine too
        or ""
    )
    username = (
        claims.get("username")
        or claims.get("email")  # for google we use email as username key in DB
        or ""
    )
    role = claims.get("role", "user")
    email = claims.get("email")

    if not username:
        # Last resort: use email or user_id as username
        username = email or user_id

    return {
        "user_id": user_id,
        "username": username,
        "email": email,
        "role": role,
        "provider": provider,
    }

async def get_current_principal(
    creds: HTTPAuthorizationCredentials = Depends(security),
) -> Principal:
    if not creds or not creds.scheme.lower() == "bearer":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    token = creds.credentials
    claims_hint = _unverified_claims(token)
    provider_hint = (claims_hint.get("provider") or "").lower()

    # 1) If token *says* which provider, validate with that first
    tried_google = tried_local = False
    last_err: Optional[Exception] = None

    if provider_hint == "local":
        tried_local = True
        try:
            c = _decode(token, LOCAL_SECRET, LOCAL_ALG)
            return _as_principal(c, "local")
        except Exception as e:
            last_err = e
    elif provider_hint == "google":
        tried_google = True
        try:
            # If secret missing in Secrets Manager, our secrets module returns fallback string.
            g_secret = get_google_access_secret()
            c = _decode(token, g_secret, "HS256")
            return _as_principal(c, "google")
        except Exception as e:
            last_err = e

    # 2) Fallback: try both paths
    if not tried_google:
        try:
            g_secret = get_google_access_secret()
            c = _decode(token, g_secret, "HS256")
            return _as_principal(c, "google")
        except Exception as e:
            last_err = e

    if not tried_local:
        try:
            c = _decode(token, LOCAL_SECRET, LOCAL_ALG)
            return _as_principal(c, "local")
        except Exception as e:
            last_err = e

    # 3) Still not valid → 401
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")
