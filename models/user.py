from typing import Optional

from pydantic import BaseModel, EmailStr

class User(BaseModel):
    first_name: str
    last_name: str
    city: str
    username: str
    email: EmailStr
    password: str
    role : str = "user" # Options: "admin", "user", "moderator", "author", "vendor"
    is_active : bool = True
    
    # Author Profile Fields (optional - only for authors)
    author_bio: Optional[str] = None
    author_profile_image: Optional[str] = None
    author_designation: Optional[str] = None  # e.g., "Senior Editor", "Staff Writer"
    author_social_links: Optional[dict] = None  # {"twitter": "url", "linkedin": "url"}
    articles_count: Optional[int] = 0  # Total articles written

    class Config:
        from_attributes = True


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
    
    # Author Profile Fields
    author_bio: Optional[str] = None
    author_profile_image: Optional[str] = None
    author_designation: Optional[str] = None
    author_social_links: Optional[dict] = None

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "first_name": "Rahul",
                "last_name": "Kumar",
                "email": "rahul.kumar@example.com",
                "city": "Patna",
                "phone_number": "+91-9876543210",
                "state": "Bihar",
                "pincode": "800001",
                "profile_picture_url": "https://projectdevops-blogs-new.s3.ap-south-1.amazonaws.com/profile-pictures/user123_profile.jpg",
                "author_bio": "Senior journalist with 10 years of experience",
                "author_designation": "Senior Editor",
                "author_social_links": {"twitter": "https://twitter.com/example", "linkedin": "https://linkedin.com/in/example"}
            }
        }


class AuthorInfo(BaseModel):
    """Public author information for displaying in news articles"""
    username: str
    full_name: str
    author_bio: Optional[str] = None
    author_profile_image: Optional[str] = None
    author_designation: Optional[str] = None
    author_social_links: Optional[dict] = None
    articles_count: Optional[int] = 0
    
    class Config:
        json_schema_extra = {
            "example": {
                "username": "rahul_kumar",
                "full_name": "Rahul Kumar",
                "author_bio": "Senior journalist with 10 years of experience",
                "author_profile_image": "https://example.com/profile.jpg",
                "author_designation": "Senior Editor",
                "author_social_links": {"twitter": "https://twitter.com/example"},
                "articles_count": 45
            }
        }


class RoleUpdateRequest(BaseModel):
    """Model for admin to update user roles"""
    username: str
    new_role: str  # "admin", "user", "moderator", "author", "vendor"
    
    class Config:
        json_schema_extra = {
            "example": {
                "username": "john_doe",
                "new_role": "author"
            }
        }
