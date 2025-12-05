# models/govt_jobs.py
"""
Government Jobs Listing System Models
Complete models for job listings, search, scraping, and analytics
"""
from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime, date
from enum import Enum


# ==================== Enums ====================

class JobType(str, Enum):
    CENTRAL = "Central Government"
    STATE = "State Government"
    PSU = "PSU"
    AUTONOMOUS = "Autonomous Body"


class JobCategory(str, Enum):
    ENGINEERING = "Engineering"
    BANKING = "Banking"
    TEACHING = "Teaching"
    POLICE = "Police"
    RAILWAY = "Railway"
    DEFENSE = "Defense"
    MEDICAL = "Medical"
    ADMINISTRATIVE = "Administrative"
    LEGAL = "Legal"
    SCIENTIFIC = "Scientific Research"
    TECHNICAL = "Technical"
    CLERICAL = "Clerical"
    OTHER = "Other"


class JobStatus(str, Enum):
    ACTIVE = "Active"
    CLOSED = "Closed"
    UPCOMING = "Upcoming"
    CANCELLED = "Cancelled"
    RESULT_PUBLISHED = "Result Published"
    ON_HOLD = "On Hold"


class ApplicationMode(str, Enum):
    ONLINE = "Online Only"
    OFFLINE = "Offline Only"
    BOTH = "Online & Offline"


# ==================== Main Job Model ====================

class GovtJobCreate(BaseModel):
    """Model for creating a new government job"""
    # Basic Information
    title: str = Field(..., min_length=10, max_length=300, description="Job title")
    slug: Optional[str] = Field(None, max_length=200, description="Custom URL slug (auto-generated if not provided)")
    short_description: str = Field(..., min_length=50, max_length=500, description="Brief summary")
    full_description: str = Field(..., min_length=100, description="Complete HTML content with all details")
    
    # Organization
    organization_name: str = Field(..., min_length=3, max_length=200)
    organization_short_name: str = Field(..., max_length=50)
    department: Optional[str] = Field(None, max_length=200)
    logo_url: Optional[str] = None
    
    # Classification
    job_type: JobType
    state: Optional[str] = Field(None, max_length=100, description="For state government jobs")
    category: JobCategory
    sub_category: Optional[str] = Field(None, max_length=100)
    
    # Post Details
    post_name: str = Field(..., min_length=3, max_length=200, description="Official designation")
    total_vacancies: int = Field(..., gt=0, description="Total number of vacancies")
    vacancy_breakup: Optional[Dict[str, int]] = Field(None, description="Category-wise breakup")
    
    # Eligibility
    qualification: str = Field(..., min_length=5, max_length=500)
    qualification_details: Optional[str] = None
    age_limit_min: Optional[int] = Field(None, ge=18, le=100)
    age_limit_max: Optional[int] = Field(None, ge=18, le=100)
    age_limit_text: str = Field(..., max_length=200)
    age_relaxation: Optional[str] = None
    
    # Salary
    salary_min: Optional[int] = Field(None, ge=0)
    salary_max: Optional[int] = Field(None, ge=0)
    salary_text: str = Field(..., max_length=300)
    pay_scale: Optional[str] = Field(None, max_length=100)
    allowances: Optional[str] = None
    
    # Location
    work_locations: List[str] = Field(..., min_items=1)
    posting_preference: Optional[str] = None
    
    # Important Dates
    notification_date: date
    application_begin_date: date
    application_end_date: date
    last_date_fee_payment: Optional[date] = None
    exam_date: Optional[date] = None
    admit_card_date: Optional[date] = None
    result_date: Optional[date] = None
    
    # Application Process
    application_mode: ApplicationMode
    how_to_apply: str = Field(..., min_length=50)
    
    # Fees
    application_fee_general: int = Field(..., ge=0)
    application_fee_obc: Optional[int] = Field(None, ge=0)
    application_fee_sc_st: Optional[int] = Field(0, ge=0)
    application_fee_female: Optional[int] = Field(None, ge=0)
    application_fee_pwd: Optional[int] = Field(0, ge=0)
    fee_payment_mode: Optional[str] = None
    
    # Official Links
    apply_link: str = Field(..., description="Direct apply URL")
    official_notification_url: str = Field(..., description="PDF notification link")
    official_website: str
    
    # Additional Resources
    syllabus_url: Optional[str] = None
    previous_papers_url: Optional[str] = None
    admit_card_url: Optional[str] = None
    result_url: Optional[str] = None
    answer_key_url: Optional[str] = None
    additional_links: Optional[Dict[str, str]] = None
    
    # Selection Process
    selection_process: str = Field(..., min_length=10)
    exam_pattern: Optional[str] = None
    exam_duration: Optional[str] = None
    exam_mode: Optional[str] = None
    negative_marking: Optional[str] = None
    
    # Important Instructions
    important_instructions: Optional[str] = None
    special_notes: Optional[str] = None
    
    # SEO & Discoverability
    meta_title: Optional[str] = Field(None, max_length=100)
    meta_description: Optional[str] = Field(None, max_length=200)
    tags: List[str] = Field(default_factory=list)
    search_keywords: str = Field(..., description="Comma-separated keywords")
    
    # Status & Display
    status: JobStatus = JobStatus.ACTIVE
    is_featured: bool = False
    is_urgent: bool = False
    
    # Scraping Metadata
    source_url: Optional[str] = None
    scraping_enabled: bool = False
    scraping_config: Optional[Dict[str, Any]] = None
    
    @validator('slug', pre=True, always=True)
    def generate_slug(cls, v, values):
        """Auto-generate slug from title if not provided"""
        if v:
            return v
        if 'title' in values:
            import re
            slug = values['title'].lower()
            slug = re.sub(r'[^a-z0-9\s-]', '', slug)
            slug = re.sub(r'[\s]+', '-', slug)
            return slug[:200]
        return None
    
    @validator('application_end_date')
    def validate_end_date(cls, v, values):
        """Ensure end date is after begin date"""
        if 'application_begin_date' in values and v < values['application_begin_date']:
            raise ValueError('Application end date must be after begin date')
        return v
    
    @validator('salary_max')
    def validate_salary_range(cls, v, values):
        """Ensure max salary is greater than min"""
        if v and 'salary_min' in values and values['salary_min']:
            if v < values['salary_min']:
                raise ValueError('Maximum salary must be greater than minimum salary')
        return v


class GovtJobUpdate(BaseModel):
    """Model for updating an existing job"""
    title: Optional[str] = Field(None, min_length=10, max_length=300)
    slug: Optional[str] = Field(None, max_length=200)
    short_description: Optional[str] = Field(None, min_length=50, max_length=500)
    full_description: Optional[str] = Field(None, min_length=100)
    organization_name: Optional[str] = None
    organization_short_name: Optional[str] = None
    department: Optional[str] = None
    logo_url: Optional[str] = None
    job_type: Optional[JobType] = None
    state: Optional[str] = None
    category: Optional[JobCategory] = None
    sub_category: Optional[str] = None
    post_name: Optional[str] = None
    total_vacancies: Optional[int] = None
    vacancy_breakup: Optional[Dict[str, int]] = None
    qualification: Optional[str] = None
    qualification_details: Optional[str] = None
    age_limit_min: Optional[int] = None
    age_limit_max: Optional[int] = None
    age_limit_text: Optional[str] = None
    age_relaxation: Optional[str] = None
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    salary_text: Optional[str] = None
    pay_scale: Optional[str] = None
    allowances: Optional[str] = None
    work_locations: Optional[List[str]] = None
    posting_preference: Optional[str] = None
    notification_date: Optional[date] = None
    application_begin_date: Optional[date] = None
    application_end_date: Optional[date] = None
    last_date_fee_payment: Optional[date] = None
    exam_date: Optional[date] = None
    admit_card_date: Optional[date] = None
    result_date: Optional[date] = None
    application_mode: Optional[ApplicationMode] = None
    how_to_apply: Optional[str] = None
    application_fee_general: Optional[int] = None
    application_fee_obc: Optional[int] = None
    application_fee_sc_st: Optional[int] = None
    application_fee_female: Optional[int] = None
    application_fee_pwd: Optional[int] = None
    fee_payment_mode: Optional[str] = None
    apply_link: Optional[str] = None
    official_notification_url: Optional[str] = None
    official_website: Optional[str] = None
    syllabus_url: Optional[str] = None
    previous_papers_url: Optional[str] = None
    admit_card_url: Optional[str] = None
    result_url: Optional[str] = None
    answer_key_url: Optional[str] = None
    additional_links: Optional[Dict[str, str]] = None
    selection_process: Optional[str] = None
    exam_pattern: Optional[str] = None
    exam_duration: Optional[str] = None
    exam_mode: Optional[str] = None
    negative_marking: Optional[str] = None
    important_instructions: Optional[str] = None
    special_notes: Optional[str] = None
    meta_title: Optional[str] = None
    meta_description: Optional[str] = None
    tags: Optional[List[str]] = None
    search_keywords: Optional[str] = None
    status: Optional[JobStatus] = None
    is_featured: Optional[bool] = None
    is_urgent: Optional[bool] = None
    source_url: Optional[str] = None
    scraping_enabled: Optional[bool] = None
    scraping_config: Optional[Dict[str, Any]] = None


class GovtJobResponse(BaseModel):
    """Response model for job with all fields including metadata"""
    id: str
    title: str
    slug: str
    short_description: str
    full_description: str
    organization_name: str
    organization_short_name: str
    department: Optional[str]
    logo_url: Optional[str]
    job_type: str
    state: Optional[str]
    category: str
    sub_category: Optional[str]
    post_name: str
    total_vacancies: int
    vacancy_breakup: Optional[Dict[str, int]]
    qualification: str
    qualification_details: Optional[str]
    age_limit_min: Optional[int]
    age_limit_max: Optional[int]
    age_limit_text: str
    age_relaxation: Optional[str]
    salary_min: Optional[int]
    salary_max: Optional[int]
    salary_text: str
    pay_scale: Optional[str]
    allowances: Optional[str]
    work_locations: List[str]
    posting_preference: Optional[str]
    notification_date: str
    application_begin_date: str
    application_end_date: str
    last_date_fee_payment: Optional[str]
    exam_date: Optional[str]
    admit_card_date: Optional[str]
    result_date: Optional[str]
    application_mode: str
    how_to_apply: str
    application_fee_general: int
    application_fee_obc: Optional[int]
    application_fee_sc_st: Optional[int]
    application_fee_female: Optional[int]
    application_fee_pwd: Optional[int]
    fee_payment_mode: Optional[str]
    apply_link: str
    official_notification_url: str
    official_website: str
    syllabus_url: Optional[str]
    previous_papers_url: Optional[str]
    admit_card_url: Optional[str]
    result_url: Optional[str]
    answer_key_url: Optional[str]
    additional_links: Optional[Dict[str, str]]
    selection_process: str
    exam_pattern: Optional[str]
    exam_duration: Optional[str]
    exam_mode: Optional[str]
    negative_marking: Optional[str]
    important_instructions: Optional[str]
    special_notes: Optional[str]
    meta_title: Optional[str]
    meta_description: Optional[str]
    tags: List[str]
    search_keywords: str
    status: str
    is_featured: bool
    is_urgent: bool
    is_new: bool
    views_count: int
    clicks_count: int
    source_url: Optional[str]
    last_scraped_at: Optional[str]
    scraping_enabled: bool
    created_by: str
    updated_by: Optional[str]
    created_at: str
    updated_at: str
    published_at: Optional[str]


class GovtJobListItem(BaseModel):
    """Lightweight model for job list/cards"""
    id: str
    title: str
    slug: str
    short_description: str
    organization_name: str
    organization_short_name: str
    logo_url: Optional[str]
    job_type: str
    state: Optional[str]
    category: str
    post_name: str
    total_vacancies: int
    salary_text: str
    work_locations: List[str]
    application_begin_date: str
    application_end_date: str
    apply_link: str
    status: str
    is_featured: bool
    is_urgent: bool
    is_new: bool
    views_count: int
    created_at: str


# ==================== Search & Filter Models ====================

class JobSearchRequest(BaseModel):
    """Search and filter parameters"""
    query: Optional[str] = Field(None, description="Free text search")
    job_types: Optional[List[str]] = None
    states: Optional[List[str]] = None
    categories: Optional[List[str]] = None
    organizations: Optional[List[str]] = None
    qualifications: Optional[List[str]] = None
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    status: Optional[List[str]] = None
    is_new: Optional[bool] = None
    is_featured: Optional[bool] = None
    application_open: Optional[bool] = None
    deadline_within_days: Optional[int] = None
    sort_by: str = Field("created_at", description="Sort field")
    sort_order: str = Field("desc", description="asc or desc")
    page: int = Field(1, ge=1)
    limit: int = Field(20, ge=1, le=100)


class JobSearchResponse(BaseModel):
    """Paginated search results"""
    jobs: List[GovtJobListItem]
    total: int
    page: int
    limit: int
    total_pages: int
    has_next: bool
    has_prev: bool


class JobStatsResponse(BaseModel):
    """Dashboard statistics"""
    total_active_jobs: int
    total_vacancies: int
    new_jobs_today: int
    new_jobs_week: int
    closing_soon: int
    jobs_by_category: Dict[str, int]
    jobs_by_type: Dict[str, int]
    jobs_by_state: Dict[str, int]
    top_organizations: List[Dict[str, Any]]


# ==================== Scraping Models ====================

class ScrapingSourceCreate(BaseModel):
    """Configuration for adding a scraping source"""
    source_name: str = Field(..., min_length=3, max_length=200)
    source_url: str
    source_type: str = Field(..., description="RSS Feed | HTML Scraping | API")
    scraping_frequency: str = Field("Weekly", description="Daily | Weekly | On-Demand")
    selectors: Optional[Dict[str, str]] = Field(None, description="CSS/XPath selectors for HTML scraping")
    categories: List[str] = Field(default_factory=list)
    job_types: List[str] = Field(default_factory=list)
    is_active: bool = True


class ScrapingSourceResponse(BaseModel):
    """Scraping source with metadata"""
    source_id: str
    source_name: str
    source_url: str
    source_type: str
    scraping_frequency: str
    last_scraped_at: Optional[str]
    next_scrape_at: Optional[str]
    selectors: Optional[Dict[str, str]]
    categories: List[str]
    job_types: List[str]
    is_active: bool
    scraping_status: str
    last_error: Optional[str]
    jobs_scraped_total: int
    jobs_scraped_today: int
    created_at: str
    updated_at: str


class ScrapingLogResponse(BaseModel):
    """Scraping execution log"""
    log_id: str
    source_id: str
    source_name: str
    started_at: str
    completed_at: Optional[str]
    status: str
    jobs_found: int
    jobs_created: int
    jobs_updated: int
    jobs_failed: int
    error_message: Optional[str]
    duration_seconds: Optional[float]


# ==================== Bulk Operations ====================

class BulkJobCreate(BaseModel):
    """Bulk create jobs"""
    jobs: List[GovtJobCreate] = Field(..., min_items=1, max_items=100)


class BulkStatusUpdate(BaseModel):
    """Bulk update job status"""
    job_ids: List[str] = Field(..., min_items=1)
    status: JobStatus


class BulkDeleteRequest(BaseModel):
    """Bulk delete jobs"""
    job_ids: List[str] = Field(..., min_items=1)


# ==================== Analytics Models ====================

class JobAnalytics(BaseModel):
    """Job performance analytics"""
    job_id: str
    title: str
    views_count: int
    clicks_count: int
    click_through_rate: float
    views_by_date: Dict[str, int]
    clicks_by_date: Dict[str, int]
    top_referrers: List[Dict[str, Any]]
    average_time_on_page: Optional[float]


# ==================== Response Models ====================

class SuccessResponse(BaseModel):
    """Generic success response"""
    success: bool = True
    message: str
    data: Optional[Any] = None


class ErrorResponse(BaseModel):
    """Generic error response"""
    success: bool = False
    error: str
    details: Optional[Any] = None
