# services/govt_jobs_tasks.py
"""
Background Tasks for Government Jobs System

Features:
- Auto-update job status based on deadlines
- Auto-manage is_new and is_urgent flags
- Scheduled scraping jobs
- Analytics updates
- Database maintenance

Usage:
    Run with APScheduler or as Celery tasks
"""
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, Any
from pymongo import MongoClient

from database.db import db

logger = logging.getLogger(__name__)


class JobMaintenanceTasks:
    """Background maintenance tasks for government jobs"""
    
    def __init__(self, db_client: MongoClient):
        self.db = db_client
        self.database = db_client[db.db_name]
        self.collection = self.database["govt_jobs"]
    
    def update_job_statuses(self) -> Dict[str, int]:
        """
        Auto-update job statuses based on application deadlines
        
        Logic:
        - Active jobs with past application_end_date → Closed
        - Pending Review jobs older than 30 days → Cancelled
        
        Returns:
            {"closed_count": int, "cancelled_count": int}
        """
        now = datetime.now(timezone.utc)
        counts = {"closed_count": 0, "cancelled_count": 0}
        
        try:
            # Close expired active jobs
            result_closed = self.collection.update_many(
                {
                    "status": "Active",
                    "application_end_date": {"$lt": now}
                },
                {
                    "$set": {
                        "status": "Closed",
                        "updated_at": now,
                        "updated_by": "system"
                    }
                }
            )
            counts["closed_count"] = result_closed.modified_count
            
            # Cancel old pending reviews
            thirty_days_ago = now - timedelta(days=30)
            result_cancelled = self.collection.update_many(
                {
                    "status": "Pending Review",
                    "created_at": {"$lt": thirty_days_ago}
                },
                {
                    "$set": {
                        "status": "Cancelled",
                        "updated_at": now,
                        "updated_by": "system"
                    }
                }
            )
            counts["cancelled_count"] = result_cancelled.modified_count
            
            logger.info(f"Status update: {counts['closed_count']} closed, {counts['cancelled_count']} cancelled")
            return counts
        
        except Exception as e:
            logger.error(f"Error updating job statuses: {e}")
            return counts
    
    def update_job_flags(self) -> Dict[str, int]:
        """
        Update is_new and is_urgent flags for all active jobs
        
        Logic:
        - is_new: True for jobs created within 3 days
        - is_urgent: True for jobs with deadline within 7 days
        
        Returns:
            {"new_updated": int, "urgent_updated": int}
        """
        now = datetime.now(timezone.utc)
        counts = {"new_updated": 0, "urgent_updated": 0}
        
        try:
            # Update is_new flag
            three_days_ago = now - timedelta(days=3)
            
            # Set is_new = True for recent jobs
            result_new_true = self.collection.update_many(
                {
                    "created_at": {"$gte": three_days_ago},
                    "is_new": {"$ne": True}
                },
                {"$set": {"is_new": True, "updated_at": now}}
            )
            
            # Set is_new = False for old jobs
            result_new_false = self.collection.update_many(
                {
                    "created_at": {"$lt": three_days_ago},
                    "is_new": True
                },
                {"$set": {"is_new": False, "updated_at": now}}
            )
            
            counts["new_updated"] = result_new_true.modified_count + result_new_false.modified_count
            
            # Update is_urgent flag
            seven_days_ahead = now + timedelta(days=7)
            
            # Set is_urgent = True for jobs closing soon
            result_urgent_true = self.collection.update_many(
                {
                    "status": "Active",
                    "application_end_date": {"$lte": seven_days_ahead, "$gte": now},
                    "is_urgent": {"$ne": True}
                },
                {"$set": {"is_urgent": True, "updated_at": now}}
            )
            
            # Set is_urgent = False for others
            result_urgent_false = self.collection.update_many(
                {
                    "$or": [
                        {"application_end_date": {"$gt": seven_days_ahead}},
                        {"application_end_date": {"$lt": now}},
                        {"status": {"$ne": "Active"}}
                    ],
                    "is_urgent": True
                },
                {"$set": {"is_urgent": False, "updated_at": now}}
            )
            
            counts["urgent_updated"] = result_urgent_true.modified_count + result_urgent_false.modified_count
            
            logger.info(f"Flags update: {counts['new_updated']} new flags, {counts['urgent_updated']} urgent flags")
            return counts
        
        except Exception as e:
            logger.error(f"Error updating job flags: {e}")
            return counts
    
    def cleanup_old_jobs(self, days: int = 365) -> int:
        """
        Archive or delete very old jobs
        
        Args:
            days: Age threshold (default: 1 year)
        
        Returns:
            Number of jobs deleted
        """
        try:
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
            
            result = self.collection.delete_many({
                "status": {"$in": ["Closed", "Cancelled"]},
                "updated_at": {"$lt": cutoff_date}
            })
            
            logger.info(f"Cleaned up {result.deleted_count} old jobs")
            return result.deleted_count
        
        except Exception as e:
            logger.error(f"Error cleaning up old jobs: {e}")
            return 0
    
    def update_analytics(self) -> Dict[str, Any]:
        """
        Update analytics data for all jobs
        
        Calculates:
        - Click-through rate (CTR)
        - Performance scores
        
        Returns:
            {"updated_count": int}
        """
        try:
            updated_count = 0
            
            # Get all jobs with views
            jobs = self.collection.find({"views_count": {"$gt": 0}})
            
            for job in jobs:
                views = job.get("views_count", 0)
                clicks = job.get("clicks_count", 0)
                
                # Calculate CTR
                ctr = (clicks / views * 100) if views > 0 else 0
                
                # Update
                self.collection.update_one(
                    {"_id": job["_id"]},
                    {"$set": {"analytics.ctr": round(ctr, 2)}}
                )
                updated_count += 1
            
            logger.info(f"Updated analytics for {updated_count} jobs")
            return {"updated_count": updated_count}
        
        except Exception as e:
            logger.error(f"Error updating analytics: {e}")
            return {"updated_count": 0}
    
    def run_all_maintenance(self) -> Dict[str, Any]:
        """
        Run all maintenance tasks
        
        Returns:
            Summary of all task results
        """
        logger.info("Starting government jobs maintenance tasks...")
        
        results = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "statuses": self.update_job_statuses(),
            "flags": self.update_job_flags(),
            "analytics": self.update_analytics(),
            "cleanup": {"deleted_count": 0}  # Optional: run cleanup less frequently
        }
        
        logger.info(f"Maintenance completed: {results}")
        return results


class ScrapingScheduler:
    """Schedule and run web scraping jobs"""
    
    def __init__(self, db_client: MongoClient):
        self.db = db_client
    
    def run_scheduled_scraping(self) -> Dict[str, Any]:
        """
        Run web scraping for all enabled sources
        
        Returns:
            Scraping results summary
        """
        try:
            from services.govt_jobs_scraper import ScraperManager
            
            scraper_manager = ScraperManager(self.db)
            scraper_manager.load_sources_from_db()
            
            results = scraper_manager.scrape_all()
            
            logger.info(f"Scraping completed: {results['total_new']} new jobs from {results['total_scraped']} total")
            return results
        
        except Exception as e:
            logger.error(f"Error in scheduled scraping: {e}")
            return {
                "error": str(e),
                "total_scraped": 0,
                "total_new": 0
            }


# ==================== Task Scheduling Setup ====================

"""
Example: Using APScheduler

from apscheduler.schedulers.background import BackgroundScheduler
from database.db import db

# Initialize
scheduler = BackgroundScheduler()
db_client = db.get_client()
maintenance = JobMaintenanceTasks(db_client)
scraping = ScrapingScheduler(db_client)

# Schedule maintenance tasks
scheduler.add_job(
    maintenance.update_job_statuses,
    'cron',
    hour=1,
    minute=0,
    id='update_statuses'
)

scheduler.add_job(
    maintenance.update_job_flags,
    'interval',
    hours=6,
    id='update_flags'
)

scheduler.add_job(
    maintenance.update_analytics,
    'cron',
    hour=3,
    minute=0,
    id='update_analytics'
)

# Schedule scraping (every 4 hours)
scheduler.add_job(
    scraping.run_scheduled_scraping,
    'interval',
    hours=4,
    id='scrape_jobs'
)

# Weekly cleanup
scheduler.add_job(
    maintenance.cleanup_old_jobs,
    'cron',
    day_of_week='sun',
    hour=2,
    minute=0,
    id='cleanup_jobs'
)

# Start scheduler
scheduler.start()
"""

"""
Example: Using Celery

from celery import Celery
from database.db import db

app = Celery('govt_jobs_tasks', broker='redis://localhost:6379/0')

@app.task
def update_job_statuses():
    db_client = db.get_client()
    maintenance = JobMaintenanceTasks(db_client)
    return maintenance.update_job_statuses()

@app.task
def update_job_flags():
    db_client = db.get_client()
    maintenance = JobMaintenanceTasks(db_client)
    return maintenance.update_job_flags()

@app.task
def run_scraping():
    db_client = db.get_client()
    scraping = ScrapingScheduler(db_client)
    return scraping.run_scheduled_scraping()

# Configure periodic tasks in celery beat
app.conf.beat_schedule = {
    'update-statuses-daily': {
        'task': 'update_job_statuses',
        'schedule': crontab(hour=1, minute=0),
    },
    'update-flags-6h': {
        'task': 'update_job_flags',
        'schedule': 21600.0,  # 6 hours
    },
    'scrape-jobs-4h': {
        'task': 'run_scraping',
        'schedule': 14400.0,  # 4 hours
    },
}
"""

"""
Example: Manual execution via FastAPI endpoint

@app.post("/admin/maintenance/run-all")
async def run_maintenance(
    current_admin: User = Depends(get_current_admin_user),
    db_client: MongoClient = Depends(db.get_client)
):
    maintenance = JobMaintenanceTasks(db_client)
    results = maintenance.run_all_maintenance()
    return results
"""


# ==================== Simple Cron Runner ====================

def create_simple_scheduler():
    """
    Create a simple scheduler using APScheduler
    
    Add this to main.py startup event:
    
    @app.on_event("startup")
    def start_scheduler():
        from services.govt_jobs_tasks import create_simple_scheduler
        create_simple_scheduler()
    """
    try:
        from apscheduler.schedulers.background import BackgroundScheduler
        
        scheduler = BackgroundScheduler()
        db_client = db.get_client()
        maintenance = JobMaintenanceTasks(db_client)
        scraping = ScrapingScheduler(db_client)
        
        # Daily status update at 1 AM
        scheduler.add_job(
            maintenance.update_job_statuses,
            'cron',
            hour=1,
            minute=0,
            id='update_statuses'
        )
        
        # Update flags every 6 hours
        scheduler.add_job(
            maintenance.update_job_flags,
            'interval',
            hours=6,
            id='update_flags'
        )
        
        # Scraping every 4 hours
        scheduler.add_job(
            scraping.run_scheduled_scraping,
            'interval',
            hours=4,
            id='scrape_jobs'
        )
        
        scheduler.start()
        logger.info("Government jobs scheduler started successfully")
        
        return scheduler
    
    except ImportError:
        logger.warning("APScheduler not installed. Install with: pip install apscheduler")
        return None
    except Exception as e:
        logger.error(f"Failed to start scheduler: {e}")
        return None
