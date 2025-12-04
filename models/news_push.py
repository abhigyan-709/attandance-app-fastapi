# models/news_push.py
"""
Fresh News Push Notification Models
Separate models for the news reader push notification system
"""
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime


class NewsPushKeys(BaseModel):
    """Web Push subscription keys (p256dh and auth)"""
    p256dh: str = Field(..., description="P256DH encryption key")
    auth: str = Field(..., description="Authentication secret")


class NewsPushSubscription(BaseModel):
    """News reader push notification subscription"""
    endpoint: str = Field(..., description="Push service endpoint URL")
    keys: NewsPushKeys = Field(..., description="Encryption keys")
    expirationTime: Optional[int] = Field(None, description="Subscription expiration timestamp")
    user_agent: Optional[str] = Field(None, description="User agent string for analytics")


class NewsPushSubscribeRequest(BaseModel):
    """Request body for subscribing to news notifications"""
    subscription: NewsPushSubscription


class NewsPushUnsubscribeRequest(BaseModel):
    """Request body for unsubscribing from news notifications"""
    endpoint: str = Field(..., description="Push service endpoint to remove")


class NewsPushTestRequest(BaseModel):
    """Request body for sending test notification"""
    endpoint: Optional[str] = Field(None, description="Optional specific endpoint to test")
    title: str = Field("Test Notification", description="Notification title")
    body: str = Field("This is a test notification from Gobar Sahi Times", description="Notification body")
    url: str = Field("https://gobarsahitimes.com", description="URL to open on click")
    icon: Optional[str] = Field(None, description="Icon URL")
    image: Optional[str] = Field(None, description="Image URL")


class NewsPushNotificationPayload(BaseModel):
    """Payload for sending news notification"""
    title: str = Field(..., description="News headline")
    body: str = Field(..., description="News summary/description")
    url: str = Field(..., description="Full news article URL")
    icon: Optional[str] = Field(None, description="Site icon/logo")
    image: Optional[str] = Field(None, description="News featured image")
    news_id: Optional[str] = Field(None, description="News article ID")


class NewsPushStatsResponse(BaseModel):
    """Response for subscription statistics"""
    total_subscriptions: int = Field(..., description="Total active subscriptions")
    total_notifications_sent: int = Field(..., description="Total notifications sent (all time)")
    last_notification_at: Optional[str] = Field(None, description="Last notification timestamp")
    oldest_subscription: Optional[str] = Field(None, description="Oldest subscription timestamp")
    newest_subscription: Optional[str] = Field(None, description="Newest subscription timestamp")


class NewsPushBroadcastResponse(BaseModel):
    """Response for broadcast notification"""
    status: str = Field(..., description="Broadcast status")
    total: int = Field(..., description="Total subscriptions attempted")
    successful: int = Field(..., description="Successfully delivered")
    failed: int = Field(..., description="Failed deliveries")
    expired: int = Field(..., description="Expired subscriptions removed")


class NewsPushConfigResponse(BaseModel):
    """Response for VAPID public key configuration"""
    public_key: str = Field(..., description="NEWS_VAPID public key for frontend")
    subject: str = Field(..., description="VAPID subject")


class NewsPushStatusResponse(BaseModel):
    """Response for subscription status check"""
    subscribed: bool = Field(..., description="Whether endpoint is subscribed")
    subscription_date: Optional[str] = Field(None, description="Date of subscription")
    notification_count: int = Field(0, description="Notifications received")
