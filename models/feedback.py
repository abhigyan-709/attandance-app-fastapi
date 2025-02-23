from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime

class Feedback(BaseModel):
    username: str
    email: EmailStr
    message: str
    rating: Optional[int] = None  # Optional rating from 1-5
    created_at: datetime = datetime.utcnow()
