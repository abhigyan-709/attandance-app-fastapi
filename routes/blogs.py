from fastapi import APIRouter, Depends, HTTPException, File, UploadFile, Form
from pymongo import MongoClient
from models.blogs import BlogPost, Comment, Category
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
from pymongo import DESCENDING
from fastapi.responses import HTMLResponse

blog_router = APIRouter()

AWS_BUCKET_NAME = "projectdevops-blogs"

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


@blog_router.post("/blogs", response_model=BlogPost, tags=["Blogs"])
async def create_blog(
    title: str = Form(...),
    content: str = Form(...),
    categories: str = Form([]),
    tags: List[str] = Form([]),  # 🔹 Accepting Tags
    published: bool = Form(True),
    file: UploadFile = File(...),
    current_admin: User = Depends(get_current_admin_user),
    db_client: MongoClient = Depends(db.get_client)
):
    file_extension = file.filename.split(".")[-1]
    unique_filename = f"blogs/{uuid.uuid4()}.{file_extension}"

    try:
        s3_client.upload_fileobj(
            file.file,
            AWS_BUCKET_NAME,
            unique_filename,
            ExtraArgs={"ContentType": file.content_type}
        )
        image_url = f"https://{AWS_BUCKET_NAME}.s3.{AWS_REGION}.amazonaws.com/{unique_filename}"
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Image upload failed: {str(e)}")

    blog_data = {
        "title": title,
        "image_url": image_url,
        "content": content,
        "author_username": current_admin.username,
        "categories": categories,
        "tags": tags,  # 🔹 Storing Tags
        "published": published,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }

    inserted_blog = db_client[db.db_name]["blogs"].insert_one(blog_data)
    blog_data["_id"] = str(inserted_blog.inserted_id)
    
    return blog_data

@blog_router.get("/blogs/tags/{tag}", response_model=List[BlogPost], tags=["Blogs"])
async def get_blogs_by_tag(tag: str, db_client: MongoClient = Depends(db.get_client)):
    blogs = list(db_client[db.db_name]["blogs"].find({"tags": tag}))

    for blog in blogs:
        blog["_id"] = str(blog["_id"])
        blog["comments"] = list(db_client[db.db_name]["comments"].find({"blog_id": blog["_id"]}))
        
        for comment in blog["comments"]:
            comment["_id"] = str(comment["_id"])
    
    return blogs


@blog_router.get("/blogs/filter", response_model=List[BlogPost], tags=["Blogs"])
async def get_blogs_by_category_and_tags(
    category: Optional[str] = None,
    tag: Optional[str] = None,
    db_client: MongoClient = Depends(db.get_client)
):
    query = {}
    if category:
        query["categories"] = category
    if tag:
        query["tags"] = tag

    blogs = list(db_client[db.db_name]["blogs"].find(query))

    for blog in blogs:
        blog["_id"] = str(blog["_id"])
        blog["comments"] = list(db_client[db.db_name]["comments"].find({"blog_id": blog["_id"]}))

        for comment in blog["comments"]:
            comment["_id"] = str(comment["_id"])

    return blogs

@blog_router.get("/blogs/tags", response_model=List[str], tags=["Blogs"])
async def get_all_tags(db_client: MongoClient = Depends(db.get_client)):
    """
    Fetch all unique tags used in blog posts.
    """
    tags_cursor = db_client[db.db_name]["blogs"].aggregate([
        {"$unwind": "$tags"},  # Unwind the tags array
        {"$group": {"_id": "$tags"}}  # Group by unique tags
    ])

    tags = [tag["_id"] for tag in tags_cursor]
    return tags


# @blog_router.get("/blogs", response_model=List[BlogPost], tags=["Blogs"])
# async def get_blogs(db_client: MongoClient = Depends(db.get_client)):
#     blogs = list(db_client[db.db_name]["blogs"].find())

#     for blog in blogs:
#         blog["_id"] = str(blog["_id"])
#         blog["comments"] = list(db_client[db.db_name]["comments"].find({"blog_id": blog["_id"]}))
        
#         for comment in blog["comments"]:
#             comment["_id"] = str(comment["_id"])
    
#     return blogs

@blog_router.get("/blogs", response_model=List[BlogPost], tags=["Blogs"])
async def get_blogs(db_client: MongoClient = Depends(db.get_client)):
    # Sort by 'created_at' in descending order (latest first)
    blogs = list(db_client[db.db_name]["blogs"].find().sort("created_at", DESCENDING))

    for blog in blogs:
        blog["_id"] = str(blog["_id"])
        blog["comments"] = list(db_client[db.db_name]["comments"].find({"blog_id": blog["_id"]}))
        
        for comment in blog["comments"]:
            comment["_id"] = str(comment["_id"])
    
    return blogs


@blog_router.get("/blogs/{blog_id}", response_model=BlogPost, tags=["Blogs"])
async def get_blog(blog_id: str, db_client: MongoClient = Depends(db.get_client)):
    blog = db_client[db.db_name]["blogs"].find_one({"_id": ObjectId(blog_id)})
    if not blog:
        raise HTTPException(status_code=404, detail="Blog not found")

    blog["_id"] = str(blog["_id"])
    blog["comments"] = list(db_client[db.db_name]["comments"].find({"blog_id": blog["_id"]}))
    
    for comment in blog["comments"]:
        comment["_id"] = str(comment["_id"])

    return blog

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
    comment.username = current_user.username
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

@blog_router.get("/categories", response_model=List[Category], tags=["Blogs"])
async def get_categories(
    db_client: MongoClient = Depends(db.get_client),
):
    categories = list(db_client[db.db_name]["categories"].find({}))
    for category in categories:
        category["_id"] = str(category["_id"])  # Convert ObjectId to string
    return categories


@blog_router.post("/categories/bulk", response_model=List[Category], tags=["Blogs"])
async def create_multiple_categories(
    categories: List[Category],
    current_admin: User = Depends(get_current_admin_user),
    db_client: MongoClient = Depends(db.get_client),
):
    category_dicts = [category.dict(by_alias=True, exclude={"id"}) for category in categories]
    inserted_categories = db_client[db.db_name]["categories"].insert_many(category_dicts)

    for i, category in enumerate(categories):
        category.id = str(inserted_categories.inserted_ids[i])

    return categories


@blog_router.get("/blogs/category/{category_name}", response_model=List[BlogPost], tags=["Blogs"])
async def get_blogs_by_category(category_name: str, db_client: MongoClient = Depends(db.get_client)):
    # blogs = list(db_client[db.db_name]["blogs"].find({"categories": category_name}))
    blogs = list(db_client[db.db_name]["blogs"].find({"categories": category_name}).sort("created_at", DESCENDING))

    if not blogs:
        raise HTTPException(status_code=404, detail="No blogs found for this category")

    for blog in blogs:
        blog["_id"] = str(blog["_id"])
        blog["comments"] = list(db_client[db.db_name]["comments"].find({"blog_id": blog["_id"]}))

        for comment in blog["comments"]:
            comment["_id"] = str(comment["_id"])

    return blogs

@blog_router.get("/blogs/{blog_id}/meta", response_class=HTMLResponse, tags=["Blogs"])
async def get_blog_meta(blog_id: str, db_client: MongoClient = Depends(db.get_client)):
    blog = db_client[db.db_name]["blogs"].find_one({"_id": ObjectId(blog_id)})
    if not blog:
        raise HTTPException(status_code=404, detail="Blog not found")

    title = blog["title"]
    description = blog["content"][:150] + "..."  # Short excerpt
    image_url = blog["image_url"]

    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <meta property="og:title" content="{title}" />
        <meta property="og:description" content="{description}" />
        <meta property="og:image" content="{image_url}" />
        <meta property="og:type" content="article" />
        <title>{title}</title>
    </head>
    <body>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)
