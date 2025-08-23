from fastapi import APIRouter, Depends, HTTPException
from pymongo import MongoClient
from database.db import db
from models.customer_details import CustomerDetails, Address
from models.user import User
from datetime import datetime
from bson import ObjectId
from typing import List
from routes.user import get_current_user

route = APIRouter()

@route.post("/customer/details", tags=["Customer Details"])
async def add_or_update_customer_details(
    customer: CustomerDetails,
    current_user: User = Depends(get_current_user),
    db_client: MongoClient = Depends(db.get_client)
):
    collection = db_client[db.db_name]["customer_details"]

    customer_dict = customer.dict()
    customer_dict.update({
        "username": current_user.username,
        "email": current_user.email,
        "updated_at": datetime.utcnow()
    })

    existing = collection.find_one({"username": current_user.username})

    if existing:
        # Update existing document
        collection.update_one({"username": current_user.username}, {"$set": customer_dict})
    else:
        # Insert new document
        customer_dict["created_at"] = datetime.utcnow()
        collection.insert_one(customer_dict)

    updated_doc = collection.find_one({"username": current_user.username})
    updated_doc["_id"] = str(updated_doc["_id"])
    # Convert nested address_ids
    for addr in updated_doc.get("addresses", []):
        if "address_id" in addr and not addr["address_id"]:
            addr["address_id"] = str(ObjectId())
    return updated_doc


@route.get("/customer/details", response_model=CustomerDetails, tags=["Customer Details"])
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
    address.created_at = datetime.utcnow()
    address.updated_at = datetime.utcnow()

    collection.update_one(
        {"username": current_user.username},
        {"$push": {"addresses": address.dict()}}
    )

    return {"message": "Address added successfully", "address": address.dict()}


@route.put("/customer/address/{address_id}", tags=["Customer Details"])
async def update_address(
    address_id: str,
    address: Address,
    current_user: User = Depends(get_current_user),
    db_client: MongoClient = Depends(db.get_client)
):
    collection = db_client[db.db_name]["customer_details"]
    address.updated_at = datetime.utcnow()
    result = collection.update_one(
        {"username": current_user.username, "addresses.address_id": address_id},
        {"$set": {f"addresses.$": address.dict()}}
    )

    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Address not found")
    return {"message": "Address updated successfully", "address": address.dict()}


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
    return {"message": "Address deleted successfully"}
