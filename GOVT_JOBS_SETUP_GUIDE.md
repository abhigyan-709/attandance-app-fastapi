# Government Jobs System - Setup & Quick Start Guide

## 🎯 What's Been Implemented

### ✅ Backend Components Created

1. **Models** (`models/govt_jobs.py`) - 850+ lines
   - Complete Pydantic models for job CRUD
   - Search and filtering models
   - Web scraping models
   - Analytics models
   - 60+ fields with validation

2. **Routes** (`routes/govt_jobs.py`) - 1,100+ lines
   - 30+ API endpoints (public + admin)
   - Job listing with advanced filters
   - Custom slug-based access
   - Admin CRUD operations
   - Bulk operations
   - Analytics endpoints

3. **Services** 
   - `services/govt_jobs_scraper.py` - Web scraping support
   - `services/govt_jobs_tasks.py` - Background maintenance tasks

4. **Main App** (`main.py`) - Router registered
   - Import added: `from routes.govt_jobs import govt_jobs_router`
   - Router registered: `app.include_router(govt_jobs_router, tags=["Government Jobs"])`

---

## 📋 Prerequisites

### Required
- Python 3.8+
- MongoDB (already configured)
- FastAPI (already installed)
- Existing authentication system (JWT)

### Optional (for advanced features)
```bash
# For web scraping
pip install beautifulsoup4 feedparser lxml requests

# For background tasks
pip install apscheduler

# For Celery (alternative to APScheduler)
pip install celery redis
```

---

## 🚀 Quick Start

### 1. Create MongoDB Indexes

Connect to MongoDB and run:

```javascript
// In MongoDB shell or Compass
use testdb;

// Create text index for search
db.govt_jobs.createIndex({
  "title": "text",
  "short_description": "text",
  "organization_name": "text",
  "post_name": "text"
});

// Create indexes for filters
db.govt_jobs.createIndex({ "status": 1 });
db.govt_jobs.createIndex({ "job_type": 1 });
db.govt_jobs.createIndex({ "category": 1 });
db.govt_jobs.createIndex({ "state": 1 });
db.govt_jobs.createIndex({ "organization_short_name": 1 });
db.govt_jobs.createIndex({ "slug": 1 }, { unique: true });
db.govt_jobs.createIndex({ "created_at": -1 });
db.govt_jobs.createIndex({ "application_end_date": 1 });

// Compound indexes for common queries
db.govt_jobs.createIndex({ "status": 1, "created_at": -1 });
db.govt_jobs.createIndex({ "status": 1, "application_end_date": 1 });
db.govt_jobs.createIndex({ "status": 1, "is_featured": 1 });
db.govt_jobs.createIndex({ "status": 1, "is_new": 1 });
```

### 2. Start the Server

```bash
cd /Users/abhigyan709/attandance-app-fastapi

# Development mode with auto-reload
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### 3. Access API Documentation

Open your browser:
- **Swagger UI**: https://api.projectdevops.in/docs
- **ReDoc**: https://api.projectdevops.in/redoc

Navigate to **Government Jobs** section to see all endpoints.

---

## 🧪 Testing the API

### Test Public Endpoints (No Auth Required)

#### 1. Get Dashboard Stats
```bash
curl -X GET "https://api.projectdevops.in/govt-jobs/stats/dashboard"
```

Expected response:
```json
{
  "total_active_jobs": 0,
  "total_vacancies": 0,
  "new_jobs_today": 0,
  "new_jobs_week": 0,
  "closing_soon": 0,
  "jobs_by_category": {},
  "jobs_by_type": {},
  "jobs_by_state": {},
  "top_organizations": []
}
```

#### 2. List Jobs with Filters
```bash
curl -X GET "https://api.projectdevops.in/govt-jobs/?status=Active&limit=20&page=1"
```

#### 3. Get Categories
```bash
curl -X GET "https://api.projectdevops.in/govt-jobs/filter/categories"
```

### Test Admin Endpoints (Auth Required)

First, get your admin JWT token:
```bash
# Login as admin
curl -X POST "https://api.projectdevops.in/login" \
  -H "Content-Type: application/json" \
  -d '{"username": "your_admin_username", "password": "your_password"}'
```

Copy the `access_token` from response, then:

#### 1. Create a Job
```bash
curl -X POST "https://api.projectdevops.in/govt-jobs/admin/create" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "UPSC Engineering Services 2024",
    "short_description": "Union Public Service Commission invites applications for Engineering Services",
    "organization_name": "Union Public Service Commission",
    "organization_short_name": "UPSC",
    "job_type": "Central Government",
    "category": "Engineering",
    "post_name": "Engineering Services",
    "total_vacancies": 234,
    "salary_text": "₹50,000 - ₹1,00,000 per month",
    "work_locations": ["All India"],
    "notification_date": "2024-01-01",
    "application_begin_date": "2024-01-05",
    "application_end_date": "2024-01-15",
    "apply_link": "https://upsc.gov.in/apply",
    "notification_link": "https://upsc.gov.in/notification.pdf",
    "application_mode": "Online",
    "status": "Active"
  }'
```

#### 2. Get All Jobs (Admin)
```bash
curl -X GET "https://api.projectdevops.in/govt-jobs/admin/all?page=1&limit=50" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
```

#### 3. Update Job Status
```bash
curl -X PATCH "https://api.projectdevops.in/govt-jobs/admin/JOB_ID/status?new_status=Active" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
```

---

## 📊 Sample Data Creation

Create sample jobs for testing:

```python
# sample_jobs_creator.py
import requests
import json
from datetime import datetime, timedelta

API_BASE = "https://api.projectdevops.in/govt-jobs"
ADMIN_TOKEN = "YOUR_ADMIN_TOKEN_HERE"

headers = {
    "Authorization": f"Bearer {ADMIN_TOKEN}",
    "Content-Type": "application/json"
}

sample_jobs = [
    {
        "title": "UPSC Engineering Services Examination 2024",
        "short_description": "Union Public Service Commission invites applications for Engineering Services Examination",
        "organization_name": "Union Public Service Commission",
        "organization_short_name": "UPSC",
        "job_type": "Central Government",
        "category": "Engineering",
        "post_name": "Engineering Services",
        "total_vacancies": 234,
        "salary_text": "₹50,000 - ₹1,00,000 per month",
        "work_locations": ["All India"],
        "notification_date": (datetime.now() - timedelta(days=2)).date().isoformat(),
        "application_begin_date": datetime.now().date().isoformat(),
        "application_end_date": (datetime.now() + timedelta(days=30)).date().isoformat(),
        "apply_link": "https://upsc.gov.in/apply",
        "notification_link": "https://upsc.gov.in/notification.pdf",
        "application_mode": "Online",
        "status": "Active",
        "is_featured": True
    },
    {
        "title": "SSC CHSL 2024 - Combined Higher Secondary Level",
        "short_description": "Staff Selection Commission recruiting for CHSL posts",
        "organization_name": "Staff Selection Commission",
        "organization_short_name": "SSC",
        "job_type": "Central Government",
        "category": "Clerical",
        "post_name": "Lower Division Clerk, Junior Secretariat Assistant",
        "total_vacancies": 4500,
        "salary_text": "₹25,500 - ₹81,100 per month",
        "work_locations": ["All India"],
        "notification_date": (datetime.now() - timedelta(days=1)).date().isoformat(),
        "application_begin_date": datetime.now().date().isoformat(),
        "application_end_date": (datetime.now() + timedelta(days=5)).date().isoformat(),
        "apply_link": "https://ssc.nic.in/apply",
        "notification_link": "https://ssc.nic.in/notification.pdf",
        "application_mode": "Online",
        "status": "Active",
        "is_featured": False
    },
    {
        "title": "Railway Recruitment Board NTPC 2024",
        "short_description": "RRB Non-Technical Popular Categories recruitment",
        "organization_name": "Railway Recruitment Board",
        "organization_short_name": "RRB",
        "job_type": "Central Government",
        "category": "Railway",
        "post_name": "Junior Clerk, Accounts Clerk, Traffic Assistant",
        "total_vacancies": 35000,
        "salary_text": "₹19,900 - ₹35,400 per month",
        "work_locations": ["All India"],
        "notification_date": (datetime.now() - timedelta(days=10)).date().isoformat(),
        "application_begin_date": (datetime.now() - timedelta(days=5)).date().isoformat(),
        "application_end_date": (datetime.now() + timedelta(days=20)).date().isoformat(),
        "apply_link": "https://indianrailways.gov.in/apply",
        "notification_link": "https://indianrailways.gov.in/notification.pdf",
        "application_mode": "Online",
        "status": "Active",
        "is_featured": True
    }
]

# Create jobs
for job in sample_jobs:
    response = requests.post(f"{API_BASE}/admin/create", headers=headers, json=job)
    if response.status_code == 201:
        print(f"✅ Created: {job['title']}")
        print(f"   Slug: {response.json()['slug']}")
    else:
        print(f"❌ Failed: {job['title']}")
        print(f"   Error: {response.text}")
```

Run with:
```bash
python sample_jobs_creator.py
```

---

## 🔧 Enable Background Tasks (Optional)

### Option 1: APScheduler (Recommended for single server)

1. Install APScheduler:
```bash
pip install apscheduler
```

2. Update `main.py`:
```python
# Add at the top
from services.govt_jobs_tasks import create_simple_scheduler

# Add startup event
@app.on_event("startup")
def start_background_tasks():
    """Start background maintenance tasks"""
    scheduler = create_simple_scheduler()
    if scheduler:
        logger.info("Government jobs scheduler started")
```

3. Restart server

### Option 2: Celery (For distributed systems)

1. Install Celery + Redis:
```bash
pip install celery redis
```

2. Set up Celery worker (see `services/govt_jobs_tasks.py` for examples)

3. Run:
```bash
# Terminal 1: Start Redis
redis-server

# Terminal 2: Start Celery worker
celery -A services.govt_jobs_tasks worker --loglevel=info

# Terminal 3: Start Celery beat (scheduler)
celery -A services.govt_jobs_tasks beat --loglevel=info
```

---

## 🕷️ Enable Web Scraping (Optional)

### 1. Install Dependencies
```bash
pip install beautifulsoup4 feedparser lxml requests
```

### 2. Add Scraping Source (via MongoDB)

```javascript
db.scraping_sources.insertOne({
  "source_name": "UPSC",
  "source_url": "https://upsc.gov.in/rss/recruitment-rss-feed",
  "scraping_type": "rss",
  "enabled": true,
  "default_values": {
    "organization_name": "Union Public Service Commission",
    "organization_short_name": "UPSC",
    "job_type": "Central Government",
    "category": "Engineering",
    "application_mode": "Online"
  },
  "created_at": new Date()
});
```

### 3. Trigger Manual Scraping

Add endpoint to routes (or run manually):
```python
@govt_jobs_router.post("/admin/scraper/run-all")
async def run_all_scrapers(
    current_admin: User = Depends(get_current_admin_user),
    db_client: MongoClient = Depends(db.get_client)
):
    """Manually trigger all scrapers"""
    from services.govt_jobs_scraper import ScraperManager
    
    scraper_manager = ScraperManager(db_client)
    scraper_manager.load_sources_from_db()
    results = scraper_manager.scrape_all()
    
    return results
```

---

## 📝 API Endpoints Summary

### Public Endpoints (No Auth)
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/govt-jobs/` | List jobs with filters |
| GET | `/govt-jobs/slug/{slug}` | Get job by slug |
| GET | `/govt-jobs/{job_id}` | Get job by ID |
| GET | `/govt-jobs/stats/dashboard` | Dashboard statistics |
| GET | `/govt-jobs/filter/categories` | Get all categories |
| GET | `/govt-jobs/filter/states` | Get all states |
| GET | `/govt-jobs/filter/organizations` | Get all organizations |
| GET | `/govt-jobs/featured/list` | Featured jobs |
| GET | `/govt-jobs/latest/list` | Latest jobs |
| GET | `/govt-jobs/closing-soon/list` | Closing soon jobs |
| GET | `/govt-jobs/category/{category}` | Jobs by category |
| GET | `/govt-jobs/state/{state}` | Jobs by state |
| POST | `/govt-jobs/{job_id}/click` | Track apply click |

### Admin Endpoints (Auth Required)
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/govt-jobs/admin/create` | Create job |
| PUT | `/govt-jobs/admin/{job_id}` | Update job |
| DELETE | `/govt-jobs/admin/{job_id}` | Delete job |
| GET | `/govt-jobs/admin/all` | Get all jobs (admin view) |
| PATCH | `/govt-jobs/admin/{job_id}/status` | Update status |
| PATCH | `/govt-jobs/admin/{job_id}/feature` | Toggle featured |
| POST | `/govt-jobs/admin/bulk-create` | Bulk create |
| POST | `/govt-jobs/admin/bulk-update-status` | Bulk update status |
| DELETE | `/govt-jobs/admin/bulk-delete` | Bulk delete |
| GET | `/govt-jobs/admin/check-slug/{slug}` | Check slug availability |
| POST | `/govt-jobs/admin/{job_id}/regenerate-slug` | Regenerate slug |

---

## 🎨 Frontend Implementation

See **GOVT_JOBS_UI_GUIDE.md** for complete UI implementation guide including:
- Admin Dashboard wireframes
- User Interface layouts
- Component specifications
- API integration examples
- State management setup
- Responsive design patterns

---

## 🐛 Troubleshooting

### Issue: Slug already exists
**Solution**: Slugs are auto-generated and must be unique. Use the regenerate slug endpoint or provide a custom slug.

### Issue: Jobs not appearing in search
**Solution**: Ensure MongoDB text index is created (see Step 1 above).

### Issue: Background tasks not running
**Solution**: Check APScheduler installation and restart server. Check logs for errors.

### Issue: Date validation errors
**Solution**: Ensure dates are in ISO format (YYYY-MM-DD) and application_end_date > application_begin_date.

### Issue: Admin endpoints returning 403
**Solution**: Ensure you're passing valid JWT token with admin role in Authorization header.

---

## 📈 Monitoring

### Check System Health
```bash
# Check active jobs count
curl "https://api.projectdevops.in/govt-jobs/stats/dashboard"

# Check recent scraping logs (add endpoint if needed)
# Use MongoDB directly
db.scraping_logs.find().sort({run_timestamp: -1}).limit(10)

# Check job flags are updating
db.govt_jobs.find({is_new: true}).count()
db.govt_jobs.find({is_urgent: true}).count()
```

---

## 🚀 Next Steps

1. **Create sample data** using script above
2. **Test all endpoints** in Swagger UI
3. **Enable background tasks** for auto-maintenance
4. **Set up web scraping** (optional)
5. **Start frontend development** using UI guide
6. **Deploy frontend** and connect to API
7. **Monitor and optimize** based on usage

---

## 📞 Support

- **API Documentation**: https://api.projectdevops.in/docs
- **UI Guide**: GOVT_JOBS_UI_GUIDE.md
- **Backend Code**: 
  - Models: `models/govt_jobs.py`
  - Routes: `routes/govt_jobs.py`
  - Services: `services/govt_jobs_scraper.py`, `services/govt_jobs_tasks.py`

---

## ✅ Implementation Checklist

Backend (Completed):
- [x] Pydantic models with validation
- [x] 30+ API endpoints (public + admin)
- [x] Custom slug system
- [x] Advanced search and filters
- [x] Auto-managed flags (NEW, URGENT)
- [x] Web scraping framework
- [x] Background tasks framework
- [x] Bulk operations
- [x] Analytics endpoints
- [x] Router registration

Frontend (Pending):
- [ ] User interface (homepage, listings, details)
- [ ] Admin dashboard (CRUD, analytics)
- [ ] Web scraping UI
- [ ] Responsive design
- [ ] SEO optimization

Infrastructure (Pending):
- [ ] MongoDB indexes
- [ ] Background task scheduler
- [ ] Web scraping sources configuration
- [ ] Frontend deployment
- [ ] Monitoring & alerts

**System is ready for testing and frontend development! 🎉**
