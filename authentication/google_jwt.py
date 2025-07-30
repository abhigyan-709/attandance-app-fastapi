from datetime import datetime, timedelta
from jose import jwt
from authentication.secrets import get_google_access_secret, get_google_refresh_secret

ALGORITHM = "HS256"

def create_google_access_token(data: dict, expires_minutes: int = 15):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=expires_minutes)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, get_google_access_secret(), algorithm=ALGORITHM)

def create_google_refresh_token(data: dict, expires_days: int = 7):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=expires_days)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, get_google_refresh_secret(), algorithm=ALGORITHM)
