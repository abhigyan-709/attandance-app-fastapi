# from pydantic import BaseModel, Field, HttpUrl
# from typing import List, Optional
# from datetime import datetime


# # ---------------- VENDOR MODELS ---------------- #
# class VendorBase(BaseModel):
#     name: str
#     email: str
#     phone: str
#     address: str
#     region: str  # GI tag region
#     description: Optional[str] = None


# class VendorCreate(VendorBase):
#     pass


# class VendorUpdate(BaseModel):
#     name: Optional[str]
#     email: Optional[str]
#     phone: Optional[str]
#     address: Optional[str]
#     region: Optional[str]
#     description: Optional[str]


# class Vendor(VendorBase):
#     id: str
#     products: List[str] = []  # list of product IDs
#     created_at: datetime
#     updated_at: datetime


# # ---------------- PRODUCT MODELS ---------------- #
# class ProductBase(BaseModel):
#     name: str
#     description: Optional[str]
#     price: float
#     region: str  # GI tag region
#     sku: str
#     category: Optional[str]


# class ProductCreate(ProductBase):
#     stock: int
#     vendor_id: str
#     images: List[HttpUrl] = Field(..., max_items=4)  # up to 4 images


# class ProductUpdate(BaseModel):
#     name: Optional[str]
#     description: Optional[str]
#     price: Optional[float]
#     region: Optional[str]
#     sku: Optional[str]
#     stock: Optional[int]
#     category: Optional[str]
#     images: Optional[List[HttpUrl]] = Field(None, max_items=4)


# class Product(ProductBase):
#     id: str
#     stock: int
#     vendor_id: str
#     images: List[HttpUrl] = []
#     created_at: datetime
#     updated_at: datetime


from pydantic import BaseModel, Field, HttpUrl
from typing import List, Optional
from datetime import datetime

# ---------------- VENDOR MODELS ---------------- #
class VendorBase(BaseModel):
    name: str
    email: str
    phone: str
    address: str
    region: str  # GI tag region
    description: Optional[str] = None


class VendorCreate(VendorBase):
    pass


class VendorUpdate(BaseModel):
    name: Optional[str]
    email: Optional[str]
    phone: Optional[str]
    address: Optional[str]
    region: Optional[str]
    description: Optional[str]


class Vendor(VendorBase):
    id: str
    products: List[str] = []  # list of product IDs
    created_at: datetime
    updated_at: datetime


# ---------------- PRODUCT MODELS ---------------- #
class ProductBase(BaseModel):
    name: str
    description: Optional[str]
    price: float
    region: str  # GI tag region
    sku: str
    category: Optional[str]
    subcategory: Optional[str]  # NEW FIELD


class ProductCreate(ProductBase):
    stock: int
    vendor_id: str
    images: List[HttpUrl] = Field(..., max_items=4)  # up to 4 images


class ProductUpdate(BaseModel):
    name: Optional[str]
    description: Optional[str]
    price: Optional[float]
    region: Optional[str]
    sku: Optional[str]
    stock: Optional[int]
    category: Optional[str]
    subcategory: Optional[str]  # NEW FIELD
    images: Optional[List[HttpUrl]] = Field(None, max_items=4)


class Product(ProductBase):
    id: str
    stock: int
    vendor_id: str
    images: List[HttpUrl] = []
    created_at: datetime
    updated_at: datetime
