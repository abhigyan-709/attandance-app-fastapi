# routes/designation.py

from fastapi import APIRouter, Depends, HTTPException, Query
from pymongo import MongoClient, ASCENDING
from typing import List, Optional
from datetime import datetime
from bson import ObjectId

from database.db import db
from models.user import User
from models.designation import (
    AuthorDesignation, DesignationResponse, DesignationLevel, DEFAULT_DESIGNATIONS
)
from routes.user import get_current_user

designation_router = APIRouter()


# ==================== PUBLIC ENDPOINTS ====================

@designation_router.get("/designations", response_model=List[DesignationResponse], tags=["Designations"])
async def get_all_designations(
    active_only: bool = Query(True, description="Return only active designations"),
    db_client: MongoClient = Depends(db.get_client)
):
    """
    Get all author designations (Public endpoint for UI dropdowns)
    """
    designations_collection = db_client[db.db_name]["designations"]
    
    # Build query
    query = {"is_active": True} if active_only else {}
    
    # Get designations sorted by display_order
    designations = list(
        designations_collection.find(query).sort("display_order", ASCENDING)
    )
    
    # Convert to response model
    result = []
    for des in designations:
        result.append(DesignationResponse(
            id=str(des["_id"]),
            name=des["name"],
            level=des["level"],
            can_handle_grievances=des.get("can_handle_grievances", False),
            auto_assign_grievances=des.get("auto_assign_grievances", False),
            display_order=des.get("display_order", 100),
            is_active=des.get("is_active", True),
            description=des.get("description"),
            created_at=des.get("created_at"),
            created_by=des.get("created_by")
        ))
    
    return result


@designation_router.get("/designations/grievance-handlers", tags=["Designations"])
async def get_grievance_handler_designations(
    db_client: MongoClient = Depends(db.get_client)
):
    """
    Get designations that can handle grievances (for auto-assignment)
    """
    designations_collection = db_client[db.db_name]["designations"]
    
    designations = list(
        designations_collection.find({
            "is_active": True,
            "can_handle_grievances": True
        }).sort("display_order", ASCENDING)
    )
    
    result = []
    for des in designations:
        result.append({
            "id": str(des["_id"]),
            "name": des["name"],
            "level": des["level"],
            "auto_assign": des.get("auto_assign_grievances", False)
        })
    
    return result


# ==================== ADMIN ENDPOINTS ====================

@designation_router.post("/designations", tags=["Designation Management"])
async def create_designation(
    designation: AuthorDesignation,
    current_user: User = Depends(get_current_user),
    db_client: MongoClient = Depends(db.get_client)
):
    """
    Create a new designation (Admin only)
    """
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    designations_collection = db_client[db.db_name]["designations"]
    
    # Check if designation name already exists
    existing = designations_collection.find_one({
        "name": designation.name,
        "is_active": True
    })
    
    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"Designation '{designation.name}' already exists"
        )
    
    # Prepare designation document
    designation_dict = designation.dict()
    designation_dict["created_at"] = datetime.utcnow()
    designation_dict["created_by"] = current_user.username
    
    # Insert designation
    result = designations_collection.insert_one(designation_dict)
    
    designation_dict["_id"] = str(result.inserted_id)
    
    return {
        "message": "Designation created successfully",
        "designation": designation_dict
    }


@designation_router.put("/designations/{designation_id}", tags=["Designation Management"])
async def update_designation(
    designation_id: str,
    designation: AuthorDesignation,
    current_user: User = Depends(get_current_user),
    db_client: MongoClient = Depends(db.get_client)
):
    """
    Update a designation (Admin only)
    """
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    designations_collection = db_client[db.db_name]["designations"]
    
    # Check if designation exists
    existing = designations_collection.find_one({"_id": ObjectId(designation_id)})
    if not existing:
        raise HTTPException(status_code=404, detail="Designation not found")
    
    # Prepare update
    update_dict = designation.dict()
    update_dict["updated_at"] = datetime.utcnow()
    update_dict["updated_by"] = current_user.username
    
    # Update designation
    designations_collection.update_one(
        {"_id": ObjectId(designation_id)},
        {"$set": update_dict}
    )
    
    return {"message": "Designation updated successfully"}


@designation_router.delete("/designations/{designation_id}", tags=["Designation Management"])
async def delete_designation(
    designation_id: str,
    current_user: User = Depends(get_current_user),
    db_client: MongoClient = Depends(db.get_client)
):
    """
    Deactivate a designation (Admin only)
    Soft delete - sets is_active to False
    """
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    designations_collection = db_client[db.db_name]["designations"]
    
    result = designations_collection.update_one(
        {"_id": ObjectId(designation_id)},
        {
            "$set": {
                "is_active": False,
                "deactivated_at": datetime.utcnow(),
                "deactivated_by": current_user.username
            }
        }
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Designation not found")
    
    return {"message": "Designation deactivated successfully"}


@designation_router.post("/designations/initialize", tags=["Designation Management"])
async def initialize_default_designations(
    current_user: User = Depends(get_current_user),
    db_client: MongoClient = Depends(db.get_client)
):
    """
    Initialize default designations (Admin only, one-time setup)
    """
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    designations_collection = db_client[db.db_name]["designations"]
    
    # Check if already initialized
    existing_count = designations_collection.count_documents({})
    if existing_count > 0:
        raise HTTPException(
            status_code=400,
            detail=f"Designations already initialized ({existing_count} found). Use update endpoints to modify."
        )
    
    # Insert default designations
    inserted_count = 0
    for designation_data in DEFAULT_DESIGNATIONS:
        designation_data["created_at"] = datetime.utcnow()
        designation_data["created_by"] = current_user.username
        designations_collection.insert_one(designation_data)
        inserted_count += 1
    
    return {
        "message": "Default designations initialized successfully",
        "count": inserted_count,
        "designations": [d["name"] for d in DEFAULT_DESIGNATIONS]
    }


@designation_router.post("/designations/sync-users", tags=["Designation Management"])
async def sync_user_designations(
    current_user: User = Depends(get_current_user),
    db_client: MongoClient = Depends(db.get_client)
):
    """
    Sync existing user designations with designation master
    Updates author_designation field to match available designations
    (Admin only)
    """
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    users_collection = db_client[db.db_name]["user"]
    designations_collection = db_client[db.db_name]["designations"]
    
    # Get all valid designation names
    valid_designations = {
        d["name"]: d 
        for d in designations_collection.find({"is_active": True})
    }
    
    # Find all authors with designations
    authors = users_collection.find({
        "role": {"$in": ["author", "admin"]},
        "author_designation": {"$exists": True, "$ne": None}
    })
    
    updated_count = 0
    invalid_count = 0
    
    for author in authors:
        current_designation = author.get("author_designation")
        
        # Check if designation is valid
        if current_designation and current_designation not in valid_designations:
            # Mark as invalid or update to default
            users_collection.update_one(
                {"_id": author["_id"]},
                {
                    "$set": {
                        "author_designation_invalid": True,
                        "author_designation_original": current_designation
                    }
                }
            )
            invalid_count += 1
        elif current_designation in valid_designations:
            # Valid designation - add metadata
            designation_info = valid_designations[current_designation]
            users_collection.update_one(
                {"_id": author["_id"]},
                {
                    "$set": {
                        "author_designation_level": designation_info["level"],
                        "can_handle_grievances": designation_info.get("can_handle_grievances", False),
                        "author_designation_synced_at": datetime.utcnow()
                    },
                    "$unset": {
                        "author_designation_invalid": "",
                        "author_designation_original": ""
                    }
                }
            )
            updated_count += 1
    
    return {
        "message": "User designations synced successfully",
        "updated": updated_count,
        "invalid": invalid_count,
        "total_valid_designations": len(valid_designations)
    }


@designation_router.get("/designations/users-by-designation", tags=["Designation Management"])
async def get_users_by_designation(
    designation_name: Optional[str] = Query(None),
    can_handle_grievances: Optional[bool] = Query(None),
    current_user: User = Depends(get_current_user),
    db_client: MongoClient = Depends(db.get_client)
):
    """
    Get users grouped by designation (Admin/Author only)
    Useful for grievance assignment
    """
    if current_user.role not in ["admin", "author"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    users_collection = db_client[db.db_name]["user"]
    
    # Build query
    query = {
        "role": {"$in": ["author", "admin"]},
        "is_active": True,
        "author_designation": {"$exists": True, "$ne": None}
    }
    
    if designation_name:
        query["author_designation"] = designation_name
    
    if can_handle_grievances is not None:
        query["can_handle_grievances"] = can_handle_grievances
    
    # Get users
    users = list(users_collection.find(
        query,
        {
            "username": 1,
            "first_name": 1,
            "last_name": 1,
            "email": 1,
            "author_designation": 1,
            "author_designation_level": 1,
            "can_handle_grievances": 1
        }
    ))
    
    # Convert ObjectId to string
    for user in users:
        user["_id"] = str(user["_id"])
    
    # Group by designation
    grouped = {}
    for user in users:
        designation = user.get("author_designation", "Unknown")
        if designation not in grouped:
            grouped[designation] = []
        grouped[designation].append(user)
    
    return {
        "total_users": len(users),
        "designations_count": len(grouped),
        "users_by_designation": grouped
    }
