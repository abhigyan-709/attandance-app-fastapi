from fastapi import APIRouter, Depends, HTTPException, File, UploadFile
from pymongo import MongoClient
from models.blogs import BlogPost, Comment, Category
from models.user import User
from database.db import db
from typing import List
from bson import ObjectId
from datetime import datetime
from routes.user import get_current_user
import uuid
import boto3
from routes.config import AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_BUCKET_NAME, AWS_REGION


blog_router = APIRouter()

s3_client = boto3.client(
    "s3",
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    region_name=AWS_REGION,
)

def get_current_admin_user(current_user: User = Depends(get_current_user)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized to perform this action")
    return current_user

def serialize_document(document):
    """Convert MongoDB document ObjectId fields to strings."""
    if document and "_id" in document:
        document["_id"] = str(document["_id"])
    return document


# @blog_router.post("/blogs", response_model=BlogPost, tags=["Blogs"])
# async def create_blog(
#     blog: BlogPost,
#     file: UploadFile = File(...),  # Image file to be uploaded
#     current_admin: User = Depends(get_current_admin_user),
#     db_client: MongoClient = Depends(db.get_client)
# ):
#     # Generate a unique filename for the uploaded image
#     file_extension = file.filename.split(".")[-1]
#     unique_filename = f"blogs/{uuid.uuid4()}.{file_extension}"

#     try:
#         # Upload the file to S3
#         s3_client.upload_fileobj(
#             file.file,
#             AWS_BUCKET_NAME,
#             unique_filename,
#             ExtraArgs={"ACL": "public-read", "ContentType": file.content_type},
#         )

#         # Generate the S3 image URL
#         image_url = f"https://{AWS_BUCKET_NAME}.s3.{AWS_REGION}.amazonaws.com/{unique_filename}"
    
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Image upload failed: {str(e)}")

#     # Assign values to blog fields
#     blog.author_username = current_admin.username
#     blog.image_url = image_url  # Store the image URL
#     blog.created_at = datetime.utcnow()
#     blog.updated_at = datetime.utcnow()

#     # Convert blog to a dictionary for MongoDB insertion
#     blog_dict = blog.dict(by_alias=True, exclude={"id"})
#     inserted_blog = db_client[db.db_name]["blogs"].insert_one(blog_dict)
    
#     # Set the inserted blog ID
#     blog.id = str(inserted_blog.inserted_id)
    
#     return blog

from fastapi import Form

@blog_router.post("/blogs", response_model=BlogPost, tags=["Blogs"])
async def create_blog(
    title: str = Form(...),
    content: str = Form(...),
    categories: List[str] = Form([]),
    published: bool = Form(True),
    file: UploadFile = File(...),  # Image file upload
    current_admin: User = Depends(get_current_admin_user),
    db_client: MongoClient = Depends(db.get_client)
):
    # Generate a unique filename for the uploaded image
    file_extension = file.filename.split(".")[-1]
    unique_filename = f"blogs/{uuid.uuid4()}.{file_extension}"

    try:
        # Upload file to S3
        s3_client.upload_fileobj(
            file.file,
            AWS_BUCKET_NAME,
            unique_filename,
            ExtraArgs={"ContentType": file.content_type}  # Keep ContentType, remove ACL
        )


        # Generate S3 image URL
        image_url = f"https://{AWS_BUCKET_NAME}.s3.{AWS_REGION}.amazonaws.com/{unique_filename}"
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Image upload failed: {str(e)}")

    # Create the blog dictionary
    blog_data = {
        "title": title,
        "image_url": image_url,
        "content": content,
        "author_username": current_admin.username,
        "categories": categories,
        "published": published,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }

    # Insert into MongoDB
    inserted_blog = db_client[db.db_name]["blogs"].insert_one(blog_data)
    
    # Assign ID to response
    blog_data["_id"] = str(inserted_blog.inserted_id)
    
    return blog_data



@blog_router.get("/blogs", response_model=List[BlogPost], tags=["Blogs"])
async def get_blogs(db_client: MongoClient = Depends(db.get_client)):
    blogs = list(db_client[db.db_name]["blogs"].find())
    return [serialize_document(blog) for blog in blogs]

@blog_router.get("/blogs/{blog_id}", response_model=BlogPost, tags=["Blogs"])
async def get_blog(blog_id: str, db_client: MongoClient = Depends(db.get_client)):
    blog = db_client[db.db_name]["blogs"].find_one({"_id": ObjectId(blog_id)})
    if not blog:
        raise HTTPException(status_code=404, detail="Blog not found")
    
    return serialize_document(blog)


@blog_router.put("/blogs/{blog_id}", response_model=BlogPost, tags=["Blogs"])
async def update_blog(
    blog_id: str,
    updated_blog: BlogPost,
    current_admin: User = Depends(get_current_admin_user),
    db_client: MongoClient = Depends(db.get_client),
):
    existing_blog = db_client[db.db_name]["blogs"].find_one({"_id": ObjectId(blog_id)})
    if not existing_blog:
        raise HTTPException(status_code=404, detail="Blog not found")
    
    updated_blog.updated_at = datetime.utcnow()
    db_client[db.db_name]["blogs"].update_one(
        {"_id": ObjectId(blog_id)},
        {"$set": updated_blog.dict(by_alias=True, exclude={"id", "author_username", "created_at"})}
    )
    updated_blog.id = blog_id
    return updated_blog

@blog_router.delete("/blogs/{blog_id}", tags=["Blogs"])
async def delete_blog(
    blog_id: str,
    current_admin: User = Depends(get_current_admin_user),
    db_client: MongoClient = Depends(db.get_client),
):
    existing_blog = db_client[db.db_name]["blogs"].find_one({"_id": ObjectId(blog_id)})
    if not existing_blog:
        raise HTTPException(status_code=404, detail="Blog not found")
    
    db_client[db.db_name]["blogs"].delete_one({"_id": ObjectId(blog_id)})
    return {"message": "Blog deleted successfully"}

@blog_router.post("/blogs/{blog_id}/comments", response_model=Comment, tags=["Blogs"])
async def add_comment(
    blog_id: str,
    comment: Comment,
    current_user: User = Depends(get_current_user),
    db_client: MongoClient = Depends(db.get_client),
):
    comment.blog_id = blog_id
    comment.username = current_user.username  # Store username instead of user ID
    comment.created_at = datetime.utcnow()
    comment_dict = comment.dict(by_alias=True, exclude={"id"})
    inserted_comment = db_client[db.db_name]["comments"].insert_one(comment_dict)
    comment.id = str(inserted_comment.inserted_id)
    return comment

@blog_router.post("/categories", response_model=Category, tags=["Blogs"])
async def create_category(
    category: Category,
    current_admin: User = Depends(get_current_admin_user),
    db_client: MongoClient = Depends(db.get_client),
):
    category_dict = category.dict(by_alias=True, exclude={"id"})
    inserted_category = db_client[db.db_name]["categories"].insert_one(category_dict)
    category.id = str(inserted_category.inserted_id)
    return category
