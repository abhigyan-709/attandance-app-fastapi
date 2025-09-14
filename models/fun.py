# models/fun.py
from pydantic import BaseModel, Field
from typing import Optional, List

class StyleRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=5000, description="Input text to style")
    style: str = Field(..., description="One of GET /fun/styles")
    decorator: Optional[str] = Field("none", description="One of GET /fun/decorators")

class StyleResponse(BaseModel):
    text: str
    styled: str
    style: str
    decorator: str

class ListResponse(BaseModel):
    items: List[str]
