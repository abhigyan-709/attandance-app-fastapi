# from fastapi import APIRouter, HTTPException
# import boto3

# route1 = APIRouter()

# # S3 bucket details
# BUCKET_NAME = "support-foundation-images"
# REGION = "ap-south-1"  # Replace with your AWS region

# # Initialize S3 client
# s3_client = boto3.client("s3", region_name=REGION)

# @route1.get("/s3/images", response_model=list[str], tags=["Utilities & Functions"])
# async def get_s3_images():
#     """
#     Fetches all images from the public S3 bucket and returns a structured JSON response.
#     """
#     try:
#         response = s3_client.list_objects_v2(Bucket=BUCKET_NAME)

#         if "Contents" not in response:
#             return {"status": "success", "message": "No images found", "data": []}

#         # Construct JSON response with object details
#         image_data = [
#             {
#                 "file_name": obj["Key"],
#                 "url": f"https://{BUCKET_NAME}.s3.{REGION}.amazonaws.com/{obj['Key']}",
#                 "size": obj["Size"],  # Size in bytes
#                 "last_modified": obj["LastModified"].isoformat()  # Convert datetime to string
#             }
#             for obj in response["Contents"]
#         ]

#         return {"status": "success", "message": "Images retrieved successfully", "data": image_data}

#     except Exception as e:
#         raise HTTPException(status_code=500, detail={"status": "error", "message": f"Error fetching images: {str(e)}"})

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import boto3
from typing import List

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
