from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from bson import ObjectId

class Courses(BaseModel):
    # id: Optional[str] = Field(alias="_id")  # Store ObjectId from MongoDB
    course_name: str
    course_duration: str
    course_fees: str

    class Config:
        orm_mode = True
        arbitrary_types_allowed = True


class UserSubscription(BaseModel):
    username: str
    password: str
    first_name: str 
    last_name: str
    email: EmailStr
    phone: str
    college: str
    fathers_name: str
    mothers_name: str
    fathers_number: str
    pin: str
    district: str
    state: str
    enrolling_for: str

    class Config:
        orm_mode = True
        arbitrary_types_allowed = True




