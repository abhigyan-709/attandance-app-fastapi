from pydantic import BaseModel, EmailStr, validator, FilePath, Field
from typing import Optional
from datetime import datetime

class Employees(BaseModel):
    username: str = Field(..., description="Unique username of the employee")
    password: str = Field(..., min_length=6, description="Password with at least 6 characters")
    first_name: str
    last_name: str
    mobile_number: str  # 10-digit validation handled below
    personal_email: EmailStr
    official_email: Optional[EmailStr] = None
    designation: str
    department: str
    employment_type: str  # Full-Time, Part-Time, Contract, Intern
    date_of_joining: datetime
    date_of_birth: datetime
    city: str
    state: str
    country: str
    aadhar_number: str  # 12-digit validation handled below
    pan_number: str  # PAN format validation handled below
    current_ctc: float
    previous_ctc: Optional[float] = None
    previous_employer: Optional[str] = None
    experience_years: Optional[int] = 0  # Default to 0 if fresher
    reporting_manager: Optional[str] = None
    emergency_contact: Optional[str] = None
    address: Optional[str] = None

    # File Upload Fields (Use FilePath for validation)
    photo: Optional[FilePath] = None
    aadhar_upload: Optional[FilePath] = None
    pan_upload: Optional[FilePath] = None
    previous_payslip_upload: Optional[FilePath] = None
    cv_upload: Optional[FilePath] = None

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Validators
    @validator("mobile_number")
    def validate_mobile(cls, value):
        if not value.isdigit() or len(value) != 10:
            raise ValueError("Mobile number must be exactly 10 digits")
        return value

    @validator("aadhar_number")
    def validate_aadhar(cls, value):
        if not value.isdigit() or len(value) != 12:
            raise ValueError("Aadhar number must be exactly 12 digits")
        return value

    @validator("pan_number")
    def validate_pan(cls, value):
        import re
        pattern = r"^[A-Z]{5}[0-9]{4}[A-Z]{1}$"
        if not re.match(pattern, value):
            raise ValueError("PAN number must be in the format ABCDE1234F")
        return value

    @validator("emergency_contact", pre=True, always=True)
    def validate_emergency_contact(cls, value):
        if value and (not value.isdigit() or len(value) != 10):
            raise ValueError("Emergency contact must be exactly 10 digits")
        return value

    @validator("updated_at", pre=True, always=True)
    def update_timestamp(cls, value):
        return datetime.utcnow()

