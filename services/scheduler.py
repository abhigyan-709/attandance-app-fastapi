# services/scheduler.py - Background scheduler for religious content
import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any
import threading
import time

from bson import ObjectId
from pymongo import MongoClient
from database.db import db
from models.news import ScheduleStatus, ReligiousContentType

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ReligiousContentScheduler:
    """Background scheduler for automatic religious content publishing"""
    
    def __init__(self):
        self.running = False
        self.thread = None
        self.check_interval = 60  # Check every minute
        
    def start(self):
        """Start the background scheduler"""
        if self.running:
            logger.warning("Scheduler is already running")
            return
            
        self.running = True
        self.thread = threading.Thread(target=self._scheduler_loop, daemon=True)
        self.thread.start()
        logger.info("Religious content scheduler started")
        
    def stop(self):
        """Stop the background scheduler"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        logger.info("Religious content scheduler stopped")
        
    def _scheduler_loop(self):
        """Main scheduler loop"""
        while self.running:
            try:
                self._process_scheduled_content()
                self._handle_recurring_content()
                time.sleep(self.check_interval)
            except Exception as e:
                logger.error(f"Scheduler error: {str(e)}")
                time.sleep(self.check_interval)
                
    def _process_scheduled_content(self):
        """Process scheduled content that's ready for publication"""
        try:
            db_client = db.get_client()
            current_time = datetime.utcnow()
            
            # Find content scheduled for publication
            scheduled_content = list(
                db_client[db.db_name]["scheduled_religious_content"].find({
                    "schedule_status": ScheduleStatus.SCHEDULED.value,
                    "schedule_date": {"$lte": current_time},
                    "auto_publish": True
                })
            )
            
            published_count = 0
            failed_count = 0
            
            for content in scheduled_content:
                try:
                    if self._publish_content(content, db_client):
                        published_count += 1
                    else:
                        failed_count += 1
                except Exception as e:
                    logger.error(f"Failed to publish content {content['_id']}: {str(e)}")
                    failed_count += 1
                    # Mark as expired
                    db_client[db.db_name]["scheduled_religious_content"].update_one(
                        {"_id": content["_id"]},
                        {"$set": {"schedule_status": ScheduleStatus.EXPIRED.value}}
                    )
            
            if published_count > 0 or failed_count > 0:
                logger.info(f"Published: {published_count}, Failed: {failed_count} religious content items")
                
        except Exception as e:
            logger.error(f"Error processing scheduled content: {str(e)}")
            
    def _publish_content(self, scheduled_content: Dict[str, Any], db_client: MongoClient) -> bool:
        """Publish a single scheduled content item"""
        try:
            # Create news post from scheduled content
            news_data = {
                "title": scheduled_content["title"],
                "content": scheduled_content["content"],
                "author_username": scheduled_content["author_username"],
                "categories": scheduled_content.get("categories", "धर्म"),
                "tags": scheduled_content.get("tags", []),
                "published": True,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
                "views": 0,
                "viewed_ips": [],
                "likes": 0,
                "liked_ips": [],
                "content_type": scheduled_content.get("content_type"),
                "schedule_date": scheduled_content.get("schedule_date"),
                "schedule_status": ScheduleStatus.PUBLISHED.value,
            }
            
            # Add religious-specific data
            if "rashifal_data" in scheduled_content:
                news_data["rashifal_data"] = scheduled_content["rashifal_data"]
            if "panchang_data" in scheduled_content:
                news_data["panchang_data"] = scheduled_content["panchang_data"]
            if "history_data" in scheduled_content:
                news_data["history_data"] = scheduled_content["history_data"]
            if "festival_data" in scheduled_content:
                news_data["festival_data"] = scheduled_content["festival_data"]
            
            # Generate SEO data
            news_data["slug"] = self._generate_seo_slug(scheduled_content["title"], "")
            news_data["meta_title"] = scheduled_content["title"]
            news_data["meta_description"] = self._extract_meta_description(scheduled_content["content"])
            news_data["keywords"] = self._extract_keywords(
                scheduled_content["title"], 
                scheduled_content["content"], 
                scheduled_content.get("categories", "")
            )
            
            # Insert into news collection
            result = db_client[db.db_name]["news"].insert_one(news_data)
            news_id = str(result.inserted_id)
            
            # Update SEO slug with actual ID
            news_data["slug"] = self._generate_seo_slug(scheduled_content["title"], news_id)
            db_client[db.db_name]["news"].update_one(
                {"_id": ObjectId(news_id)},
                {"$set": {"slug": news_data["slug"]}}
            )
            
            # Update scheduled content status
            db_client[db.db_name]["scheduled_religious_content"].update_one(
                {"_id": scheduled_content["_id"]},
                {"$set": {
                    "schedule_status": ScheduleStatus.PUBLISHED.value,
                    "published_at": datetime.utcnow(),
                    "published_news_id": news_id
                }}
            )
            
            logger.info(f"Successfully published religious content: {scheduled_content['title']} (ID: {news_id})")
            return True
            
        except Exception as e:
            logger.error(f"Failed to publish content {scheduled_content['_id']}: {str(e)}")
            return False
            
    def _handle_recurring_content(self):
        """Handle recurring content scheduling"""
        try:
            db_client = db.get_client()
            current_time = datetime.utcnow()
            
            # Find recurring content that needs rescheduling
            recurring_content = list(
                db_client[db.db_name]["scheduled_religious_content"].find({
                    "is_recurring": True,
                    "schedule_status": ScheduleStatus.PUBLISHED.value,
                    "next_schedule_date": {"$lte": current_time}
                })
            )
            
            for content in recurring_content:
                try:
                    self._create_next_recurring_instance(content, db_client)
                except Exception as e:
                    logger.error(f"Failed to create recurring instance for {content['_id']}: {str(e)}")
                    
        except Exception as e:
            logger.error(f"Error handling recurring content: {str(e)}")
            
    def _create_next_recurring_instance(self, content: Dict[str, Any], db_client: MongoClient):
        """Create next instance of recurring content"""
        
        # Calculate next schedule date
        next_date = content.get("next_schedule_date")
        if not next_date:
            return
            
        # Create new scheduled content
        new_content = {
            "content_type": content["content_type"],
            "title": self._update_title_with_date(content["title"], next_date),
            "content": self._update_content_with_date(content["content"], next_date),
            "schedule_date": next_date,
            "schedule_status": ScheduleStatus.SCHEDULED.value,
            "author_username": content["author_username"],
            "categories": content.get("categories", "धर्म"),
            "tags": content.get("tags", []),
            "auto_publish": content.get("auto_publish", True),
            "timezone": content.get("timezone", "Asia/Kolkata"),
            "created_at": datetime.utcnow(),
            "is_recurring": True,
            "recurrence_pattern": content.get("recurrence_pattern"),
            "template_id": content.get("template_id"),
        }
        
        # Copy religious-specific data if present
        for field in ["rashifal_data", "panchang_data", "history_data", "festival_data"]:
            if field in content:
                new_content[field] = content[field]
        
        # Calculate next schedule date for the recurring pattern
        recurrence = content.get("recurrence_pattern", "daily")
        if recurrence == "daily":
            new_content["next_schedule_date"] = next_date + timedelta(days=1)
        elif recurrence == "weekly":
            new_content["next_schedule_date"] = next_date + timedelta(weeks=1)
        elif recurrence == "monthly":
            new_content["next_schedule_date"] = next_date + timedelta(days=30)
        
        # Insert new scheduled content
        db_client[db.db_name]["scheduled_religious_content"].insert_one(new_content)
        
        # Update the original content's next schedule date
        db_client[db.db_name]["scheduled_religious_content"].update_one(
            {"_id": content["_id"]},
            {"$set": {"next_schedule_date": new_content["next_schedule_date"]}}
        )
        
        logger.info(f"Created next recurring instance for {content['title']}")
        
    def _update_title_with_date(self, title: str, date: datetime) -> str:
        """Update title with current date"""
        formatted_date = date.strftime("%d %B %Y")
        # Replace date placeholder or append date
        if "{{date}}" in title:
            return title.replace("{{date}}", formatted_date)
        elif date.strftime("%Y") not in title:
            return f"{title} - {formatted_date}"
        return title
        
    def _update_content_with_date(self, content: str, date: datetime) -> str:
        """Update content with current date"""
        formatted_date = date.strftime("%d %B %Y")
        weekday = date.strftime("%A")
        
        # Replace common placeholders
        content = content.replace("{{date}}", formatted_date)
        content = content.replace("{{weekday}}", weekday)
        content = content.replace("{{day}}", str(date.day))
        content = content.replace("{{month}}", date.strftime("%B"))
        content = content.replace("{{year}}", str(date.year))
        
        return content
        
    def _generate_seo_slug(self, title: str, news_id: str) -> str:
        """Generate SEO-friendly slug"""
        import re
        base_slug = re.sub(r'[^a-zA-Z0-9\u0900-\u097F]+', '-', title.lower()).strip('-')
        slug_part = base_slug[:50] if len(base_slug) > 50 else base_slug
        return f"{slug_part}-{news_id}" if news_id else slug_part
        
    def _extract_meta_description(self, content: str, max_length: int = 160) -> str:
        """Extract meta description from content"""
        from bs4 import BeautifulSoup
        if not content:
            return ""
        soup = BeautifulSoup(content, "html.parser")
        text = soup.get_text().strip()
        return text[:max_length] + "..." if len(text) > max_length else text
        
    def _extract_keywords(self, title: str, content: str, categories: str) -> List[str]:
        """Extract keywords from content"""
        import re
        keywords = []
        
        if categories:
            keywords.append(categories.lower())
            
        title_words = re.findall(r'[\u0900-\u097F]+|[a-zA-Z]+', title.lower())
        keywords.extend([word for word in title_words if len(word) > 3])
        
        return list(dict.fromkeys(keywords))[:10]


# Global scheduler instance
scheduler = ReligiousContentScheduler()

def start_scheduler():
    """Start the religious content scheduler"""
    scheduler.start()
    
def stop_scheduler():
    """Stop the religious content scheduler"""
    scheduler.stop()

# Auto-start scheduler when module is imported
# start_scheduler()  # Uncomment for auto-start