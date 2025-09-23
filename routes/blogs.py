# # added ---RBAC

# from fastapi import APIRouter, Depends, HTTPException, File, UploadFile, Form, Request, BackgroundTasks
# from fastapi.responses import HTMLResponse
# from pymongo import MongoClient, DESCENDING
# from models.blogs import BlogPost, Comment, Category
# from models.user import User
# from database.db import db
# from typing import List, Optional
# from bson import ObjectId
# from datetime import datetime
# import uuid
# import boto3
# from routes.user import get_current_user
# from routes.config import AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_REGION
# import logging
# from bs4 import BeautifulSoup

# # --- new imports for web-push notify helper ---
# import os
# import re
# import requests

# logging.basicConfig(level=logging.INFO)
# logger = logging.getLogger(__name__)

# blog_router = APIRouter()

# AWS_BUCKET_NAME = "projectdevops-blogs-new"

# s3_client = boto3.client(
#     "s3",
#     aws_access_key_id=AWS_ACCESS_KEY_ID,
#     aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
#     region_name=AWS_REGION,
# )

# # --- web-push notify plumbing (uses your /push/notify-new-blog) ---
# PUBLIC_API_BASE = os.getenv("PUBLIC_API_BASE", "http://localhost:8000")  # container-local default
# ADMIN_API_TOKEN = os.getenv("ADMIN_API_TOKEN")  # you already put this in app.env
# BLOG_BASE_URL = os.getenv("BLOG_BASE_URL", "https://blogs.projectdevops.in")


# def _slugify(s: str) -> str:
#     return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


# def _notify_new_blog_async(title: str, url: str, image: Optional[str] = None):
#     """Fire-and-forget POST to /push/notify-new-blog (runs in BackgroundTasks)."""
#     try:
#         payload = {
#             "title": title,
#             "body": "New post just landed! Tap to read.",
#             "url": url,
#             "image": image,
#             "tag": "new-blog",
#         }
#         headers = {"Content-Type": "application/json"}
#         if ADMIN_API_TOKEN:
#             headers["x-admin-token"] = ADMIN_API_TOKEN
#         requests.post(
#             f"{PUBLIC_API_BASE}/push/notify-new-blog",
#             json=payload,
#             headers=headers,
#             timeout=5,
#         )
#     except Exception as e:
#         logger.warning(f"notify_new_blog failed: {e}")


# # New dependency for admin or author
# def get_current_author_or_admin_user(current_user: User = Depends(get_current_user)):
#     if current_user.role not in ["admin", "author"]:
#         raise HTTPException(
#             status_code=403,
#             detail="Not authorized to perform this action. Requires admin or author role.",
#         )
#     return current_user


# # Keep this for admin-only actions if needed
# def get_current_admin_user(current_user: User = Depends(get_current_user)):
#     if current_user.role != "admin":
#         raise HTTPException(status_code=403, detail="Not authorized to perform this action")
#     return current_user


# @blog_router.post("/blogs", response_model=BlogPost, tags=["Blogs"])
# async def create_blog(
#     title: str = Form(...),
#     content: str = Form(...),
#     categories: str = Form([]),
#     tags: List[str] = Form([]),
#     published: bool = Form(True),
#     file: UploadFile = File(...),
#     background_tasks: BackgroundTasks = None,  # IMPORTANT: no Depends(), FastAPI injects it
#     current_user: User = Depends(get_current_author_or_admin_user),
#     db_client: MongoClient = Depends(db.get_client),
# ):
#     file_extension = file.filename.split(".")[-1]
#     unique_filename = f"blogs/{uuid.uuid4()}.{file_extension}"

#     try:
#         s3_client.upload_fileobj(
#             file.file,
#             AWS_BUCKET_NAME,
#             unique_filename,
#             ExtraArgs={"ContentType": file.content_type},
#         )
#         image_url = f"https://{AWS_BUCKET_NAME}.s3.{AWS_REGION}.amazonaws.com/{unique_filename}"
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Image upload failed: {str(e)}")

#     blog_data = {
#         "title": title,
#         "image_url": image_url,
#         "content": content,
#         "author_username": current_user.username,
#         "categories": categories,
#         "tags": tags,
#         "published": published,
#         "created_at": datetime.utcnow(),
#         "updated_at": datetime.utcnow(),
#         "views": 0,
#         "viewed_ips": [],
#         "likes": 0,
#         "liked_ips": [],
#     }

#     inserted_blog = db_client[db.db_name]["blogs"].insert_one(blog_data)
#     blog_id = str(inserted_blog.inserted_id)
#     blog_data["_id"] = blog_id

#     # 🔔 Notify subscribers (fire-and-forget) only if published
#     if published and background_tasks is not None:
#         slug = _slugify(title)
#         canonical_url = f"{BLOG_BASE_URL}/b/{blog_id}-{slug}"
#         background_tasks.add_task(_notify_new_blog_async, title, canonical_url, image_url)

#     return blog_data


# @blog_router.get("/blogs/tags/{tag}", response_model=List[BlogPost], tags=["Blogs"])
# async def get_blogs_by_tag(tag: str, db_client: MongoClient = Depends(db.get_client)):
#     blogs = list(db_client[db.db_name]["blogs"].find({"tags": tag}))

#     for blog in blogs:
#         blog["_id"] = str(blog["_id"])
#         blog["comments"] = list(db_client[db.db_name]["comments"].find({"blog_id": blog["_id"]}))
#         for comment in blog["comments"]:
#             comment["_id"] = str(comment["_id"])

#     return blogs


# @blog_router.get("/blogs/filter", response_model=List[BlogPost], tags=["Blogs"])
# async def get_blogs_by_category_and_tags(
#     category: Optional[str] = None,
#     tag: Optional[str] = None,
#     db_client: MongoClient = Depends(db.get_client),
# ):
#     query = {}
#     if category:
#         query["categories"] = category
#     if tag:
#         query["tags"] = tag

#     blogs = list(db_client[db.db_name]["blogs"].find(query))

#     for blog in blogs:
#         blog["_id"] = str(blog["_id"])
#         blog["comments"] = list(db_client[db.db_name]["comments"].find({"blog_id": blog["_id"]}))
#         for comment in blog["comments"]:
#             comment["_id"] = str(comment["_id"])

#     return blogs


# @blog_router.get("/blogs/tags", response_model=List[str], tags=["Blogs"])
# async def get_all_tags(db_client: MongoClient = Depends(db.get_client)):
#     tags_cursor = db_client[db.db_name]["blogs"].aggregate(
#         [{"$unwind": "$tags"}, {"$group": {"_id": "$tags"}}]
#     )

#     tags = [tag["_id"] for tag in tags_cursor]
#     return tags


# @blog_router.get("/blogs", response_model=List[BlogPost], tags=["Blogs"])
# async def get_blogs(db_client: MongoClient = Depends(db.get_client)):
#     blogs = list(db_client[db.db_name]["blogs"].find().sort("created_at", DESCENDING))

#     for blog in blogs:
#         blog["_id"] = str(blog["_id"])
#         blog["comments"] = list(db_client[db.db_name]["comments"].find({"blog_id": blog["_id"]}))
#         for comment in blog["comments"]:
#             comment["_id"] = str(comment["_id"])

#     return blogs


# @blog_router.get("/blogs/{blog_id}", response_model=BlogPost, tags=["Blogs"])
# async def get_blog(blog_id: str, db_client: MongoClient = Depends(db.get_client)):
#     blog = db_client[db.db_name]["blogs"].find_one({"_id": ObjectId(blog_id)})
#     if not blog:
#         raise HTTPException(status_code=404, detail="Blog not found")

#     blog["_id"] = str(blog["_id"])
#     blog["comments"] = list(db_client[db.db_name]["comments"].find({"blog_id": blog["_id"]}))
#     for comment in blog["comments"]:
#         comment["_id"] = str(comment["_id"])

#     blog["views"] = blog.get("views", 0)
#     blog["viewed_ips"] = blog.get("viewed_ips", [])
#     blog["likes"] = blog.get("likes", 0)
#     blog["liked_ips"] = blog.get("liked_ips", [])

#     return blog


# @blog_router.post("/blogs/{blog_id}/views", response_model=dict, tags=["Blogs"])
# async def increment_blog_views(
#     blog_id: str,
#     request: Request,
#     db_client: MongoClient = Depends(db.get_client),
# ):
#     blog = db_client[db.db_name]["blogs"].find_one({"_id": ObjectId(blog_id)})
#     if not blog:
#         raise HTTPException(status_code=404, detail="Blog not found")

#     client_ip = request.headers.get("X-Forwarded-For", request.client.host)
#     if client_ip and "," in client_ip:
#         client_ip = client_ip.split(",")[0].strip()
#     if not client_ip:
#         logger.warning("No valid client IP detected for views")
#         client_ip = "unknown"

#     viewed_ips = blog.get("viewed_ips", [])
#     current_views = blog.get("views", 0)

#     logger.info(f"Client IP: {client_ip}, Viewed IPs: {viewed_ips}, Current Views: {current_views}")

#     if client_ip not in viewed_ips:
#         viewed_ips.append(client_ip)
#         current_views += 1
#         db_client[db.db_name]["blogs"].update_one(
#             {"_id": ObjectId(blog_id)},
#             {"$set": {"viewed_ips": viewed_ips, "views": current_views}},
#         )
#         logger.info(f"Updated - New Views: {current_views}, Added IP: {client_ip}")

#     return {"views": current_views}


# @blog_router.post("/blogs/{blog_id}/likes", response_model=dict, tags=["Blogs"])
# async def increment_blog_likes(
#     blog_id: str,
#     request: Request,
#     db_client: MongoClient = Depends(db.get_client),
# ):
#     blog = db_client[db.db_name]["blogs"].find_one({"_id": ObjectId(blog_id)})
#     if not blog:
#         raise HTTPException(status_code=404, detail="Blog not found")

#     client_ip = request.headers.get("X-Forwarded-For", request.client.host)
#     if client_ip and "," in client_ip:
#         client_ip = client_ip.split(",")[0].strip()
#     if not client_ip:
#         logger.warning("No valid client IP detected for likes")
#         client_ip = "unknown"

#     liked_ips = blog.get("liked_ips", [])
#     current_likes = blog.get("likes", 0)

#     logger.info(f"Client IP: {client_ip}, Liked IPs: {liked_ips}, Current Likes: {current_likes}")

#     if client_ip not in liked_ips:
#         liked_ips.append(client_ip)
#         current_likes += 1
#         db_client[db.db_name]["blogs"].update_one(
#             {"_id": ObjectId(blog_id)},
#             {"$set": {"liked_ips": liked_ips, "likes": current_likes}},
#         )
#         logger.info(f"Updated - New Likes: {current_likes}, Added IP: {client_ip}")

#     return {"likes": current_likes}


# @blog_router.put("/blogs/{blog_id}", response_model=BlogPost, tags=["Blogs"])
# async def update_blog(
#     blog_id: str,
#     updated_blog: BlogPost,
#     current_user: User = Depends(get_current_author_or_admin_user),
#     db_client: MongoClient = Depends(db.get_client),
# ):
#     existing_blog = db_client[db.db_name]["blogs"].find_one({"_id": ObjectId(blog_id)})
#     if not existing_blog:
#         raise HTTPException(status_code=404, detail="Blog not found")

#     updated_blog.updated_at = datetime.utcnow()
#     db_client[db.db_name]["blogs"].update_one(
#         {"_id": ObjectId(blog_id)},
#         {
#             "$set": updated_blog.dict(
#                 by_alias=True,
#                 exclude={
#                     "id",
#                     "author_username",
#                     "created_at",
#                     "views",
#                     "viewed_ips",
#                     "likes",
#                     "liked_ips",
#                 },
#             )
#         },
#     )
#     updated_blog.id = blog_id
#     return updated_blog


# # @blog_router.put("/blogs/{blog_id}", response_model=BlogPost, tags=["Blogs"])
# # async def update_blog(
# #     blog_id: str,
# #     updated_blog: BlogPostUpdate,  # Use the new model here
# #     current_user: User = Depends(get_current_author_or_admin_user),
# #     db_client: MongoClient = Depends(db.get_client),
# # ):
# #     # Check if blog exists
# #     existing_blog = db_client[db.db_name]["blogs"].find_one({"_id": ObjectId(blog_id)})
# #     if not existing_blog:
# #         raise HTTPException(status_code=404, detail="Blog not found")
# #
# #     # Set updated_at timestamp
# #     update_data = updated_blog.dict(exclude_unset=True)  # Only include fields that were provided
# #     update_data["updated_at"] = datetime.utcnow()
# #
# #     # Update the blog in the database
# #     db_client[db.db_name]["blogs"].update_one(
# #         {"_id": ObjectId(blog_id)},
# #         {"$set": update_data}
# #     )
# #
# #     # Fetch the updated blog to return
# #     updated_blog_full = db_client[db.db_name]["blogs"].find_one({"_id": ObjectId(blog_id)})
# #     return BlogPost(**updated_blog_full)


# @blog_router.delete("/blogs/{blog_id}", tags=["Blogs"])
# async def delete_blog(
#     blog_id: str,
#     current_user: User = Depends(get_current_author_or_admin_user),
#     db_client: MongoClient = Depends(db.get_client),
# ):
#     existing_blog = db_client[db.db_name]["blogs"].find_one({"_id": ObjectId(blog_id)})
#     if not existing_blog:
#         raise HTTPException(status_code=404, detail="Blog not found")

#     db_client[db.db_name]["blogs"].delete_one({"_id": ObjectId(blog_id)})
#     return {"message": "Blog deleted successfully"}


# @blog_router.post("/blogs/{blog_id}/comments", response_model=Comment, tags=["Blogs"])
# async def add_comment(
#     blog_id: str,
#     comment: Comment,
#     db_client: MongoClient = Depends(db.get_client),
# ):
#     blog = db_client[db.db_name]["blogs"].find_one({"_id": ObjectId(blog_id)})
#     if not blog:
#         raise HTTPException(status_code=404, detail="Blog not found")

#     comment.blog_id = blog_id
#     comment.created_at = datetime.utcnow()

#     comment_dict = comment.dict(by_alias=True, exclude={"id"})
#     inserted_comment = db_client[db.db_name]["comments"].insert_one(comment_dict)
#     comment.id = str(inserted_comment.inserted_id)

#     return comment
#     # return comment


# @blog_router.post("/categories", response_model=Category, tags=["Blogs"])
# async def create_category(
#     category: Category,
#     current_admin: User = Depends(get_current_admin_user),
#     db_client: MongoClient = Depends(db.get_client),
# ):
#     category_dict = category.dict(by_alias=True, exclude={"id"})
#     inserted_category = db_client[db.db_name]["categories"].insert_one(category_dict)
#     category.id = str(inserted_category.inserted_id)
#     return category


# @blog_router.get("/categories", response_model=List[Category], tags=["Blogs"])
# async def get_categories(
#     db_client: MongoClient = Depends(db.get_client),
# ):
#     categories = list(db_client[db.db_name]["categories"].find({}))
#     for category in categories:
#         category["_id"] = str(category["_id"])
#     return categories


# @blog_router.post("/categories/bulk", response_model=List[Category], tags=["Blogs"])
# async def create_multiple_categories(
#     categories: List[Category],
#     current_admin: User = Depends(get_current_admin_user),
#     db_client: MongoClient = Depends(db.get_client),
# ):
#     category_dicts = [category.dict(by_alias=True, exclude={"id"}) for category in categories]
#     inserted_categories = db_client[db.db_name]["categories"].insert_many(category_dicts)

#     for i, category in enumerate(categories):
#         category.id = str(inserted_categories.inserted_ids[i])

#     return categories


# @blog_router.get("/blogs/category/{category_name}", response_model=List[BlogPost], tags=["Blogs"])
# async def get_blogs_by_category(
#     category_name: str, db_client: MongoClient = Depends(db.get_client)
# ):
#     blogs = list(
#         db_client[db.db_name]["blogs"]
#         .find({"categories": category_name})
#         .sort("created_at", DESCENDING)
#     )

#     if not blogs:
#         raise HTTPException(status_code=404, detail="No blogs found for this category")

#     for blog in blogs:
#         blog["_id"] = str(blog["_id"])
#         blog["comments"] = list(db_client[db.db_name]["comments"].find({"blog_id": blog["_id"]}))
#         for comment in blog["comments"]:
#             comment["_id"] = str(comment["_id"])

#     return blogs


# @blog_router.get("/blogs/{blog_id}/meta", response_class=HTMLResponse, tags=["Blogs"])
# async def get_blog_meta(blog_id: str, db_client: MongoClient = Depends(db.get_client)):
#     blog = db_client[db.db_name]["blogs"].find_one({"_id": ObjectId(blog_id)})
#     if not blog:
#         raise HTTPException(status_code=404, detail="Blog not found")

#     title = blog["title"]
#     description = BeautifulSoup(blog["content"], "html.parser").get_text()[:150] + "..."
#     image_url = blog["image_url"]
#     if not image_url.startswith("http"):
#         image_url = f"https://{AWS_BUCKET_NAME}.s3.{AWS_REGION}.amazonaws.com/{image_url}"
#     blog_url = f"https://www.projectdevops.in/blog/{blog_id}/{title.replace(' ', '-').lower()}"

#     html_content = f"""
#     <!DOCTYPE html>
#     <html lang="en">
#     <head>
#         <meta charset="UTF-8">
#         <meta name="viewport" content="width=device-width, initial-scale=1.0">
#         <meta property="og:title" content="{title}" />
#         <meta property="og:description" content="{description}" />
#         <meta property="og:image" content="{image_url}" />
#         <meta property="og:url" content="{blog_url}" />
#         <meta property="og:type" content="article" />
#         <meta name="twitter:card" content="summary_large_image" />
#         <title>{title}</title>
#     </head>
#     <body>
#         <p>Visit the full blog post at <a href="{blog_url}">{title}</a></p>
#     </body>
#     </html>
#     """
#     return HTMLResponse(content=html_content)

#-------------------------------------------------v1----------------------------------------------------------------#

# from fastapi import APIRouter, Depends, HTTPException, File, UploadFile, Form, Request, BackgroundTasks, Query
# from fastapi.responses import HTMLResponse
# from pymongo import MongoClient, DESCENDING
# from models.blogs import BlogPost, Comment, Category
# from models.user import User
# from database.db import db
# from typing import List, Optional
# from bson import ObjectId
# from datetime import datetime
# import uuid
# import boto3
# from routes.user import get_current_user
# from routes.config import AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_REGION
# import logging
# from bs4 import BeautifulSoup

# # --- new imports for web-push notify helper ---
# import os
# import re
# import requests

# logging.basicConfig(level=logging.INFO)
# logger = logging.getLogger(__name__)

# blog_router = APIRouter()

# AWS_BUCKET_NAME = "projectdevops-blogs-new"

# s3_client = boto3.client(
#     "s3",
#     aws_access_key_id=AWS_ACCESS_KEY_ID,
#     aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
#     region_name=AWS_REGION,
# )

# # --- web-push notify plumbing (uses your /push/notify-new-blog) ---
# PUBLIC_API_BASE = os.getenv("PUBLIC_API_BASE", "http://localhost:8000")
# ADMIN_API_TOKEN = os.getenv("ADMIN_API_TOKEN")
# BLOG_BASE_URL = os.getenv("BLOG_BASE_URL", "https://blogs.projectdevops.in")


# def _slugify(s: str) -> str:
#     return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


# def _notify_new_blog_async(title: str, url: str, image: Optional[str] = None):
#     """Fire-and-forget POST to /push/notify-new-blog (runs in BackgroundTasks)."""
#     try:
#         payload = {
#             "title": title,
#             "body": "New post just landed! Tap to read.",
#             "url": url,
#             "image": image,
#             "tag": "new-blog",
#         }
#         headers = {"Content-Type": "application/json"}
#         if ADMIN_API_TOKEN:
#             headers["x-admin-token"] = ADMIN_API_TOKEN
#         requests.post(
#             f"{PUBLIC_API_BASE}/push/notify-new-blog",
#             json=payload,
#             headers=headers,
#             timeout=5,
#         )
#     except Exception as e:
#         logger.warning(f"notify_new_blog failed: {e}")


# # New dependency for admin or author
# def get_current_author_or_admin_user(current_user: User = Depends(get_current_user)):
#     if current_user.role not in ["admin", "author"]:
#         raise HTTPException(
#             status_code=403,
#             detail="Not authorized to perform this action. Requires admin or author role.",
#         )
#     return current_user


# # Keep this for admin-only actions if needed
# def get_current_admin_user(current_user: User = Depends(get_current_user)):
#     if current_user.role != "admin":
#         raise HTTPException(status_code=403, detail="Not authorized to perform this action")
#     return current_user


# @blog_router.post("/blogs", response_model=BlogPost, tags=["Blogs"])
# async def create_blog(
#     title: str = Form(...),
#     content: str = Form(...),
#     categories: str = Form([]),
#     tags: List[str] = Form([]),
#     published: bool = Form(True),
#     file: UploadFile = File(...),
#     background_tasks: BackgroundTasks = None,
#     current_user: User = Depends(get_current_author_or_admin_user),
#     db_client: MongoClient = Depends(db.get_client),
# ):
#     file_extension = file.filename.split(".")[-1]
#     unique_filename = f"blogs/{uuid.uuid4()}.{file_extension}"

#     try:
#         s3_client.upload_fileobj(
#             file.file,
#             AWS_BUCKET_NAME,
#             unique_filename,
#             ExtraArgs={"ContentType": file.content_type},
#         )
#         image_url = f"https://{AWS_BUCKET_NAME}.s3.{AWS_REGION}.amazonaws.com/{unique_filename}"
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Image upload failed: {str(e)}")

#     blog_data = {
#         "title": title,
#         "image_url": image_url,
#         "content": content,
#         "author_username": current_user.username,
#         "categories": categories,
#         "tags": tags,
#         "published": published,
#         "created_at": datetime.utcnow(),
#         "updated_at": datetime.utcnow(),
#         "views": 0,
#         "viewed_ips": [],
#         "likes": 0,
#         "liked_ips": [],
#     }

#     inserted_blog = db_client[db.db_name]["blogs"].insert_one(blog_data)
#     blog_id = str(inserted_blog.inserted_id)
#     blog_data["_id"] = blog_id

#     # 🔔 Notify subscribers (fire-and-forget) only if published
#     if published and background_tasks is not None:
#         slug = _slugify(title)
#         canonical_url = f"{BLOG_BASE_URL}/b/{blog_id}-{slug}"
#         background_tasks.add_task(_notify_new_blog_async, title, canonical_url, image_url)

#     return blog_data


# @blog_router.get("/blogs/tags/{tag}", response_model=List[BlogPost], tags=["Blogs"])
# async def get_blogs_by_tag(
#     tag: str,
#     published: Optional[bool] = Query(default=None),
#     db_client: MongoClient = Depends(db.get_client)
# ):
#     query = {"tags": tag}
#     if published is not None:
#         query["published"] = published

#     blogs = list(db_client[db.db_name]["blogs"].find(query).sort("created_at", DESCENDING))

#     for blog in blogs:
#         blog["_id"] = str(blog["_id"])
#         blog["comments"] = list(db_client[db.db_name]["comments"].find({"blog_id": blog["_id"]}))
#         for comment in blog["comments"]:
#             comment["_id"] = str(comment["_id"])
#     return blogs


# @blog_router.get("/blogs/filter", response_model=List[BlogPost], tags=["Blogs"])
# async def get_blogs_by_category_and_tags(
#     category: Optional[str] = None,
#     tag: Optional[str] = None,
#     published: Optional[bool] = Query(default=None),
#     db_client: MongoClient = Depends(db.get_client),
# ):
#     query = {}
#     if category:
#         query["categories"] = category
#     if tag:
#         query["tags"] = tag
#     if published is not None:
#         query["published"] = published

#     blogs = list(db_client[db.db_name]["blogs"].find(query).sort("created_at", DESCENDING))

#     for blog in blogs:
#         blog["_id"] = str(blog["_id"])
#         blog["comments"] = list(db_client[db.db_name]["comments"].find({"blog_id": blog["_id"]}))
#         for comment in blog["comments"]:
#             comment["_id"] = str(comment["_id"])
#     return blogs


# @blog_router.get("/blogs/tags", response_model=List[str], tags=["Blogs"])
# async def get_all_tags(db_client: MongoClient = Depends(db.get_client)):
#     tags_cursor = db_client[db.db_name]["blogs"].aggregate(
#         [{"$unwind": "$tags"}, {"$group": {"_id": "$tags"}}]
#     )
#     tags = [tag["_id"] for tag in tags_cursor]
#     return tags


# @blog_router.get("/blogs", response_model=List[BlogPost], tags=["Blogs"])
# async def get_blogs(
#     published: Optional[bool] = Query(default=None),
#     db_client: MongoClient = Depends(db.get_client)
# ):
#     query = {}
#     if published is not None:
#         query["published"] = published

#     blogs = list(db_client[db.db_name]["blogs"].find(query).sort("created_at", DESCENDING))

#     for blog in blogs:
#         blog["_id"] = str(blog["_id"])
#         blog["comments"] = list(db_client[db.db_name]["comments"].find({"blog_id": blog["_id"]}))
#         for comment in blog["comments"]:
#             comment["_id"] = str(comment["_id"])

#     return blogs


# @blog_router.get("/blogs/{blog_id}", response_model=BlogPost, tags=["Blogs"])
# async def get_blog(blog_id: str, db_client: MongoClient = Depends(db.get_client)):
#     blog = db_client[db.db_name]["blogs"].find_one({"_id": ObjectId(blog_id)})
#     if not blog:
#         raise HTTPException(status_code=404, detail="Blog not found")

#     blog["_id"] = str(blog["_id"])
#     blog["comments"] = list(db_client[db.db_name]["comments"].find({"blog_id": blog["_id"]}))
#     for comment in blog["comments"]:
#         comment["_id"] = str(comment["_id"])

#     blog["views"] = blog.get("views", 0)
#     blog["viewed_ips"] = blog.get("viewed_ips", [])
#     blog["likes"] = blog.get("likes", 0)
#     blog["liked_ips"] = blog.get("liked_ips", [])

#     return blog


# @blog_router.post("/blogs/{blog_id}/views", response_model=dict, tags=["Blogs"])
# async def increment_blog_views(
#     blog_id: str,
#     request: Request,
#     db_client: MongoClient = Depends(db.get_client),
# ):
#     blog = db_client[db.db_name]["blogs"].find_one({"_id": ObjectId(blog_id)})
#     if not blog:
#         raise HTTPException(status_code=404, detail="Blog not found")

#     client_ip = request.headers.get("X-Forwarded-For", request.client.host)
#     if client_ip and "," in client_ip:
#         client_ip = client_ip.split(",")[0].strip()
#     if not client_ip:
#         logger.warning("No valid client IP detected for views")
#         client_ip = "unknown"

#     viewed_ips = blog.get("viewed_ips", [])
#     current_views = blog.get("views", 0)

#     if client_ip not in viewed_ips:
#         viewed_ips.append(client_ip)
#         current_views += 1
#         db_client[db.db_name]["blogs"].update_one(
#             {"_id": ObjectId(blog_id)},
#             {"$set": {"viewed_ips": viewed_ips, "views": current_views}},
#         )

#     return {"views": current_views}


# @blog_router.post("/blogs/{blog_id}/likes", response_model=dict, tags=["Blogs"])
# async def increment_blog_likes(
#     blog_id: str,
#     request: Request,
#     db_client: MongoClient = Depends(db.get_client),
# ):
#     blog = db_client[db.db_name]["blogs"].find_one({"_id": ObjectId(blog_id)})
#     if not blog:
#         raise HTTPException(status_code=404, detail="Blog not found")

#     client_ip = request.headers.get("X-Forwarded-For", request.client.host)
#     if client_ip and "," in client_ip:
#         client_ip = client_ip.split(",")[0].strip()
#     if not client_ip:
#         logger.warning("No valid client IP detected for likes")
#         client_ip = "unknown"

#     liked_ips = blog.get("liked_ips", [])
#     current_likes = blog.get("likes", 0)

#     if client_ip not in liked_ips:
#         liked_ips.append(client_ip)
#         current_likes += 1
#         db_client[db.db_name]["blogs"].update_one(
#             {"_id": ObjectId(blog_id)},
#             {"$set": {"liked_ips": liked_ips, "likes": current_likes}},
#         )

#     return {"likes": current_likes}


# @blog_router.put("/blogs/{blog_id}", response_model=BlogPost, tags=["Blogs"])
# async def update_blog(
#     blog_id: str,
#     updated_blog: BlogPost,
#     current_user: User = Depends(get_current_author_or_admin_user),
#     db_client: MongoClient = Depends(db.get_client),
# ):
#     existing_blog = db_client[db.db_name]["blogs"].find_one({"_id": ObjectId(blog_id)})
#     if not existing_blog:
#         raise HTTPException(status_code=404, detail="Blog not found")

#     updated_blog.updated_at = datetime.utcnow()
#     db_client[db.db_name]["blogs"].update_one(
#         {"_id": ObjectId(blog_id)},
#         {
#             "$set": updated_blog.dict(
#                 by_alias=True,
#                 exclude={
#                     "id",
#                     "author_username",
#                     "created_at",
#                     "views",
#                     "viewed_ips",
#                     "likes",
#                     "liked_ips",
#                 },
#             )
#         },
#     )
#     updated_blog.id = blog_id
#     return updated_blog


# @blog_router.delete("/blogs/{blog_id}", tags=["Blogs"])
# async def delete_blog(
#     blog_id: str,
#     current_user: User = Depends(get_current_author_or_admin_user),
#     db_client: MongoClient = Depends(db.get_client),
# ):
#     existing_blog = db_client[db.db_name]["blogs"].find_one({"_id": ObjectId(blog_id)})
#     if not existing_blog:
#         raise HTTPException(status_code=404, detail="Blog not found")

#     db_client[db.db_name]["blogs"].delete_one({"_id": ObjectId(blog_id)})
#     return {"message": "Blog deleted successfully"}


# @blog_router.post("/blogs/{blog_id}/comments", response_model=Comment, tags=["Blogs"])
# async def add_comment(
#     blog_id: str,
#     comment: Comment,
#     db_client: MongoClient = Depends(db.get_client),
# ):
#     blog = db_client[db.db_name]["blogs"].find_one({"_id": ObjectId(blog_id)})
#     if not blog:
#         raise HTTPException(status_code=404, detail="Blog not found")

#     comment.blog_id = blog_id
#     comment.created_at = datetime.utcnow()

#     comment_dict = comment.dict(by_alias=True, exclude={"id"})
#     inserted_comment = db_client[db.db_name]["comments"].insert_one(comment_dict)
#     comment.id = str(inserted_comment.inserted_id)

#     return comment


# @blog_router.post("/categories", response_model=Category, tags=["Blogs"])
# async def create_category(
#     category: Category,
#     current_admin: User = Depends(get_current_admin_user),
#     db_client: MongoClient = Depends(db.get_client),
# ):
#     category_dict = category.dict(by_alias=True, exclude={"id"})
#     inserted_category = db_client[db.db_name]["categories"].insert_one(category_dict)
#     category.id = str(inserted_category.inserted_id)
#     return category


# @blog_router.get("/categories", response_model=List[Category], tags=["Blogs"])
# async def get_categories(
#     db_client: MongoClient = Depends(db.get_client),
# ):
#     categories = list(db_client[db.db_name]["categories"].find({}))
#     for category in categories:
#         category["_id"] = str(category["_id"])
#     return categories


# @blog_router.post("/categories/bulk", response_model=List[Category], tags=["Blogs"])
# async def create_multiple_categories(
#     categories: List[Category],
#     current_admin: User = Depends(get_current_admin_user),
#     db_client: MongoClient = Depends(db.get_client),
# ):
#     category_dicts = [category.dict(by_alias=True, exclude={"id"}) for category in categories]
#     inserted_categories = db_client[db.db_name]["categories"].insert_many(category_dicts)

#     for i, category in enumerate(categories):
#         category.id = str(inserted_categories.inserted_ids[i])

#     return categories


# @blog_router.get("/blogs/category/{category_name}", response_model=List[BlogPost], tags=["Blogs"])
# async def get_blogs_by_category(
#     category_name: str,
#     published: Optional[bool] = Query(default=None),
#     db_client: MongoClient = Depends(db.get_client)
# ):
#     query = {"categories": category_name}
#     if published is not None:
#         query["published"] = published

#     blogs = list(
#         db_client[db.db_name]["blogs"]
#         .find(query)
#         .sort("created_at", DESCENDING)
#     )

#     if not blogs:
#         raise HTTPException(status_code=404, detail="No blogs found for this category")

#     for blog in blogs:
#         blog["_id"] = str(blog["_id"])
#         blog["comments"] = list(db_client[db.db_name]["comments"].find({"blog_id": blog["_id"]}))
#         for comment in blog["comments"]:
#             comment["_id"] = str(comment["_id"])

#     return blogs


# @blog_router.get("/blogs/{blog_id}/meta", response_class=HTMLResponse, tags=["Blogs"])
# async def get_blog_meta(blog_id: str, db_client: MongoClient = Depends(db.get_client)):
#     blog = db_client[db.db_name]["blogs"].find_one({"_id": ObjectId(blog_id)})
#     if not blog:
#         raise HTTPException(status_code=404, detail="Blog not found")

#     title = blog["title"]
#     description = BeautifulSoup(blog["content"], "html.parser").get_text()[:150] + "..."
#     image_url = blog["image_url"]
#     if not image_url.startswith("http"):
#         image_url = f"https://{AWS_BUCKET_NAME}.s3.{AWS_REGION}.amazonaws.com/{image_url}"
#     blog_url = f"https://www.projectdevops.in/blog/{blog_id}/{title.replace(' ', '-').lower()}"

#     html_content = f"""
#     <!DOCTYPE html>
#     <html lang="en">
#     <head>
#         <meta charset="UTF-8">
#         <meta name="viewport" content="width=device-width, initial-scale=1.0">
#         <meta property="og:title" content="{title}" />
#         <meta property="og:description" content="{description}" />
#         <meta property="og:image" content="{image_url}" />
#         <meta property="og:url" content="{blog_url}" />
#         <meta property="og:type" content="article" />
#         <meta name="twitter:card" content="summary_large_image" />
#         <title>{title}</title>
#     </head>
#     <body>
#         <p>Visit the full blog post at <a href="{blog_url}">{title}</a></p>
#     </body>
#     </html>
#     """
#     return HTMLResponse(content=html_content)


#-----------------------------------------------------v2----------------------------------------------------------------#

from fastapi import APIRouter, Depends, HTTPException, File, UploadFile, Form, Request, BackgroundTasks, Query
from fastapi.responses import HTMLResponse
from pymongo import MongoClient, DESCENDING
from models.blogs import BlogPost, Comment, Category
from models.user import User
from database.db import db
from typing import List, Optional
from bson import ObjectId
from datetime import datetime
import uuid
import boto3
from routes.user import get_current_user
from routes.config import AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_REGION
import logging
from bs4 import BeautifulSoup

# --- new imports for web-push notify helper ---
import os
import re
import requests

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

blog_router = APIRouter()

AWS_BUCKET_NAME = "projectdevops-blogs-new"

s3_client = boto3.client(
    "s3",
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    region_name=AWS_REGION,
)

# --- web-push notify plumbing (uses your /push/notify-new-blog) ---
PUBLIC_API_BASE = os.getenv("PUBLIC_API_BASE", "http://localhost:8000")
ADMIN_API_TOKEN = os.getenv("ADMIN_API_TOKEN")
BLOG_BASE_URL = os.getenv("BLOG_BASE_URL", "https://blogs.projectdevops.in")


def _slugify(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def _notify_new_blog_async(title: str, url: str, image: Optional[str] = None):
    """Fire-and-forget POST to /push/notify-new-blog (runs in BackgroundTasks)."""
    try:
        payload = {
            "title": title,
            "body": "New post just landed! Tap to read.",
            "url": url,
            "image": image,
            "tag": "new-blog",
        }
        headers = {"Content-Type": "application/json"}
        if ADMIN_API_TOKEN:
            headers["x-admin-token"] = ADMIN_API_TOKEN
        requests.post(
            f"{PUBLIC_API_BASE}/push/notify-new-blog",
            json=payload,
            headers=headers,
            timeout=5,
        )
    except Exception as e:
        logger.warning(f"notify_new_blog failed: {e}")


# New dependency for admin or author
def get_current_author_or_admin_user(current_user: User = Depends(get_current_user)):
    if current_user.role not in ["admin", "author"]:
        raise HTTPException(
            status_code=403,
            detail="Not authorized to perform this action. Requires admin or author role.",
        )
    return current_user


# Keep this for admin-only actions if needed
def get_current_admin_user(current_user: User = Depends(get_current_user)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized to perform this action")
    return current_user


# ---------- helper: default to published-only for anonymous/public requests ----------
def _should_force_published_only(request: Request, published_param: Optional[bool]) -> bool:
    """
    If 'published' query is NOT provided:
      - Public (no Authorization header): return True => force published=True
      - Admin/author (Authorization present): return False => return all
    If 'published' query IS provided: never force; respect the explicit filter.
    """
    if published_param is not None:
        return False
    auth = (request.headers.get("Authorization") or "").strip()
    return not bool(auth)


@blog_router.post("/blogs", response_model=BlogPost, tags=["Blogs"])
async def create_blog(
    title: str = Form(...),
    content: str = Form(...),
    categories: str = Form([]),
    tags: List[str] = Form([]),
    published: bool = Form(True),
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = None,
    current_user: User = Depends(get_current_author_or_admin_user),
    db_client: MongoClient = Depends(db.get_client),
):
    file_extension = file.filename.split(".")[-1]
    unique_filename = f"blogs/{uuid.uuid4()}.{file_extension}"

    try:
        s3_client.upload_fileobj(
            file.file,
            AWS_BUCKET_NAME,
            unique_filename,
            ExtraArgs={"ContentType": file.content_type},
        )
        image_url = f"https://{AWS_BUCKET_NAME}.s3.{AWS_REGION}.amazonaws.com/{unique_filename}"
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Image upload failed: {str(e)}")

    blog_data = {
        "title": title,
        "image_url": image_url,
        "content": content,
        "author_username": current_user.username,
        "categories": categories,
        "tags": tags,
        "published": published,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
        "views": 0,
        "viewed_ips": [],
        "likes": 0,
        "liked_ips": [],
    }

    inserted_blog = db_client[db.db_name]["blogs"].insert_one(blog_data)
    blog_id = str(inserted_blog.inserted_id)
    blog_data["_id"] = blog_id

    # 🔔 Notify subscribers (fire-and-forget) only if published
    if published and background_tasks is not None:
        slug = _slugify(title)
        canonical_url = f"{BLOG_BASE_URL}/b/{blog_id}-{slug}"
        background_tasks.add_task(_notify_new_blog_async, title, canonical_url, image_url)

    return blog_data


@blog_router.get("/blogs/tags/{tag}", response_model=List[BlogPost], tags=["Blogs"])
async def get_blogs_by_tag(
    request: Request,
    tag: str,
    published: Optional[bool] = Query(default=None),
    db_client: MongoClient = Depends(db.get_client)
):
    query = {"tags": tag}
    if _should_force_published_only(request, published):
        query["published"] = True
    elif published is not None:
        query["published"] = published

    blogs = list(db_client[db.db_name]["blogs"].find(query).sort("created_at", DESCENDING))

    for blog in blogs:
        blog["_id"] = str(blog["_id"])
        blog["comments"] = list(db_client[db.db_name]["comments"].find({"blog_id": blog["_id"]}))
        for comment in blog["comments"]:
            comment["_id"] = str(comment["_id"])
    return blogs


@blog_router.get("/blogs/filter", response_model=List[BlogPost], tags=["Blogs"])
async def get_blogs_by_category_and_tags(
    request: Request,
    category: Optional[str] = None,
    tag: Optional[str] = None,
    published: Optional[bool] = Query(default=None),
    db_client: MongoClient = Depends(db.get_client),
):
    query = {}
    if category:
        query["categories"] = category
    if tag:
        query["tags"] = tag

    if _should_force_published_only(request, published):
        query["published"] = True
    elif published is not None:
        query["published"] = published

    blogs = list(db_client[db.db_name]["blogs"].find(query).sort("created_at", DESCENDING))

    for blog in blogs:
        blog["_id"] = str(blog["_id"])
        blog["comments"] = list(db_client[db.db_name]["comments"].find({"blog_id": blog["_id"]}))
        for comment in blog["comments"]:
            comment["_id"] = str(comment["_id"])
    return blogs


@blog_router.get("/blogs/tags", response_model=List[str], tags=["Blogs"])
async def get_all_tags(db_client: MongoClient = Depends(db.get_client)):
    tags_cursor = db_client[db.db_name]["blogs"].aggregate(
        [{"$unwind": "$tags"}, {"$group": {"_id": "$tags"}}]
    )
    tags = [tag["_id"] for tag in tags_cursor]
    return tags


@blog_router.get("/blogs", response_model=List[BlogPost], tags=["Blogs"])
async def get_blogs(
    request: Request,
    published: Optional[bool] = Query(default=None),
    db_client: MongoClient = Depends(db.get_client)
):
    query = {}
    if _should_force_published_only(request, published):
        query["published"] = True
    elif published is not None:
        query["published"] = published

    blogs = list(db_client[db.db_name]["blogs"].find(query).sort("created_at", DESCENDING))

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

    blog["views"] = blog.get("views", 0)
    blog["viewed_ips"] = blog.get("viewed_ips", [])
    blog["likes"] = blog.get("likes", 0)
    blog["liked_ips"] = blog.get("liked_ips", [])

    return blog


@blog_router.post("/blogs/{blog_id}/views", response_model=dict, tags=["Blogs"])
async def increment_blog_views(
    blog_id: str,
    request: Request,
    db_client: MongoClient = Depends(db.get_client),
):
    blog = db_client[db.db_name]["blogs"].find_one({"_id": ObjectId(blog_id)})
    if not blog:
        raise HTTPException(status_code=404, detail="Blog not found")

    client_ip = request.headers.get("X-Forwarded-For", request.client.host)
    if client_ip and "," in client_ip:
        client_ip = client_ip.split(",")[0].strip()
    if not client_ip:
        logger.warning("No valid client IP detected for views")
        client_ip = "unknown"

    viewed_ips = blog.get("viewed_ips", [])
    current_views = blog.get("views", 0)

    if client_ip not in viewed_ips:
        viewed_ips.append(client_ip)
        current_views += 1
        db_client[db.db_name]["blogs"].update_one(
            {"_id": ObjectId(blog_id)},
            {"$set": {"viewed_ips": viewed_ips, "views": current_views}},
        )

    return {"views": current_views}


@blog_router.post("/blogs/{blog_id}/likes", response_model=dict, tags=["Blogs"])
async def increment_blog_likes(
    blog_id: str,
    request: Request,
    db_client: MongoClient = Depends(db.get_client),
):
    blog = db_client[db.db_name]["blogs"].find_one({"_id": ObjectId(blog_id)})
    if not blog:
        raise HTTPException(status_code=404, detail="Blog not found")

    client_ip = request.headers.get("X-Forwarded-For", request.client.host)
    if client_ip and "," in client_ip:
        client_ip = client_ip.split(",")[0].strip()
    if not client_ip:
        logger.warning("No valid client IP detected for likes")
        client_ip = "unknown"

    liked_ips = blog.get("liked_ips", [])
    current_likes = blog.get("likes", 0)

    if client_ip not in liked_ips:
        liked_ips.append(client_ip)
        current_likes += 1
        db_client[db.db_name]["blogs"].update_one(
            {"_id": ObjectId(blog_id)},
            {"$set": {"liked_ips": liked_ips, "likes": current_likes}},
        )

    return {"likes": current_likes}


@blog_router.put("/blogs/{blog_id}", response_model=BlogPost, tags=["Blogs"])
async def update_blog(
    blog_id: str,
    updated_blog: BlogPost,
    current_user: User = Depends(get_current_author_or_admin_user),
    db_client: MongoClient = Depends(db.get_client),
):
    existing_blog = db_client[db.db_name]["blogs"].find_one({"_id": ObjectId(blog_id)})
    if not existing_blog:
        raise HTTPException(status_code=404, detail="Blog not found")

    updated_blog.updated_at = datetime.utcnow()
    db_client[db.db_name]["blogs"].update_one(
        {"_id": ObjectId(blog_id)},
        {
            "$set": updated_blog.dict(
                by_alias=True,
                exclude={
                    "id",
                    "author_username",
                    "created_at",
                    "views",
                    "viewed_ips",
                    "likes",
                    "liked_ips",
                },
            )
        },
    )
    updated_blog.id = blog_id
    return updated_blog


@blog_router.delete("/blogs/{blog_id}", tags=["Blogs"])
async def delete_blog(
    blog_id: str,
    current_user: User = Depends(get_current_author_or_admin_user),
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
    db_client: MongoClient = Depends(db.get_client),
):
    blog = db_client[db.db_name]["blogs"].find_one({"_id": ObjectId(blog_id)})
    if not blog:
        raise HTTPException(status_code=404, detail="Blog not found")

    comment.blog_id = blog_id
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
        category["_id"] = str(category["_id"])
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
async def get_blogs_by_category(
    request: Request,
    category_name: str,
    published: Optional[bool] = Query(default=None),
    db_client: MongoClient = Depends(db.get_client)
):
    query = {"categories": category_name}
    if _should_force_published_only(request, published):
        query["published"] = True
    elif published is not None:
        query["published"] = published

    blogs = list(
        db_client[db.db_name]["blogs"]
        .find(query)
        .sort("created_at", DESCENDING)
    )

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
    description = BeautifulSoup(blog["content"], "html.parser").get_text()[:150] + "..."
    image_url = blog["image_url"]
    if not image_url.startswith("http"):
        image_url = f"https://{AWS_BUCKET_NAME}.s3.{AWS_REGION}.amazonaws.com/{image_url}"
    blog_url = f"https://www.projectdevops.in/blog/{blog_id}/{title.replace(' ', '-').lower()}"

    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <meta property="og:title" content="{title}" />
        <meta property="og:description" content="{description}" />
        <meta property="og:image" content="{image_url}" />
        <meta property="og:url" content="{blog_url}" />
        <meta property="og:type" content="article" />
        <meta name="twitter:card" content="summary_large_image" />
        <title>{title}</title>
    </head>
    <body>
        <p>Visit the full blog post at <a href="{blog_url}">{title}</a></p>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)


@blog_router.put("/categories/{category_id}", response_model=Category, tags=["Blogs"])
async def update_category(
    category_id: str,
    category: Category,
    current_admin: User = Depends(get_current_admin_user),
    db_client: MongoClient = Depends(db.get_client),
):
    existing = db_client[db.db_name]["categories"].find_one({"_id": ObjectId(category_id)})
    if not existing:
        raise HTTPException(status_code=404, detail="Category not found")

    update_doc = category.dict(by_alias=True, exclude={"id", "_id"})
    db_client[db.db_name]["categories"].update_one(
        {"_id": ObjectId(category_id)},
        {"$set": update_doc},
    )
    category.id = category_id
    return category


@blog_router.delete("/categories/{category_id}", tags=["Blogs"])
async def delete_category(
    category_id: str,
    current_admin: User = Depends(get_current_admin_user),
    db_client: MongoClient = Depends(db.get_client),
):
    existing = db_client[db.db_name]["categories"].find_one({"_id": ObjectId(category_id)})
    if not existing:
        raise HTTPException(status_code=404, detail="Category not found")

    db_client[db.db_name]["categories"].delete_one({"_id": ObjectId(category_id)})
    return {"message": "Category deleted successfully"}
