from fastapi import APIRouter, Depends
from database.db import db

router4 = APIRouter()

@router4.get("/visitor-count")
async def get_visitor_count():
    """Fetch the current visitor count."""
    visitors = db.visitors.find_one({"_id": "visitor_count"})
    if not visitors:
        db.visitors.insert_one({"_id": "visitor_count", "count": 1})
        return {"count": 1}
    return {"count": visitors["count"]}

@router4.post("/increment-visitor")
async def increment_visitor_count():
    """Increment the visitor count and return the updated value."""
    visitors = db.visitors.find_one({"_id": "visitor_count"})
    
    if not visitors:
        db.visitors.insert_one({"_id": "visitor_count", "count": 1})
        return {"count": 1}

    new_count = visitors["count"] + 1
    db.visitors.update_one({"_id": "visitor_count"}, {"$set": {"count": new_count}})
    
    return {"count": new_count}
