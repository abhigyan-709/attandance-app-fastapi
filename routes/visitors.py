from fastapi import APIRouter
from database.db import db  # Importing db instance

router4 = APIRouter()

@router4.get("/visitor-count")
async def get_visitor_count():
    """Fetch the current visitor count."""
    client = db.get_client()  # Get MongoDB client
    visitors_collection = client.testdb["visitors"]  # Access the correct database and collection

    visitors = visitors_collection.find_one({"_id": "visitor_count"})
    if not visitors:
        visitors_collection.insert_one({"_id": "visitor_count", "count": 1})
        return {"count": 1}
    
    return {"count": visitors["count"]}

@router4.post("/increment-visitor")
async def increment_visitor_count():
    """Increment the visitor count and return the updated value."""
    client = db.get_client()  
    visitors_collection = client.testdb["visitors"]  

    visitors = visitors_collection.find_one({"_id": "visitor_count"})
    
    if not visitors:
        visitors_collection.insert_one({"_id": "visitor_count", "count": 1})
        return {"count": 1}

    new_count = visitors["count"] + 1
    visitors_collection.update_one({"_id": "visitor_count"}, {"$set": {"count": new_count}})
    
    return {"count": new_count}


