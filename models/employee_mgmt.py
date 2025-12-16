from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional, List
from datetime import datetime, date
from enum import Enum


class EquipmentType(str, Enum):
    """Equipment types that can be allotted to employees"""
    CAMERA = "Camera"
    MIC = "Mic"
    STICKER = "Sticker"
    EYECARD = "Eyecard"


class EmploymentArea(str, Enum):
    """Employment area types"""
    GROUND = "ground"
    REMOTE = "remote"
    OFFICE = "office"


class EmployeeBase(BaseModel):
    """Base employee model with common fields"""
    name: str = Field(..., min_length=2, max_length=100)
    fathers_name: str = Field(..., min_length=2, max_length=100)
    mothers_name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    phone_number: str = Field(..., pattern=r'^\+?[0-9]{10,15}$')
    district: str = Field(..., min_length=2, max_length=100)
    village: str = Field(..., min_length=2, max_length=100)
    pincode: str = Field(..., pattern=r'^[0-9]{6}$')
    address: str = Field(..., min_length=10, max_length=500)
    aadhar_number: str = Field(..., pattern=r'^[0-9]{12}$')
    position: str = Field(..., min_length=2, max_length=100)
    employment_area_type: EmploymentArea
    employment_area_location: Optional[str] = Field(None, max_length=200)  # Specific place if ground
    employment_date: date
    equipment_alloted: List[EquipmentType] = Field(default_factory=list)

    @validator('phone_number')
    def validate_phone(cls, v):
        # Remove spaces and special characters
        cleaned = ''.join(filter(str.isdigit, v))
        if len(cleaned) < 10:
            raise ValueError('Phone number must be at least 10 digits')
        return v

    @validator('employment_area_location')
    def validate_location(cls, v, values):
        # If ground deployment, location is required
        if 'employment_area_type' in values and values['employment_area_type'] == EmploymentArea.GROUND:
            if not v:
                raise ValueError('Location is required for ground deployment')
        return v


class CreateEmployeeRequest(EmployeeBase):
    """Request model for creating employee"""
    pass


class UpdateEmployeeRequest(BaseModel):
    """Request model for updating employee"""
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    fathers_name: Optional[str] = Field(None, min_length=2, max_length=100)
    mothers_name: Optional[str] = Field(None, min_length=2, max_length=100)
    email: Optional[EmailStr] = None
    phone_number: Optional[str] = Field(None, pattern=r'^\+?[0-9]{10,15}$')
    district: Optional[str] = Field(None, min_length=2, max_length=100)
    village: Optional[str] = Field(None, min_length=2, max_length=100)
    pincode: Optional[str] = Field(None, pattern=r'^[0-9]{6}$')
    address: Optional[str] = Field(None, min_length=10, max_length=500)
    aadhar_number: Optional[str] = Field(None, pattern=r'^[0-9]{12}$')
    position: Optional[str] = Field(None, min_length=2, max_length=100)
    employment_area_type: Optional[EmploymentArea] = None
    employment_area_location: Optional[str] = Field(None, max_length=200)
    employment_date: Optional[date] = None
    date_of_leaving: Optional[date] = None
    equipment_alloted: Optional[List[EquipmentType]] = None


class EmployeeResponse(EmployeeBase):
    """Response model for employee"""
    id: str = Field(..., alias="_id")
    employee_id: str  # Unique generated ID like "GTNE-2024-001"
    resume_url: Optional[str] = None
    passport_photo_url: Optional[str] = None
    aadhar_front_url: Optional[str] = None
    aadhar_back_url: Optional[str] = None
    date_of_leaving: Optional[date] = None
    qr_code_url: Optional[str] = None
    is_active: bool = True
    created_at: datetime
    updated_at: datetime
    created_by: str

    class Config:
        populate_by_name = True


class EmployeeListResponse(BaseModel):
    """Response model for employee list with pagination"""
    employees: List[EmployeeResponse]
    total: int
    page: int
    limit: int
    total_pages: int


class EmployeeSearchRequest(BaseModel):
    """Search/filter request for employees"""
    name: Optional[str] = None
    employee_id: Optional[str] = None
    email: Optional[EmailStr] = None
    phone_number: Optional[str] = None
    district: Optional[str] = None
    position: Optional[str] = None
    employment_area_type: Optional[EmploymentArea] = None
    is_active: Optional[bool] = None


class QRCodeGenerateRequest(BaseModel):
    """Request to generate QR code for employee"""
    employee_id: str
    include_photo: bool = Field(default=True)


class QRCodeResponse(BaseModel):
    """Response with QR code data"""
    employee_id: str
    qr_code_url: str
    qr_code_data: str  # JSON string of employee data
    generated_at: datetime
