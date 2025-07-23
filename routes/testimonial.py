from fastapi import APIRouter, Depends, HTTPException, File, UploadFile, Form
from pymongo import MongoClient
from models.testimonial import Testimonial
from models.user import User
from database.db import db
from typing import List
from bson import ObjectId
from datetime import datetime
import uuid
import boto3
from routes.user import get_current_user
from routes.config import AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_REGION
from typing import Optional
from typing import List

route5 = APIRouter()

AWS_BUCKET_NAME = "projectdevops-blogs-new"

s3_client = boto3.client(
    "s3",
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    region_name=AWS_REGION,
)

@route5.post("/testimonials", response_model=Testimonial, tags=["Testimonials"])
async def create_testimonial(
    username: str = Form(...),
    name: str = Form(...),
    city: str = Form(...),
    email: str = Form(...),
    linkedin: str = Form(...),
    phone: str = Form(...),
    content: str = Form(...),
    file: UploadFile = File(...),
    db_client: MongoClient = Depends(db.get_client)
):
    file_extension = file.filename.split(".")[-1]
    unique_filename = f"testimonials/{uuid.uuid4()}.{file_extension}"

    try:
        s3_client.upload_fileobj(
            file.file,
            AWS_BUCKET_NAME,
            unique_filename,
            ExtraArgs={"ContentType": file.content_type, "ACL": "public-read"}
        )
        image_url = f"https://{AWS_BUCKET_NAME}.s3.{AWS_REGION}.amazonaws.com/{unique_filename}"
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Image upload failed: {str(e)}")

    testimonial_data = {
        "username": username,
        "name": name,
        "city": city,
        "email": email,
        "linkedin": linkedin,
        "phone": phone,
        "content": content,
        "image_url": image_url
    }

    result = db_client[db.db_name]["testimonials"].insert_one(testimonial_data)
    testimonial_data["_id"] = str(result.inserted_id)

    return testimonial_data

@route5.get("/testimonials", response_model=List[Testimonial], tags=["Testimonials"])
async def get_testimonials(db_client: MongoClient = Depends(db.get_client)):
    testimonials = list(db_client[db.db_name]["testimonials"].find())
    
    for testimonial in testimonials:
        testimonial["_id"] = str(testimonial["_id"])
        
    return testimonials




