from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Optional, List

class Employees(BaseModel):
    username: str
    password: str
    employee_id: str
    first_name: str
    last_name: str
    mobile_number: str
    email: EmailStr
    official_email: Optional[EmailStr] = None
    designation: str
    employment_type: str # ft, pt, contract, intern, intern-with ppo
    dob: datetime.date
    aadhar: str
    pan: str
    experience: Optional[float] = None
    previous_ctc: Optional[float] = None
    current_ctc: Optional[float] = None
    fathers_name: str
    monther_name: str
    college: str
    city: str
    pin: str
    state: str
    emergency_contact: str
    blood_group: str
    is_active: bool = False
    date_of_joining: datetime.utcnow
    date_of_leaving: Optional[datetime] = None
    skills: Optional[List[str]] = []
    projects: Optional[List[str]] = []
    manager_id: Optional[str] = None
    department: str
    address: str
    bank_account_number: str
    ifsc_code: str
    pf_account_number: Optional[str] = None
    esi_account_number: Optional[str] = None

    class Config:
        orm_mode = True


