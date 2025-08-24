# from pydantic import BaseModel, Field
# from typing import List, Optional
# from datetime import datetime

# class Address(BaseModel):
#     address_id: Optional[str] = None
#     address: str
#     address_type: str  # Home, Office, etc.
#     pincode: str
#     city: str
#     district: str
#     is_default: bool = False
#     created_at: Optional[datetime] = None
#     updated_at: Optional[datetime] = None


# class CustomerDetails(BaseModel):
#     username: str
#     email: str
#     name: str
#     phone_number: str
#     addresses: List[Address] = []
#     created_at: Optional[datetime] = None
#     updated_at: Optional[datetime] = None
    
#     class Config:
#         schema_extra = {
#             "example": {
#                 "name": "John Doe",
#                 "phone_number": "+1234567890",
#                 "addresses": [
#                     {
#                         "address": "123 Main St, Springfield",
#                         "address_type": "Home",
#                         "pincode": "123456",
#                         "city": "Springfield",
#                         "district": "Central",
#                         "is_default": True
#                     }
#                 ]
#             }
#         }

# models/customer_details.py
from pydantic import BaseModel
from typing import List, Optional

class Address(BaseModel):
    address_id: Optional[str] = None
    address: str
    address_type: Optional[str] = "Home"
    pincode: Optional[str] = None
    city: Optional[str] = None
    district: Optional[str] = None
    is_default: Optional[bool] = False
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

# What the client RECEIVES
class CustomerDetailsOut(BaseModel):
    id: Optional[str] = None
    username: str
    email: Optional[str] = None
    name: Optional[str] = None
    phone_number: Optional[str] = None    # ✅ allow null
    addresses: List[Address] = []
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

# What the client SENDS
class CustomerDetailsUpsert(BaseModel):
    name: Optional[str] = None
    phone_number: Optional[str] = None
    addresses: Optional[List[Address]] = None
