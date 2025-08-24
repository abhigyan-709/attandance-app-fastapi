from pydantic import BaseModel, Field, HttpUrl
from typing import List, Optional
from datetime import datetime
from uuid import uuid4



# ---------------- ORDER MODELS ---------------- #
class OrderItem(BaseModel):
    product_id: str  # ID of the product being ordered
    quantity: int = Field(..., gt=0)  # quantity must be positive
    price: float  # price per unit at the time of order
    total: float  # total price = price * quantity

class OrderBase(BaseModel):
    user_id: str  # ID of the user placing the order
    items: List[OrderItem]  # list of products and their quantities
    total_amount: float  # sum of all item totals
    shipping_address: str
    contact_phone: str
    status: Optional[str] = "pending"  # pending, confirmed, shipped, delivered, cancelled

class OrderCreate(OrderBase):
    pass  # all required fields are in OrderBase

class OrderUpdate(BaseModel):
    status: Optional[str]  # for updating order status
    shipping_address: Optional[str]
    contact_phone: Optional[str]

class Order(OrderBase):
    id: str
    created_at: datetime
    updated_at: datetime



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
    gst: float
    unit: Optional[str]
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
    gst: Optional[float]
    unit: Optional[str]
    region: Optional[str]
    sku: Optional[str]
    stock: Optional[int]
    category: Optional[str]
    subcategory: Optional[str]  # NEW FIELD
    images: Optional[List[HttpUrl]] = Field(None, max_items=4)


class Product(ProductBase):
    id: str
    stock: int
    vendor_id: Optional[str] = None
    images: List[HttpUrl] = []
    created_at: datetime
    updated_at: datetime


from pydantic import BaseModel, Field, HttpUrl
from typing import List, Optional
from datetime import datetime

# ---------------- PRODUCT IN ORDER ---------------- #
class OrderItem(BaseModel):
    product_id: str
    name: str
    unit_price: float
    quantity: int = Field(..., gt=0)
    subtotal: float  # unit_price * quantity

# ---------------- PAYMENT BREAKDOWN ---------------- #
class PaymentBreakdown(BaseModel):
    product_total: float = Field(..., ge=0)
    gst_total: float = Field(..., ge=0)
    delivery_charge: float = Field(..., ge=0)
    handling_fee: float = Field(..., ge=0)
    discount_amount: Optional[float] = Field(0, ge=0)
    final_amount: float = Field(..., ge=0)

# ---------------- PAYMENT ---------------- #
class Payment(BaseModel):
    payment_method: str  # "card", "upi", "wallet", "cod"
    status: str = "pending"  # pending, completed, failed
    breakdown: PaymentBreakdown

# ---------------- ORDER ---------------- #
class OrderBase(BaseModel):
    user_id: str
    items: List[OrderItem]
    delivery_address: str
    contact_phone: str
    vendor_id: Optional[str] = None

class OrderCreate(OrderBase):
    payment_method: str  # used to initialize Payment

class Order(OrderBase):
    id: str
    created_at: datetime
    updated_at: datetime
    payment: Payment
    status: str = "pending"  # pending, confirmed, shipped, delivered, canceled


# --- CART MODELS (add near your other models imports) ---

class CartItemIn(BaseModel):
    product_id: str
    quantity: int = Field(..., gt=0)

class CartQtyUpdate(BaseModel):
    quantity: int = Field(..., gt=0)

class CartCheckoutRequest(BaseModel):
    delivery_address: str
    contact_phone: str
    payment_method: str  # "card", "upi", "wallet", "cod"
