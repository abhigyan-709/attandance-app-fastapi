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

route3 = APIRouter()

@route3.post("/message", tags=["Message"])
async def create_message(message: Message):
    db_client = db.get_client()
    db_client[db.db_name]["messages"].insert_one(message.dict())
    return JSONResponse(content={"message": "Message sent successfully"}, status_code=201)

