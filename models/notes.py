# models.py
from pydantic import BaseModel
from bson import ObjectId

class NoteModel(BaseModel):
    title: str
    file_url: str

    class Config:
        arbitrary_types_allowed = True