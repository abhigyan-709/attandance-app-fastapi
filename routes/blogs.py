from fastapi import APIRouter, Depends, HTTPException
from pymongo import MongoClient
from models.blogs import BlogPost, Comment, Category
from models.user import User
from database.db import db
from typing import List
from bson import ObjectId
from datetime import datetime
from routes.user import get_current_user

blog_router = APIRouter()

def get_current_admin_user(current_user: User = Depends(get_current_user)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized to perform this action")
    return current_user

@blog_router.post("/blogs", response_model=BlogPost, tags=["Blogs"])
async def create_blog(
    blog: BlogPost,
    current_admin: User = Depends(get_current_admin_user),
    db_client: MongoClient = Depends(db.get_client),
):
    blog.author_id = str(current_admin.username)
    blog.created_at = datetime.utcnow()
    blog.updated_at = datetime.utcnow()
    blog_dict = blog.dict(by_alias=True, exclude={"id"})
    inserted_blog = db_client[db.db_name]["blogs"].insert_one(blog_dict)
    blog.id = str(inserted_blog.inserted_id)
    return blog

@blog_router.get("/blogs", response_model=List[BlogPost], tags=["Blogs"])
async def get_blogs(db_client: MongoClient = Depends(db.get_client)):
    blogs = list(db_client[db.db_name]["blogs"].find())
    for blog in blogs:
        blog["id"] = str(blog("_id"))
    return blogs

@blog_router.get("/blogs/{blog_id}", response_model=BlogPost, tags=["Blogs"])
async def get_blog(blog_id: str, db_client: MongoClient = Depends(db.get_client)):
    blog = db_client[db.db_name]["blogs"].find_one({"_id": ObjectId(blog_id)})
    if not blog:
        raise HTTPException(status_code=404, detail="Blog not found")
    blog["id"] = str(blog.pop("_id"))
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
        {"$set": updated_blog.dict(by_alias=True, exclude={"id", "author_id", "created_at"})}
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
    comment.post_id = blog_id
    comment.user_id = str(current_user.username)
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
