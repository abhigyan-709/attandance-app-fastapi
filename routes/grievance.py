# routes/grievance.py

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from pymongo import MongoClient, DESCENDING
from typing import List, Optional
from datetime import datetime, timedelta
from bson import ObjectId
import uuid

from database.db import db
from models.user import User
from models.grievance import (
    GrievanceOfficer, SelfRegulatoryBody, NewsEditor,
    GrievanceComplaint, GrievanceUpdate, GrievanceResponse,
    GrievanceStatus, GrievanceCategory, GrievanceStatistics
)
from routes.user import get_current_user
from routes.send_email import send_grievance_acknowledgment, send_grievance_resolution

grievance_router = APIRouter()


# ==================== PUBLIC ENDPOINTS (No Auth Required) ====================

@grievance_router.get("/grievance/info", tags=["Grievance Redressal"])
async def get_grievance_info(db_client: MongoClient = Depends(db.get_client)):
    """
    Get complete grievance redressal mechanism information
    (Public endpoint - required for compliance)
    """
    grievance_collection = db_client[db.db_name]["grievance_info"]
    
    # Get active Grievance Officer
    officer = grievance_collection.find_one({"type": "officer", "is_active": True})
    
    # Get active Self Regulatory Body
    srb = grievance_collection.find_one({"type": "self_regulatory_body", "is_active": True})
    
    # Get active News Editors
    editors = list(grievance_collection.find({"type": "editor", "is_active": True}))
    
    return {
        "grievance_officer": officer if officer else None,
        "self_regulatory_body": srb if srb else None,
        "news_editors": editors if editors else [],
        "complaint_submission_url": "/grievance/submit",
        "last_updated": datetime.utcnow()
    }


@grievance_router.post("/grievance/submit", tags=["Grievance Redressal"])
async def submit_grievance(
    complaint: GrievanceComplaint,
    background_tasks: BackgroundTasks,
    db_client: MongoClient = Depends(db.get_client)
):
    """
    Submit a new grievance complaint (Public endpoint)
    Auto-assigns to appropriate editor based on designation
    """
    complaints_collection = db_client[db.db_name]["grievance_complaints"]
    users_collection = db_client[db.db_name]["user"]
    
    # Generate unique complaint ID
    complaint_id = f"GRV-{datetime.utcnow().year}-{str(uuid.uuid4())[:8].upper()}"
    
    # Auto-assign to appropriate handler based on designation
    assigned_to = None
    
    # Try to find editors with auto-assign designations (Chief Editor, Regional Editor, etc.)
    auto_assign_editors = list(users_collection.find({
        "role": {"$in": ["author", "admin"]},
        "is_active": True,
        "can_handle_grievances": True,
        "author_designation": {"$exists": True}
    }).sort("author_designation_level", DESCENDING).limit(1))
    
    if auto_assign_editors:
        assigned_to = auto_assign_editors[0]["username"]
    
    # Prepare complaint document
    complaint_dict = complaint.dict()
    complaint_dict["complaint_id"] = complaint_id
    complaint_dict["submitted_at"] = datetime.utcnow()
    complaint_dict["status"] = GrievanceStatus.SUBMITTED
    complaint_dict["assigned_to"] = assigned_to
    complaint_dict["status_history"] = [{
        "status": GrievanceStatus.SUBMITTED,
        "timestamp": datetime.utcnow(),
        "notes": f"Complaint submitted{f' and auto-assigned to {assigned_to}' if assigned_to else ''}"
    }]
    
    # Insert complaint
    result = complaints_collection.insert_one(complaint_dict)
    
    # Send acknowledgment email in background
    background_tasks.add_task(
        send_grievance_acknowledgment,
        complaint_dict["complainant_email"],
        complaint_dict["complainant_name"],
        complaint_id
    )
    
    return {
        "message": "Grievance complaint submitted successfully",
        "complaint_id": complaint_id,
        "status": GrievanceStatus.SUBMITTED,
        "submitted_at": complaint_dict["submitted_at"],
        "assigned_to": assigned_to,
        "acknowledgment": "You will receive an acknowledgment email shortly. We aim to resolve complaints within 15 days."
    }


@grievance_router.get("/grievance/track/{complaint_id}", tags=["Grievance Redressal"])
async def track_grievance(
    complaint_id: str,
    db_client: MongoClient = Depends(db.get_client)
):
    """
    Track grievance complaint status (Public endpoint)
    """
    complaints_collection = db_client[db.db_name]["grievance_complaints"]
    
    complaint = complaints_collection.find_one({"complaint_id": complaint_id})
    
    if not complaint:
        raise HTTPException(status_code=404, detail="Complaint not found")
    
    # Return public information only
    return {
        "complaint_id": complaint["complaint_id"],
        "status": complaint["status"],
        "submitted_at": complaint["submitted_at"],
        "category": complaint["category"],
        "subject": complaint["subject"],
        "resolved_at": complaint.get("resolved_at"),
        "resolution_notes": complaint.get("resolution_notes"),
        "status_history": complaint.get("status_history", [])
    }


# ==================== ADMIN ENDPOINTS (Auth Required) ====================

@grievance_router.get("/grievance/complaints", tags=["Grievance Management"])
async def get_all_complaints(
    status: Optional[GrievanceStatus] = Query(None),
    category: Optional[GrievanceCategory] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db_client: MongoClient = Depends(db.get_client)
):
    """
    Get all grievance complaints (Admin/Editor only)
    """
    if current_user.role not in ["admin", "author"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    complaints_collection = db_client[db.db_name]["grievance_complaints"]
    
    # Build query
    query = {}
    if status:
        query["status"] = status
    if category:
        query["category"] = category
    
    # Get complaints
    complaints = list(
        complaints_collection.find(query)
        .sort("submitted_at", DESCENDING)
        .skip(skip)
        .limit(limit)
    )
    
    # Convert ObjectId to string
    for complaint in complaints:
        complaint["_id"] = str(complaint["_id"])
    
    total = complaints_collection.count_documents(query)
    
    return {
        "complaints": complaints,
        "total": total,
        "skip": skip,
        "limit": limit
    }


@grievance_router.get("/grievance/complaints/{complaint_id}", tags=["Grievance Management"])
async def get_complaint_details(
    complaint_id: str,
    current_user: User = Depends(get_current_user),
    db_client: MongoClient = Depends(db.get_client)
):
    """
    Get detailed complaint information (Admin/Editor only)
    Supports both complaint ID (GRV-2025-XXXXX) and MongoDB ObjectId
    """
    if current_user.role not in ["admin", "author"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    complaints_collection = db_client[db.db_name]["grievance_complaints"]
    
    # Try to find by complaint_id first
    complaint = complaints_collection.find_one({"complaint_id": complaint_id})
    
    # If not found, try by MongoDB ObjectId
    if not complaint and ObjectId.is_valid(complaint_id):
        complaint = complaints_collection.find_one({"_id": ObjectId(complaint_id)})
    
    if not complaint:
        raise HTTPException(status_code=404, detail="Complaint not found")
    
    complaint["_id"] = str(complaint["_id"])
    return complaint


@grievance_router.patch("/grievance/complaints/{complaint_id}", tags=["Grievance Management"])
async def update_complaint(
    complaint_id: str,
    update: GrievanceUpdate,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db_client: MongoClient = Depends(db.get_client)
):
    """
    Update grievance complaint (Admin/Editor only)
    Supports both complaint ID (GRV-2025-XXXXX) and MongoDB ObjectId
    """
    if current_user.role not in ["admin", "author"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    complaints_collection = db_client[db.db_name]["grievance_complaints"]
    
    # Try to find by complaint_id first
    complaint = complaints_collection.find_one({"complaint_id": complaint_id})
    
    # If not found, try by MongoDB ObjectId
    if not complaint and ObjectId.is_valid(complaint_id):
        complaint = complaints_collection.find_one({"_id": ObjectId(complaint_id)})
    
    if not complaint:
        raise HTTPException(status_code=404, detail="Complaint not found")
    
    # Get the actual complaint_id for query
    actual_complaint_id = complaint["complaint_id"]
    
    # Prepare update
    update_dict = {}
    update_dict["updated_at"] = datetime.utcnow()
    update_dict["updated_by"] = current_user.username
    
    if update.status:
        update_dict["status"] = update.status
        
        # Add to status history
        status_history = complaint.get("status_history", [])
        status_history.append({
            "status": update.status,
            "timestamp": datetime.utcnow(),
            "updated_by": current_user.username,
            "notes": update.resolution_notes or ""
        })
        update_dict["status_history"] = status_history
        
        # If resolved, add resolution timestamp
        if update.status == GrievanceStatus.RESOLVED:
            update_dict["resolved_at"] = datetime.utcnow()
            update_dict["resolved_by"] = current_user.username
    
    if update.assigned_to:
        update_dict["assigned_to"] = update.assigned_to
    
    if update.resolution_notes:
        update_dict["resolution_notes"] = update.resolution_notes
    
    if update.internal_notes:
        internal_notes = complaint.get("internal_notes", [])
        internal_notes.append({
            "note": update.internal_notes,
            "added_by": current_user.username,
            "timestamp": datetime.utcnow()
        })
        update_dict["internal_notes"] = internal_notes
    
    # Update complaint using _id to ensure correct document
    complaints_collection.update_one(
        {"_id": complaint["_id"]},
        {"$set": update_dict}
    )
    
    # Send resolution email if resolved
    if update.status == GrievanceStatus.RESOLVED and update.resolution_notes:
        background_tasks.add_task(
            send_grievance_resolution,
            complaint["complainant_email"],
            complaint["complainant_name"],
            actual_complaint_id,
            update.resolution_notes
        )
    
    return {"message": "Complaint updated successfully", "complaint_id": actual_complaint_id}


@grievance_router.get("/grievance/statistics", tags=["Grievance Management"])
async def get_grievance_statistics(
    current_user: User = Depends(get_current_user),
    db_client: MongoClient = Depends(db.get_client)
):
    """
    Get grievance statistics (Admin only)
    """
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    complaints_collection = db_client[db.db_name]["grievance_complaints"]
    
    # Total complaints
    total = complaints_collection.count_documents({})
    
    # By status
    pending = complaints_collection.count_documents({"status": {"$in": [GrievanceStatus.SUBMITTED, GrievanceStatus.UNDER_REVIEW, GrievanceStatus.IN_PROGRESS]}})
    resolved = complaints_collection.count_documents({"status": GrievanceStatus.RESOLVED})
    rejected = complaints_collection.count_documents({"status": GrievanceStatus.REJECTED})
    
    # By category
    categories = {}
    for category in GrievanceCategory:
        count = complaints_collection.count_documents({"category": category.value})
        if count > 0:
            categories[category.value] = count
    
    # This month
    first_day = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    this_month = complaints_collection.count_documents({"submitted_at": {"$gte": first_day}})
    
    # Calculate average resolution time
    resolved_complaints = list(complaints_collection.find({
        "status": GrievanceStatus.RESOLVED,
        "resolved_at": {"$exists": True}
    }))
    
    avg_resolution_hours = 0.0
    if resolved_complaints:
        total_hours = sum([
            (c["resolved_at"] - c["submitted_at"]).total_seconds() / 3600
            for c in resolved_complaints
        ])
        avg_resolution_hours = total_hours / len(resolved_complaints)
    
    resolution_rate = (resolved / total * 100) if total > 0 else 0.0
    
    return GrievanceStatistics(
        total_complaints=total,
        pending_complaints=pending,
        resolved_complaints=resolved,
        rejected_complaints=rejected,
        avg_resolution_time_hours=round(avg_resolution_hours, 2),
        complaints_by_category=categories,
        complaints_this_month=this_month,
        resolution_rate_percentage=round(resolution_rate, 2)
    )


# ==================== GRIEVANCE INFO MANAGEMENT (Admin Only) ====================

@grievance_router.post("/grievance/officer", tags=["Grievance Management"])
async def set_grievance_officer(
    officer: GrievanceOfficer,
    current_user: User = Depends(get_current_user),
    db_client: MongoClient = Depends(db.get_client)
):
    """
    Set or update Grievance Redressal Officer (Admin only)
    """
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    grievance_collection = db_client[db.db_name]["grievance_info"]
    
    # Deactivate existing officers
    grievance_collection.update_many(
        {"type": "officer"},
        {"$set": {"is_active": False}}
    )
    
    # Insert new officer
    officer_dict = officer.dict()
    officer_dict["type"] = "officer"
    officer_dict["appointed_date"] = datetime.utcnow()
    officer_dict["appointed_by"] = current_user.username
    
    grievance_collection.insert_one(officer_dict)
    
    return {"message": "Grievance Officer updated successfully"}


@grievance_router.post("/grievance/self-regulatory-body", tags=["Grievance Management"])
async def set_self_regulatory_body(
    body: SelfRegulatoryBody,
    current_user: User = Depends(get_current_user),
    db_client: MongoClient = Depends(db.get_client)
):
    """
    Set or update Self Regulatory Body membership (Admin only)
    """
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    grievance_collection = db_client[db.db_name]["grievance_info"]
    
    # Deactivate existing entries
    grievance_collection.update_many(
        {"type": "self_regulatory_body"},
        {"$set": {"is_active": False}}
    )
    
    # Insert new entry
    body_dict = body.dict()
    body_dict["type"] = "self_regulatory_body"
    body_dict["updated_at"] = datetime.utcnow()
    body_dict["updated_by"] = current_user.username
    
    grievance_collection.insert_one(body_dict)
    
    return {"message": "Self Regulatory Body information updated successfully"}


@grievance_router.post("/grievance/editor", tags=["Grievance Management"])
async def add_news_editor(
    editor: NewsEditor,
    current_user: User = Depends(get_current_user),
    db_client: MongoClient = Depends(db.get_client)
):
    """
    Add a News Editor (Admin only)
    """
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    grievance_collection = db_client[db.db_name]["grievance_info"]
    
    # Check if email already exists
    existing = grievance_collection.find_one({"type": "editor", "email": editor.email, "is_active": True})
    if existing:
        raise HTTPException(status_code=400, detail="Editor with this email already exists")
    
    # Insert editor
    editor_dict = editor.dict()
    editor_dict["type"] = "editor"
    editor_dict["appointed_date"] = datetime.utcnow()
    editor_dict["appointed_by"] = current_user.username
    
    result = grievance_collection.insert_one(editor_dict)
    editor_dict["_id"] = str(result.inserted_id)
    
    return {"message": "News Editor added successfully", "editor": editor_dict}


@grievance_router.get("/grievance/editors", tags=["Grievance Management"])
async def get_all_editors(
    current_user: User = Depends(get_current_user),
    db_client: MongoClient = Depends(db.get_client)
):
    """
    Get all News Editors (Admin only)
    """
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    grievance_collection = db_client[db.db_name]["grievance_info"]
    
    editors = list(grievance_collection.find({"type": "editor"}))
    
    for editor in editors:
        editor["_id"] = str(editor["_id"])
    
    return {"editors": editors}


@grievance_router.delete("/grievance/editor/{editor_id}", tags=["Grievance Management"])
async def remove_news_editor(
    editor_id: str,
    current_user: User = Depends(get_current_user),
    db_client: MongoClient = Depends(db.get_client)
):
    """
    Remove/deactivate a News Editor (Admin only)
    """
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    grievance_collection = db_client[db.db_name]["grievance_info"]
    
    result = grievance_collection.update_one(
        {"_id": ObjectId(editor_id), "type": "editor"},
        {"$set": {"is_active": False, "deactivated_at": datetime.utcnow(), "deactivated_by": current_user.username}}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Editor not found")
    
    return {"message": "News Editor removed successfully"}
