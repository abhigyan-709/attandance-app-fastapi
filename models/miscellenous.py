from typing import Optional

from pydantic import BaseModel, EmailStr

class SFMessage(BaseModel):
    first_name: str
    last_anem: str
    email: EmailStr
    mobile: str
    message: str

    class Config:
        orm_mode = True