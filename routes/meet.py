# from fastapi import APIRouter, Depends, HTTPException
# from models.meet import MeetLink
# from database.db import db
# from fastapi.responses import JSONResponse
# from bson import ObjectId
# from models.user import User
# from models.token import Token  # Ensure this import is present for `User` and `get_current_user`

# # Import the get_current_user function
# from routes.user import get_current_user  # Adjust this path to where get_current_user is defined

# router6 = APIRouter()

# # Add Meet Link Endpoint
# @router6.post("/add-meet-link", response_model=MeetLink)
# async def add_meet_link(meet_link: MeetLink, current_user: User = Depends(get_current_user)):
#     # Check if the current user is an admin
#     if current_user.role != "admin":
#         raise HTTPException(
#             status_code=403,
#             detail="You do not have permission to add a Google Meet link"
#         )

#     db_client = db.get_client()
#     db_client[db.db_name]["meet"].insert_one(meet_link.dict())
#     return JSONResponse(content={"message": "Meet link added successfully"}, status_code=201)

# # Fetch the latest Google Meet link
# @router6.get("/get-meet-link")
# async def get_meet_link():
#     db_client = db.get_client()
#     meet_link = db_client[db.db_name]["meet"].find_one(sort=[("created_at", -1)])

#     if not meet_link:
#         raise HTTPException(status_code=404, detail="No Google Meet link found")

#     # Convert ObjectId to string
#     meet_link["_id"] = str(meet_link["_id"])

#     return meet_link

from fastapi import APIRouter, Depends, HTTPException
from models.meet import MeetLink
from database.db import db
from fastapi.responses import JSONResponse
from bson import ObjectId
from models.user import User
from models.token import Token  # Ensure this import is present for `User` and `get_current_user`

# Import the get_current_user function
from routes.user import get_current_user  # Adjust this path to where get_current_user is defined

router6 = APIRouter()

# Add Meet Link Endpoint
@router6.post("/add-meet-link", response_model=MeetLink)
async def add_meet_link(meet_link: MeetLink, current_user: User = Depends(get_current_user)):
    # Check if the current user is an admin
    if current_user.role != "admin":
        raise HTTPException(
            status_code=403,
            detail="You do not have permission to add a Google Meet link"
        )

    db_client = db.get_client()

    # Delete the previous meet link if it exists
    db_client[db.db_name]["meet"].delete_many({})  # Deletes all previous meet links

    # Insert the new meet link
    db_client[db.db_name]["meet"].insert_one(meet_link.dict())

    return JSONResponse(content={"message": "Meet link added and previous one replaced successfully"}, status_code=201)

# Fetch the latest Google Meet link
@router6.get("/get-meet-link")
async def get_meet_link():
    db_client = db.get_client()
    meet_link = db_client[db.db_name]["meet"].find_one(sort=[("created_at", -1)])

    if not meet_link:
        raise HTTPException(status_code=404, detail="No Google Meet link found")

    # Convert ObjectId to string
    meet_link["_id"] = str(meet_link["_id"])

    return meet_link
