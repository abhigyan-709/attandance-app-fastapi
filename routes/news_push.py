# routes/news_push.py
"""
Fresh News Push Notification Routes
Separate API endpoints for news reader push subscriptions
Uses 'news_subscriptions' MongoDB collection (separate from other systems)
"""
import logging
import os
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, status
from pymongo import MongoClient, DESCENDING
from datetime import datetime, timezone
from typing import Optional, List
from bson import ObjectId

from database.db import db
from services.news_push import (
    get_news_vapid_config,
    send_news_push_notification,
    broadcast_news_notification,
    validate_news_vapid_config,
)
from models.news_push import (
    NewsPushSubscribeRequest,
    NewsPushUnsubscribeRequest,
    NewsPushTestRequest,
    NewsPushStatsResponse,
    NewsPushBroadcastResponse,
    NewsPushConfigResponse,
    NewsPushStatusResponse,
)
from models.user import User
from routes.user import get_current_user

logger = logging.getLogger(__name__)

news_push_router = APIRouter(prefix="/news-push", tags=["News Push"])

NEWS_BASE_URL = os.getenv("NEWS_BASE_URL", "https://gobarsahitimes.com")


def get_news_subscriptions_collection(db_client: MongoClient = Depends(db.get_client)):
    """Get the news_subscriptions collection (separate collection)"""
    database = db_client[db.db_name]
    return database["news_subscriptions"]


def get_current_admin_user(current_user: User = Depends(get_current_user)):
    """Admin authentication - same as news.py"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized. Admin access required.")
    return current_user


def _extract_meta_description(content: str, max_length: int = 120) -> str:
    """Extract plain text from HTML content for notification body"""
    if not content:
        return ""
    # Simple HTML tag removal
    import re
    text = re.sub(r'<[^>]+>', '', content)
    text = text.strip()
    return text[:max_length] + "..." if len(text) > max_length else text


# ==================== Public Endpoints ====================

@news_push_router.get("/config", response_model=NewsPushConfigResponse)
async def get_news_push_config():
    """
    Get NEWS_VAPID public key for frontend subscription
    Frontend needs this to subscribe users to push notifications
    """
    try:
        vapid_config = get_news_vapid_config()
        
        if not vapid_config["public_key"]:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="NEWS_VAPID public key not configured on server"
            )
        
        return NewsPushConfigResponse(
            public_key=vapid_config["public_key"],
            subject=vapid_config["subject"]
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[news-push] Error getting config: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve push configuration"
        )


@news_push_router.post("/subscribe")
async def subscribe_to_news_push(
    request: NewsPushSubscribeRequest,
    db_client: MongoClient = Depends(db.get_client)
):
    """
    Subscribe a user to news push notifications
    Stores subscription in 'news_subscriptions' collection
    """
    try:
        collection = get_news_subscriptions_collection(db_client)
        
        subscription_data = request.subscription.dict()
        endpoint = subscription_data["endpoint"]
        
        # Check if already subscribed
        existing = collection.find_one({"endpoint": endpoint})
        
        now = datetime.now(timezone.utc)
        
        if existing:
            # Update existing subscription
            collection.update_one(
                {"endpoint": endpoint},
                {
                    "$set": {
                        "keys": subscription_data["keys"],
                        "expirationTime": subscription_data.get("expirationTime"),
                        "user_agent": subscription_data.get("user_agent"),
                        "updated_at": now,
                        "is_active": True,
                    }
                }
            )
            logger.info(f"[news-push] Updated subscription: {endpoint[:50]}...")
            return {"status": "updated", "message": "Subscription updated successfully"}
        
        else:
            # Create new subscription
            subscription_doc = {
                "endpoint": endpoint,
                "keys": subscription_data["keys"],
                "expirationTime": subscription_data.get("expirationTime"),
                "user_agent": subscription_data.get("user_agent"),
                "created_at": now,
                "updated_at": now,
                "is_active": True,
                "notification_count": 0,
                "last_notified_at": None,
            }
            
            collection.insert_one(subscription_doc)
            logger.info(f"[news-push] New subscription created: {endpoint[:50]}...")
            return {"status": "subscribed", "message": "Subscribed successfully to news notifications"}
    
    except Exception as e:
        logger.error(f"[news-push] Error subscribing: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to subscribe to notifications"
        )


@news_push_router.post("/unsubscribe")
async def unsubscribe_from_news_push(
    request: NewsPushUnsubscribeRequest,
    db_client: MongoClient = Depends(db.get_client)
):
    """
    Unsubscribe a user from news push notifications
    Marks subscription as inactive (soft delete)
    """
    try:
        collection = get_news_subscriptions_collection(db_client)
        
        result = collection.update_one(
            {"endpoint": request.endpoint},
            {
                "$set": {
                    "is_active": False,
                    "unsubscribed_at": datetime.now(timezone.utc)
                }
            }
        )
        
        if result.matched_count == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Subscription not found"
            )
        
        logger.info(f"[news-push] Unsubscribed: {request.endpoint[:50]}...")
        return {"status": "unsubscribed", "message": "Unsubscribed successfully"}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[news-push] Error unsubscribing: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to unsubscribe"
        )


@news_push_router.get("/status/{endpoint:path}", response_model=NewsPushStatusResponse)
async def check_news_push_status(
    endpoint: str,
    db_client: MongoClient = Depends(db.get_client)
):
    """
    Check if an endpoint is subscribed to news notifications
    """
    try:
        collection = get_news_subscriptions_collection(db_client)
        
        subscription = collection.find_one({"endpoint": endpoint, "is_active": True})
        
        if subscription:
            return NewsPushStatusResponse(
                subscribed=True,
                subscription_date=subscription.get("created_at").isoformat() if subscription.get("created_at") else None,
                notification_count=subscription.get("notification_count", 0)
            )
        else:
            return NewsPushStatusResponse(
                subscribed=False,
                subscription_date=None,
                notification_count=0
            )
    
    except Exception as e:
        logger.error(f"[news-push] Error checking status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to check subscription status"
        )


@news_push_router.get("/stats", response_model=NewsPushStatsResponse)
async def get_news_push_stats(db_client: MongoClient = Depends(db.get_client)):
    """
    Get statistics about news push subscriptions
    """
    try:
        collection = get_news_subscriptions_collection(db_client)
        
        # Count active subscriptions
        total_active = collection.count_documents({"is_active": True})
        
        # Get total notifications sent
        pipeline = [
            {"$match": {"is_active": True}},
            {"$group": {"_id": None, "total_notifications": {"$sum": "$notification_count"}}}
        ]
        notification_stats = list(collection.aggregate(pipeline))
        total_notifications = notification_stats[0]["total_notifications"] if notification_stats else 0
        
        # Get last notification timestamp
        last_notified = collection.find_one(
            {"is_active": True, "last_notified_at": {"$ne": None}},
            sort=[("last_notified_at", -1)]
        )
        
        # Get oldest and newest subscriptions
        oldest = collection.find_one({"is_active": True}, sort=[("created_at", 1)])
        newest = collection.find_one({"is_active": True}, sort=[("created_at", -1)])
        
        return NewsPushStatsResponse(
            total_subscriptions=total_active,
            total_notifications_sent=total_notifications,
            last_notification_at=last_notified.get("last_notified_at").isoformat() if last_notified and last_notified.get("last_notified_at") else None,
            oldest_subscription=oldest.get("created_at").isoformat() if oldest and oldest.get("created_at") else None,
            newest_subscription=newest.get("created_at").isoformat() if newest and newest.get("created_at") else None
        )
    
    except Exception as e:
        logger.error(f"[news-push] Error getting stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve statistics"
        )


@news_push_router.post("/test")
async def send_news_push_test(
    request: NewsPushTestRequest,
    background_tasks: BackgroundTasks,
    db_client: MongoClient = Depends(db.get_client)
):
    """
    Send test notification to specific endpoint or all active subscriptions
    """
    try:
        collection = get_news_subscriptions_collection(db_client)
        
        # Get subscriptions to test
        if request.endpoint:
            # Test specific endpoint
            subscription = collection.find_one({"endpoint": request.endpoint, "is_active": True})
            if not subscription:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Active subscription not found for this endpoint"
                )
            subscriptions = [subscription]
        else:
            # Test all active subscriptions (limit to 5 for safety)
            subscriptions = list(collection.find({"is_active": True}).limit(5))
            
            if not subscriptions:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="No active subscriptions found"
                )
        
        # Send test notification in background
        background_tasks.add_task(
            _send_test_notification_background,
            subscriptions=subscriptions,
            title=request.title,
            body=request.body,
            url=request.url,
            icon=request.icon,
            image=request.image,
            collection=collection,
        )
        
        return {
            "status": "queued",
            "message": f"Test notification queued for {len(subscriptions)} subscription(s)",
            "count": len(subscriptions)
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[news-push] Error sending test: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send test notification"
        )


@news_push_router.get("/admin/subscriptions")
async def admin_get_all_subscriptions(
    current_admin: User = Depends(get_current_admin_user),
    db_client: MongoClient = Depends(db.get_client),
    page: int = 1,
    limit: int = 50,
    active_only: bool = True
):
    """
    Admin endpoint: Get list of all subscribed devices with details
    
    Returns paginated list of subscriptions with:
    - Device information (user agent, platform, browser)
    - Subscription dates and activity
    - Notification delivery statistics
    - Subscription status (active/expired)
    
    Query Parameters:
    - page: Page number (default: 1)
    - limit: Results per page (default: 50, max: 200)
    - active_only: Show only active subscriptions (default: true)
    """
    try:
        collection = get_news_subscriptions_collection(db_client)
        
        # Validate and limit page size
        limit = min(limit, 200)
        skip = (page - 1) * limit
        
        # Build query filter
        query = {"is_active": True} if active_only else {}
        
        # Get total count
        total_count = collection.count_documents(query)
        total_pages = (total_count + limit - 1) // limit  # Ceiling division
        
        # Get paginated subscriptions
        subscriptions = list(
            collection.find(query)
            .sort("created_at", DESCENDING)
            .skip(skip)
            .limit(limit)
        )
        
        # Format subscription data for admin view
        subscription_list = []
        for sub in subscriptions:
            # Extract device info from metadata
            metadata = sub.get("metadata", {})
            user_agent = metadata.get("user_agent", "Unknown")
            
            # Parse browser and platform from user agent
            browser = "Unknown"
            platform = metadata.get("platform", "Unknown")
            
            if "Chrome" in user_agent:
                browser = "Chrome"
            elif "Firefox" in user_agent:
                browser = "Firefox"
            elif "Safari" in user_agent and "Chrome" not in user_agent:
                browser = "Safari"
            elif "Edge" in user_agent:
                browser = "Edge"
            
            # Detect mobile vs desktop
            device_type = "Desktop"
            if any(mobile in user_agent for mobile in ["Mobile", "Android", "iPhone", "iPad"]):
                device_type = "Mobile"
            
            subscription_list.append({
                "id": str(sub["_id"]),
                "endpoint": sub.get("endpoint", "")[:60] + "...",  # Truncate endpoint
                "browser": browser,
                "platform": platform,
                "device_type": device_type,
                "language": metadata.get("language", "Unknown"),
                "subscribed_at": sub.get("created_at").isoformat() if sub.get("created_at") else None,
                "last_notified_at": sub.get("last_notified_at").isoformat() if sub.get("last_notified_at") else None,
                "notification_count": sub.get("notification_count", 0),
                "is_active": sub.get("is_active", False),
                "expired_at": sub.get("expired_at").isoformat() if sub.get("expired_at") else None,
            })
        
        # Calculate statistics
        total_active = collection.count_documents({"is_active": True})
        total_inactive = collection.count_documents({"is_active": False})
        
        # Get browser breakdown
        pipeline_browser = [
            {"$match": {"is_active": True}},
            {"$project": {
                "browser": {
                    "$cond": [
                        {"$regexMatch": {"input": "$metadata.user_agent", "regex": "Chrome"}},
                        "Chrome",
                        {"$cond": [
                            {"$regexMatch": {"input": "$metadata.user_agent", "regex": "Firefox"}},
                            "Firefox",
                            {"$cond": [
                                {"$regexMatch": {"input": "$metadata.user_agent", "regex": "Safari"}},
                                "Safari",
                                "Other"
                            ]}
                        ]}
                    ]
                }
            }},
            {"$group": {"_id": "$browser", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}}
        ]
        
        browser_stats = list(collection.aggregate(pipeline_browser))
        browser_breakdown = {item["_id"]: item["count"] for item in browser_stats}
        
        # Get device type breakdown
        pipeline_device = [
            {"$match": {"is_active": True}},
            {"$project": {
                "device_type": {
                    "$cond": [
                        {"$regexMatch": {"input": "$metadata.user_agent", "regex": "Mobile|Android|iPhone|iPad"}},
                        "Mobile",
                        "Desktop"
                    ]
                }
            }},
            {"$group": {"_id": "$device_type", "count": {"$sum": 1}}}
        ]
        
        device_stats = list(collection.aggregate(pipeline_device))
        device_breakdown = {item["_id"]: item["count"] for item in device_stats}
        
        logger.info(f"[news-push] Admin {current_admin.username} viewed subscriptions page {page}")
        
        return {
            "status": "success",
            "pagination": {
                "page": page,
                "limit": limit,
                "total_count": total_count,
                "total_pages": total_pages,
                "has_next": page < total_pages,
                "has_prev": page > 1
            },
            "statistics": {
                "total_active": total_active,
                "total_inactive": total_inactive,
                "total_all": total_active + total_inactive,
                "browser_breakdown": browser_breakdown,
                "device_breakdown": device_breakdown
            },
            "subscriptions": subscription_list
        }
    
    except Exception as e:
        logger.error(f"[news-push] Error getting admin subscriptions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve subscriptions: {str(e)}"
        )


@news_push_router.post("/admin/notify-latest", response_model=NewsPushBroadcastResponse)
async def admin_notify_latest_news(
    background_tasks: BackgroundTasks,
    current_admin: User = Depends(get_current_admin_user),
    db_client: MongoClient = Depends(db.get_client)
):
    """
    Admin endpoint: Manually trigger notification for the latest published news
    
    Use this from admin dashboard when:
    - Users report missing notifications
    - Need to resend notification for important breaking news
    - Testing notification delivery
    
    Sends notification for the most recent published news article.
    """
    try:
        # Get latest published news
        news_collection = db_client[db.db_name]["news"]
        latest_news = news_collection.find_one(
            {"published": True},
            sort=[("created_at", DESCENDING)]
        )
        
        if not latest_news:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No published news found to notify"
            )
        
        # Get active subscriptions count
        subscriptions_collection = get_news_subscriptions_collection(db_client)
        active_count = subscriptions_collection.count_documents({"is_active": True})
        
        if active_count == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No active subscriptions found"
            )
        
        # Prepare notification data
        news_id = str(latest_news["_id"])
        title = latest_news.get("title", "Latest News")
        content = latest_news.get("content", "")
        slug = latest_news.get("slug", news_id)
        image_url = latest_news.get("image_url")
        
        # Generate notification body (summary)
        body = _extract_meta_description(content, max_length=120)
        
        # Generate full URL
        news_url = f"{NEWS_BASE_URL}/news/{slug}"
        
        # Queue broadcast in background
        background_tasks.add_task(
            broadcast_to_all_news_subscribers,
            title=title,
            body=body,
            url=news_url,
            image=image_url,
            news_id=news_id,
            db_client=db_client
        )
        
        logger.info(f"[news-push] Admin {current_admin.username} triggered manual notification for news: {news_id}")
        
        return NewsPushBroadcastResponse(
            status="queued",
            message=f"Notification queued for latest news: {title[:50]}...",
            total_subscribers=active_count,
            news_id=news_id,
            news_title=title,
            news_url=news_url
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[news-push] Error in admin notify latest: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to queue notification: {str(e)}"
        )


# ==================== Helper Functions ====================

def _send_test_notification_background(
    subscriptions: List[dict],
    title: str,
    body: str,
    url: str,
    icon: Optional[str],
    image: Optional[str],
    collection,
):
    """Background task to send test notifications"""
    try:
        stats = broadcast_news_notification(
            subscriptions=subscriptions,
            title=title,
            body=body,
            url=url,
            icon=icon,
            image=image,
        )
        
        # Remove expired subscriptions
        if stats["expired_endpoints"]:
            collection.update_many(
                {"endpoint": {"$in": stats["expired_endpoints"]}},
                {"$set": {"is_active": False, "expired_at": datetime.now(timezone.utc)}}
            )
            logger.info(f"[news-push] Marked {len(stats['expired_endpoints'])} subscriptions as expired")
        
        logger.info(f"[news-push] Test notification complete: {stats}")
    
    except Exception as e:
        logger.error(f"[news-push] Error in test notification background task: {e}")


def broadcast_to_all_news_subscribers(
    title: str,
    body: str,
    url: str,
    icon: Optional[str] = None,
    image: Optional[str] = None,
    news_id: Optional[str] = None,
    db_client: Optional[MongoClient] = None,
) -> dict:
    """
    Broadcast notification to all active news subscribers
    This function is called from routes/news.py when news is published
    
    Args:
        title: News headline
        body: News summary
        url: Full article URL
        icon: Site icon (optional)
        image: Featured image (optional)
        news_id: Article ID (optional)
        db_client: MongoDB client (optional, will get new if not provided)
    
    Returns:
        Dict with broadcast statistics
    """
    try:
        # Get database client if not provided
        if db_client is None:
            db_client = db.get_client()
        
        collection = db_client[db.db_name]["news_subscriptions"]
        
        # Get all active subscriptions
        subscriptions = list(collection.find({"is_active": True}))
        
        if not subscriptions:
            logger.info("[news-push] No active subscriptions to notify")
            return {"status": "skipped", "reason": "no_subscriptions", "total": 0}
        
        logger.info(f"[news-push] Broadcasting to {len(subscriptions)} subscribers")
        
        # Broadcast notification
        stats = broadcast_news_notification(
            subscriptions=subscriptions,
            title=title,
            body=body,
            url=url,
            icon=icon,
            image=image,
            news_id=news_id,
        )
        
        # Update subscription statistics
        now = datetime.now(timezone.utc)
        
        # Increment notification count for successful deliveries
        successful_endpoints = [
            sub["endpoint"] for sub in subscriptions
            if sub["endpoint"] not in stats["expired_endpoints"]
        ][:stats["successful"]]
        
        if successful_endpoints:
            collection.update_many(
                {"endpoint": {"$in": successful_endpoints}},
                {
                    "$inc": {"notification_count": 1},
                    "$set": {"last_notified_at": now}
                }
            )
        
        # Mark expired subscriptions as inactive
        if stats["expired_endpoints"]:
            collection.update_many(
                {"endpoint": {"$in": stats["expired_endpoints"]}},
                {"$set": {"is_active": False, "expired_at": now}}
            )
            logger.info(f"[news-push] Cleaned up {len(stats['expired_endpoints'])} expired subscriptions")
        
        return {
            "status": "completed",
            "total": stats["total"],
            "successful": stats["successful"],
            "failed": stats["failed"],
            "expired": len(stats["expired_endpoints"]),
        }
    
    except Exception as e:
        logger.error(f"[news-push] Error broadcasting to subscribers: {e}")
        return {"status": "error", "error": str(e), "total": 0}


# ==================== Health Check ====================

@news_push_router.get("/health")
async def news_push_health_check():
    """
    Health check endpoint for news push system
    Validates NEWS_VAPID configuration
    """
    try:
        is_valid = validate_news_vapid_config()
        vapid_config = get_news_vapid_config()
        
        return {
            "status": "healthy" if is_valid else "unhealthy",
            "vapid_configured": bool(vapid_config["public_key"] and vapid_config["private_key"]),
            "subject": vapid_config["subject"],
            "service": "news-push",
        }
    
    except Exception as e:
        logger.error(f"[news-push] Health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "service": "news-push",
        }
