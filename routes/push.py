from fastapi import APIRouter
from pydantic import BaseModel, Field, EmailStr

# use your Database class EXACTLY as-is
from database.db import Database
from services.fcm import register_token, unregister_token

push_router = APIRouter(prefix="/push", tags=["Push"])

def _get_db():
    _db = Database()
    client = _db.get_client()
    return client[_db.db_name]

class RegisterBody(BaseModel):
    email: EmailStr
    token: str = Field(..., min_length=20)
    platform: str = Field(..., regex="^(web|android|ios)$")
    user_type: str = Field("vendor", regex="^(vendor|customer|admin)$")
    user_agent: str | None = None

@push_router.post("/register")
def register(body: RegisterBody):
    db = _get_db()
    topic = register_token(
        db,
        email=str(body.email),
        token=body.token,
        platform=body.platform,
        user_type=body.user_type,
        user_agent=body.user_agent,
    )
    return {"ok": True, "topic": topic}

class UnregisterBody(BaseModel):
    token: str

@push_router.post("/unregister")
def unregister(body: UnregisterBody):
    db = _get_db()
    unregister_token(db, token=body.token)
    return {"ok": True}
