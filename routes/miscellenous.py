from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import boto3
from typing import List
from models.miscellenous import SFMessage
from database.db import db
from fastapi.responses import JSONResponse
from send_email import send_message_receipt_email
from fastapi import BackgroundTasks

route1 = APIRouter()

# S3 bucket details
BUCKET_NAME = "support-foundation-images"
REGION = "ap-south-1"  # Replace with your AWS region

# Initialize S3 client
s3_client = boto3.client("s3", region_name=REGION)

# Define Pydantic model
class ImageData(BaseModel):
    file_name: str
    url: str
    size: int
    last_modified: str

# Define response model for consistent JSON structure
class ImageResponse(BaseModel):
    status: str
    message: str
    data: List[ImageData]

@route1.get("/s3/images", response_model=ImageResponse, tags=["Utilities & Functions"])
async def get_s3_images():
    """
    Fetches all images from the public S3 bucket and returns a structured JSON response.
    """
    try:
        response = s3_client.list_objects_v2(Bucket=BUCKET_NAME)

        if "Contents" not in response:
            return {"status": "success", "message": "No images found", "data": []}

        # Construct JSON response with object details
        image_data = [
            ImageData(
                file_name=obj["Key"],
                url=f"https://{BUCKET_NAME}.s3.{REGION}.amazonaws.com/{obj['Key']}",
                size=obj["Size"],  # Size in bytes
                last_modified=obj["LastModified"].isoformat()  # Convert datetime to string
            )
            for obj in response["Contents"]
        ]

        return {"status": "success", "message": "Images retrieved successfully", "data": image_data}

    except Exception as e:
        raise HTTPException(status_code=500, detail={"status": "error", "message": f"Error fetching images: {str(e)}"})
    


@route1.post("/sf-message/", tags=["Utilities & Functions"])
async def create_message(message: SFMessage, background_tasks: BackgroundTasks):
    db_client = db.get_client()
    db_client[db.db_name]["sf-messages"].insert_one(message.dict())

    # Send email in the background
    background_tasks.add_task(
        send_message_receipt_email,
        email=message.email,
        first_name=message.first_name,
        last_name=message.last_name,
        mobile=message.mobile,
        message_content=message.message
    )

    return JSONResponse(content={"message": "Message sent successfully"}, status_code=201)


