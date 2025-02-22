from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from bson import ObjectId

class Courses(BaseModel):
    
    course_name: str
    course_duration: str
    course_fees: str
    payment_link: str

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
    role : str = "user" # default user is set to the user role
    is_active : bool = False

    class Config:
        orm_mode = True
        arbitrary_types_allowed = True




