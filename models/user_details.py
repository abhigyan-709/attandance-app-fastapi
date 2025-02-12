from pydantic import BaseModel
from typing import Optional

class UserDetails(BaseModel):
    username: str
    father_name: str
    mother_name: str
    mobile_number: str
    college_name: str
    course: str
    branch: str
    year_of_passing: int
    date_of_birth: str

    class Config:
        orm_mode = True