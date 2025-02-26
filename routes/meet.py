from fastapi import APIRouter, Depends, HTTPException, Query
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
async def add_meet_link(meet_link: MeetLink, batch: str, current_user: User = Depends(get_current_user)):
    # Check if the current user is an admin
    if current_user.role != "admin":
        raise HTTPException(
            status_code=403,
            detail="You do not have permission to add a Google Meet link"
        )

    db_client = db.get_client()

    # Delete the previous meet link for the batch if it exists
    db_client[db.db_name]["meet"].delete_many({"batch": batch})  # Deletes all previous meet links for the batch

    # Insert the new meet link with the batch
    meet_link_dict = meet_link.dict()
    meet_link_dict["batch"] = batch
    db_client[db.db_name]["meet"].insert_one(meet_link_dict)

    return JSONResponse(content={"message": f"Meet link for batch {batch} added and previous one replaced successfully"}, status_code=201)

# Fetch the latest Google Meet link for a batch
@router6.get("/get-meet-link")
async def get_meet_link(batch: str = Query(...)):
    db_client = db.get_client()
    meet_link = db_client[db.db_name]["meet"].find_one({"batch": batch}, sort=[("created_at", -1)])

    if not meet_link:
        raise HTTPException(status_code=404, detail=f"No Google Meet link found for batch {batch}")

    # Convert ObjectId to string
    meet_link["_id"] = str(meet_link["_id"])

    return meet_link
