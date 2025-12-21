# FastAPI Enterprise Platform - AI Coding Agent Instructions

## Quick Reference

| Aspect | Pattern |
|--------|---------|
| **Database** | `db_client: MongoClient = Depends(db.get_client)` → `db_client["testdb"]["collection_name"]` |
| **Auth** | `current_user: User = Depends(get_current_user)` from `routes/user.py` |
| **S3 Upload** | `s3_client.upload_fileobj()` → `get_cdn_url(key)` from `routes/config.py` |
| **Roles** | `admin`, `author`, `moderator`, `user`, `vendor` |

## Core Architecture

**Multi-tenant SaaS**: Attendance, news/blogs, govt jobs, grievance redressal  
**Stack**: FastAPI + MongoDB + AWS (S3, Secrets Manager) + Firebase FCM + Google Gemini AI  
**Production**: `https://api.projectdevops.in` | Docs: `/docs`

### Route Handler Template
```python
from fastapi import APIRouter, Depends, HTTPException
from pymongo import MongoClient
from database.db import db
from routes.user import get_current_user
from models.user import User

router = APIRouter()

@router.post("/endpoint", tags=["Category Name"])
async def handler(
    db_client: MongoClient = Depends(db.get_client),
    current_user: User = Depends(get_current_user)  # Remove for public endpoints
):
    collection = db_client[db.db_name]["your_collection"]
    # Always serialize ObjectId: str(doc["_id"])
```

### Key Files
- **DB singleton**: `database/db.py` - MongoDB URI from AWS Secrets Manager (`my_mongo_secret`)
- **Auth**: `authentication/auth.py` - JWT with `SECRET_KEY`, `ALGORITHM`, `create_access_token()`
- **S3/CDN config**: `routes/config.py` - `get_cdn_url()`, `s3_client`, AWS env vars
- **FCM push**: `services/fcm.py` - Firebase HTTP v1 with `FIREBASE_SA_PATH` or `FIREBASE_SA_JSON`
- **Router registration**: `main.py` - All `app.include_router()` calls

## Critical Patterns

### MongoDB ObjectId - ALWAYS serialize
```python
# ✅ Correct
{"id": str(doc["_id"]), "name": doc["name"]}
# ❌ Wrong - causes JSON serialization error
{"id": doc["_id"]}
```

### Role-Based Access
```python
if current_user.role not in ["admin", "author"]:
    raise HTTPException(403, "Insufficient permissions")
```

### Date/Time - Store UTC, Display IST
```python
from datetime import datetime
import pytz
IST = pytz.timezone("Asia/Kolkata")
# Store: datetime.utcnow()
# Display: utc_time.replace(tzinfo=pytz.UTC).astimezone(IST)
```

### S3 File Upload Pattern
```python
from routes.config import s3_client, AWS_BUCKET_NAME, get_cdn_url
import uuid

file_key = f"blogs/{uuid.uuid4()}-{file.filename}"
s3_client.upload_fileobj(file.file, AWS_BUCKET_NAME, file_key, 
                         ExtraArgs={"ContentType": file.content_type})
url = get_cdn_url(file_key)
```

## Development Commands

```bash
# Setup
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Run (reload on changes)
uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# Docker
docker build -t attendance-api . && docker run -p 8000:8000 --env-file .env attendance-api
```

## Testing Approach

**No pytest** - Use shell scripts with curl:
- `test_author_system.sh`, `test_govt_jobs_api.sh`, `test_scheduling.sh`
- Pattern: curl with JWT token, parse JSON with Python one-liners
- Swagger UI at `/docs` for interactive testing

## Required Environment Variables

```bash
# AWS (S3, Secrets Manager)
AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_REGION=ap-south-1, AWS_BUCKET_NAME=projectdevops-blogs-new

# Firebase Push
FIREBASE_PROJECT_ID, FIREBASE_SA_PATH or FIREBASE_SA_JSON

# AI Generation
GEMINI_MODEL=gemini-1.5-flash, GOOGLE_API_KEY

# Email (SMTP)
MAIL_USERNAME, MAIL_PASSWORD, MAIL_FROM, MAIL_PORT, MAIL_SERVER

# CDN (optional)
CLOUDFRONT_DOMAIN, CLOUDFRONT_ENABLED=true
```

**Runtime secrets** (AWS Secrets Manager): `MONGO_URI` from secret `my_mongo_secret`

## Feature-Specific Notes

| Feature | Key Files | Collections |
|---------|-----------|-------------|
| News/Blogs | `routes/news.py`, `routes/blogs.py` | `news`, `blogs` |
| Govt Jobs | `routes/govt_jobs.py`, `services/govt_jobs_scraper.py` | `govt_jobs`, `scraping_sources` |
| Grievance | `routes/grievance.py` | `grievance_info`, `grievance_complaints` |
| Push Notifications | `routes/push.py`, `services/fcm.py` | `push_subscriptions` |
| AI Generators | `routes/dockerfile_gen.py`, `routes/sql_gen.py` | Uses Gemini API |

### Background Scheduler
`main.py` runs horoscope scheduler in daemon thread - check `_process_scheduled_horoscopes()` for pattern.

### Hindi Content (News)
`routes/news.py` has `HINDI_TO_LATIN` mapping for URL slug transliteration.

## Gotchas

1. **JWT tokens** must have `sub` field - `create_access_token()` handles fallback to `username`
2. **CORS origins** in `main.py` are explicit - don't add without security review
3. **Password reset** uses separate `RESET_SECRET_KEY` with 15-min expiry
4. **Collections use `testdb`** - hardcoded in `db.db_name`, not configurable
