from fastapi import APIRouter, Depends, HTTPException
from models.product import ProductCreate, ProductUpdate, Product
from models.user import User
from routes.user import get_current_user
from database.db import db
from bson import ObjectId
from datetime import datetime

router = APIRouter()

collection = db.get_client()[db.db_name]["products"]

@router.post("/products", response_model=Product, tags=["Products"])
async def create_product(product: ProductCreate, user: User = Depends(get_current_user)):
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required.")

    data = product.dict()
    data["created_at"] = datetime.utcnow()
    data["updated_at"] = datetime.utcnow()

    result = collection.insert_one(data)
    data["id"] = str(result.inserted_id)
    return data

@router.get("/products", response_model=list[Product], tags=["Products"])
async def list_products():
    products = collection.find()
    return [{**prod, "id": str(prod["_id"])} for prod in products]

@router.patch("/products/{product_id}", response_model=Product, tags=["Products"])
async def update_product(product_id: str, update: ProductUpdate, user: User = Depends(get_current_user)):
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required.")
    
    update_data = {k: v for k, v in update.dict().items() if v is not None}
    update_data["updated_at"] = datetime.utcnow()

    result = collection.find_one_and_update(
        {"_id": ObjectId(product_id)},
        {"$set": update_data},
        return_document=True
    )
    if not result:
        raise HTTPException(status_code=404, detail="Product not found")

    result["id"] = str(result["_id"])
    return result

@router.delete("/products/{product_id}", tags=["Products"])
async def delete_product(product_id: str, user: User = Depends(get_current_user)):
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required.")
    
    result = collection.delete_one({"_id": ObjectId(product_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Product not found")
    
    return {"message": "Product deleted"}
