# models/designation.py

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum


class DesignationLevel(str, Enum):
    """Hierarchy level of designation"""
    EXECUTIVE = "executive"  # CEO, CTO, CFO
    CHIEF = "chief"  # Chief Editor
    SENIOR = "senior"  # Regional Editor, Senior Staff Editor
    MID = "mid"  # Staff Editor
    JUNIOR = "junior"  # Junior Editor, Reporter


class AuthorDesignation(BaseModel):
    """Author designation with grievance role mapping"""
    name: str = Field(..., description="Designation name")
    level: DesignationLevel = Field(..., description="Hierarchy level")
    can_handle_grievances: bool = Field(default=False, description="Can be assigned grievances")
    auto_assign_grievances: bool = Field(default=False, description="Auto-assign grievances to this designation")
    display_order: int = Field(default=100, description="Display order in dropdowns")
    is_active: bool = Field(default=True)
    description: Optional[str] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "name": "Chief Editor",
                "level": "chief",
                "can_handle_grievances": True,
                "auto_assign_grievances": True,
                "display_order": 1,
                "description": "Chief Editor oversees all editorial content"
            }
        }


class DesignationResponse(BaseModel):
    """Response model for designation"""
    id: str
    name: str
    level: str
    can_handle_grievances: bool
    auto_assign_grievances: bool
    display_order: int
    is_active: bool
    description: Optional[str] = None
    created_at: Optional[datetime] = None
    created_by: Optional[str] = None


# Predefined designations with grievance role mapping
DEFAULT_DESIGNATIONS = [
    {
        "name": "Chief Editor",
        "level": DesignationLevel.CHIEF,
        "can_handle_grievances": True,
        "auto_assign_grievances": True,
        "display_order": 1,
        "description": "Chief Editor - Overall editorial responsibility",
        "is_active": True
    },
    {
        "name": "Regional Editor",
        "level": DesignationLevel.SENIOR,
        "can_handle_grievances": True,
        "auto_assign_grievances": True,
        "display_order": 2,
        "description": "Regional Editor - Manages regional content and grievances",
        "is_active": True
    },
    {
        "name": "Staff Editor",
        "level": DesignationLevel.MID,
        "can_handle_grievances": True,
        "auto_assign_grievances": False,
        "display_order": 3,
        "description": "Staff Editor - Regular editorial duties",
        "is_active": True
    },
    {
        "name": "Senior Staff Editor",
        "level": DesignationLevel.SENIOR,
        "can_handle_grievances": True,
        "auto_assign_grievances": True,
        "display_order": 4,
        "description": "Senior Staff Editor - Senior editorial position",
        "is_active": True
    },
    {
        "name": "CEO",
        "level": DesignationLevel.EXECUTIVE,
        "can_handle_grievances": True,
        "auto_assign_grievances": False,
        "display_order": 5,
        "description": "Chief Executive Officer",
        "is_active": True
    },
    {
        "name": "CTO",
        "level": DesignationLevel.EXECUTIVE,
        "can_handle_grievances": False,
        "auto_assign_grievances": False,
        "display_order": 6,
        "description": "Chief Technology Officer",
        "is_active": True
    },
    {
        "name": "CFO",
        "level": DesignationLevel.EXECUTIVE,
        "can_handle_grievances": False,
        "auto_assign_grievances": False,
        "display_order": 7,
        "description": "Chief Financial Officer",
        "is_active": True
    },
    {
        "name": "Managing Editor",
        "level": DesignationLevel.CHIEF,
        "can_handle_grievances": True,
        "auto_assign_grievances": True,
        "display_order": 8,
        "description": "Managing Editor - Day-to-day editorial management",
        "is_active": True
    },
    {
        "name": "Associate Editor",
        "level": DesignationLevel.MID,
        "can_handle_grievances": True,
        "auto_assign_grievances": False,
        "display_order": 9,
        "description": "Associate Editor - Mid-level editorial position",
        "is_active": True
    },
    {
        "name": "Assistant Editor",
        "level": DesignationLevel.JUNIOR,
        "can_handle_grievances": False,
        "auto_assign_grievances": False,
        "display_order": 10,
        "description": "Assistant Editor - Entry-level editorial position",
        "is_active": True
    },
    {
        "name": "Copy Editor",
        "level": DesignationLevel.MID,
        "can_handle_grievances": False,
        "auto_assign_grievances": False,
        "display_order": 11,
        "description": "Copy Editor - Content review and editing",
        "is_active": True
    },
    {
        "name": "Reporter",
        "level": DesignationLevel.JUNIOR,
        "can_handle_grievances": False,
        "auto_assign_grievances": False,
        "display_order": 12,
        "description": "Reporter - Field reporting",
        "is_active": True
    },
    {
        "name": "Senior Reporter",
        "level": DesignationLevel.MID,
        "can_handle_grievances": False,
        "auto_assign_grievances": False,
        "display_order": 13,
        "description": "Senior Reporter - Experienced field reporting",
        "is_active": True
    },
    {
        "name": "Contributor",
        "level": DesignationLevel.JUNIOR,
        "can_handle_grievances": False,
        "auto_assign_grievances": False,
        "display_order": 14,
        "description": "Contributor - External content contributor",
        "is_active": True
    },
    {
        "name": "Correspondent",
        "level": DesignationLevel.MID,
        "can_handle_grievances": False,
        "auto_assign_grievances": False,
        "display_order": 15,
        "description": "Correspondent - Special assignment coverage",
        "is_active": True
    }
]
