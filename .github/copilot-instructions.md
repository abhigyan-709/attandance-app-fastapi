# FastAPI Attendance App - AI Coding Agent Instructions

## Project Architecture

This is a **FastAPI-based enterprise attendance and user management system** with MongoDB backend, JWT authentication, and AWS integrations.

### Core Structure
- **`main.py`**: Central FastAPI app with CORS, router registration, and Swagger config
- **`routes/`**: Feature-organized route modules (user, attendance, blogs, etc.)
- **`models/`**: Pydantic models for request/response validation
- **`database/db.py`**: MongoDB singleton with AWS Secrets Manager integration
- **`authentication/`**: JWT utilities and role-based access patterns

## Key Patterns & Conventions

### Authentication Architecture
- **JWT tokens** use shared `SECRET_KEY` from `authentication/auth.py`
- **Dependency injection** pattern: `current_user: User = Depends(get_current_user)`
- **Role-based access**: Check `current_user.role` for "admin", "user", "vendor", "author"
- **MongoDB sessions**: Active sessions stored in `active_sessions` collection

### Database Patterns
- **Singleton DB instance**: Always use `db_client: MongoClient = Depends(db.get_client)`
- **Database name**: Hardcoded as `"testdb"` in `database/db.py`
- **AWS Secrets**: MongoDB URI retrieved from AWS Secrets Manager (`my_mongo_secret`)
- **ObjectId handling**: Convert to string for JSON responses: `str(doc["_id"])`

### Router Organization
```python
# Standard pattern for route modules
from routes.user import get_current_user  # Import shared auth
router = APIRouter()

@router.post("/endpoint", tags=["Category"])
async def endpoint(
    current_user: User = Depends(get_current_user),
    db_client: MongoClient = Depends(db.get_client)
):
```

### Email Integration
- **SMTP config** in `models/email_config.py` using environment variables
- **Email functions** in `routes/send_email.py` (registration, password reset)
- **Template pattern**: HTML emails with company branding

### AWS Dependencies
- **S3 uploads** for blog images/files using boto3
- **Secrets Manager** for sensitive config (MongoDB URI, JWT keys)
- **Environment variables** for AWS credentials and regions

## Development Workflow

### Local Development
```bash
# Install dependencies
pip install -r requirements.txt

# Run with auto-reload
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### Docker Deployment
- **Dockerfile** uses Python 3.10-slim with DejaVu fonts for Pillow
- **Port 8000** exposed for FastAPI
- **Environment variables** for Gemini API and AWS config

### Key Environment Variables
- `MONGO_URI` (from AWS Secrets Manager)
- `GEMINI_MODEL=gemini-1.5-flash`
- `MAIL_*` variables for SMTP configuration
- AWS credentials for S3/Secrets Manager

## Critical Implementation Notes

### User Registration Flow
1. Check username/email uniqueness in `user` collection
2. Hash password with bcrypt before storage
3. Send welcome email via `send_registration_email()`
4. Default role: "user", `is_active: false` (requires admin activation)

### Attendance System
- **Collection**: `attendance` with `username` and `attendance_days` array
- **Admin functions**: Manual attendance addition for any user
- **User functions**: Self-service attendance marking with date validation

### Role-Based Features
- **Admin**: Full user management, attendance oversight, content moderation
- **Author**: Content creation for blogs/tutorials
- **Vendor**: Product management in e-commerce features
- **User**: Basic attendance, profile management

## Common Gotchas

1. **JWT Tokens**: Ensure `"sub"` field in payload matches `get_current_user()` expectations
2. **MongoDB Dates**: Use `datetime.utcnow()` and handle timezone conversion (IST) for display
3. **CORS**: Currently allows all origins (`["*"]`) - restrict for production
4. **ObjectId Serialization**: Always convert to string for JSON responses
5. **Password Reset**: Tokens expire in 15 minutes and use separate `RESET_SECRET_KEY`