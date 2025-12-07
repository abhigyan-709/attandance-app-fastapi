from pydantic import BaseModel, EmailStr, Field
from typing import Optional


class SurveyForm(BaseModel):
    name: Optional[str] = Field(None, description="Name of the respondent")
    age: Optional[int] = Field(None, ge=0, le=150, description="Age of the respondent")
    address: Optional[str] = Field(None, description="Address of the respondent")
    city: Optional[str] = Field(None, description="City")
    pincode: Optional[str] = Field(None, description="Pincode")
    whatsapp_number: Optional[str] = Field(None, description="WhatsApp number")
    phone_number: Optional[str] = Field(None, description="Phone number")
    email: Optional[EmailStr] = Field(None, description="Email address")

    class Config:
        json_schema_extra = {
            "example": {
                "name": "John Doe",
                "age": 30,
                "address": "123 Main Street",
                "city": "Mumbai",
                "pincode": "400001",
                "whatsapp_number": "+919876543210",
                "phone_number": "+919876543210",
                "email": "john.doe@example.com"
            }
        }


class SurveyResponse(BaseModel):
    id: str
    name: Optional[str] = None
    age: Optional[int] = None
    address: Optional[str] = None
    city: Optional[str] = None
    pincode: Optional[str] = None
    whatsapp_number: Optional[str] = None
    phone_number: Optional[str] = None
    email: Optional[EmailStr] = None
    submitted_at: str

    class Config:
        json_schema_extra = {
            "example": {
                "id": "507f1f77bcf86cd799439011",
                "name": "John Doe",
                "age": 30,
                "address": "123 Main Street",
                "city": "Mumbai",
                "pincode": "400001",
                "whatsapp_number": "+919876543210",
                "phone_number": "+919876543210",
                "email": "john.doe@example.com",
                "submitted_at": "2025-12-07T10:30:00"
            }
        }
