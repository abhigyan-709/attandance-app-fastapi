from pydantic import BaseModel
from typing import Optional
from datetime import datetime

# Pydantic Model for request & response validation
class MeetLink(BaseModel):
    meet_link: str
    created_at: Optional[datetime] = datetime.utcnow()
