# # routes/push.py
# from fastapi import APIRouter, HTTPException
# from pydantic import BaseModel, EmailStr, Field
# from typing import Literal, Optional, Dict, Any, List
# from datetime import datetime, timezone

# from database.db import db
# from services.fcm import send_fcm

# push_router = APIRouter(prefix="/push", tags=["Push Notifications"])

# def _tokens_collection():
#     client = db.get_client()
#     return client[db.db_name]["push_tokens"]

# class RegisterBody(BaseModel):
#     vendor_email: EmailStr
#     token: str = Field(..., min_length=10)
#     platform: Literal["web", "android", "ios"]

# @push_router.post("/register")
# def register_token(body: RegisterBody):
#     col = _tokens_collection()
#     now = datetime.now(timezone.utc)
#     result = col.update_one(
#         {"vendor_email": body.vendor_email, "token": body.token, "platform": body.platform},
#         {"$set": {"vendor_email": body.vendor_email, "token": body.token, "platform": body.platform, "updated_at": now},
#          "$setOnInsert": {"created_at": now}},
#         upsert=True,
#     )
#     return {"status": "ok", "upserted": bool(result.upserted_id), "matched_count": result.matched_count, "modified_count": result.modified_count}

# class SendBody(BaseModel):
#     vendor_email: EmailStr
#     title: str = "New order"
#     body: str = "You have a new order"
#     data: Optional[Dict[str, Any]] = None

# @push_router.post("/send")
# def send_to_vendor(body: SendBody):
#     col = _tokens_collection()
#     docs = list(col.find({"vendor_email": body.vendor_email}, {"token": 1, "_id": 0}))
#     tokens: List[str] = [d["token"] for d in docs if d.get("token")]
#     if not tokens:
#         raise HTTPException(status_code=404, detail="No tokens registered for this vendor")
#     results = send_fcm(tokens=tokens, title=body.title, body=body.body, data=body.data or {})
#     return {"status": "sent", "count": len(results), "results": results}

# routes/push.py
from fastapi import APIRouter, HTTPException, Request, status
from datetime import datetime, timezone
from typing import Dict, Any, List
import os
import json

from database.db import db
from services.fcm import send_fcm

# All request/response schemas now live in models/push.py
from models.push import (
    RegisterBody,
    SendBody,
    WebPushSubscription,
    NotifyPayload,
    NewBlogPayload,
)

# Optional dependency for Web Push (VAPID)
# Add to requirements.txt: pywebpush==2.0.0
try:
    from pywebpush import webpush, WebPushException
except Exception:
    webpush = None
    WebPushException = Exception

push_router = APIRouter(prefix="/push", tags=["Push Notifications"])

# -----------------------------
# Mongo collections
# -----------------------------
def _tokens_collection():
    client = db.get_client()
    return client[db.db_name]["push_tokens"]  # existing FCM tokens

def _webpush_collection():
    client = db.get_client()
    return client[db.db_name]["webpush_subscriptions"]  # Web Push VAPID subs


# =============================
# FCM-BASED ENDPOINTS (unchanged)
# =============================

@push_router.post("/register")
def register_token(body: RegisterBody):
    """
    Register or update a device token for FCM (existing behavior).
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

@push_router.post("/send")
def send_to_vendor(body: SendBody):
    """
    Send a push via FCM to all tokens for a vendor_email.
    """
    col = _tokens_collection()
    docs = list(col.find({"vendor_email": body.vendor_email}, {"token": 1, "_id": 0}))
    tokens: List[str] = [d["token"] for d in docs if d.get("token")]
    if not tokens:
        raise HTTPException(status_code=404, detail="No tokens registered for this vendor")
    results = send_fcm(tokens=tokens, title=body.title, body=body.body, data=body.data or {})
    return {"status": "sent", "count": len(results), "results": results}


# =============================
# WEB PUSH (VAPID) ENDPOINTS
# =============================

# Read from environment (you put these in Actions -> .env on EC2)
VAPID_PUBLIC_KEY  = os.getenv("VAPID_PUBLIC_KEY")
VAPID_PRIVATE_KEY = os.getenv("VAPID_PRIVATE_KEY")
VAPID_SUBJECT     = os.getenv("VAPID_SUBJECT", "mailto:connect@projectdevops.in")

# Optional shared-secret header for admin/broadcast calls
ADMIN_API_TOKEN   = os.getenv("ADMIN_API_TOKEN")

def _require_pywebpush():
    if webpush is None:
        raise HTTPException(status_code=500, detail="pywebpush not installed on server")

def _require_vapid():
    if not VAPID_PUBLIC_KEY or not VAPID_PRIVATE_KEY:
        raise HTTPException(status_code=500, detail="VAPID keys are not configured on server")

def _webpush_send_one(sub: Dict[str, Any], payload: Dict[str, Any]) -> bool:
    """
    Send a web push to single subscription. Returns False if it should be pruned.
    """
    _require_pywebpush()
    _require_vapid()
    try:
        webpush(
            subscription_info={
                "endpoint": sub["endpoint"],
                "keys": {
                    "p256dh": sub["keys"]["p256dh"],
                    "auth": sub["keys"]["auth"],
                },
            },
            data=json.dumps(payload, ensure_ascii=False),
            vapid_private_key=VAPID_PRIVATE_KEY,
            vapid_claims={"sub": VAPID_SUBJECT},
        )
        return True
    except WebPushException as e:
        status_code = getattr(e.response, "status_code", None)
        # 404/410 => gone/expired; prune it
        if status_code in (404, 410):
            _webpush_collection().delete_one({"endpoint": sub["endpoint"]})
            return False
        # log and keep otherwise (transient errors)
        print("[webpush] send error:", e)
        return True

@push_router.get("/public-key")
def public_key():
    """
    Expose VAPID public key so clients can fetch dynamically if needed.
    """
    _require_vapid()
    return {"key": VAPID_PUBLIC_KEY}

@push_router.post("/subscribe")
def subscribe_webpush(sub: WebPushSubscription, request: Request):
    """
    Save or update a Web Push subscription (idempotent upsert on endpoint).
    """
    _require_vapid()
    col = _webpush_collection()
    now = datetime.now(timezone.utc)

    doc = sub.dict()
    doc["ua"] = doc.get("ua") or request.headers.get("user-agent")
    doc["updated_at"] = now

    res = col.update_one(
        {"endpoint": sub.endpoint},
        {
            "$set": doc,
            "$setOnInsert": {"created_at": now},
        },
        upsert=True,
    )
    return {
        "status": "ok",
        "upserted": bool(res.upserted_id),
        "matched_count": res.matched_count,
        "modified_count": res.modified_count,
    }

@push_router.post("/unsubscribe")
def unsubscribe_webpush(sub: WebPushSubscription):
    """
    Remove a Web Push subscription by endpoint.
    """
    col = _webpush_collection()
    col.delete_one({"endpoint": sub.endpoint})
    return {"status": "ok"}

@push_router.post("/broadcast")
def broadcast_webpush(payload: NotifyPayload, request: Request):
    """
    Broadcast a payload to ALL Web Push subscribers.
    If ADMIN_API_TOKEN is set, requires: header x-admin-token: <token>
    """
    _require_vapid()
    if ADMIN_API_TOKEN and request.headers.get("x-admin-token") != ADMIN_API_TOKEN:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")

    col = _webpush_collection()
    to_send = payload.dict(exclude_none=True)

    total = 0
    sent_ok = 0
    for sub in col.find({}, {"_id": 0}):
        total += 1
        if _webpush_send_one(sub, to_send):
            sent_ok += 1
    return {"status": "ok", "sent": sent_ok, "total": total}

@push_router.post("/notify-new-blog")
def notify_new_blog(payload: NewBlogPayload, request: Request):
    """
    Convenience endpoint to notify all web subscribers of a new blog.
    If ADMIN_API_TOKEN is set, requires: header x-admin-token: <token>
    """
    _require_vapid()
    if ADMIN_API_TOKEN and request.headers.get("x-admin-token") != ADMIN_API_TOKEN:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")

    data = {
        "title": payload.title,
        "body": payload.body or "New post just landed! Tap to read.",
        "url": payload.url,
        "image": payload.image,
        "icon": payload.icon or "https://blogs.projectdevops.in/favicon.ico",
        "tag": payload.tag or "new-blog",
    }

    col = _webpush_collection()
    total = 0
    sent_ok = 0
    for sub in col.find({}, {"_id": 0}):
        total += 1
        if _webpush_send_one(sub, data):
            sent_ok += 1

    return {"status": "ok", "sent": sent_ok, "total": total}

@push_router.get("/stats")
def push_stats():
    """
    Quick stats: count of FCM tokens and Web Push subscriptions.
    """
    fcm_count = _tokens_collection().count_documents({})
    webpush_count = _webpush_collection().count_documents({})
    return {"fcm_tokens": fcm_count, "webpush_subscriptions": webpush_count}
