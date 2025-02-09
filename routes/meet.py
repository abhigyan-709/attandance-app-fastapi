from fastapi import APIRouter, HTTPException
from models.meet import MeetLink
from database.db import db
from datetime import datetime
from fastapi.responses import JSONResponse
router6 = APIRouter()



@router6.post("/add-meet-link", response_model=MeetLink)
async def add_meet_link(meet_link: MeetLink):
    db_client = db.get_client()
    db_client[db.db_name]["meet"].insert_one(meet_link.dict())
    return JSONResponse(content={"message": "Message sent successfully"}, status_code=201)


# Fetch the latest Google Meet link
@router6.get("/get-meet-link")
async def get_meet_link():
    db_client = db.get_client()
    meet_link = db_client[db.db_name]["meet"].find_one(sort=[("created_at", -1)])
    if meet_link:
        return meet_link
    raise HTTPException(status_code=404, detail="No Google Meet link found")
