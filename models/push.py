# models/push.py
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, Dict, Any, Literal

# ---------- FCM models (existing behavior) ----------

class RegisterBody(BaseModel):
    vendor_email: EmailStr
    token: str = Field(..., min_length=10)
    platform: Literal["web", "android", "ios"]

class SendBody(BaseModel):
    vendor_email: EmailStr
    title: str = "New order"
    body: str = "You have a new order"
    data: Optional[Dict[str, Any]] = None


# ---------- Web Push (VAPID) models ----------

class PushKeys(BaseModel):
    p256dh: str
    auth: str

class WebPushSubscription(BaseModel):
    endpoint: str
    keys: PushKeys
    expirationTime: Optional[int] = None
    ua: Optional[str] = None  # optional: store user-agent for analytics/debug

class NotifyPayload(BaseModel):
    title: str = "ProjectDevOps"
    body: str = "New update"
    url: Optional[str] = None
    image: Optional[str] = None
    icon: Optional[str] = None
    tag: Optional[str] = "projectdevops"

class NewBlogPayload(BaseModel):
    title: str
    url: Optional[str] = None
    image: Optional[str] = None
    body: Optional[str] = "New post just landed! Tap to read."
    icon: Optional[str] = None
    tag: Optional[str] = "new-blog"
