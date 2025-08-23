from fastapi import APIRouter, Depends, HTTPException
from pymongo import MongoClient
from database.db import db
from models.customer_details import CustomerDetails, Address
from models.user import User
from datetime import datetime
from bson import ObjectId
from routes.user import get_current_user

route = APIRouter()

@route.post("/customer/details", tags=["Customer Details"])
async def add_or_update_customer_details(
    customer: CustomerDetails,
    current_user: User = Depends(get_current_user),
    db_client: MongoClient = Depends(db.get_client)
):
    collection = db_client[db.db_name]["customer_details"]

    # Ensure username and email are from logged-in user
    customer_dict = customer.dict()
    customer_dict.update({
        "username": current_user.username,
        "email": current_user.email,
        "updated_at": datetime.utcnow()
    })

    existing = collection.find_one({"username": current_user.username})
    if existing:
        collection.update_one({"username": current_user.username}, {"$set": customer_dict})
    else:
        customer_dict["created_at"] = datetime.utcnow()
        collection.insert_one(customer_dict)

    updated_doc = collection.find_one({"username": current_user.username})
    updated_doc["_id"] = str(updated_doc["_id"])
    return updated_doc


@route.get("/customer/details", tags=["Customer Details"])
async def get_customer_details(
    current_user: User = Depends(get_current_user),
    db_client: MongoClient = Depends(db.get_client)
):
    collection = db_client[db.db_name]["customer_details"]
    doc = collection.find_one({"username": current_user.username})
    if not doc:
        raise HTTPException(status_code=404, detail="Customer details not found")
    doc["_id"] = str(doc["_id"])
    return doc


@route.post("/customer/address", tags=["Customer Details"])
async def add_address(
    address: Address,
    current_user: User = Depends(get_current_user),
    db_client: MongoClient = Depends(db.get_client)
):
    collection = db_client[db.db_name]["customer_details"]
    doc = collection.find_one({"username": current_user.username})
    if not doc:
        raise HTTPException(status_code=404, detail="Customer details not found")

    if not address.address_id:
        address.address_id = str(ObjectId())

    now = datetime.utcnow()
    address.created_at = now
    address.updated_at = now

    # Ensure only one default address
    if address.is_default:
        collection.update_one(
            {"username": current_user.username},
            {"$set": {"addresses.$[].is_default": False}}
        )

    collection.update_one(
        {"username": current_user.username},
        {"$push": {"addresses": address.dict()}}
    )

    updated_doc = collection.find_one({"username": current_user.username})
    updated_doc["_id"] = str(updated_doc["_id"])
    return updated_doc


@route.put("/customer/address/{address_id}", tags=["Customer Details"])
async def update_address(
    address_id: str,
    address: Address,
    current_user: User = Depends(get_current_user),
    db_client: MongoClient = Depends(db.get_client)
):
    collection = db_client[db.db_name]["customer_details"]
    address.updated_at = datetime.utcnow()

    # If setting default, unset previous default addresses
    if address.is_default:
        collection.update_one(
            {"username": current_user.username},
            {"$set": {"addresses.$[].is_default": False}}
        )

    result = collection.update_one(
        {"username": current_user.username, "addresses.address_id": address_id},
        {"$set": {f"addresses.$": address.dict()}}
    )

    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Address not found")

    updated_doc = collection.find_one({"username": current_user.username})
    updated_doc["_id"] = str(updated_doc["_id"])
    return updated_doc


@route.delete("/customer/address/{address_id}", tags=["Customer Details"])
async def delete_address(
    address_id: str,
    current_user: User = Depends(get_current_user),
    db_client: MongoClient = Depends(db.get_client)
):
    collection = db_client[db.db_name]["customer_details"]
    result = collection.update_one(
        {"username": current_user.username},
        {"$pull": {"addresses": {"address_id": address_id}}}
    )
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Address not found")

    updated_doc = collection.find_one({"username": current_user.username})
    updated_doc["_id"] = str(updated_doc["_id"])
    return updated_doc
