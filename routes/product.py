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
from models.product import Order, OrderCreate, PaymentBreakdown, Payment, OrderItem
from models.product import CartQtyUpdate, CartItemIn, CartCheckoutRequest

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
order_collection = database["orders"]
cart_collection = database["carts"]


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


def ensure_cart_indexes() -> None:
    # one cart doc per user
    cart_collection.create_index("user.id", unique=True)
    cart_collection.create_index("vendor_id")
    cart_collection.create_index("updated_at")

ensure_cart_indexes()


#-----------------Order Serialization-----------------#
def serialize_order(doc: Dict[str, Any]) -> Dict[str, Any]:
    if not doc:
        return doc
    d = dict(doc)
    d["id"] = str(d["_id"])
    d.pop("_id", None)
    # vendor is already serialized via serialize_vendor when creating the order,
    # but if it isn't for some reason, make it safe:
    if isinstance(d.get("vendor"), dict) and "_id" in d["vendor"]:
        d["vendor"]["id"] = str(d["vendor"]["_id"])
        d["vendor"].pop("_id", None)
    return serialize_id(d)

def _u(user, key: str):
    if hasattr(user, key):
        return getattr(user, key)
    if hasattr(user, "dict"):
        dd = user.dict()
        if key in dd:
            return dd[key]
    if isinstance(user, dict):
        return user.get(key)
    return None

def _user_id_str(user) -> str:
    uid = _u(user, "id") or _u(user, "_id")
    if not uid:
        raise HTTPException(status_code=400, detail="Authenticated user is missing id/_id")
    return str(uid)

def ensure_order_indexes() -> None:
    order_collection.create_index("user_id")
    order_collection.create_index("vendor.id")
    order_collection.create_index("status")

ensure_order_indexes()

def serialize_cart(doc: Dict[str, Any]) -> Dict[str, Any]:
    if not doc:
        return doc
    d = dict(doc)
    d["id"] = str(d["_id"])
    d.pop("_id", None)
    # normalize ObjectId-like vendor_id to str
    if "vendor_id" in d and d["vendor_id"] is not None:
        d["vendor_id"] = str(d["vendor_id"])
    # items: product_id always as string, quantity as int
    d["items"] = [{"product_id": str(it["product_id"]), "quantity": int(it["quantity"])} for it in d.get("items", [])]
    return serialize_id(d)

def _get_or_create_cart_for_user(user: User) -> Dict[str, Any]:
    user_id = _user_id_str(user)
    doc = cart_collection.find_one({"user.id": user_id})
    if doc:
        return doc
    # create new empty cart
    payload = {
        "user": {
            "id": user_id,
            "username": _u(user, "username") or _u(user, "email"),
            "email": _u(user, "email"),
        },
        "items": [],
        "vendor_id": None,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }
    res = cart_collection.insert_one(payload)
    return cart_collection.find_one({"_id": res.inserted_id})

def _hydrate_cart(cart_doc: Dict[str, Any], *, hydrate: bool = True) -> Dict[str, Any]:
    base = serialize_cart(cart_doc)
    if not hydrate:
        return base

    items_out: List[Dict[str, Any]] = []
    for it in base.get("items", []):
        p = product_collection.find_one({"_id": oid(it["product_id"])})
        if not p:
            # product was deleted – skip it from output (and you may clean later)
            continue
        items_out.append({
            **it,
            "product": serialize_product(p)
        })

    base["items"] = items_out
    return base

def _enforce_single_vendor(cart_doc: Dict[str, Any], product: Dict[str, Any]) -> None:
    """Raise 400 if cart has items from a different vendor."""
    existing_vendor = cart_doc.get("vendor_id")
    new_vendor = product.get("vendor_id")
    if existing_vendor is None:
        return
    if existing_vendor and new_vendor and str(existing_vendor) != str(new_vendor):
        raise HTTPException(status_code=400, detail="Cart can only contain products from one vendor.")

#------------------------------------------------------#

@router.post("/products", response_model=Product, tags=["Products"])
async def create_product(
    name: str = Form(...),
    description: str = Form(...),
    price: float = Form(...),
    gst: float = Form(...),
    unit: Optional[str] = Form(...),
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
        "gst": gst,  # Default GST; adjust as needed
        "unit": unit,
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


# -------------------- PRODUCTS BY CATEGORY -------------------- #
@router.get("/products/category/{category_name}", response_model=List[Product], tags=["Products"])
async def get_products_by_category(category_name: str):
    """
    Get all products belonging to a specific category
    """
    docs = product_collection.find({"category": category_name})
    products = [serialize_product(d) for d in docs]
    if not products:
        raise HTTPException(status_code=404, detail="No products found for this category")
    return products


# -------------------- PRODUCTS BY SUBCATEGORY -------------------- #
@router.get("/products/category/{category_name}/subcategory/{subcategory_name}", response_model=List[Product], tags=["Products"])
async def get_products_by_subcategory(category_name: str, subcategory_name: str):
    """
    Get all products belonging to a specific category and subcategory
    """
    docs = product_collection.find({"category": category_name, "subcategory": subcategory_name})
    products = [serialize_product(d) for d in docs]
    if not products:
        raise HTTPException(status_code=404, detail="No products found for this category and subcategory")
    return products



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

#---------------------------Search Endpoint---------------------------#

@router.get("/search", tags=["Search"])
async def search(
    q: Optional[str] = Query(None, description="Search term for products/vendors"),
    region: Optional[str] = Query(None, description="Filter by GI region"),
    category: Optional[str] = Query(None, description="Filter by product category"),
    subcategory: Optional[str] = Query(None, description="Filter by product subcategory"),
    limit: int = Query(20, ge=1, le=100),
):
    """
    Enhanced flexible search:
    - If q is provided:
        * First try category/subcategory match (case-insensitive)
        * Then text search for relevance
        * If no text search results, fallback to partial regex search
    - If q is not provided: return all products/vendors (with filters if applied)
    """
    products = []
    vendors = []

    if q:
        q_normalized = q.strip()

        # 1️⃣ Exact category match
        products = [
            serialize_product(p) for p in product_collection.find(
                {"category": {"$regex": f"^{q_normalized}$", "$options": "i"}}
            )
        ]

        # 2️⃣ Exact subcategory match
        if not products:
            products = [
                serialize_product(p) for p in product_collection.find(
                    {"subcategory": {"$regex": f"^{q_normalized}$", "$options": "i"}}
                )
            ]

        # 3️⃣ MongoDB text search (if text index exists)
        if not products:
            product_filter: Dict[str, Any] = {"$text": {"$search": q_normalized}}
            if region:
                product_filter["region"] = region
            if category:
                product_filter["category"] = category
            if subcategory:
                product_filter["subcategory"] = subcategory

            product_cursor = (
                product_collection.find(product_filter, {"score": {"$meta": "textScore"}})
                .sort([("score", {"$meta": "textScore"})])
                .limit(limit)
            )
            products = [serialize_product(p) for p in product_cursor]

        # 4️⃣ Fallback to partial regex if text search gives no results
        if not products:
            products = [
                serialize_product(p) for p in product_collection.find(
                    {"$or": [
                        {"name": {"$regex": q_normalized, "$options": "i"}},
                        {"description": {"$regex": q_normalized, "$options": "i"}},
                        {"subcategory": {"$regex": q_normalized, "$options": "i"}},
                        {"category": {"$regex": q_normalized, "$options": "i"}},
                    ]}
                ).limit(limit)
            ]

        # 5️⃣ Vendor search with fallback
        vendor_filter = {"$or": [
            {"name": {"$regex": q_normalized, "$options": "i"}},
            {"$text": {"$search": q_normalized}},
        ]}
        if region:
            vendor_filter["region"] = region

        vendor_cursor = vendor_collection.find(vendor_filter).limit(limit)
        vendors = [serialize_vendor(v) for v in vendor_cursor]

        # Vendor fallback if text search fails
        if not vendors:
            vendors = [
                serialize_vendor(v) for v in vendor_collection.find(
                    {"name": {"$regex": q_normalized, "$options": "i"}}
                ).limit(limit)
            ]

    else:
        # If no query, just return everything (with filters if applied)
        product_filter: Dict[str, Any] = {}
        if region:
            product_filter["region"] = region
        if category:
            product_filter["category"] = category
        if subcategory:
            product_filter["subcategory"] = subcategory

        product_cursor = product_collection.find(product_filter).limit(limit)
        products = [serialize_product(p) for p in product_cursor]

        vendor_filter: Dict[str, Any] = {}
        if region:
            vendor_filter["region"] = region

        vendor_cursor = vendor_collection.find(vendor_filter).limit(limit)
        vendors = [serialize_vendor(v) for v in vendor_cursor]

    return {"products": products, "vendors": vendors}


#-----------------------------Orders-----------------------------

@router.post("/orders", response_model=Dict[str, Any], tags=["Orders"])
async def create_order(order: OrderCreate, user: User = Depends(get_current_user)):
    """
    Place a new order. Only allowed for users (role=user or admin).
    Decreases product stock dynamically.
    """
    if user.role not in ["user", "admin"]:
        raise HTTPException(status_code=403, detail="Only users/admins can place orders.")

    user_id = str(getattr(user, "id", None) or getattr(user, "_id", None))
    if not user_id:
        raise HTTPException(status_code=400, detail="Authenticated user is missing id/_id")

    username = getattr(user, "username", None) or getattr(user, "email", None)
    email = getattr(user, "email", None)

    items: List[Dict[str, Any]] = []
    product_total = 0.0
    gst_total = 0.0
    vendor_id: Optional[ObjectId] = None
    vendor_details: Optional[Dict[str, Any]] = None

    for it in order.items:
        product = product_collection.find_one({"_id": oid(it.product_id)})
        if not product:
            raise HTTPException(status_code=404, detail=f"Product not found: {it.product_id}")

        if product["stock"] < it.quantity:
            raise HTTPException(status_code=400, detail=f"Insufficient stock for {product['name']}")

        # Calculate subtotal and GST
        subtotal = float(product["price"]) * it.quantity
        product_total += subtotal
        product_gst_percent = float(product.get("gst", 0.0))
        gst_amount = subtotal * product_gst_percent / 100
        gst_total += gst_amount

        # Append order item
        items.append({
            "product_id": str(product["_id"]),
            "name": product["name"],
            "unit_price": float(product["price"]),
            "quantity": it.quantity,
            "subtotal": subtotal,
            "gst_percent": product_gst_percent,
            "gst_amount": gst_amount,
        })

        # Ensure single vendor per order
        if vendor_id is None:
            vendor_id = product.get("vendor_id")
            if vendor_id:
                vendor_details = vendor_collection.find_one({"_id": vendor_id})
        elif vendor_id != product.get("vendor_id"):
            raise HTTPException(status_code=400, detail="Order can only contain products from one vendor.")

        # ----------------- UPDATE STOCK ----------------- #
        new_stock = product["stock"] - it.quantity
        product_collection.update_one(
            {"_id": product["_id"]},
            {"$set": {"stock": new_stock, "updated_at": datetime.utcnow()}}
        )

    if not vendor_details:
        raise HTTPException(status_code=400, detail="Vendor not found for order.")

    # Charges
    delivery_charge = 50.0
    handling_fee = 10.0
    discount_amount = 0.0
    final_amount = product_total + gst_total + delivery_charge + handling_fee - discount_amount

    payment: Payment = Payment(
        payment_method=order.payment_method,
        status="pending",
        breakdown=PaymentBreakdown(
            product_total=product_total,
            gst_total=gst_total,
            delivery_charge=delivery_charge,
            handling_fee=handling_fee,
            discount_amount=discount_amount,
            final_amount=final_amount,
        ),
    )

    # Build order document
    doc = {
        "user": {
            "id": user_id,
            "username": username,
            "email": email,
        },
        "items": items,
        "vendor": serialize_vendor(vendor_details),
        "delivery_address": order.delivery_address,
        "contact_phone": order.contact_phone,
        "payment": payment.dict(),
        "status": "pending",
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }

    result = order_collection.insert_one(doc)
    created = order_collection.find_one({"_id": result.inserted_id})
    return serialize_order(created)



@router.get("/orders", response_model=List[Dict[str, Any]], tags=["Orders"])
async def list_orders(user: User = Depends(get_current_user)):
    """
    List orders. Users see their own, admin sees all.
    """
    if user.role == "admin":
        docs = order_collection.find()
    else:
        user_id = str(getattr(user, "id", None) or getattr(user, "_id", None))
        docs = order_collection.find({"user.id": user_id})
    return [serialize_order(d) for d in docs]


@router.get("/orders/{order_id}", response_model=Dict[str, Any], tags=["Orders"])
async def get_order(order_id: str, user: User = Depends(get_current_user)):
    """
    Get a single order. User can see own orders, admin sees all.
    """
    order = order_collection.find_one({"_id": oid(order_id)})
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    if user.role != "admin":
        user_id = str(getattr(user, "id", None) or getattr(user, "_id", None))
        if order.get("user", {}).get("id") != user_id:
            raise HTTPException(status_code=403, detail="Not allowed to view this order.")

    return serialize_order(order)


@router.patch("/orders/{order_id}", response_model=Dict[str, Any], tags=["Orders"])
async def update_order_status(
    order_id: str,
    status: str = Query(..., description="New status (confirmed/shipped/delivered/canceled)"),
    user: User = Depends(get_current_user),
):
    """
    Admin can update order status.
    """
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required.")

    updated = order_collection.find_one_and_update(
        {"_id": oid(order_id)},
        {"$set": {"status": status, "updated_at": datetime.utcnow()}},
        return_document=ReturnDocument.AFTER,
    )

    if not updated:
        raise HTTPException(status_code=404, detail="Order not found")

    return serialize_order(updated)


# ----------------------------- CART -----------------------------

@router.get("/cart", tags=["Cart"])
async def get_my_cart(
    hydrate: bool = Query(True, description="Include product details for each item"),
    user: User = Depends(get_current_user),
):
    """
    Return the current user's cart. Creates an empty cart if none exists.
    """
    cart_doc = _get_or_create_cart_for_user(user)
    return _hydrate_cart(cart_doc, hydrate=hydrate)


@router.post("/cart/items", tags=["Cart"])
async def cart_add_item(
    item: CartItemIn,
    user: User = Depends(get_current_user),
):
    """
    Add an item to the cart (or increase its quantity). Enforces single-vendor cart.
    Quantity cannot exceed current product stock.
    """
    cart_doc = _get_or_create_cart_for_user(user)
    product = product_collection.find_one({"_id": oid(item.product_id)})
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    _enforce_single_vendor(cart_doc, product)

    # find existing
    items = cart_doc.get("items", [])
    idx = next((i for i, it in enumerate(items) if str(it["product_id"]) == str(product["_id"])), -1)
    new_qty = item.quantity
    if idx != -1:
        new_qty = int(items[idx]["quantity"]) + item.quantity

    stock = int(product.get("stock", 0))
    if new_qty > stock:
        raise HTTPException(status_code=400, detail="Cannot exceed available stock")

    if idx == -1:
        items.append({"product_id": str(product["_id"]), "quantity": item.quantity})
    else:
        items[idx]["quantity"] = new_qty

    # set vendor if empty
    vendor_id = cart_doc.get("vendor_id")
    if vendor_id is None:
        vendor_id = product.get("vendor_id")

    updated = cart_collection.find_one_and_update(
        {"_id": cart_doc["_id"]},
        {"$set": {"items": items, "vendor_id": vendor_id, "updated_at": datetime.utcnow()}},
        return_document=ReturnDocument.AFTER,
    )
    return _hydrate_cart(updated, hydrate=True)


@router.patch("/cart/items/{product_id}", tags=["Cart"])
async def cart_update_quantity(
    product_id: str,
    payload: CartQtyUpdate,
    user: User = Depends(get_current_user),
):
    """
    Set quantity for a product already in the cart.
    If quantity==0, the item is removed.
    """
    cart_doc = _get_or_create_cart_for_user(user)
    items = cart_doc.get("items", [])

    idx = next((i for i, it in enumerate(items) if str(it["product_id"]) == str(product_id)), -1)
    if idx == -1:
        raise HTTPException(status_code=404, detail="Item not in cart")

    if payload.quantity == 0:
        items.pop(idx)
    else:
        # stock check
        product = product_collection.find_one({"_id": oid(product_id)})
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")
        stock = int(product.get("stock", 0))
        if payload.quantity > stock:
            raise HTTPException(status_code=400, detail="Cannot exceed available stock")
        items[idx]["quantity"] = payload.quantity

    # reset vendor if cart becomes empty
    vendor_id = cart_doc.get("vendor_id")
    if not items:
        vendor_id = None

    updated = cart_collection.find_one_and_update(
        {"_id": cart_doc["_id"]},
        {"$set": {"items": items, "vendor_id": vendor_id, "updated_at": datetime.utcnow()}},
        return_document=ReturnDocument.AFTER,
    )
    return _hydrate_cart(updated, hydrate=True)


@router.delete("/cart/items/{product_id}", tags=["Cart"])
async def cart_remove_item(
    product_id: str,
    user: User = Depends(get_current_user),
):
    """
    Remove a product from the cart.
    """
    cart_doc = _get_or_create_cart_for_user(user)
    items = [it for it in cart_doc.get("items", []) if str(it["product_id"]) != str(product_id)]
    vendor_id = cart_doc.get("vendor_id")
    if not items:
        vendor_id = None

    updated = cart_collection.find_one_and_update(
        {"_id": cart_doc["_id"]},
        {"$set": {"items": items, "vendor_id": vendor_id, "updated_at": datetime.utcnow()}},
        return_document=ReturnDocument.AFTER,
    )
    return _hydrate_cart(updated, hydrate=True)


@router.delete("/cart", tags=["Cart"])
async def cart_clear(user: User = Depends(get_current_user)):
    """
    Clear the entire cart for the current user.
    """
    cart_doc = _get_or_create_cart_for_user(user)
    updated = cart_collection.find_one_and_update(
        {"_id": cart_doc["_id"]},
        {"$set": {"items": [], "vendor_id": None, "updated_at": datetime.utcnow()}},
        return_document=ReturnDocument.AFTER,
    )
    return _hydrate_cart(updated, hydrate=True)
