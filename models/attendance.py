from pydantic import BaseModel
from datetime import datetime

class Attendance(BaseModel):
    username: str  # User's unique username (email)
    date: str = datetime.utcnow().strftime("%Y-%m-%d")  # Store only YYYY-MM-DD
