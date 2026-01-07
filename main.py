from fastapi import FastAPI, Depends
import threading
import time
import logging
from contextlib import asynccontextmanager
from database.db import db
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.middleware.cors import CORSMiddleware
from routes.user import route2
from routes.message import route3
from routes.visitors import router4 as visitor_router
from routes.meet import router6 as meet_router  # Import the dependency
from routes.attendance import router7 as attendance_router
from routes.notes import router10 as notes_router
from routes.quiz import router17
from routes.feedback import router18
from routes.forgot_username import router
from routes.blogs import blog_router
from routes.subscription import route21
from routes.testimonial import route5
from routes import product
from routes.push import push_router 
from routes.google_auth import router31
from fastapi.middleware.cors import CORSMiddleware
from routes.google_refresh import router as google_refresh_router
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from routes.fun import fun_router
from routes.social import social_router
from routes.password import router as password_router
from routes.dockerfile_gen import dockerfile_router
from routes import sql_gen
from routes.cicd_gen import cicd_router
from routes.cli_gen import cli_router
from routes.diagram_gen import diagram_router
from routes.tutorials import tutorial_router
from routes.news import news_router
from routes.news_push import news_push_router
from routes.govt_jobs import govt_jobs_router
from routes.survey import router as survey_router
from routes.grievance import grievance_router
from routes.designation import designation_router
from routes.employee_mgmt import router as employee_router

logger = logging.getLogger(__name__)

# Background scheduler for horoscopes
def scheduled_horoscope_publisher():
    """Background thread to continuously check and publish scheduled horoscopes"""
    from pymongo import MongoClient
    from routes.news import _process_scheduled_horoscopes
    import os
    
    # Get MongoDB URI from secrets manager (same as db.py)
    try:
        from database.db import get_mongo_uri
        MONGODB_URI = get_mongo_uri()
    except:
        # Fallback - should not happen in production
        logger.error("Failed to get MongoDB URI for scheduler")
        return
    
    logger.info("🚀 [Horoscope Scheduler] Background thread started")
    
    while True:
        try:
            client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=5000)
            _process_scheduled_horoscopes(client)
            client.close()
        except Exception as e:
            logger.error(f"❌ [Horoscope Scheduler Error]: {str(e)}")
        
        # Check every 1 minute
        time.sleep(60)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    scheduler_thread = threading.Thread(
        target=scheduled_horoscope_publisher,
        daemon=True,
        name="HoroscopeScheduler"
    )
    scheduler_thread.start()
    logger.info("✅ [Horoscope Scheduler] Background scheduler initialized")
    
    yield
    
    # Shutdown (optional cleanup)
    logger.info("🛑 [Horoscope Scheduler] Shutting down")

app = FastAPI(
    title="OpenSource Enterprise API",
    description="All in ONE API for basic authentication, user registration, attendance mapping and message sending",
    version="1.1.0",
    docs_url="/docs",
    lifespan=lifespan,
    contact={
        "name": "Project DevOps",
        "url": "https://api.projectdevops.in/docs",
        "email": "connect@projectdevops.in",

    },
    swagger_ui_parameters={"syntaxHighlight.theme": "obsidian"})


app.openapi_version = "3.0.2"

# Increase max request body size for file uploads (50MB for employee documents)
app.router.route_class = None  # Will be set by uvicorn with --limit-max-requests



# Allow all origins for CORS (update this to a specific origin in production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:3000",

        "https://gobarsahitimes.com",
        "https://www.gobarsahitimes.com",

        "https://gtnews18.in",
        "https://www.gtnews18.in",

        "https://projectdevops.in",
        "https://www.projectdevops.in"
    ],
    allow_credentials=True,

    # Only what you actually need
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],

    # Explicit headers only (prevents abuse)
    allow_headers=[
        "Authorization",
        "Content-Type",
        "Accept",
        "x-admin-token"
    ],
)


app.include_router(route21)
app.include_router(blog_router)
app.include_router(route2)
app.include_router(route3)
app.include_router(route5)
app.include_router(visitor_router, prefix="/api", tags=["Visitors"])
app.include_router(meet_router, prefix="/api", tags=["Google Meet"])
app.include_router(attendance_router, prefix="/api", tags=["Attendance"])
app.include_router(notes_router, prefix="/api", tags=["Notes"])
app.include_router(router17)
app.include_router(router18)
app.include_router(router)
app.include_router(product.router)
app.include_router(router31)
app.include_router(google_refresh_router)
app.include_router(push_router)
app.include_router(fun_router) 
app.include_router(social_router, prefix="/api", tags=["Social Mock"])
app.include_router(password_router)
app.include_router(dockerfile_router, prefix="/api", tags=["Dockerfile Generation"])
app.include_router(sql_gen.sql_router)
app.include_router(cicd_router, prefix="/api", tags=["CI/CD"])
app.include_router(cli_router, prefix="/api")
app.include_router(diagram_router, prefix="/api")
app.include_router(tutorial_router, tags=["Tutorials"])        # /tutorials/*
app.include_router(tutorial_router, prefix="/api", include_in_schema=False)  # /api/tutorials/*
app.include_router(news_router)
app.include_router(news_push_router, tags=["News Push"])
app.include_router(govt_jobs_router, tags=["Government Jobs"])
app.include_router(survey_router, prefix="/api", tags=["Survey"])
app.include_router(grievance_router, tags=["Grievance Redressal"])
app.include_router(designation_router, tags=["Designations"])
app.include_router(employee_router, tags=["Employee Management"])  # Direct /employees route

if __name__ == "__main__":
    import uvicorn
    # Increase request body size limit to 50MB for employee file uploads
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True, limit_max_requests=50*1024*1024)
