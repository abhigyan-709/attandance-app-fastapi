from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

class Address(BaseModel):
    address_id: Optional[str] = None
    address: str
    address_type: str = Field(..., description="Home / Office / Other")
    pincode: str
    city: str
    district: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        orm_mode = True

class CustomerDetails(BaseModel):
    name: str
    phone_number: str
    username: Optional[str] = None
    email: Optional[str] = None
    addresses: Optional[List[Address]] = []
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        orm_mode = True