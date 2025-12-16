# FastAPI Enterprise Platform - AI Coding Agent Instructions

## Project Overview

**Multi-tenant SaaS platform** combining attendance management, news/blog publishing, government jobs aggregation, and grievance redressal. Built with FastAPI, MongoDB, AWS services, Google Gemini AI, and Firebase push notifications.

**Production API**: `https://api.projectdevops.in` | **Multiple frontends**: blogs.projectdevops.in, gtnews18.in, tools.projectdevops.in

## Architecture & Core Patterns

### Database (MongoDB)
- **Singleton pattern** in [database/db.py](database/db.py): MongoDB URI from AWS Secrets Manager (`my_mongo_secret`, region: ap-south-1)
- **Database name**: Always `testdb` (hardcoded in `db.db_name`)
- **Dependency injection**: `db_client: MongoClient = Depends(db.get_client)` in ALL route handlers
- **ObjectId serialization**: Convert to string for JSON: `str(doc["_id"])` or use `{"_id": ObjectId(id_str)}`
- **Collections**: `user`, `attendance`, `blogs`, `news`, `govt_jobs`, `grievance_complaints`, `active_sessions`, `push_subscriptions`, etc.

### Authentication & Authorization
**Token creation** ([authentication/auth.py](authentication/auth.py)):
```python
from authentication.auth import SECRET_KEY, ALGORITHM, create_access_token
access_token = create_access_token(data={"username": username})
```
**Protected routes** ([routes/user.py](routes/user.py#L68-L87)):
```python
from routes.user import get_current_user
async def endpoint(current_user: User = Depends(get_current_user)):
    # current_user.role: "admin", "user", "author", "moderator", "vendor"
    # current_user.username, .email, .full_name
```
**Google OAuth** ([authentication/google_auth.py](authentication/google_auth.py)): Verify ID tokens, fetch secrets from AWS Secrets Manager

### Router Registration Pattern
[main.py](main.py#L82-L105) includes routers with prefix/tags:
```python
app.include_router(blog_router)                              # /blogs/*
app.include_router(news_router)                              # /news/*
app.include_router(govt_jobs_router, prefix="/govt-jobs")    # /govt-jobs/*
app.include_router(grievance_router)                         # /grievance/*
```
**New route modules** must follow [routes/attendance.py](routes/attendance.py) pattern:
```python
router = APIRouter()
@router.post("/endpoint", tags=["Category Name"])
async def handler(
    db_client: MongoClient = Depends(db.get_client),
    current_user: User = Depends(get_current_user)
):
```

### AWS Integrations
- **S3 uploads** ([routes/blogs.py](routes/blogs.py#L43-L49)): Use `s3_client` from [routes/config.py](routes/config.py#L7-L11) (boto3, bucket: `projectdevops-blogs-new`)
- **Secrets Manager** ([database/db.py](database/db.py#L12-L29)): Fetch `MONGO_URI`, Google OAuth secrets at runtime
- **CloudFront CDN** ([routes/config.py](routes/config.py#L22-L31)): `get_cdn_url()` converts S3 keys to CDN URLs

### Firebase Cloud Messaging (Push Notifications)
**FCM HTTP v1** ([services/fcm.py](services/fcm.py)):
- Service account from `FIREBASE_SA_PATH` or `FIREBASE_SA_JSON` env vars
- Project ID: `FIREBASE_PROJECT_ID`
- Send to multiple tokens with notification + data payload
- Used by [routes/push.py](routes/push.py) for web push and [routes/news_push.py](routes/news_push.py) for news alerts

### AI/Gemini Integration
**Code generation routes** use Google Gemini (`gemini-1.5-flash` from `GEMINI_MODEL` env):
- [routes/dockerfile_gen.py](routes/dockerfile_gen.py), [routes/sql_gen.py](routes/sql_gen.py), [routes/cicd_gen.py](routes/cicd_gen.py), [routes/cli_gen.py](routes/cli_gen.py), [routes/diagram_gen.py](routes/diagram_gen.py)
- All use [services/generator.py](services/generator.py) for Gemini API calls

## Feature-Specific Implementation Notes

### News/Blogs System ([routes/news.py](routes/news.py), [routes/blogs.py](routes/blogs.py))
**Scheduled publishing** ([routes/news.py](routes/news.py#L2233-L2261)):
- Posts have `scheduled_publish: bool` and `scheduled_at: datetime` (IST timezone)
- Background task auto-publishes when `scheduled_at` time reached
- Status transitions: draft → scheduled → published

**Hindi content** ([routes/news.py](routes/news.py#L67-L105)):
- Transliterate Hindi to Latin for URL slugs using `HINDI_TO_LATIN` mapping
- Horoscope system with 12 zodiac signs (Mesh, Vrishchik, etc.)

**Push notifications** ([routes/news.py](routes/news.py#L57-L76)):
- Call `/push/notify-new-blog` with `ADMIN_API_TOKEN` header after publish
- Separate fresh news push: [routes/news_push.py](routes/news_push.py), [services/news_push.py](services/news_push.py)

### Government Jobs ([routes/govt_jobs.py](routes/govt_jobs.py))
**Scraping system** ([services/govt_jobs_scraper.py](services/govt_jobs_scraper.py)):
- RSS feeds + HTML scraping with BeautifulSoup
- Deduplication via content hash
- Collections: `govt_jobs`, `scraping_sources`, `scraping_logs`

**Maintenance tasks** ([services/govt_jobs_tasks.py](services/govt_jobs_tasks.py)):
- Auto-close jobs past `application_end_date`
- Update `is_new`, `is_urgent` flags
- Run with APScheduler (not included yet—implement separately)

### Grievance Redressal ([routes/grievance.py](routes/grievance.py))
**Compliance system** for news platforms:
- Public info endpoints (no auth): `/grievance/info`
- Complaint submission with acknowledgment emails ([routes/send_email.py](routes/send_email.py))
- Collections: `grievance_info`, `grievance_complaints`
- Roles: Grievance Officer, Self Regulatory Body, News Editors

### Designation System ([routes/designation.py](routes/designation.py))
**Master designation list** for user roles:
- 15 defaults: Chief Editor, Regional Editor, Reporter, etc.
- `/designations/initialize` (admin-only) seeds on deployment
- Auto-assigns designations to grievances based on author role

## Development Workflow

### Local Setup
```bash
python -m venv .venv && source .venv/bin/activate  # or .venv\Scripts\activate on Windows
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```
**API docs**: http://localhost:8000/docs (Swagger with obsidian theme)

### Testing
**Manual testing** with shell scripts:
- [test_author_system.sh](test_author_system.sh), [test_govt_jobs_api.sh](test_govt_jobs_api.sh), [test_scheduling.sh](test_scheduling.sh), [test_production_biodata.sh](test_production_biodata.sh)
- Pattern: curl with JWT token, parse JSON with Python one-liners
- No pytest/unittest framework (use shell scripts or manual Swagger UI)

### Docker
[Dockerfile](Dockerfile): Python 3.10-slim, installs DejaVu fonts for Pillow, runs on port 8000
```bash
docker build -t attendance-api .
docker run -p 8000:8000 --env-file .env attendance-api
```

### Deployment
1. Git pull on production server
2. Restart service (systemd/pm2/docker)
3. **One-time setup**: Run `/designations/initialize` with admin token (see [DEPLOYMENT_CHECKLIST.md](DEPLOYMENT_CHECKLIST.md))

### Environment Variables (.env)
**Required**:
- `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_REGION=ap-south-1`, `AWS_BUCKET_NAME=projectdevops-blogs-new`
- `FIREBASE_PROJECT_ID`, `FIREBASE_SA_PATH` or `FIREBASE_SA_JSON`
- `GEMINI_MODEL=gemini-1.5-flash`, `GOOGLE_API_KEY`
- `MAIL_USERNAME`, `MAIL_PASSWORD`, `MAIL_FROM`, `MAIL_PORT`, `MAIL_SERVER`
- `CLOUDFRONT_DOMAIN`, `CLOUDFRONT_ENABLED=true` (optional CDN)
- `ADMIN_API_TOKEN`, `PUBLIC_API_BASE=https://api.projectdevops.in`, `NEWS_BASE_URL=https://gtnews18.in`

**Fetched at runtime** (AWS Secrets Manager):
- `MONGO_URI` (secret: `my_mongo_secret`)
- Google OAuth secrets (secret: varies by [authentication/secrets.py](authentication/secrets.py))

## Common Patterns & Gotchas

### Date/Time Handling
- **Store in UTC**: `datetime.utcnow()` for MongoDB
- **Display in IST**: Convert UTC to IST (pytz) for API responses ([routes/news.py](routes/news.py) uses IST timezone extensively)
- **Scheduled posts**: Accept IST datetime from frontend, normalize to UTC for storage

### Role-Based Access
**Check pattern**:
```python
if current_user.role not in ["admin", "author"]:
    raise HTTPException(403, "Insufficient permissions")
```
**Roles**: admin (full access), author (content creation), moderator (content moderation), user (basic), vendor (products)

### Email Sending
[routes/send_email.py](routes/send_email.py):
- `send_registration_email()`, `send_password_reset_email()`, `send_grievance_acknowledgment()`
- Uses [models/email_config.py](models/email_config.py) EmailSettings from env vars
- **HTML templates** with company branding, fallback text

### S3 File Uploads
Pattern from [routes/blogs.py](routes/blogs.py#L265-L288):
```python
file_key = f"blogs/{uuid.uuid4()}-{file.filename}"
s3_client.upload_fileobj(file.file, AWS_BUCKET_NAME, file_key, ExtraArgs={"ContentType": file.content_type})
url = get_cdn_url(file_key)  # CloudFront or S3 direct
```

### CORS Configuration
[main.py](main.py#L65-L77): Specific origins allowed (production domains + localhost for dev)
- **Do NOT add new origins** without security review
- Headers include `x-admin-token` for internal API calls

### Critical Bug Fixes
1. **JWT "sub" field** ([authentication/auth.py](authentication/auth.py#L20-L22)): Fallback to `username` if `sub` missing
2. **Password reset tokens** ([routes/user.py](routes/user.py#L53-L54)): Separate `RESET_SECRET_KEY`, 15-min expiry
3. **ObjectId in responses**: Always `str(doc["_id"])` or catch serialization errors

## Documentation References
- [AUTHOR_MODERATOR_SYSTEM.md](AUTHOR_MODERATOR_SYSTEM.md): Author profiles, articles_count auto-update
- [DESIGNATION_SYSTEM.md](DESIGNATION_SYSTEM.md): Master designation list, API endpoints
- [GOVT_JOBS_SETUP_GUIDE.md](GOVT_JOBS_SETUP_GUIDE.md): Jobs system architecture, scraping config
- [GRIEVANCE_SYSTEM.md](GRIEVANCE_SYSTEM.md): Compliance requirements, email templates
- [SURVEY_API_GUIDE.md](SURVEY_API_GUIDE.md): Survey creation, responses, analytics
