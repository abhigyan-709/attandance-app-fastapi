from typing import Optional

from pydantic import BaseModel, EmailStr

class User(BaseModel):
    first_name: str
    last_name: str
    city: str
    username: str
    email: EmailStr
    password: str
    role : str = "user" # default user is set to the user role
    is_active : bool = True

    class Config:
        orm_mode = True


class UserProfileUpdate(BaseModel):
    """Model for updating user profile information"""
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[EmailStr] = None
    city: Optional[str] = None
    phone_number: Optional[str] = None
    state: Optional[str] = None
    pincode: Optional[str] = None
    profile_picture_url: Optional[str] = None

    class Config:
        orm_mode = True
        json_schema_extra = {
            "example": {
                "first_name": "Rahul",
                "last_name": "Kumar",
                "email": "rahul.kumar@example.com",
                "city": "Patna",
                "phone_number": "+91-9876543210",
                "state": "Bihar",
                "pincode": "800001",
                "profile_picture_url": "https://projectdevops-blogs-new.s3.ap-south-1.amazonaws.com/profile-pictures/user123_profile.jpg"
            }
        }