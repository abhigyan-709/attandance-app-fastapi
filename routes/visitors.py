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


# from fastapi import APIRouter, Request
# from datetime import datetime, timedelta
# from database.db import db
# from pydantic import BaseModel

# router4 = APIRouter()

# # Pydantic model for response
# class VisitorCountResponse(BaseModel):
#     count: int

# @router4.get("/visitor-count", response_model=VisitorCountResponse)
# async def get_visitor_count():
#     """Fetch the current visitor count."""
#     client = db.get_client()  # Get MongoDB client
#     visitors_collection = client.testdb["visitors"]  # Access the correct database and collection

#     visitors = visitors_collection.find_one({"_id": "visitor_count"})
#     if not visitors:
#         visitors_collection.insert_one({"_id": "visitor_count", "count": 1})
#         return {"count": 1}
    
#     return {"count": visitors["count"]}

# @router4.post("/increment-visitor", response_model=VisitorCountResponse)
# async def increment_visitor_count(request: Request):
#     """Increment the visitor count and return the updated value, once per hour per unique IP."""
#     client = db.get_client()  
#     visitors_collection = client.testdb["visitors"]  

#     # Get the IP address of the visitor
#     ip = request.client.host

#     # Check if the visitor has been recorded and their last visit timestamp
#     visitor = visitors_collection.find_one({"ip": ip})

#     # Get current timestamp
#     current_time = datetime.utcnow()

#     # If the visitor exists, check if their last visit was within the last hour
#     if visitor:
#         last_visited = visitor.get("last_visited")
#         if last_visited:
#             last_visited = last_visited.replace(tzinfo=None)  # Remove timezone info if present
#             time_diff = current_time - last_visited

#             # If the last visit was within the last hour, don't increment the count
#             if time_diff < timedelta(hours=1):
#                 return {"count": visitor.get("count", 0)}  # Return current count without incrementing
    
#     # Visitor is either new or last visit was over an hour ago, increment the visitor count
#     visitors = visitors_collection.find_one({"_id": "visitor_count"})
#     if not visitors:
#         visitors_collection.insert_one({"_id": "visitor_count", "count": 1})
#         visitors_count = 1
#     else:
#         visitors_count = visitors["count"] + 1
#         visitors_collection.update_one({"_id": "visitor_count"}, {"$set": {"count": visitors_count}})

#     # Insert or update visitor info
#     visitors_collection.update_one(
#         {"ip": ip},
#         {"$set": {"ip": ip, "last_visited": current_time, "count": 1}},
#         upsert=True,
#     )

#     return {"count": visitors_count}
