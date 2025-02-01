from pydantic import BaseModel, EmailStr
from typing import Optional

class User(BaseModel):
    first_name: str
    last_name: str
    email: EmailStr
    phone: str
    district: str
    username: str
    password: str
    activated: bool = False
    user_type: str  # "admin" or "user"

    class Config:
        schema_extra = {
            "example": {
                "first_name": "John",
                "last_name": "Doe",
                "email": "john@example.com",
                "phone": "+1234567890",
                "district": "New York",
                "username": "john_doe",
                "activated": True,
                "user_type": "user"
            }
        }
