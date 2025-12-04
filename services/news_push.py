# services/news_push.py
"""
Fresh News Push Notification Service
Separate system for news reader subscriptions using Web Push API & VAPID
"""
import os
import json
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
from pywebpush import webpush, WebPushException

logger = logging.getLogger(__name__)


def get_news_vapid_config() -> Dict[str, str]:
    """
    Get VAPID configuration from environment variables (NEWS_VAPID_*)
    Separate from any other push notification systems
    """
    config = {
        "public_key": os.getenv("NEWS_VAPID_PUBLIC_KEY", ""),
        "private_key": os.getenv("NEWS_VAPID_PRIVATE_KEY", ""),
        "subject": os.getenv("NEWS_VAPID_SUBJECT", "mailto:connect@projectdevops.in"),
    }
    
    if not config["public_key"] or not config["private_key"]:
        logger.warning("NEWS_VAPID keys not configured. Push notifications will not work.")
    
    return config


def send_news_push_notification(
    subscription_info: Dict[str, Any],
    notification_payload: Dict[str, Any],
) -> bool:
    """
    Send a single push notification to a news subscriber
    
    Args:
        subscription_info: Dict with 'endpoint', 'keys' (p256dh, auth)
        notification_payload: Dict with 'title', 'body', 'icon', 'url', etc.
    
    Returns:
        True if sent successfully, False otherwise
    """
    try:
        vapid_config = get_news_vapid_config()
        
        if not vapid_config["public_key"] or not vapid_config["private_key"]:
            logger.error("NEWS_VAPID keys missing. Cannot send notification.")
            return False
        
        # Prepare VAPID claims
        vapid_claims = {
            "sub": vapid_config["subject"]
        }
        
        # Send the notification with TTL for mobile reliability
        # TTL = 24 hours (86400 seconds) - notification stays valid for 1 day
        # This helps with mobile devices that go offline or sleep
        webpush(
            subscription_info=subscription_info,
            data=json.dumps(notification_payload),
            vapid_private_key=vapid_config["private_key"],
            vapid_claims=vapid_claims,
            ttl=86400,  # 24 hours - critical for mobile devices
            timeout=10,
        )
        
        logger.info(f"[news-push] Notification sent successfully to: {subscription_info.get('endpoint', '')[:50]}...")
        return True
        
    except WebPushException as e:
        logger.error(f"[news-push] WebPushException: {e}")
        
        # Handle specific error codes
        if e.response and e.response.status_code in [404, 410]:
            logger.warning(f"[news-push] Subscription expired/invalid (status {e.response.status_code})")
            # Caller should mark this subscription as invalid
        
        return False
        
    except Exception as e:
        logger.error(f"[news-push] Unexpected error sending notification: {e}")
        return False


def broadcast_news_notification(
    subscriptions: List[Dict[str, Any]],
    title: str,
    body: str,
    url: str,
    icon: Optional[str] = None,
    image: Optional[str] = None,
    news_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Broadcast notification to multiple news subscribers
    
    Args:
        subscriptions: List of subscription dicts from MongoDB
        title: Notification title
        body: Notification body text
        url: URL to open when notification is clicked
        icon: Optional icon URL
        image: Optional large image URL
        news_id: Optional news article ID
    
    Returns:
        Dict with statistics: total, successful, failed, expired_endpoints
    """
    # Prepare notification payload with mobile optimization
    notification_payload = {
        "title": title,
        "body": body,
        "icon": icon or "https://gobarsahitimes.com/logo.png",
        "badge": icon or "https://gobarsahitimes.com/logo.png",  # Small icon for notification bar
        "url": url,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "tag": f"news-{news_id}" if news_id else "news-notification",  # Group notifications
        "requireInteraction": False,  # Don't force user to dismiss (better for mobile)
        "vibrate": [200, 100, 200],  # Vibration pattern for mobile attention
        "silent": False,  # Play notification sound
    }
    
    if image:
        notification_payload["image"] = image
    
    if news_id:
        notification_payload["data"] = {"news_id": news_id, "url": url}
    
    # Send to all subscriptions
    stats = {
        "total": len(subscriptions),
        "successful": 0,
        "failed": 0,
        "expired_endpoints": [],
    }
    
    for sub in subscriptions:
        try:
            # Extract subscription info
            subscription_info = {
                "endpoint": sub.get("endpoint"),
                "keys": sub.get("keys"),
            }
            
            # Send notification
            success = send_news_push_notification(subscription_info, notification_payload)
            
            if success:
                stats["successful"] += 1
            else:
                stats["failed"] += 1
                # Check if subscription is expired (endpoint in error)
                stats["expired_endpoints"].append(sub.get("endpoint"))
                
        except Exception as e:
            logger.error(f"[news-push] Error broadcasting to subscription: {e}")
            stats["failed"] += 1
    
    logger.info(f"[news-push] Broadcast complete: {stats['successful']}/{stats['total']} sent successfully")
    
    return stats


def validate_news_vapid_config() -> bool:
    """
    Validate that NEWS_VAPID environment variables are properly configured
    
    Returns:
        True if configuration is valid, False otherwise
    """
    config = get_news_vapid_config()
    
    if not config["public_key"]:
        logger.error("NEWS_VAPID_PUBLIC_KEY is not set")
        return False
    
    if not config["private_key"]:
        logger.error("NEWS_VAPID_PRIVATE_KEY is not set")
        return False
    
    if not config["subject"]:
        logger.error("NEWS_VAPID_SUBJECT is not set")
        return False
    
    # Basic validation of key format
    if not config["public_key"].startswith("B"):
        logger.error("NEWS_VAPID_PUBLIC_KEY has invalid format (should start with 'B')")
        return False
    
    logger.info("[news-push] NEWS_VAPID configuration is valid")
    return True
