from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from jose import jwt, JWTError
from authentication.secrets import get_google_refresh_secret
from authentication.google_jwt import create_google_access_token

router = APIRouter()

class RefreshTokenRequest(BaseModel):
    refresh_token: str

@router.post("/auth/google-refresh")
async def refresh_google_token(request: RefreshTokenRequest):
    try:
        payload = jwt.decode(
            request.refresh_token,
            get_google_refresh_secret(),
            algorithms=["HS256"]
        )
        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid refresh token")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    new_access_token = create_google_access_token({"sub": user_id})
    return {
        "access_token": new_access_token,
        "token_type": "bearer"
    }
