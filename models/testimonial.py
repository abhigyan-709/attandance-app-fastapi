from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

class Testimonial(BaseModel):
    id: Optional[str] = Field(default=None, alias="_id")
    username: str
    name: str
    city: str
    email: str
    linkedin: str
    phone: str
    content: str
    image_url: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        from_attributes = True
        arbitrary_types_allowed = True
