# routes/marketplace.py

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional, Any, Dict
from datetime import datetime
from bson import ObjectId
from pymongo import ReturnDocument

from database.db import db
from routes.user import get_current_user
from models.user import User
from models.product import Product, ProductCreate, ProductUpdate
from models.product import Vendor, VendorCreate, VendorUpdate

router = APIRouter()

client = db.get_client()
database = client[db.db_name]
product_collection = database["products"]
vendor_collection = database["vendors"]


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
    # ensure vendor_id is string
    if "vendor_id" in doc:
        doc["vendor_id"] = serialize_id(doc["vendor_id"])
    return serialize_id(doc)

def serialize_vendor(doc: Dict[str, Any]) -> Dict[str, Any]:
    if not doc:
        return doc
    doc = dict(doc)
    doc["id"] = str(doc["_id"])
    doc.pop("_id", None)
    # products array contains ObjectIds
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


# -------------------- PRODUCT ENDPOINTS -------------------- #
@router.post("/products", response_model=Product, tags=["Products"])
async def create_product(product: ProductCreate, user: User = Depends(get_current_user)):
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required.")

    v_id = oid(product.vendor_id)
    vendor = vendor_collection.find_one({"_id": v_id})
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")

    data = product.dict()
    data["vendor_id"] = v_id
    data["created_at"] = datetime.utcnow()
    data["updated_at"] = datetime.utcnow()

    result = product_collection.insert_one(data)
    product_id = result.inserted_id

    vendor_collection.update_one({"_id": v_id}, {"$push": {"products": product_id}})

    created = product_collection.find_one({"_id": product_id})
    return serialize_product(created)


@router.get("/products", response_model=List[Product], tags=["Products"])
async def list_products():
    docs = product_collection.find()
    return [serialize_product(d) for d in docs]


@router.patch("/products/{product_id}", response_model=Product, tags=["Products"])
async def update_product(
    product_id: str,
    update: ProductUpdate,
    user: User = Depends(get_current_user),
):
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required.")

    # Fetch existing product first to handle potential vendor change
    existing = product_collection.find_one({"_id": oid(product_id)})
    if not existing:
        raise HTTPException(status_code=404, detail="Product not found")

    update_data = {k: v for k, v in update.dict().items() if v is not None}
    update_data["updated_at"] = datetime.utcnow()

    # If vendor_id is being updated, validate and rewire vendor links
    if "vendor_id" in update_data:
        new_vendor_id_str = update_data["vendor_id"]
        new_vendor_id = oid(new_vendor_id_str)
        if not vendor_collection.find_one({"_id": new_vendor_id}):
            raise HTTPException(status_code=404, detail="New vendor not found")
        old_vendor_id = existing.get("vendor_id")
        if old_vendor_id != new_vendor_id:
            # Pull from old vendor, push to new vendor
            if old_vendor_id:
                vendor_collection.update_one(
                    {"_id": old_vendor_id}, {"$pull": {"products": existing["_id"]}}
                )
            vendor_collection.update_one(
                {"_id": new_vendor_id}, {"$push": {"products": existing["_id"]}}
            )
        update_data["vendor_id"] = new_vendor_id

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

    # Remove reference from vendor
    if product.get("vendor_id"):
        vendor_collection.update_one(
            {"_id": product["vendor_id"]},
            {"$pull": {"products": product["_id"]}},
        )

    return {"message": "Product deleted"}


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
        # Orphan products by clearing vendor_id; keep data intact
        product_collection.update_many(
            {"vendor_id": vendor["_id"]},
            {"$unset": {"vendor_id": ""}},
        )

    return {"message": "Vendor deleted"}


# -------------------- SEARCH (PUBLIC) -------------------- #
@router.get("/search", tags=["Search"])
async def search(
    q: str = Query(..., description="Search term for products/vendors"),
    region: Optional[str] = Query(None, description="Filter by GI region"),
    category: Optional[str] = Query(None, description="Filter by product category"),
    limit: int = Query(20, ge=1, le=100),
):
    # Products
    product_filter: Dict[str, Any] = {"$text": {"$search": q}}
    if region:
        product_filter["region"] = region
    if category:
        product_filter["category"] = category

    product_cursor = (
        product_collection
        .find(product_filter, {"score": {"$meta": "textScore"}})
        .sort([("score", {"$meta": "textScore"})])
        .limit(limit)
    )
    products = [serialize_product(p) for p in product_cursor]

    # Vendors
    vendor_filter: Dict[str, Any] = {"$text": {"$search": q}}
    if region:
        vendor_filter["region"] = region

    vendor_cursor = (
        vendor_collection
        .find(vendor_filter, {"score": {"$meta": "textScore"}})
        .sort([("score", {"$meta": "textScore"})])
        .limit(limit)
    )
    vendors = [serialize_vendor(v) for v in vendor_cursor]

    return {"products": products, "vendors": vendors}
