from fastapi import APIRouter, Depends, HTTPException
from passlib.context import CryptContext
from database.db import db
from models.user import User
from models.messages import Message
from models.token import Token
from typing import Union
from pymongo import MongoClient
import secrets
from bson import ObjectId
from fastapi.responses import JSONResponse
from routes.user import get_current_user 

route3 = APIRouter()

@route3.post("/message", tags=["Message"])
async def create_message(message: Message):
    db_client = db.get_client()
    db_client[db.db_name]["messages"].insert_one(message.dict())
    return JSONResponse(content={"message": "Message sent successfully"}, status_code=201)

@route3.get("/messages", tags=["Message"])
async def get_messages(current_user: User = Depends(get_current_user)):

    if current_user.role != "admin":
        raise HTTPException(
            status_code=403,
            detail="You do not have permission to access this resource"
        )
    
    db_client = db.get_client()
    messages = db_client[db.db_name]["messages"].find()
    messages_list = []
    for message in messages:
        message["_id"] = str(message["_id"])
        messages_list.append(message)

    return messages_list