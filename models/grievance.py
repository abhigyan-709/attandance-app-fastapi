# models/grievance.py

from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum


class GrievanceStatus(str, Enum):
    """Status of grievance complaint"""
    SUBMITTED = "submitted"
    UNDER_REVIEW = "under_review"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    REJECTED = "rejected"
    CLOSED = "closed"


class GrievanceCategory(str, Enum):
    """Categories of grievances"""
    FACTUAL_ERROR = "factual_error"
    DEFAMATION = "defamation"
    COPYRIGHT = "copyright"
    PRIVACY_VIOLATION = "privacy_violation"
    OFFENSIVE_CONTENT = "offensive_content"
    MISINFORMATION = "misinformation"
    OTHER = "other"


class GrievanceOfficer(BaseModel):
    """Grievance Redressal Officer details"""
    name: str = Field(..., description="Full name of the officer")
    designation: str = Field(..., description="Official designation")
    email: EmailStr = Field(..., description="Official email address")
    phone: str = Field(..., description="Contact phone number")
    address: str = Field(..., description="Official address")
    working_hours: str = Field(default="Monday to Friday, 10:00 AM - 6:00 PM IST")
    is_active: bool = Field(default=True)
    appointed_date: Optional[datetime] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "name": "Rajesh Kumar",
                "designation": "Grievance Redressal Officer",
                "email": "grievance@gobarsahitimes.com",
                "phone": "+91-9876543210",
                "address": "Gobar Sahi Times Office, Patna, Bihar - 800001",
                "working_hours": "Monday to Friday, 10:00 AM - 6:00 PM IST"
            }
        }


class SelfRegulatoryBody(BaseModel):
    """Self Regulating Body membership details"""
    body_name: str = Field(..., description="Name of the self-regulatory body")
    membership_number: Optional[str] = Field(None, description="Membership ID")
    registration_date: Optional[datetime] = None
    website_url: Optional[str] = None
    contact_email: Optional[EmailStr] = None
    is_active: bool = Field(default=True)
    
    class Config:
        json_schema_extra = {
            "example": {
                "body_name": "News Broadcasters & Digital Association (NBDA)",
                "membership_number": "NBDA-2024-12345",
                "website_url": "https://www.nbda.in",
                "contact_email": "info@nbda.in"
            }
        }


class NewsEditor(BaseModel):
    """News Editor details"""
    name: str = Field(..., description="Full name of the editor")
    designation: str = Field(..., description="Editorial designation")
    email: EmailStr = Field(..., description="Official email address")
    phone: Optional[str] = None
    bio: Optional[str] = Field(None, description="Brief biography")
    profile_image: Optional[str] = None
    is_chief_editor: bool = Field(default=False)
    is_active: bool = Field(default=True)
    appointed_date: Optional[datetime] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "name": "Dr. Priya Sharma",
                "designation": "Chief Editor",
                "email": "editor@gobarsahitimes.com",
                "phone": "+91-9876543211",
                "bio": "20+ years of journalism experience",
                "is_chief_editor": True
            }
        }


class GrievanceComplaint(BaseModel):
    """Grievance complaint submission"""
    complainant_name: str = Field(..., description="Name of the person filing complaint")
    complainant_email: EmailStr = Field(..., description="Email of complainant")
    complainant_phone: Optional[str] = None
    category: GrievanceCategory = Field(..., description="Category of grievance")
    subject: str = Field(..., min_length=10, max_length=200, description="Brief subject")
    description: str = Field(..., min_length=50, description="Detailed description")
    article_url: Optional[str] = Field(None, description="URL of the concerned article/news")
    article_id: Optional[str] = Field(None, description="ID of the concerned article")
    evidence_urls: List[str] = Field(default_factory=list, description="Supporting evidence URLs")
    preferred_resolution: Optional[str] = Field(None, description="What resolution is sought")
    
    # Internal fields (populated by system)
    complaint_id: Optional[str] = None
    status: GrievanceStatus = Field(default=GrievanceStatus.SUBMITTED)
    submitted_at: Optional[datetime] = None
    assigned_to: Optional[str] = None
    resolution_notes: Optional[str] = None
    resolved_at: Optional[datetime] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "complainant_name": "John Doe",
                "complainant_email": "john.doe@example.com",
                "complainant_phone": "+91-9876543210",
                "category": "factual_error",
                "subject": "Incorrect information about election results",
                "description": "The article published on 10th Dec contains factually incorrect election result data for Ward 5. The actual winner was Candidate A, not Candidate B as mentioned.",
                "article_url": "https://gobarsahitimes.com/news/election-results-2024",
                "preferred_resolution": "Request correction of the article with proper fact-checking"
            }
        }


class GrievanceUpdate(BaseModel):
    """Update to an existing grievance"""
    status: Optional[GrievanceStatus] = None
    assigned_to: Optional[str] = None
    resolution_notes: Optional[str] = None
    internal_notes: Optional[str] = None


class GrievanceResponse(BaseModel):
    """Response sent to complainant"""
    complaint_id: str
    complainant_name: str
    complainant_email: str
    category: str
    subject: str
    description: str
    status: str
    submitted_at: datetime
    resolved_at: Optional[datetime] = None
    resolution_notes: Optional[str] = None
    article_url: Optional[str] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "complaint_id": "GRV-2024-00001",
                "complainant_name": "John Doe",
                "complainant_email": "john.doe@example.com",
                "category": "factual_error",
                "subject": "Incorrect information",
                "description": "Details...",
                "status": "resolved",
                "submitted_at": "2024-12-11T10:30:00Z",
                "resolved_at": "2024-12-13T15:45:00Z",
                "resolution_notes": "Article corrected and clarification published"
            }
        }


class GrievanceStatistics(BaseModel):
    """Statistics for grievance dashboard"""
    total_complaints: int = 0
    pending_complaints: int = 0
    resolved_complaints: int = 0
    rejected_complaints: int = 0
    avg_resolution_time_hours: float = 0.0
    complaints_by_category: dict = Field(default_factory=dict)
    complaints_this_month: int = 0
    resolution_rate_percentage: float = 0.0
