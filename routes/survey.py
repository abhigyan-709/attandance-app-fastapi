from fastapi import APIRouter, Depends, HTTPException, status
from pymongo import MongoClient
from datetime import datetime
from typing import List
from bson import ObjectId

from models.survey import SurveyForm, SurveyResponse
from models.user import User
from routes.user import get_current_user
from database.db import db

router = APIRouter()


@router.post("/survey", response_model=dict, tags=["Survey"])
async def submit_survey(
    survey: SurveyForm,
    db_client: MongoClient = Depends(db.get_client)
):
    """
    Submit a new survey form (public endpoint - no authentication required)
    """
    database = db_client[db.db_name]
    survey_collection = database["surveys"]
    
    # Convert survey to dict and add timestamp
    survey_dict = survey.model_dump(exclude_none=False)
    survey_dict["submitted_at"] = datetime.utcnow()
    
    # Insert into database
    result = survey_collection.insert_one(survey_dict)
    
    return {
        "message": "Survey submitted successfully",
        "survey_id": str(result.inserted_id),
        "submitted_at": survey_dict["submitted_at"].isoformat()
    }


@router.get("/survey", response_model=List[SurveyResponse], tags=["Survey"])
async def get_all_surveys(
    current_user: User = Depends(get_current_user),
    db_client: MongoClient = Depends(db.get_client)
):
    """
    Get all survey submissions (admin only)
    """
    # Check if user is admin
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can view all surveys"
        )
    
    database = db_client[db.db_name]
    survey_collection = database["surveys"]
    
    # Retrieve all surveys
    surveys = list(survey_collection.find())
    
    # Format response
    survey_responses = []
    for survey in surveys:
        survey["id"] = str(survey["_id"])
        survey["submitted_at"] = survey["submitted_at"].isoformat()
        del survey["_id"]
        survey_responses.append(SurveyResponse(**survey))
    
    return survey_responses


@router.get("/survey/{survey_id}", response_model=SurveyResponse, tags=["Survey"])
async def get_survey_by_id(
    survey_id: str,
    current_user: User = Depends(get_current_user),
    db_client: MongoClient = Depends(db.get_client)
):
    """
    Get a specific survey by ID (admin only)
    """
    # Check if user is admin
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can view surveys"
        )
    
    database = db_client[db.db_name]
    survey_collection = database["surveys"]
    
    # Validate ObjectId
    try:
        survey = survey_collection.find_one({"_id": ObjectId(survey_id)})
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid survey ID format"
        )
    
    if not survey:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Survey not found"
        )
    
    # Format response
    survey["id"] = str(survey["_id"])
    survey["submitted_at"] = survey["submitted_at"].isoformat()
    del survey["_id"]
    
    return SurveyResponse(**survey)


@router.delete("/survey/{survey_id}", response_model=dict, tags=["Survey"])
async def delete_survey(
    survey_id: str,
    current_user: User = Depends(get_current_user),
    db_client: MongoClient = Depends(db.get_client)
):
    """
    Delete a survey by ID (admin only)
    """
    # Check if user is admin
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can delete surveys"
        )
    
    database = db_client[db.db_name]
    survey_collection = database["surveys"]
    
    # Validate ObjectId
    try:
        result = survey_collection.delete_one({"_id": ObjectId(survey_id)})
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid survey ID format"
        )
    
    if result.deleted_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Survey not found"
        )
    
    return {
        "message": "Survey deleted successfully",
        "survey_id": survey_id
    }


@router.get("/survey/stats/summary", response_model=dict, tags=["Survey"])
async def get_survey_stats(
    current_user: User = Depends(get_current_user),
    db_client: MongoClient = Depends(db.get_client)
):
    """
    Get survey statistics (admin only)
    """
    # Check if user is admin
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can view survey statistics"
        )
    
    database = db_client[db.db_name]
    survey_collection = database["surveys"]
    
    # Get total count
    total_surveys = survey_collection.count_documents({})
    
    # Get count by city
    city_pipeline = [
        {"$match": {"city": {"$ne": None, "$exists": True}}},
        {"$group": {"_id": "$city", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": 10}
    ]
    city_stats = list(survey_collection.aggregate(city_pipeline))
    
    # Get recent submissions
    recent_surveys = list(
        survey_collection.find()
        .sort("submitted_at", -1)
        .limit(5)
    )
    
    return {
        "total_surveys": total_surveys,
        "top_cities": [{"city": stat["_id"], "count": stat["count"]} for stat in city_stats],
        "recent_submissions": len(recent_surveys)
    }
