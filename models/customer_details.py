# # models/customer_details.py
# from pydantic import BaseModel
# from typing import List, Optional

# class Address(BaseModel):
#     address_id: Optional[str] = None
#     address: str
#     address_type: Optional[str] = "Home"
#     pincode: Optional[str] = None
#     city: Optional[str] = None
#     district: Optional[str] = None
#     is_default: Optional[bool] = False
#     created_at: Optional[str] = None
#     updated_at: Optional[str] = None

# # What the client RECEIVES
# class CustomerDetailsOut(BaseModel):
#     id: Optional[str] = None
#     username: str
#     email: Optional[str] = None
#     name: Optional[str] = None
#     phone_number: Optional[str] = None    # ✅ allow null
#     addresses: List[Address] = []
#     created_at: Optional[str] = None
#     updated_at: Optional[str] = None

# # What the client SENDS
# class CustomerDetailsUpsert(BaseModel):
#     name: Optional[str] = None
#     phone_number: Optional[str] = None
#     addresses: Optional[List[Address]] = None


# models/customer_details.py
from datetime import datetime
from typing import List, Optional, Dict, Any
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, confloat, constr

router = APIRouter()

# --- NEW: nested location payload we get from the app ---
class GeoLocation(BaseModel):
    lat: confloat(ge=-90, le=90)                     # required
    lng: confloat(ge=-180, le=180)                   # required
    accuracy_m: Optional[confloat(ge=0)] = None
    place_id: Optional[str] = None                   # Google place_id (if available)
    plus_code: Optional[str] = None
    maps_url: Optional[str] = None                   # convenience link

class Address(BaseModel):
    address_id: Optional[str] = None
    address: str
    address_type: Optional[str] = "Home"
    pincode: Optional[str] = None
    city: Optional[str] = None
    district: Optional[str] = None
    is_default: Optional[bool] = False
    # --- NEW fields ---
    location: Optional[GeoLocation] = None           # precise coordinates, optional
    driver_note: Optional[str] = None                # landmark/instructions
    # ---
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

# What the client RECEIVES
class CustomerDetailsOut(BaseModel):
    id: Optional[str] = None
    username: str
    email: Optional[str] = None
    name: Optional[str] = None
    phone_number: Optional[str] = None
    addresses: List[Address] = []
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

# What the client SENDS
class CustomerDetailsUpsert(BaseModel):
    name: Optional[str] = None
    phone_number: Optional[str] = None
    addresses: Optional[List[Address]] = None
