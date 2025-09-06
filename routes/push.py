# routes/push.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr, Field
from typing import Literal, Optional, Dict, Any, List
from datetime import datetime, timezone

from database.db import db
from services.fcm import send_fcm  # defined below

push_router = APIRouter(prefix="/push", tags=["Push Notifications"])


def _tokens_collection():
    """
    Use existing db.py without modifying it.
    """
    client = db.get_client()
    return client[db.db_name]["push_tokens"]  # collection name: push_tokens


class RegisterBody(BaseModel):
    vendor_email: EmailStr
    token: str = Field(..., min_length=10)
    # Cleanest validation with Literal (no regex/pattern needed)
    platform: Literal["web", "android", "ios"]


@push_router.post("/register")
def register_token(body: RegisterBody):
    """
    Upsert an FCM token for a vendor.
    Deduplicates on (vendor_email, token, platform).
    """
    col = _tokens_collection()
    now = datetime.now(timezone.utc)

    result = col.update_one(
        {
            "vendor_email": body.vendor_email,
            "token": body.token,
            "platform": body.platform,
        },
        {
            "$set": {
                "vendor_email": body.vendor_email,
                "token": body.token,
                "platform": body.platform,
                "updated_at": now,
            },
            "$setOnInsert": {"created_at": now},
        },
        upsert=True,
    )

    return {
        "status": "ok",
        "upserted": bool(result.upserted_id),
        "matched_count": result.matched_count,
        "modified_count": result.modified_count,
    }


class SendBody(BaseModel):
    vendor_email: EmailStr
    title: str = "New order"
    body: str = "You have a new order"
    data: Optional[Dict[str, Any]] = None  # e.g., {"order_id": "abc123"}


@push_router.post("/send")
def send_to_vendor(body: SendBody):
    """
    Sends a push notification to all tokens registered for this vendor_email.
    Works for web & mobile tokens.
    """
    col = _tokens_collection()
    docs = list(col.find({"vendor_email": body.vendor_email}, {"token": 1, "_id": 0}))
    tokens: List[str] = [d["token"] for d in docs if d.get("token")]

    if not tokens:
        raise HTTPException(status_code=404, detail="No tokens registered for this vendor")

    resp = send_fcm(tokens=tokens, title=body.title, body=body.body, data=body.data or {})
    return {"status": "sent", "results": resp}
