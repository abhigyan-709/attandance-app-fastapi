from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

# Quiz Schema
class QuizCreate(BaseModel):
    question: str
    options: List[str]
    correct_answer: str
    time_limit: int  # in seconds

# User Response Schema
class UserResponse(BaseModel):
    username: str
    quiz_id: str
    selected_option: str
    submitted_at: datetime
