from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

class ProductBase(BaseModel):
    name: str
    description: Optional[str]
    price: float
    region: str
    sku: str
    category: Optional[str]

class ProductCreate(ProductBase):
    stock: int

class ProductUpdate(BaseModel):
    name: Optional[str]
    description: Optional[str]
    price: Optional[float]
    region: Optional[str]
    sku: Optional[str]
    stock: Optional[int]
    category: Optional[str]

class Product(ProductBase):
    id: str
    stock: int
    created_at: datetime
    updated_at: datetime
