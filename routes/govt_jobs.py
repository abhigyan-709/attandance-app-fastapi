# routes/govt_jobs.py
"""
Government Jobs Listing System Routes
Complete API endpoints for job management, search, and scraping
"""
import logging
import re
from fastapi import APIRouter, HTTPException, Depends, Query, BackgroundTasks, status
from pymongo import MongoClient, ASCENDING, DESCENDING, TEXT
from datetime import datetime, date, timedelta, timezone
from typing import Optional, List, Dict, Any
from bson import ObjectId

from database.db import db
from models.govt_jobs import (
    GovtJobCreate, GovtJobUpdate, GovtJobResponse, GovtJobListItem,
    JobSearchRequest, JobSearchResponse, JobStatsResponse,
    ScrapingSourceCreate, ScrapingSourceResponse, ScrapingLogResponse,
    BulkJobCreate, BulkStatusUpdate, BulkDeleteRequest,
    JobAnalytics, SuccessResponse, ErrorResponse,
    JobStatus, JobType, JobCategory
)
from models.user import User
from routes.user import get_current_user

logger = logging.getLogger(__name__)

govt_jobs_router = APIRouter(prefix="/govt-jobs", tags=["Government Jobs"])


# ==================== Helper Functions ====================

def get_jobs_collection(db_client: MongoClient = Depends(db.get_client)):
    """Get govt_jobs collection"""
    database = db_client[db.db_name]
    return database["govt_jobs"]


def get_scraping_sources_collection(db_client: MongoClient = Depends(db.get_client)):
    """Get scraping_sources collection"""
    database = db_client[db.db_name]
    return database["scraping_sources"]


def get_scraping_logs_collection(db_client: MongoClient = Depends(db.get_client)):
    """Get scraping_logs collection"""
    database = db_client[db.db_name]
    return database["scraping_logs"]


def get_current_admin_user(current_user: User = Depends(get_current_user)):
    """Admin authentication"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user


def generate_unique_slug(title: str, collection) -> str:
    """Generate unique slug from title"""
    # Clean and create base slug
    slug = title.lower()
    slug = re.sub(r'[^a-z0-9\s-]', '', slug)
    slug = re.sub(r'[\s]+', '-', slug)
    slug = slug[:180]
    
    # Check uniqueness
    base_slug = slug
    counter = 1
    while collection.count_documents({"slug": slug}) > 0:
        slug = f"{base_slug}-{counter}"
        counter += 1
    
    return slug


def job_to_response(job: Dict) -> GovtJobResponse:
    """Convert MongoDB job document to response model"""
    job["id"] = str(job.pop("_id"))
    
    # Convert dates to ISO strings
    date_fields = ["notification_date", "application_begin_date", "application_end_date",
                   "last_date_fee_payment", "exam_date", "admit_card_date", "result_date",
                   "created_at", "updated_at", "published_at", "last_scraped_at"]
    
    for field in date_fields:
        if field in job and job[field]:
            if isinstance(job[field], (datetime, date)):
                job[field] = job[field].isoformat()
    
    return GovtJobResponse(**job)


def job_to_list_item(job: Dict) -> GovtJobListItem:
    """Convert MongoDB job document to list item"""
    return GovtJobListItem(
        id=str(job["_id"]),
        title=job["title"],
        slug=job["slug"],
        short_description=job["short_description"],
        organization_name=job["organization_name"],
        organization_short_name=job["organization_short_name"],
        logo_url=job.get("logo_url"),
        job_type=job["job_type"],
        state=job.get("state"),
        category=job["category"],
        post_name=job["post_name"],
        total_vacancies=job["total_vacancies"],
        salary_text=job["salary_text"],
        work_locations=job["work_locations"],
        application_begin_date=job["application_begin_date"].isoformat() if isinstance(job["application_begin_date"], (datetime, date)) else job["application_begin_date"],
        application_end_date=job["application_end_date"].isoformat() if isinstance(job["application_end_date"], (datetime, date)) else job["application_end_date"],
        apply_link=job["apply_link"],
        status=job["status"],
        is_featured=job.get("is_featured", False),
        is_urgent=job.get("is_urgent", False),
        is_new=job.get("is_new", False),
        views_count=job.get("views_count", 0),
        created_at=job["created_at"].isoformat() if isinstance(job["created_at"], datetime) else job["created_at"]
    )


def update_job_flags(job: Dict) -> Dict:
    """Update auto-managed flags (is_new, is_urgent)"""
    now = datetime.now(timezone.utc)
    created_at = job.get("created_at")
    application_end_date = job.get("application_end_date")
    
    # Update is_new flag (jobs within 3 days)
    if created_at and isinstance(created_at, datetime):
        days_old = (now - created_at).days
        job["is_new"] = days_old <= 3
    
    # Update is_urgent flag (deadline within 7 days)
    if application_end_date:
        if isinstance(application_end_date, date) and not isinstance(application_end_date, datetime):
            application_end_date = datetime.combine(application_end_date, datetime.min.time()).replace(tzinfo=timezone.utc)
        
        if isinstance(application_end_date, datetime):
            days_until_deadline = (application_end_date - now).days
            job["is_urgent"] = 0 <= days_until_deadline <= 7
    
    # Auto-update status if deadline passed
    if application_end_date:
        if isinstance(application_end_date, date) and not isinstance(application_end_date, datetime):
            application_end_date = datetime.combine(application_end_date, datetime.min.time()).replace(tzinfo=timezone.utc)
        
        if isinstance(application_end_date, datetime) and application_end_date < now and job.get("status") == "Active":
            job["status"] = "Closed"
    
    return job


# ==================== Public Endpoints ====================

@govt_jobs_router.get("/", response_model=JobSearchResponse)
async def list_jobs(
    query: Optional[str] = Query(None, description="Search query"),
    job_types: Optional[str] = Query(None, description="Comma-separated job types"),
    states: Optional[str] = Query(None, description="Comma-separated states"),
    categories: Optional[str] = Query(None, description="Comma-separated categories"),
    organizations: Optional[str] = Query(None, description="Comma-separated organizations"),
    status: Optional[str] = Query("Active", description="Comma-separated status values"),
    is_new: Optional[bool] = Query(None, description="Show only new jobs"),
    is_featured: Optional[bool] = Query(None, description="Show only featured jobs"),
    application_open: Optional[bool] = Query(True, description="Show only jobs accepting applications"),
    deadline_within_days: Optional[int] = Query(None, ge=1, le=365),
    salary_min: Optional[int] = Query(None, ge=0),
    salary_max: Optional[int] = Query(None, ge=0),
    sort_by: str = Query("created_at", description="Sort field"),
    sort_order: str = Query("desc", description="asc or desc"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db_client: MongoClient = Depends(db.get_client)
):
    """
    List and filter government jobs
    
    Public endpoint with advanced search and filtering
    """
    try:
        collection = get_jobs_collection(db_client)
        
        # Build query filter
        filter_query: Dict[str, Any] = {}
        
        # Text search
        if query:
            filter_query["$text"] = {"$search": query}
        
        # Status filter
        if status:
            status_list = [s.strip() for s in status.split(",")]
            filter_query["status"] = {"$in": status_list}
        
        # Job types filter
        if job_types:
            types_list = [t.strip() for t in job_types.split(",")]
            filter_query["job_type"] = {"$in": types_list}
        
        # States filter
        if states:
            states_list = [s.strip() for s in states.split(",")]
            filter_query["state"] = {"$in": states_list}
        
        # Categories filter
        if categories:
            categories_list = [c.strip() for c in categories.split(",")]
            filter_query["category"] = {"$in": categories_list}
        
        # Organizations filter
        if organizations:
            orgs_list = [o.strip() for o in organizations.split(",")]
            filter_query["organization_short_name"] = {"$in": orgs_list}
        
        # Boolean filters
        if is_new is not None:
            filter_query["is_new"] = is_new
        
        if is_featured is not None:
            filter_query["is_featured"] = is_featured
        
        # Application open filter
        if application_open:
            filter_query["application_end_date"] = {"$gte": datetime.now(timezone.utc)}
        
        # Deadline within days
        if deadline_within_days:
            end_date = datetime.now(timezone.utc) + timedelta(days=deadline_within_days)
            filter_query["application_end_date"] = {"$lte": end_date}
        
        # Salary range filter
        if salary_min or salary_max:
            salary_filter = {}
            if salary_min:
                salary_filter["$gte"] = salary_min
            if salary_max:
                salary_filter["$lte"] = salary_max
            filter_query["salary_max"] = salary_filter
        
        # Count total
        total = collection.count_documents(filter_query)
        
        # Calculate pagination
        skip = (page - 1) * limit
        total_pages = (total + limit - 1) // limit
        
        # Sort
        sort_direction = DESCENDING if sort_order == "desc" else ASCENDING
        sort_spec = [(sort_by, sort_direction)]
        
        # If text search, add relevance score
        if query:
            sort_spec.insert(0, ("score", {"$meta": "textScore"}))
        
        # Execute query
        cursor = collection.find(filter_query).sort(sort_spec).skip(skip).limit(limit)
        jobs = [job_to_list_item(update_job_flags(job)) for job in cursor]
        
        return JobSearchResponse(
            jobs=jobs,
            total=total,
            page=page,
            limit=limit,
            total_pages=total_pages,
            has_next=page < total_pages,
            has_prev=page > 1
        )
    
    except Exception as e:
        logger.error(f"Error listing jobs: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list jobs: {str(e)}")


@govt_jobs_router.get("/slug/{slug}", response_model=GovtJobResponse)
async def get_job_by_slug(
    slug: str,
    increment_view: bool = Query(True, description="Increment view count"),
    db_client: MongoClient = Depends(db.get_client)
):
    """
    Get job details by custom slug
    
    Public endpoint - increments view count by default
    """
    try:
        collection = get_jobs_collection(db_client)
        
        job = collection.find_one({"slug": slug})
        if not job:
            raise HTTPException(status_code=404, detail=f"Job with slug '{slug}' not found")
        
        # Increment view count
        if increment_view:
            collection.update_one(
                {"_id": job["_id"]},
                {"$inc": {"views_count": 1}}
            )
            job["views_count"] = job.get("views_count", 0) + 1
        
        job = update_job_flags(job)
        return job_to_response(job)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting job by slug: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get job: {str(e)}")


@govt_jobs_router.get("/{job_id}", response_model=GovtJobResponse)
async def get_job_by_id(
    job_id: str,
    increment_view: bool = Query(True, description="Increment view count"),
    db_client: MongoClient = Depends(db.get_client)
):
    """
    Get job details by ID
    
    Fallback endpoint when slug is not available
    """
    try:
        collection = get_jobs_collection(db_client)
        
        if not ObjectId.is_valid(job_id):
            raise HTTPException(status_code=400, detail="Invalid job ID format")
        
        job = collection.find_one({"_id": ObjectId(job_id)})
        if not job:
            raise HTTPException(status_code=404, detail=f"Job with ID '{job_id}' not found")
        
        # Increment view count
        if increment_view:
            collection.update_one(
                {"_id": job["_id"]},
                {"$inc": {"views_count": 1}}
            )
            job["views_count"] = job.get("views_count", 0) + 1
        
        job = update_job_flags(job)
        return job_to_response(job)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting job by ID: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get job: {str(e)}")


@govt_jobs_router.get("/stats/dashboard", response_model=JobStatsResponse)
async def get_dashboard_stats(db_client: MongoClient = Depends(db.get_client)):
    """
    Get dashboard statistics
    
    Public endpoint for homepage/dashboard
    """
    try:
        collection = get_jobs_collection(db_client)
        now = datetime.now(timezone.utc)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week_start = now - timedelta(days=7)
        closing_soon_date = now + timedelta(days=7)
        
        # Basic counts
        total_active = collection.count_documents({"status": "Active"})
        
        # Total vacancies
        pipeline = [
            {"$match": {"status": "Active"}},
            {"$group": {"_id": None, "total": {"$sum": "$total_vacancies"}}}
        ]
        vacancies_result = list(collection.aggregate(pipeline))
        total_vacancies = vacancies_result[0]["total"] if vacancies_result else 0
        
        # New jobs today
        new_today = collection.count_documents({
            "created_at": {"$gte": today_start},
            "status": "Active"
        })
        
        # New jobs this week
        new_week = collection.count_documents({
            "created_at": {"$gte": week_start},
            "status": "Active"
        })
        
        # Closing soon (within 7 days)
        closing_soon = collection.count_documents({
            "application_end_date": {"$lte": closing_soon_date, "$gte": now},
            "status": "Active"
        })
        
        # Jobs by category
        category_pipeline = [
            {"$match": {"status": "Active"}},
            {"$group": {"_id": "$category", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}},
            {"$limit": 10}
        ]
        category_results = list(collection.aggregate(category_pipeline))
        jobs_by_category = {item["_id"]: item["count"] for item in category_results}
        
        # Jobs by type
        type_pipeline = [
            {"$match": {"status": "Active"}},
            {"$group": {"_id": "$job_type", "count": {"$sum": 1}}}
        ]
        type_results = list(collection.aggregate(type_pipeline))
        jobs_by_type = {item["_id"]: item["count"] for item in type_results}
        
        # Jobs by state (top 10)
        state_pipeline = [
            {"$match": {"status": "Active", "state": {"$ne": None}}},
            {"$group": {"_id": "$state", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}},
            {"$limit": 10}
        ]
        state_results = list(collection.aggregate(state_pipeline))
        jobs_by_state = {item["_id"]: item["count"] for item in state_results}
        
        # Top organizations
        org_pipeline = [
            {"$match": {"status": "Active"}},
            {"$group": {
                "_id": "$organization_short_name",
                "count": {"$sum": 1},
                "total_vacancies": {"$sum": "$total_vacancies"}
            }},
            {"$sort": {"count": -1}},
            {"$limit": 10}
        ]
        org_results = list(collection.aggregate(org_pipeline))
        top_organizations = [
            {
                "name": item["_id"],
                "jobs_count": item["count"],
                "vacancies_count": item["total_vacancies"]
            }
            for item in org_results
        ]
        
        return JobStatsResponse(
            total_active_jobs=total_active,
            total_vacancies=total_vacancies,
            new_jobs_today=new_today,
            new_jobs_week=new_week,
            closing_soon=closing_soon,
            jobs_by_category=jobs_by_category,
            jobs_by_type=jobs_by_type,
            jobs_by_state=jobs_by_state,
            top_organizations=top_organizations
        )
    
    except Exception as e:
        logger.error(f"Error getting dashboard stats: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get statistics: {str(e)}")


@govt_jobs_router.get("/filter/categories")
async def get_categories(db_client: MongoClient = Depends(db.get_client)):
    """Get all categories with job counts"""
    try:
        collection = get_jobs_collection(db_client)
        
        pipeline = [
            {"$match": {"status": "Active"}},
            {"$group": {"_id": "$category", "count": {"$sum": 1}}},
            {"$sort": {"_id": 1}}
        ]
        results = list(collection.aggregate(pipeline))
        
        categories = [{"name": item["_id"], "count": item["count"]} for item in results]
        return {"categories": categories, "total": len(categories)}
    
    except Exception as e:
        logger.error(f"Error getting categories: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@govt_jobs_router.get("/filter/organizations")
async def get_organizations(db_client: MongoClient = Depends(db.get_client)):
    """Get all organizations with job counts"""
    try:
        collection = get_jobs_collection(db_client)
        
        pipeline = [
            {"$match": {"status": "Active"}},
            {"$group": {
                "_id": "$organization_short_name",
                "full_name": {"$first": "$organization_name"},
                "count": {"$sum": 1}
            }},
            {"$sort": {"count": -1}}
        ]
        results = list(collection.aggregate(pipeline))
        
        organizations = [
            {
                "short_name": item["_id"],
                "full_name": item["full_name"],
                "count": item["count"]
            }
            for item in results
        ]
        return {"organizations": organizations, "total": len(organizations)}
    
    except Exception as e:
        logger.error(f"Error getting organizations: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@govt_jobs_router.get("/filter/states")
async def get_states(db_client: MongoClient = Depends(db.get_client)):
    """Get all states with job counts"""
    try:
        collection = get_jobs_collection(db_client)
        
        pipeline = [
            {"$match": {"status": "Active", "state": {"$ne": None}}},
            {"$group": {"_id": "$state", "count": {"$sum": 1}}},
            {"$sort": {"_id": 1}}
        ]
        results = list(collection.aggregate(pipeline))
        
        states = [{"name": item["_id"], "count": item["count"]} for item in results]
        return {"states": states, "total": len(states)}
    
    except Exception as e:
        logger.error(f"Error getting states: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@govt_jobs_router.get("/featured/list", response_model=List[GovtJobListItem])
async def get_featured_jobs(
    limit: int = Query(10, ge=1, le=50),
    db_client: MongoClient = Depends(db.get_client)
):
    """Get featured jobs"""
    try:
        collection = get_jobs_collection(db_client)
        
        cursor = collection.find({
            "is_featured": True,
            "status": "Active"
        }).sort("created_at", DESCENDING).limit(limit)
        
        jobs = [job_to_list_item(update_job_flags(job)) for job in cursor]
        return jobs
    
    except Exception as e:
        logger.error(f"Error getting featured jobs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@govt_jobs_router.get("/latest/list", response_model=List[GovtJobListItem])
async def get_latest_jobs(
    limit: int = Query(20, ge=1, le=50),
    db_client: MongoClient = Depends(db.get_client)
):
    """Get latest jobs"""
    try:
        collection = get_jobs_collection(db_client)
        
        cursor = collection.find({
            "status": "Active"
        }).sort("created_at", DESCENDING).limit(limit)
        
        jobs = [job_to_list_item(update_job_flags(job)) for job in cursor]
        return jobs
    
    except Exception as e:
        logger.error(f"Error getting latest jobs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@govt_jobs_router.get("/closing-soon/list", response_model=List[GovtJobListItem])
async def get_closing_soon_jobs(
    days: int = Query(7, ge=1, le=30),
    limit: int = Query(20, ge=1, le=50),
    db_client: MongoClient = Depends(db.get_client)
):
    """Get jobs closing soon"""
    try:
        collection = get_jobs_collection(db_client)
        now = datetime.now(timezone.utc)
        end_date = now + timedelta(days=days)
        
        cursor = collection.find({
            "status": "Active",
            "application_end_date": {"$lte": end_date, "$gte": now}
        }).sort("application_end_date", ASCENDING).limit(limit)
        
        jobs = [job_to_list_item(update_job_flags(job)) for job in cursor]
        return jobs
    
    except Exception as e:
        logger.error(f"Error getting closing soon jobs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@govt_jobs_router.get("/category/{category}", response_model=JobSearchResponse)
async def get_jobs_by_category(
    category: str,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db_client: MongoClient = Depends(db.get_client)
):
    """Get jobs by category"""
    try:
        collection = get_jobs_collection(db_client)
        
        filter_query = {"category": category, "status": "Active"}
        total = collection.count_documents(filter_query)
        
        skip = (page - 1) * limit
        total_pages = (total + limit - 1) // limit
        
        cursor = collection.find(filter_query).sort("created_at", DESCENDING).skip(skip).limit(limit)
        jobs = [job_to_list_item(update_job_flags(job)) for job in cursor]
        
        return JobSearchResponse(
            jobs=jobs,
            total=total,
            page=page,
            limit=limit,
            total_pages=total_pages,
            has_next=page < total_pages,
            has_prev=page > 1
        )
    
    except Exception as e:
        logger.error(f"Error getting jobs by category: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@govt_jobs_router.get("/state/{state}", response_model=JobSearchResponse)
async def get_jobs_by_state(
    state: str,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db_client: MongoClient = Depends(db.get_client)
):
    """Get jobs by state"""
    try:
        collection = get_jobs_collection(db_client)
        
        filter_query = {"state": state, "status": "Active"}
        total = collection.count_documents(filter_query)
        
        skip = (page - 1) * limit
        total_pages = (total + limit - 1) // limit
        
        cursor = collection.find(filter_query).sort("created_at", DESCENDING).skip(skip).limit(limit)
        jobs = [job_to_list_item(update_job_flags(job)) for job in cursor]
        
        return JobSearchResponse(
            jobs=jobs,
            total=total,
            page=page,
            limit=limit,
            total_pages=total_pages,
            has_next=page < total_pages,
            has_prev=page > 1
        )
    
    except Exception as e:
        logger.error(f"Error getting jobs by state: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@govt_jobs_router.post("/{job_id}/click")
async def track_click(
    job_id: str,
    db_client: MongoClient = Depends(db.get_client)
):
    """
    Track apply link clicks
    
    Call this when user clicks the apply button
    """
    try:
        collection = get_jobs_collection(db_client)
        
        if not ObjectId.is_valid(job_id):
            raise HTTPException(status_code=400, detail="Invalid job ID")
        
        result = collection.update_one(
            {"_id": ObjectId(job_id)},
            {"$inc": {"clicks_count": 1}}
        )
        
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Job not found")
        
        return {"success": True, "message": "Click tracked"}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error tracking click: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Admin Endpoints ====================

@govt_jobs_router.post("/admin/create", response_model=GovtJobResponse, status_code=status.HTTP_201_CREATED)
async def create_job(
    job: GovtJobCreate,
    current_admin: User = Depends(get_current_admin_user),
    db_client: MongoClient = Depends(db.get_client)
):
    """
    Create a new government job
    
    Admin only endpoint
    """
    try:
        collection = get_jobs_collection(db_client)
        
        # Generate unique slug if not provided or check uniqueness
        if job.slug:
            if collection.count_documents({"slug": job.slug}) > 0:
                raise HTTPException(status_code=400, detail=f"Slug '{job.slug}' already exists")
        else:
            job.slug = generate_unique_slug(job.title, collection)
        
        # Prepare document
        now = datetime.now(timezone.utc)
        job_dict = job.dict()
        job_dict.update({
            "is_new": True,  # New jobs always marked as new
            "views_count": 0,
            "clicks_count": 0,
            "created_by": current_admin.username,
            "updated_by": None,
            "created_at": now,
            "updated_at": now,
            "published_at": now if job.status == JobStatus.ACTIVE else None,
            "last_scraped_at": None
        })
        
        # Update flags
        job_dict = update_job_flags(job_dict)
        
        # Insert
        result = collection.insert_one(job_dict)
        job_dict["_id"] = result.inserted_id
        
        logger.info(f"Job created: {job.title} by {current_admin.username}")
        
        return job_to_response(job_dict)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating job: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create job: {str(e)}")


@govt_jobs_router.put("/admin/{job_id}", response_model=GovtJobResponse)
async def update_job(
    job_id: str,
    job_update: GovtJobUpdate,
    current_admin: User = Depends(get_current_admin_user),
    db_client: MongoClient = Depends(db.get_client)
):
    """
    Update an existing job
    
    Admin only endpoint
    """
    try:
        collection = get_jobs_collection(db_client)
        
        if not ObjectId.is_valid(job_id):
            raise HTTPException(status_code=400, detail="Invalid job ID")
        
        # Check if job exists
        existing_job = collection.find_one({"_id": ObjectId(job_id)})
        if not existing_job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        # Prepare update data (only non-None fields)
        update_data = {k: v for k, v in job_update.dict().items() if v is not None}
        
        if not update_data:
            raise HTTPException(status_code=400, detail="No fields to update")
        
        # Check slug uniqueness if updating slug
        if "slug" in update_data and update_data["slug"] != existing_job.get("slug"):
            if collection.count_documents({"slug": update_data["slug"]}) > 0:
                raise HTTPException(status_code=400, detail=f"Slug '{update_data['slug']}' already exists")
        
        # Add metadata
        update_data["updated_by"] = current_admin.username
        update_data["updated_at"] = datetime.now(timezone.utc)
        
        # Update published_at if status changed to Active
        if "status" in update_data and update_data["status"] == JobStatus.ACTIVE and not existing_job.get("published_at"):
            update_data["published_at"] = datetime.now(timezone.utc)
        
        # Update
        collection.update_one(
            {"_id": ObjectId(job_id)},
            {"$set": update_data}
        )
        
        # Fetch updated job
        updated_job = collection.find_one({"_id": ObjectId(job_id)})
        updated_job = update_job_flags(updated_job)
        
        logger.info(f"Job updated: {job_id} by {current_admin.username}")
        
        return job_to_response(updated_job)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating job: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update job: {str(e)}")


@govt_jobs_router.delete("/admin/{job_id}")
async def delete_job(
    job_id: str,
    current_admin: User = Depends(get_current_admin_user),
    db_client: MongoClient = Depends(db.get_client)
):
    """
    Delete a job
    
    Admin only endpoint
    """
    try:
        collection = get_jobs_collection(db_client)
        
        if not ObjectId.is_valid(job_id):
            raise HTTPException(status_code=400, detail="Invalid job ID")
        
        result = collection.delete_one({"_id": ObjectId(job_id)})
        
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Job not found")
        
        logger.info(f"Job deleted: {job_id} by {current_admin.username}")
        
        return SuccessResponse(message="Job deleted successfully")
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting job: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@govt_jobs_router.get("/admin/all", response_model=JobSearchResponse)
async def get_all_jobs_admin(
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    status: Optional[str] = Query(None, description="Filter by status"),
    current_admin: User = Depends(get_current_admin_user),
    db_client: MongoClient = Depends(db.get_client)
):
    """
    Get all jobs including closed/cancelled
    
    Admin only endpoint
    """
    try:
        collection = get_jobs_collection(db_client)
        
        filter_query = {}
        if status:
            filter_query["status"] = status
        
        total = collection.count_documents(filter_query)
        skip = (page - 1) * limit
        total_pages = (total + limit - 1) // limit
        
        cursor = collection.find(filter_query).sort("created_at", DESCENDING).skip(skip).limit(limit)
        jobs = [job_to_list_item(update_job_flags(job)) for job in cursor]
        
        return JobSearchResponse(
            jobs=jobs,
            total=total,
            page=page,
            limit=limit,
            total_pages=total_pages,
            has_next=page < total_pages,
            has_prev=page > 1
        )
    
    except Exception as e:
        logger.error(f"Error getting all jobs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@govt_jobs_router.patch("/admin/{job_id}/status")
async def update_job_status(
    job_id: str,
    new_status: JobStatus,
    current_admin: User = Depends(get_current_admin_user),
    db_client: MongoClient = Depends(db.get_client)
):
    """Update job status"""
    try:
        collection = get_jobs_collection(db_client)
        
        if not ObjectId.is_valid(job_id):
            raise HTTPException(status_code=400, detail="Invalid job ID")
        
        update_data = {
            "status": new_status.value,
            "updated_by": current_admin.username,
            "updated_at": datetime.now(timezone.utc)
        }
        
        # Set published_at if activating
        if new_status == JobStatus.ACTIVE:
            job = collection.find_one({"_id": ObjectId(job_id)})
            if job and not job.get("published_at"):
                update_data["published_at"] = datetime.now(timezone.utc)
        
        result = collection.update_one(
            {"_id": ObjectId(job_id)},
            {"$set": update_data}
        )
        
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Job not found")
        
        return SuccessResponse(message=f"Status updated to {new_status.value}")
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@govt_jobs_router.patch("/admin/{job_id}/feature")
async def toggle_featured(
    job_id: str,
    is_featured: bool,
    current_admin: User = Depends(get_current_admin_user),
    db_client: MongoClient = Depends(db.get_client)
):
    """Toggle featured status"""
    try:
        collection = get_jobs_collection(db_client)
        
        if not ObjectId.is_valid(job_id):
            raise HTTPException(status_code=400, detail="Invalid job ID")
        
        result = collection.update_one(
            {"_id": ObjectId(job_id)},
            {"$set": {
                "is_featured": is_featured,
                "updated_by": current_admin.username,
                "updated_at": datetime.now(timezone.utc)
            }}
        )
        
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Job not found")
        
        return SuccessResponse(message=f"Featured status set to {is_featured}")
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error toggling featured: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@govt_jobs_router.post("/admin/bulk-create", status_code=status.HTTP_201_CREATED)
async def bulk_create_jobs(
    bulk_data: BulkJobCreate,
    current_admin: User = Depends(get_current_admin_user),
    db_client: MongoClient = Depends(db.get_client)
):
    """
    Bulk create jobs from CSV/JSON
    
    Admin only endpoint
    """
    try:
        collection = get_jobs_collection(db_client)
        now = datetime.now(timezone.utc)
        
        created_jobs = []
        errors = []
        
        for idx, job in enumerate(bulk_data.jobs):
            try:
                # Generate unique slug
                if not job.slug:
                    job.slug = generate_unique_slug(job.title, collection)
                else:
                    if collection.count_documents({"slug": job.slug}) > 0:
                        raise ValueError(f"Slug '{job.slug}' already exists")
                
                # Prepare document
                job_dict = job.dict()
                job_dict.update({
                    "is_new": True,
                    "views_count": 0,
                    "clicks_count": 0,
                    "created_by": current_admin.username,
                    "updated_by": None,
                    "created_at": now,
                    "updated_at": now,
                    "published_at": now if job.status == JobStatus.ACTIVE else None,
                    "last_scraped_at": None
                })
                
                job_dict = update_job_flags(job_dict)
                
                result = collection.insert_one(job_dict)
                created_jobs.append(str(result.inserted_id))
            
            except Exception as e:
                errors.append({"index": idx, "title": job.title, "error": str(e)})
        
        return {
            "success": True,
            "created_count": len(created_jobs),
            "created_ids": created_jobs,
            "errors_count": len(errors),
            "errors": errors
        }
    
    except Exception as e:
        logger.error(f"Error bulk creating jobs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@govt_jobs_router.post("/admin/bulk-update-status")
async def bulk_update_status(
    bulk_data: BulkStatusUpdate,
    current_admin: User = Depends(get_current_admin_user),
    db_client: MongoClient = Depends(db.get_client)
):
    """Bulk update job status"""
    try:
        collection = get_jobs_collection(db_client)
        
        job_object_ids = [ObjectId(job_id) for job_id in bulk_data.job_ids if ObjectId.is_valid(job_id)]
        
        if not job_object_ids:
            raise HTTPException(status_code=400, detail="No valid job IDs provided")
        
        result = collection.update_many(
            {"_id": {"$in": job_object_ids}},
            {"$set": {
                "status": bulk_data.status.value,
                "updated_by": current_admin.username,
                "updated_at": datetime.now(timezone.utc)
            }}
        )
        
        return {
            "success": True,
            "matched_count": result.matched_count,
            "modified_count": result.modified_count
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error bulk updating status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@govt_jobs_router.delete("/admin/bulk-delete")
async def bulk_delete_jobs(
    bulk_data: BulkDeleteRequest,
    current_admin: User = Depends(get_current_admin_user),
    db_client: MongoClient = Depends(db.get_client)
):
    """Bulk delete jobs"""
    try:
        collection = get_jobs_collection(db_client)
        
        job_object_ids = [ObjectId(job_id) for job_id in bulk_data.job_ids if ObjectId.is_valid(job_id)]
        
        if not job_object_ids:
            raise HTTPException(status_code=400, detail="No valid job IDs provided")
        
        result = collection.delete_many({"_id": {"$in": job_object_ids}})
        
        return {
            "success": True,
            "deleted_count": result.deleted_count
        }
    
    except Exception as e:
        logger.error(f"Error bulk deleting jobs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@govt_jobs_router.get("/admin/check-slug/{slug}")
async def check_slug_availability(
    slug: str,
    current_admin: User = Depends(get_current_admin_user),
    db_client: MongoClient = Depends(db.get_client)
):
    """Check if slug is available"""
    try:
        collection = get_jobs_collection(db_client)
        
        exists = collection.count_documents({"slug": slug}) > 0
        
        return {
            "slug": slug,
            "available": not exists
        }
    
    except Exception as e:
        logger.error(f"Error checking slug: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@govt_jobs_router.post("/admin/{job_id}/regenerate-slug")
async def regenerate_slug(
    job_id: str,
    custom_slug: Optional[str] = None,
    current_admin: User = Depends(get_current_admin_user),
    db_client: MongoClient = Depends(db.get_client)
):
    """Generate new slug for job"""
    try:
        collection = get_jobs_collection(db_client)
        
        if not ObjectId.is_valid(job_id):
            raise HTTPException(status_code=400, detail="Invalid job ID")
        
        job = collection.find_one({"_id": ObjectId(job_id)})
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        if custom_slug:
            # Check uniqueness
            if collection.count_documents({"slug": custom_slug, "_id": {"$ne": ObjectId(job_id)}}) > 0:
                raise HTTPException(status_code=400, detail=f"Slug '{custom_slug}' already exists")
            new_slug = custom_slug
        else:
            # Generate from title
            new_slug = generate_unique_slug(job["title"], collection)
        
        collection.update_one(
            {"_id": ObjectId(job_id)},
            {"$set": {
                "slug": new_slug,
                "updated_by": current_admin.username,
                "updated_at": datetime.now(timezone.utc)
            }}
        )
        
        return {
            "success": True,
            "old_slug": job["slug"],
            "new_slug": new_slug
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error regenerating slug: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Scraping Endpoints (Placeholder) ====================

@govt_jobs_router.get("/scraper/sources")
async def list_scraping_sources(
    current_admin: User = Depends(get_current_admin_user),
    db_client: MongoClient = Depends(db.get_client)
):
    """
    List all scraping sources
    
    Note: Scraping implementation requires additional libraries (BeautifulSoup4, Selenium, etc.)
    This is a placeholder for future implementation
    """
    return {
        "message": "Scraping feature coming soon",
        "sources": []
    }


@govt_jobs_router.post("/scraper/run/{source_id}")
async def trigger_scraping(
    source_id: str,
    current_admin: User = Depends(get_current_admin_user),
    db_client: MongoClient = Depends(db.get_client)
):
    """
    Trigger manual scraping for a source
    
    Placeholder for future implementation
    """
    return {
        "message": "Scraping feature coming soon",
        "note": "Will implement web scraping with BeautifulSoup4/Selenium"
    }
