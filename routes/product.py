# # routes/marketplace.py
# from fastapi import (
#     APIRouter,
#     Depends,
#     HTTPException,
#     Query,
#     File,
#     UploadFile,
#     Form,
# )
# from typing import List, Optional, Any, Dict
# from datetime import datetime
# from bson import ObjectId
# from pymongo import ReturnDocument

# from database.db import db
# from routes.user import get_current_user
# from models.user import User
# from models.product import Product, ProductCreate, ProductUpdate
# from models.product import Vendor, VendorCreate, VendorUpdate

# # NEW: AWS S3 config
# import uuid
# import boto3
# from routes.config import (
#     AWS_ACCESS_KEY_ID,
#     AWS_SECRET_ACCESS_KEY,
#     AWS_REGION,
# )
# import mimetypes

# router = APIRouter()

# client = db.get_client()
# database = client[db.db_name]
# product_collection = database["products"]
# vendor_collection = database["vendors"]

# # ---------- S3 SETUP ----------
# AWS_BUCKET_NAME = "projectdevops-blogs-new"  # same bucket you mentioned
# s3_client = boto3.client(
#     "s3",
#     aws_access_key_id=AWS_ACCESS_KEY_ID,
#     aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
#     region_name=AWS_REGION,
# )

# ALLOWED_IMAGE_MIMES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
# MAX_IMAGE_BYTES = 10 * 1024 * 1024  # 10MB


# def s3_key_for_product(product_id: str, filename: str) -> str:
#     # store under products/{product_id}/{uuid4}-{clean-filename}
#     clean_name = filename.replace("/", "_").replace("\\", "_")
#     return f"products/{product_id}/{uuid.uuid4().hex}-{clean_name}"


# def s3_url(bucket: str, region: str, key: str) -> str:
#     # Works for most regions; if you use a special partition (Gov/China), adjust accordingly.
#     return f"https://{bucket}.s3.{region}.amazonaws.com/{key}"


# def extract_key_from_url(url: str) -> Optional[str]:
#     # Expecting format like: https://bucket.s3.region.amazonaws.com/<key>
#     try:
#         prefix = f"https://{AWS_BUCKET_NAME}.s3.{AWS_REGION}.amazonaws.com/"
#         if url.startswith(prefix):
#             return url[len(prefix) :]
#         return None
#     except Exception:
#         return None


# # -------------------- UTILITIES -------------------- #
# def oid(id_str: str) -> ObjectId:
#     try:
#         return ObjectId(id_str)
#     except Exception:
#         raise HTTPException(status_code=400, detail="Invalid ObjectId")


# def serialize_id(x: Any) -> Any:
#     if isinstance(x, ObjectId):
#         return str(x)
#     if isinstance(x, list):
#         return [serialize_id(i) for i in x]
#     if isinstance(x, dict):
#         return {k: serialize_id(v) for k, v in x.items()}
#     return x


# def serialize_product(doc: Dict[str, Any]) -> Dict[str, Any]:
#     if not doc:
#         return doc
#     doc = dict(doc)
#     doc["id"] = str(doc["_id"])
#     doc.pop("_id", None)
#     if "vendor_id" in doc:
#         doc["vendor_id"] = serialize_id(doc["vendor_id"])
#     # ensure images is a list
#     if "images" not in doc or doc["images"] is None:
#         doc["images"] = []
#     return serialize_id(doc)


# def serialize_vendor(doc: Dict[str, Any]) -> Dict[str, Any]:
#     if not doc:
#         return doc
#     doc = dict(doc)
#     doc["id"] = str(doc["_id"])
#     doc.pop("_id", None)
#     if "products" in doc:
#         doc["products"] = [str(p) for p in doc["products"]]
#     return serialize_id(doc)


# def ensure_indexes() -> None:
#     # Vendors
#     vendor_collection.create_index([("name", "text"), ("region", 1)])
#     vendor_collection.create_index("email", unique=True)
#     vendor_collection.create_index("phone", unique=True)
#     # Products
#     product_collection.create_index([("name", "text"), ("category", "text")])
#     product_collection.create_index("sku", unique=True)
#     product_collection.create_index("vendor_id")
#     product_collection.create_index("region")
#     product_collection.create_index("price")


# # Create indexes at import time (idempotent)
# ensure_indexes()

# @router.post("/products", response_model=Product, tags=["Products"])
# async def create_product(
#     name: str = Form(...),
#     description: str = Form(...),
#     price: float = Form(...),
#     region: str = Form(...),
#     sku: str = Form(...),
#     category: str = Form(...),
#     stock: int = Form(...),
#     vendor_id: str = Form(...),
#     files: List[UploadFile] = File([], description="Optional product images"),
#     user: User = Depends(get_current_user),
# ):
#     """
#     Create a new product with optional image uploads.
#     - Product details are received as form fields
#     - Images are uploaded to S3
#     - Stored in MongoDB with image URLs
#     """
#     if user.role != "admin":
#         raise HTTPException(status_code=403, detail="Admin access required.")

#     v_id = oid(vendor_id)
#     vendor = vendor_collection.find_one({"_id": v_id})
#     if not vendor:
#         raise HTTPException(status_code=404, detail="Vendor not found")

#     image_urls: List[str] = []
#     for f in files:
#         content_type = f.content_type or mimetypes.guess_type(f.filename)[0] or ""
#         if content_type.lower() not in ALLOWED_IMAGE_MIMES:
#             raise HTTPException(
#                 status_code=400,
#                 detail=f"Unsupported file type for {f.filename}: {content_type}",
#             )
#         data = await f.read()
#         if len(data) > MAX_IMAGE_BYTES:
#             raise HTTPException(status_code=400, detail=f"File too large: {f.filename}")

#         key = s3_key_for_product(str(v_id), f.filename)
#         s3_client.put_object(
#             Bucket=AWS_BUCKET_NAME,
#             Key=key,
#             Body=data,
#             ContentType=content_type,
#         )
#         image_urls.append(s3_url(AWS_BUCKET_NAME, AWS_REGION, key))

#     # Build product document
#     data = {
#         "name": name,
#         "description": description,
#         "price": price,
#         "region": region,
#         "sku": sku,
#         "category": category,
#         "stock": stock,
#         "vendor_id": v_id,
#         "images": image_urls,
#         "created_at": datetime.utcnow(),
#         "updated_at": datetime.utcnow(),
#     }

#     result = product_collection.insert_one(data)
#     product_id = result.inserted_id

#     vendor_collection.update_one({"_id": v_id}, {"$push": {"products": product_id}})

#     created = product_collection.find_one({"_id": product_id})
#     return serialize_product(created)


# @router.get("/products", response_model=List[Product], tags=["Products"])
# async def list_products():
#     docs = product_collection.find()
#     return [serialize_product(d) for d in docs]

# @router.get("/products/{product_id}", response_model=Product, tags=["Products"])
# async def get_product(product_id: str):
#     """
#     Get details of a specific product by ID
#     """
#     product = product_collection.find_one({"_id": oid(product_id)})
#     if not product:
#         raise HTTPException(status_code=404, detail="Product not found")
#     return serialize_product(product)



# @router.patch("/products/{product_id}", response_model=Product, tags=["Products"])
# async def update_product(
#     product_id: str,
#     update: ProductUpdate,
#     user: User = Depends(get_current_user),
# ):
#     # Only admins can update
#     if user.role != "admin":
#         raise HTTPException(status_code=403, detail="Admin access required.")

#     # Fetch existing product
#     existing = product_collection.find_one({"_id": oid(product_id)})
#     if not existing:
#         raise HTTPException(status_code=404, detail="Product not found")

#     # Convert update to dict, skipping None
#     update_data = {k: v for k, v in update.dict().items() if v is not None}

#     # Convert HttpUrl to str if images are present
#     if "images" in update_data:
#         update_data["images"] = [str(url) for url in update_data["images"]]

#     # Update timestamp
#     update_data["updated_at"] = datetime.utcnow()

#     # Handle vendor change
#     if "vendor_id" in update_data:
#         new_vendor_id_str = update_data["vendor_id"]
#         new_vendor_id = oid(new_vendor_id_str)

#         # Check if new vendor exists
#         if not vendor_collection.find_one({"_id": new_vendor_id}):
#             raise HTTPException(status_code=404, detail="New vendor not found")

#         old_vendor_id = existing.get("vendor_id")
#         if old_vendor_id != new_vendor_id:
#             # Remove product from old vendor
#             if old_vendor_id:
#                 vendor_collection.update_one(
#                     {"_id": old_vendor_id},
#                     {"$pull": {"products": existing["_id"]}}
#                 )
#             # Add product to new vendor
#             vendor_collection.update_one(
#                 {"_id": new_vendor_id},
#                 {"$push": {"products": existing["_id"]}}
#             )
#         # Store as ObjectId
#         update_data["vendor_id"] = new_vendor_id

#     # Update product in MongoDB
#     updated = product_collection.find_one_and_update(
#         {"_id": oid(product_id)},
#         {"$set": update_data},
#         return_document=ReturnDocument.AFTER,
#     )

#     return serialize_product(updated)

# @router.delete("/products/{product_id}", tags=["Products"])
# async def delete_product(product_id: str, user: User = Depends(get_current_user)):
#     if user.role != "admin":
#         raise HTTPException(status_code=403, detail="Admin access required.")

#     product = product_collection.find_one({"_id": oid(product_id)})
#     if not product:
#         raise HTTPException(status_code=404, detail="Product not found")

#     product_collection.delete_one({"_id": product["_id"]})

#     if product.get("vendor_id"):
#         vendor_collection.update_one(
#             {"_id": product["vendor_id"]},
#             {"$pull": {"products": product["_id"]}},
#         )

#     # (Optional) You could also delete S3 objects for this product here.
#     return {"message": "Product deleted"}


# # -------------------- PRODUCT IMAGES (S3) -------------------- #
# @router.post(
#     "/products/{product_id}/images",
#     tags=["Products"],
#     response_model=Product,
# )
# async def upload_product_images(
#     product_id: str,
#     files: List[UploadFile] = File(..., description="One or more image files"),
#     user: User = Depends(get_current_user),
# ):
#     """
#     Upload 1..N images for a product.
#     - Validates mime and size
#     - Uploads to S3 under products/{product_id}/
#     - Appends URLs to product.images
#     """
#     if user.role != "admin":
#         raise HTTPException(status_code=403, detail="Admin access required.")

#     product = product_collection.find_one({"_id": oid(product_id)})
#     if not product:
#         raise HTTPException(status_code=404, detail="Product not found")

#     uploaded_urls: List[str] = []

#     for f in files:
#         # Validate mime
#         content_type = f.content_type or mimetypes.guess_type(f.filename)[0] or ""
#         if content_type.lower() not in ALLOWED_IMAGE_MIMES:
#             raise HTTPException(
#                 status_code=400,
#                 detail=f"Unsupported content type for {f.filename}: {content_type}",
#             )
#         # Validate size (stream to bytes to check size)
#         data = await f.read()
#         if len(data) > MAX_IMAGE_BYTES:
#             raise HTTPException(
#                 status_code=400, detail=f"File too large: {f.filename} (max 10MB)"
#             )

#         key = s3_key_for_product(product_id, f.filename)

#         # Put to S3
#         s3_client.put_object(
#             Bucket=AWS_BUCKET_NAME,
#             Key=key,
#             Body=data,
#             ContentType=content_type,
#             ACL="public-read",  # public; remove if you prefer presigned only
#         )
#         uploaded_urls.append(s3_url(AWS_BUCKET_NAME, AWS_REGION, key))

#     # Ensure images field exists
#     if "images" not in product or product["images"] is None:
#         product["images"] = []

#     # Update MongoDB (append)
#     updated = product_collection.find_one_and_update(
#         {"_id": product["_id"]},
#         {"$push": {"images": {"$each": uploaded_urls}}, "$set": {"updated_at": datetime.utcnow()}},
#         return_document=ReturnDocument.AFTER,
#     )
#     return serialize_product(updated)


# @router.delete(
#     "/products/{product_id}/images",
#     tags=["Products"],
#     response_model=Product,
# )
# async def delete_product_images(
#     product_id: str,
#     urls: List[str] = Query(..., description="Full S3 URLs to remove"),
#     delete_from_s3: bool = Query(True, description="Also delete objects from S3"),
#     user: User = Depends(get_current_user),
# ):
#     """
#     Remove one or more image URLs from product.images.
#     Optionally deletes the S3 objects (default True).
#     """
#     if user.role != "admin":
#         raise HTTPException(status_code=403, detail="Admin access required.")

#     product = product_collection.find_one({"_id": oid(product_id)})
#     if not product:
#         raise HTTPException(status_code=404, detail="Product not found")

#     # Pull urls from Mongo first
#     updated = product_collection.find_one_and_update(
#         {"_id": product["_id"]},
#         {"$pull": {"images": {"$in": urls}}, "$set": {"updated_at": datetime.utcnow()}},
#         return_document=ReturnDocument.AFTER,
#     )

#     # Optionally delete from S3
#     if delete_from_s3:
#         objects_to_delete = []
#         for u in urls:
#             key = extract_key_from_url(u)
#             if key:
#                 objects_to_delete.append({"Key": key})

#         if objects_to_delete:
#             # Batch delete (max 1000 objects per call)
#             s3_client.delete_objects(
#                 Bucket=AWS_BUCKET_NAME,
#                 Delete={"Objects": objects_to_delete, "Quiet": True},
#             )

#     return serialize_product(updated)


# # -------------------- VENDOR ENDPOINTS -------------------- #
# @router.post("/vendors", response_model=Vendor, tags=["Vendors"])
# async def create_vendor(vendor: VendorCreate, user: User = Depends(get_current_user)):
#     if user.role != "admin":
#         raise HTTPException(status_code=403, detail="Admin access required.")

#     data = vendor.dict()
#     data["products"] = []
#     data["created_at"] = datetime.utcnow()
#     data["updated_at"] = datetime.utcnow()

#     result = vendor_collection.insert_one(data)
#     created = vendor_collection.find_one({"_id": result.inserted_id})
#     return serialize_vendor(created)


# @router.get("/vendors", response_model=List[Vendor], tags=["Vendors"])
# async def list_vendors():
#     docs = vendor_collection.find()
#     return [serialize_vendor(d) for d in docs]

# @router.get("/vendors/{vendor_id}", response_model=Vendor, tags=["Vendors"])
# async def get_vendor(vendor_id: str):
#     """
#     Get details of a specific vendor by ID
#     """
#     vendor = vendor_collection.find_one({"_id": oid(vendor_id)})
#     if not vendor:
#         raise HTTPException(status_code=404, detail="Vendor not found")
#     return serialize_vendor(vendor)


# @router.patch("/vendors/{vendor_id}", response_model=Vendor, tags=["Vendors"])
# async def update_vendor(
#     vendor_id: str,
#     update: VendorUpdate,
#     user: User = Depends(get_current_user),
# ):
#     if user.role != "admin":
#         raise HTTPException(status_code=403, detail="Admin access required.")

#     update_data = {k: v for k, v in update.dict().items() if v is not None}
#     update_data["updated_at"] = datetime.utcnow()

#     updated = vendor_collection.find_one_and_update(
#         {"_id": oid(vendor_id)},
#         {"$set": update_data},
#         return_document=ReturnDocument.AFTER,
#     )
#     if not updated:
#         raise HTTPException(status_code=404, detail="Vendor not found")

#     return serialize_vendor(updated)


# @router.delete("/vendors/{vendor_id}", tags=["Vendors"])
# async def delete_vendor(
#     vendor_id: str,
#     user: User = Depends(get_current_user),
#     force: bool = Query(False, description="Delete vendor even if products exist (will NOT delete products)"),
# ):
#     if user.role != "admin":
#         raise HTTPException(status_code=403, detail="Admin access required.")

#     vendor = vendor_collection.find_one({"_id": oid(vendor_id)})
#     if not vendor:
#         raise HTTPException(status_code=404, detail="Vendor not found")

#     has_products = bool(vendor.get("products"))
#     if has_products and not force:
#         raise HTTPException(
#             status_code=400,
#             detail="Vendor has products. Move or delete products first, or pass ?force=true to proceed (will orphan products).",
#         )

#     vendor_collection.delete_one({"_id": vendor["_id"]})

#     if has_products and force:
#         product_collection.update_many(
#             {"vendor_id": vendor["_id"]},
#             {"$unset": {"vendor_id": ""}},
#         )

#     return {"message": "Vendor deleted"}


# # -------------------- SEARCH (PUBLIC) -------------------- #
# @router.get("/search", tags=["Search"])
# async def search(
#     q: str = Query(..., description="Search term for products/vendors"),
#     region: Optional[str] = Query(None, description="Filter by GI region"),
#     category: Optional[str] = Query(None, description="Filter by product category"),
#     limit: int = Query(20, ge=1, le=100),
# ):
#     product_filter: Dict[str, Any] = {"$text": {"$search": q}}
#     if region:
#         product_filter["region"] = region
#     if category:
#         product_filter["category"] = category

#     product_cursor = (
#         product_collection
#         .find(product_filter, {"score": {"$meta": "textScore"}})
#         .sort([("score", {"$meta": "textScore"})])
#         .limit(limit)
#     )
#     products = [serialize_product(p) for p in product_cursor]

#     vendor_filter: Dict[str, Any] = {"$text": {"$search": q}}
#     if region:
#         vendor_filter["region"] = region

#     vendor_cursor = (
#         vendor_collection
#         .find(vendor_filter, {"score": {"$meta": "textScore"}})
#         .sort([("score", {"$meta": "textScore"})])
#         .limit(limit)
#     )
#     vendors = [serialize_vendor(v) for v in vendor_cursor]

#     return {"products": products, "vendors": vendors}


# routes/marketplace.py
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    File,
    UploadFile,
    Form,
)
from typing import List, Optional, Any, Dict
from datetime import datetime
from bson import ObjectId
from pymongo import ReturnDocument

from database.db import db
from routes.user import get_current_user
from models.user import User
from models.product import Product, ProductCreate, ProductUpdate
from models.product import Vendor, VendorCreate, VendorUpdate

# NEW: AWS S3 config
import uuid
import boto3
from routes.config import (
    AWS_ACCESS_KEY_ID,
    AWS_SECRET_ACCESS_KEY,
    AWS_REGION,
)
import mimetypes

router = APIRouter()

client = db.get_client()
database = client[db.db_name]
product_collection = database["products"]
vendor_collection = database["vendors"]

# ---------- S3 SETUP ----------
AWS_BUCKET_NAME = "projectdevops-blogs-new"  # same bucket you mentioned
s3_client = boto3.client(
    "s3",
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    region_name=AWS_REGION,
)

ALLOWED_IMAGE_MIMES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
MAX_IMAGE_BYTES = 10 * 1024 * 1024  # 10MB


def s3_key_for_product(product_id: str, filename: str) -> str:
    # store under products/{product_id}/{uuid4}-{clean-filename}
    clean_name = filename.replace("/", "_").replace("\\", "_")
    return f"products/{product_id}/{uuid.uuid4().hex}-{clean_name}"


def s3_url(bucket: str, region: str, key: str) -> str:
    # Works for most regions; if you use a special partition (Gov/China), adjust accordingly.
    return f"https://{bucket}.s3.{region}.amazonaws.com/{key}"


def extract_key_from_url(url: str) -> Optional[str]:
    # Expecting format like: https://bucket.s3.region.amazonaws.com/<key>
    try:
        prefix = f"https://{AWS_BUCKET_NAME}.s3.{AWS_REGION}.amazonaws.com/"
        if url.startswith(prefix):
            return url[len(prefix) :]
        return None
    except Exception:
        return None


# -------------------- UTILITIES -------------------- #
def oid(id_str: str) -> ObjectId:
    try:
        return ObjectId(id_str)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid ObjectId")


def serialize_id(x: Any) -> Any:
    if isinstance(x, ObjectId):
        return str(x)
    if isinstance(x, list):
        return [serialize_id(i) for i in x]
    if isinstance(x, dict):
        return {k: serialize_id(v) for k, v in x.items()}
    return x


def serialize_product(doc: Dict[str, Any]) -> Dict[str, Any]:
    if not doc:
        return doc
    doc = dict(doc)
    doc["id"] = str(doc["_id"])
    doc.pop("_id", None)
    if "vendor_id" in doc:
        doc["vendor_id"] = serialize_id(doc["vendor_id"])
    # ensure images is a list
    if "images" not in doc or doc["images"] is None:
        doc["images"] = []
    return serialize_id(doc)


def serialize_vendor(doc: Dict[str, Any]) -> Dict[str, Any]:
    if not doc:
        return doc
    doc = dict(doc)
    doc["id"] = str(doc["_id"])
    doc.pop("_id", None)
    if "products" in doc:
        doc["products"] = [str(p) for p in doc["products"]]
    return serialize_id(doc)


def ensure_indexes() -> None:
    # Vendors
    vendor_collection.create_index([("name", "text"), ("region", 1)])
    vendor_collection.create_index("email", unique=True)
    vendor_collection.create_index("phone", unique=True)
    # Products
    product_collection.create_index([("name", "text"), ("category", "text")])
    product_collection.create_index("sku", unique=True)
    product_collection.create_index("vendor_id")
    product_collection.create_index("region")
    product_collection.create_index("price")


# Create indexes at import time (idempotent)
ensure_indexes()

@router.post("/products", response_model=Product, tags=["Products"])
async def create_product(
    name: str = Form(...),
    description: str = Form(...),
    price: float = Form(...),
    region: str = Form(...),
    sku: str = Form(...),
    category: str = Form(...),
    subcategory: str = Form(...),
    stock: int = Form(...),
    vendor_id: str = Form(...),
    files: List[UploadFile] = File([], description="Optional product images"),
    user: User = Depends(get_current_user),
):
    """
    Create a new product with optional image uploads.
    - Product details are received as form fields
    - Images are uploaded to S3
    - Stored in MongoDB with image URLs
    """
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required.")

    v_id = oid(vendor_id)
    vendor = vendor_collection.find_one({"_id": v_id})
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")

    image_urls: List[str] = []
    for f in files:
        content_type = f.content_type or mimetypes.guess_type(f.filename)[0] or ""
        if content_type.lower() not in ALLOWED_IMAGE_MIMES:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file type for {f.filename}: {content_type}",
            )
        data = await f.read()
        if len(data) > MAX_IMAGE_BYTES:
            raise HTTPException(status_code=400, detail=f"File too large: {f.filename}")

        key = s3_key_for_product(str(v_id), f.filename)
        s3_client.put_object(
            Bucket=AWS_BUCKET_NAME,
            Key=key,
            Body=data,
            ContentType=content_type,
        )
        image_urls.append(s3_url(AWS_BUCKET_NAME, AWS_REGION, key))

    # Build product document
    data = {
        "name": name,
        "description": description,
        "price": price,
        "region": region,
        "sku": sku,
        "category": category,
        "subcategory": subcategory,
        "stock": stock,
        "vendor_id": v_id,
        "images": image_urls,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }

    result = product_collection.insert_one(data)
    product_id = result.inserted_id

    vendor_collection.update_one({"_id": v_id}, {"$push": {"products": product_id}})

    created = product_collection.find_one({"_id": product_id})
    return serialize_product(created)


@router.get("/products", response_model=List[Product], tags=["Products"])
async def list_products():
    docs = product_collection.find()
    return [serialize_product(d) for d in docs]

@router.get("/products/{product_id}", response_model=Product, tags=["Products"])
async def get_product(product_id: str):
    """
    Get details of a specific product by ID
    """
    product = product_collection.find_one({"_id": oid(product_id)})
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return serialize_product(product)



@router.patch("/products/{product_id}", response_model=Product, tags=["Products"])
async def update_product(
    product_id: str,
    update: ProductUpdate,
    user: User = Depends(get_current_user),
):
    # Only admins can update
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required.")

    # Fetch existing product
    existing = product_collection.find_one({"_id": oid(product_id)})
    if not existing:
        raise HTTPException(status_code=404, detail="Product not found")

    # Convert update to dict, skipping None
    update_data = {k: v for k, v in update.dict().items() if v is not None}

    # Convert HttpUrl to str if images are present
    if "images" in update_data:
        update_data["images"] = [str(url) for url in update_data["images"]]

    # Update timestamp
    update_data["updated_at"] = datetime.utcnow()

    # Handle vendor change
    if "vendor_id" in update_data:
        new_vendor_id_str = update_data["vendor_id"]
        new_vendor_id = oid(new_vendor_id_str)

        # Check if new vendor exists
        if not vendor_collection.find_one({"_id": new_vendor_id}):
            raise HTTPException(status_code=404, detail="New vendor not found")

        old_vendor_id = existing.get("vendor_id")
        if old_vendor_id != new_vendor_id:
            # Remove product from old vendor
            if old_vendor_id:
                vendor_collection.update_one(
                    {"_id": old_vendor_id},
                    {"$pull": {"products": existing["_id"]}}
                )
            # Add product to new vendor
            vendor_collection.update_one(
                {"_id": new_vendor_id},
                {"$push": {"products": existing["_id"]}}
            )
        # Store as ObjectId
        update_data["vendor_id"] = new_vendor_id

    # Update product in MongoDB
    updated = product_collection.find_one_and_update(
        {"_id": oid(product_id)},
        {"$set": update_data},
        return_document=ReturnDocument.AFTER,
    )

    return serialize_product(updated)



@router.delete("/products/{product_id}", tags=["Products"])
async def delete_product(product_id: str, user: User = Depends(get_current_user)):
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required.")

    product = product_collection.find_one({"_id": oid(product_id)})
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    product_collection.delete_one({"_id": product["_id"]})

    if product.get("vendor_id"):
        vendor_collection.update_one(
            {"_id": product["vendor_id"]},
            {"$pull": {"products": product["_id"]}},
        )

    # (Optional) You could also delete S3 objects for this product here.
    return {"message": "Product deleted"}


# -------------------- PRODUCT IMAGES (S3) -------------------- #
@router.post(
    "/products/{product_id}/images",
    tags=["Products"],
    response_model=Product,
)
async def upload_product_images(
    product_id: str,
    files: List[UploadFile] = File(..., description="One or more image files"),
    user: User = Depends(get_current_user),
):
    """
    Upload 1..N images for a product.
    - Validates mime and size
    - Uploads to S3 under products/{product_id}/
    - Appends URLs to product.images
    """
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required.")

    product = product_collection.find_one({"_id": oid(product_id)})
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    uploaded_urls: List[str] = []

    for f in files:
        # Validate mime
        content_type = f.content_type or mimetypes.guess_type(f.filename)[0] or ""
        if content_type.lower() not in ALLOWED_IMAGE_MIMES:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported content type for {f.filename}: {content_type}",
            )
        # Validate size (stream to bytes to check size)
        data = await f.read()
        if len(data) > MAX_IMAGE_BYTES:
            raise HTTPException(
                status_code=400, detail=f"File too large: {f.filename} (max 10MB)"
            )

        key = s3_key_for_product(product_id, f.filename)

        # Put to S3
        s3_client.put_object(
            Bucket=AWS_BUCKET_NAME,
            Key=key,
            Body=data,
            ContentType=content_type,
            ACL="public-read",  # public; remove if you prefer presigned only
        )
        uploaded_urls.append(s3_url(AWS_BUCKET_NAME, AWS_REGION, key))

    # Ensure images field exists
    if "images" not in product or product["images"] is None:
        product["images"] = []

    # Update MongoDB (append)
    updated = product_collection.find_one_and_update(
        {"_id": product["_id"]},
        {"$push": {"images": {"$each": uploaded_urls}}, "$set": {"updated_at": datetime.utcnow()}},
        return_document=ReturnDocument.AFTER,
    )
    return serialize_product(updated)


@router.delete(
    "/products/{product_id}/images",
    tags=["Products"],
    response_model=Product,
)
async def delete_product_images(
    product_id: str,
    urls: List[str] = Query(..., description="Full S3 URLs to remove"),
    delete_from_s3: bool = Query(True, description="Also delete objects from S3"),
    user: User = Depends(get_current_user),
):
    """
    Remove one or more image URLs from product.images.
    Optionally deletes the S3 objects (default True).
    """
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required.")

    product = product_collection.find_one({"_id": oid(product_id)})
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    # Pull urls from Mongo first
    updated = product_collection.find_one_and_update(
        {"_id": product["_id"]},
        {"$pull": {"images": {"$in": urls}}, "$set": {"updated_at": datetime.utcnow()}},
        return_document=ReturnDocument.AFTER,
    )

    # Optionally delete from S3
    if delete_from_s3:
        objects_to_delete = []
        for u in urls:
            key = extract_key_from_url(u)
            if key:
                objects_to_delete.append({"Key": key})

        if objects_to_delete:
            # Batch delete (max 1000 objects per call)
            s3_client.delete_objects(
                Bucket=AWS_BUCKET_NAME,
                Delete={"Objects": objects_to_delete, "Quiet": True},
            )

    return serialize_product(updated)


# -------------------- VENDOR ENDPOINTS -------------------- #
@router.post("/vendors", response_model=Vendor, tags=["Vendors"])
async def create_vendor(vendor: VendorCreate, user: User = Depends(get_current_user)):
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required.")

    data = vendor.dict()
    data["products"] = []
    data["created_at"] = datetime.utcnow()
    data["updated_at"] = datetime.utcnow()

    result = vendor_collection.insert_one(data)
    created = vendor_collection.find_one({"_id": result.inserted_id})
    return serialize_vendor(created)


@router.get("/vendors", response_model=List[Vendor], tags=["Vendors"])
async def list_vendors():
    docs = vendor_collection.find()
    return [serialize_vendor(d) for d in docs]

@router.get("/vendors/{vendor_id}", response_model=Vendor, tags=["Vendors"])
async def get_vendor(vendor_id: str):
    """
    Get details of a specific vendor by ID
    """
    vendor = vendor_collection.find_one({"_id": oid(vendor_id)})
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")
    return serialize_vendor(vendor)


@router.patch("/vendors/{vendor_id}", response_model=Vendor, tags=["Vendors"])
async def update_vendor(
    vendor_id: str,
    update: VendorUpdate,
    user: User = Depends(get_current_user),
):
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required.")

    update_data = {k: v for k, v in update.dict().items() if v is not None}
    update_data["updated_at"] = datetime.utcnow()

    updated = vendor_collection.find_one_and_update(
        {"_id": oid(vendor_id)},
        {"$set": update_data},
        return_document=ReturnDocument.AFTER,
    )
    if not updated:
        raise HTTPException(status_code=404, detail="Vendor not found")

    return serialize_vendor(updated)


@router.delete("/vendors/{vendor_id}", tags=["Vendors"])
async def delete_vendor(
    vendor_id: str,
    user: User = Depends(get_current_user),
    force: bool = Query(False, description="Delete vendor even if products exist (will NOT delete products)"),
):
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required.")

    vendor = vendor_collection.find_one({"_id": oid(vendor_id)})
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")

    has_products = bool(vendor.get("products"))
    if has_products and not force:
        raise HTTPException(
            status_code=400,
            detail="Vendor has products. Move or delete products first, or pass ?force=true to proceed (will orphan products).",
        )

    vendor_collection.delete_one({"_id": vendor["_id"]})

    if has_products and force:
        product_collection.update_many(
            {"vendor_id": vendor["_id"]},
            {"$unset": {"vendor_id": ""}},
        )

    return {"message": "Vendor deleted"}


# -------------------- SEARCH (PUBLIC) -------------------- #
# @router.get("/search", tags=["Search"])
# async def search(
#     q: str = Query(..., description="Search term for products/vendors"),
#     region: Optional[str] = Query(None, description="Filter by GI region"),
#     category: Optional[str] = Query(None, description="Filter by product category"),
#     limit: int = Query(20, ge=1, le=100),
# ):
#     product_filter: Dict[str, Any] = {"$text": {"$search": q}}
#     if region:
#         product_filter["region"] = region
#     if category:
#         product_filter["category"] = category

#     product_cursor = (
#         product_collection
#         .find(product_filter, {"score": {"$meta": "textScore"}})
#         .sort([("score", {"$meta": "textScore"})])
#         .limit(limit)
#     )
#     products = [serialize_product(p) for p in product_cursor]

#     vendor_filter: Dict[str, Any] = {"$text": {"$search": q}}
#     if region:
#         vendor_filter["region"] = region

#     vendor_cursor = (
#         vendor_collection
#         .find(vendor_filter, {"score": {"$meta": "textScore"}})
#         .sort([("score", {"$meta": "textScore"})])
#         .limit(limit)
#     )
#     vendors = [serialize_vendor(v) for v in vendor_cursor]

#     return {"products": products, "vendors": vendors}

@router.get("/search", tags=["Search"])
async def search(
    q: str = Query(..., description="Search term for products/vendors"),
    region: Optional[str] = Query(None, description="Filter by GI region"),
    category: Optional[str] = Query(None, description="Filter by product category"),
    subcategory: Optional[str] = Query(None, description="Filter by product subcategory"),  # ✅ NEW FIELD
    limit: int = Query(20, ge=1, le=100),
):
    product_filter: Dict[str, Any] = {"$text": {"$search": q}}
    if region:
        product_filter["region"] = region
    if category:
        product_filter["category"] = category
    if subcategory:
        product_filter["subcategory"] = subcategory  # ✅ NEW FILTER

    product_cursor = (
        product_collection.find(product_filter, {"score": {"$meta": "textScore"}})
        .sort([("score", {"$meta": "textScore"})])
        .limit(limit)
    )
    products = [serialize_product(p) for p in product_cursor]

    vendor_filter: Dict[str, Any] = {"$text": {"$search": q}}
    if region:
        vendor_filter["region"] = region

    vendor_cursor = (
        vendor_collection.find(vendor_filter, {"score": {"$meta": "textScore"}})
        .sort([("score", {"$meta": "textScore"})])
        .limit(limit)
    )
    vendors = [serialize_vendor(v) for v in vendor_cursor]

    return {"products": products, "vendors": vendors}