from typing import Optional

from pydantic import BaseModel, EmailStr

class Message(BaseModel):
    name: str
    email: EmailStr
    phone: str
    message: str

    class Config:
        orm_mode = True