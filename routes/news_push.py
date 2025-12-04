# routes/news_push.py
"""
Fresh News Push Notification Routes
Separate API endpoints for news reader push subscriptions
Uses 'news_subscriptions' MongoDB collection (separate from other systems)
"""
import logging
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, status
from pymongo import MongoClient
from datetime import datetime, timezone
from typing import Optional, List

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

logger = logging.getLogger(__name__)

news_push_router = APIRouter(prefix="/news-push", tags=["News Push"])


def get_news_subscriptions_collection(db_client: MongoClient = Depends(db.get_client)):
    """Get the news_subscriptions collection (separate collection)"""
    database = db_client[db.db_name]
    return database["news_subscriptions"]


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
