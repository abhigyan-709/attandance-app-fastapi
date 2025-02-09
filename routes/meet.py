from fastapi import APIRouter, HTTPException
from models.meet import MeetLink
from database.db import db
from datetime import datetime

router = APIRouter()

MEET_COLLECTION = db["meet_links"]

# Generate a new Google Meet link
@router.post("/generate-meet")
async def generate_meet_link():
    new_meet_link = "https://meet.google.com/"  # You can integrate Google API later to generate dynamic links

    # Store in MongoDB
    meet_entry = {"meet_link": new_meet_link, "created_at": datetime.utcnow()}
    MEET_COLLECTION.insert_one(meet_entry)

    return {"meet_link": new_meet_link}


# Fetch the latest Google Meet link
@router.get("/get-meet-link")
async def get_meet_link():
    meet_entry = MEET_COLLECTION.find_one(sort=[("created_at", -1)])  # Get latest link

    if not meet_entry:
        raise HTTPException(status_code=404, detail="No Google Meet link found.")

    return {"meet_link": meet_entry["meet_link"]}
