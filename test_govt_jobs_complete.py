#!/usr/bin/env python3
"""
Complete Government Jobs API Testing Script
Tests all public and admin endpoints
"""
import requests
import json
from datetime import datetime, timedelta
from typing import Dict, Any

# Configuration
API_BASE = "https://api.projectdevops.in/govt-jobs"
ADMIN_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VybmFtZSI6ImFkbWluIiwic3ViIjoiYWRtaW4iLCJleHAiOjE3NjQ5NzE3NTl9.SN_vkQvtkJRJme14bzr9sbfypVQumXDhWKT_zpghiU0"

# Colors for terminal output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    END = '\033[0m'

# Test results
passed = 0
failed = 0
skipped = 0
test_results = []

def print_header(text: str):
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{text}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.END}\n")

def test_endpoint(name: str, method: str, endpoint: str, 
                  auth_required: bool = False, data: Dict = None,
                  expected_status: int = 200) -> tuple:
    """Test an API endpoint"""
    global passed, failed, skipped
    
    url = f"{API_BASE}{endpoint}"
    headers = {"Content-Type": "application/json"}
    
    if auth_required:
        if not ADMIN_TOKEN:
            print(f"{Colors.YELLOW}⊘ SKIPPED:{Colors.END} {name} (no admin token)")
            skipped += 1
            return (False, "No admin token", None)
        headers["Authorization"] = f"Bearer {ADMIN_TOKEN}"
    
    try:
        if method == "GET":
            response = requests.get(url, headers=headers, timeout=10)
        elif method == "POST":
            response = requests.post(url, headers=headers, json=data, timeout=10)
        elif method == "PUT":
            response = requests.put(url, headers=headers, json=data, timeout=10)
        elif method == "PATCH":
            response = requests.patch(url, headers=headers, json=data, timeout=10)
        elif method == "DELETE":
            response = requests.delete(url, headers=headers, json=data, timeout=10)
        else:
            raise ValueError(f"Unknown method: {method}")
        
        # Check status
        if response.status_code == expected_status:
            print(f"{Colors.GREEN}✓ PASSED:{Colors.END} {name} (HTTP {response.status_code})")
            passed += 1
            
            # Try to parse JSON
            try:
                json_data = response.json()
                return (True, None, json_data)
            except:
                return (True, None, response.text)
        else:
            print(f"{Colors.RED}✗ FAILED:{Colors.END} {name} (HTTP {response.status_code}, expected {expected_status})")
            print(f"  Response: {response.text[:200]}")
            failed += 1
            return (False, f"HTTP {response.status_code}", response.text[:200])
    
    except Exception as e:
        print(f"{Colors.RED}✗ ERROR:{Colors.END} {name} - {str(e)}")
        failed += 1
        return (False, str(e), None)

# Store created job for later tests
created_job_id = None
created_job_slug = None

print_header("🧪 GOVERNMENT JOBS API TESTING")
print(f"API Base: {API_BASE}")
print(f"Admin Token: {'Provided' if ADMIN_TOKEN else 'Not Provided (admin tests will be skipped)'}")

# ==================== PUBLIC ENDPOINTS ====================
print_header("📊 PUBLIC ENDPOINTS (No Authentication)")

# Dashboard stats
success, error, data = test_endpoint(
    "Get Dashboard Stats",
    "GET",
    "/stats/dashboard"
)
if success and data:
    print(f"  Active Jobs: {data.get('total_active_jobs', 0)}")
    print(f"  New Today: {data.get('new_jobs_today', 0)}")

# List jobs (default)
success, error, data = test_endpoint(
    "List Jobs (default)",
    "GET",
    "/"
)
if success and data:
    print(f"  Total Jobs: {data.get('total', 0)}")
    print(f"  Returned: {len(data.get('jobs', []))}")

# List jobs with filters
success, error, data = test_endpoint(
    "List Jobs (with status filter)",
    "GET",
    "/?status=Active&limit=10&page=1"
)

# List jobs with multiple filters
success, error, data = test_endpoint(
    "List Jobs (multiple filters)",
    "GET",
    "/?status=Active&is_new=true&sort_by=created_at&sort_order=desc"
)

# Latest jobs
success, error, data = test_endpoint(
    "Get Latest Jobs",
    "GET",
    "/latest/list?limit=5"
)
if success and data:
    print(f"  Returned: {len(data)} jobs")

# Featured jobs
success, error, data = test_endpoint(
    "Get Featured Jobs",
    "GET",
    "/featured/list?limit=5"
)
if success and data:
    print(f"  Returned: {len(data)} jobs")

# Closing soon
success, error, data = test_endpoint(
    "Get Closing Soon Jobs",
    "GET",
    "/closing-soon/list?days=7&limit=5"
)
if success and data:
    print(f"  Returned: {len(data)} jobs")

# Get categories
success, error, data = test_endpoint(
    "Get All Categories",
    "GET",
    "/filter/categories"
)
if success and data:
    print(f"  Total Categories: {data.get('total', 0)}")

# Get states
success, error, data = test_endpoint(
    "Get All States",
    "GET",
    "/filter/states"
)
if success and data:
    print(f"  Total States: {data.get('total', 0)}")

# Get organizations
success, error, data = test_endpoint(
    "Get All Organizations",
    "GET",
    "/filter/organizations"
)
if success and data:
    print(f"  Total Organizations: {data.get('total', 0)}")

# ==================== ADMIN ENDPOINTS ====================
print_header("🔐 ADMIN ENDPOINTS (Authentication Required)")

if not ADMIN_TOKEN:
    print(f"{Colors.YELLOW}⚠️  Admin token not provided. Skipping admin tests.{Colors.END}")
    print(f"{Colors.YELLOW}To test admin endpoints:{Colors.END}")
    print("1. Get JWT token: curl -X POST https://api.projectdevops.in/login \\")
    print("   -H 'Content-Type: application/json' \\")
    print("   -d '{\"username\":\"your_admin\",\"password\":\"your_password\"}'")
    print("2. Edit this script and set ADMIN_TOKEN variable")
    print("3. Run script again")
else:
    # Create a test job
    today = datetime.now().date()
    job_data = {
        "title": "Test UPSC Engineering Services 2024",
        "short_description": "Test job for API validation - Union Public Service Commission",
        "full_description": "The Union Public Service Commission (UPSC) invites applications for Engineering Services Examination 2024. This is a comprehensive test job created for API validation purposes. Candidates with B.E./B.Tech degree in relevant engineering disciplines are eligible to apply.",
        "organization_name": "Union Public Service Commission",
        "organization_short_name": "UPSC",
        "job_type": "Central Government",
        "category": "Engineering",
        "post_name": "Engineering Services",
        "total_vacancies": 234,
        "qualification": "B.E./B.Tech in Engineering",
        "age_limit_text": "21-30 years",
        "salary_text": "₹50,000 - ₹1,00,000 per month",
        "work_locations": ["All India"],
        "notification_date": today.isoformat(),
        "application_begin_date": today.isoformat(),
        "application_end_date": (today + timedelta(days=30)).isoformat(),
        "apply_link": "https://upsc.gov.in/apply",
        "notification_link": "https://upsc.gov.in/notification.pdf",
        "official_notification_url": "https://upsc.gov.in/notification.pdf",
        "official_website": "https://upsc.gov.in",
        "application_mode": "Online Only",
        "how_to_apply": "Visit official website, register, fill application form, upload documents, pay fee, and submit.",
        "application_fee_general": 200,
        "application_fee_obc": 200,
        "application_fee_sc_st": 0,
        "selection_process": "Preliminary Examination, Main Examination, and Interview",
        "search_keywords": "UPSC, Engineering Services, Central Government, Engineering",
        "status": "Active"
    }
    
    success, error, data = test_endpoint(
        "Create Job (Admin)",
        "POST",
        "/admin/create",
        auth_required=True,
        data=job_data,
        expected_status=201
    )
    
    if success and data:
        created_job_id = data.get('id')
        created_job_slug = data.get('slug')
        print(f"  Created Job ID: {created_job_id}")
        print(f"  Created Job Slug: {created_job_slug}")
        
        # Test get job by slug
        if created_job_slug:
            success, error, data = test_endpoint(
                "Get Job by Slug (Public)",
                "GET",
                f"/slug/{created_job_slug}?increment_view=false"
            )
            if success and data:
                print(f"  Job Title: {data.get('title')}")
                print(f"  Views: {data.get('views_count', 0)}")
        
        # Test get job by ID
        if created_job_id:
            success, error, data = test_endpoint(
                "Get Job by ID (Public)",
                "GET",
                f"/{created_job_id}?increment_view=false"
            )
        
        # Test update job
        if created_job_id:
            update_data = {
                "short_description": "Updated test description",
                "is_featured": True
            }
            success, error, data = test_endpoint(
                "Update Job (Admin)",
                "PUT",
                f"/admin/{created_job_id}",
                auth_required=True,
                data=update_data
            )
            if success and data:
                print(f"  Featured: {data.get('is_featured')}")
        
        # Test update status
        if created_job_id:
            success, error, data = test_endpoint(
                "Update Job Status (Admin)",
                "PATCH",
                f"/admin/{created_job_id}/status?new_status=Active",
                auth_required=True
            )
        
        # Test toggle featured
        if created_job_id:
            success, error, data = test_endpoint(
                "Toggle Featured (Admin)",
                "PATCH",
                f"/admin/{created_job_id}/feature?is_featured=true",
                auth_required=True
            )
        
        # Test check slug availability
        success, error, data = test_endpoint(
            "Check Slug Availability (Admin)",
            "GET",
            "/admin/check-slug/test-unique-slug-123",
            auth_required=True
        )
        if success and data:
            print(f"  Slug Available: {data.get('available')}")
        
        # Test track click
        if created_job_id:
            success, error, data = test_endpoint(
                "Track Apply Click (Public)",
                "POST",
                f"/{created_job_id}/click"
            )
    
    # Test get all jobs (admin)
    success, error, data = test_endpoint(
        "Get All Jobs Admin View",
        "GET",
        "/admin/all?page=1&limit=10",
        auth_required=True
    )
    if success and data:
        print(f"  Total Jobs: {data.get('total', 0)}")
        print(f"  Returned: {len(data.get('jobs', []))}")
    
    # Test bulk operations
    if created_job_id:
        # Test bulk status update
        bulk_status_data = {
            "job_ids": [created_job_id],
            "status": "Active"
        }
        success, error, data = test_endpoint(
            "Bulk Update Status (Admin)",
            "POST",
            "/admin/bulk-update-status",
            auth_required=True,
            data=bulk_status_data
        )
        if success and data:
            print(f"  Modified: {data.get('modified_count', 0)} jobs")
    
    # Test category page (public)
    success, error, data = test_endpoint(
        "Get Jobs by Category (Public)",
        "GET",
        "/category/Engineering?page=1&limit=5"
    )
    if success and data:
        print(f"  Total in Category: {data.get('total', 0)}")
    
    # Clean up - delete test job
    if created_job_id:
        success, error, data = test_endpoint(
            "Delete Job (Admin)",
            "DELETE",
            f"/admin/{created_job_id}",
            auth_required=True
        )
        if success:
            print(f"  Test job cleaned up successfully")

# ==================== RESULTS ====================
print_header("📈 TEST RESULTS")

total = passed + failed + skipped
print(f"{Colors.GREEN}Passed:  {passed}{Colors.END}")
print(f"{Colors.RED}Failed:  {failed}{Colors.END}")
print(f"{Colors.YELLOW}Skipped: {skipped}{Colors.END}")
print(f"{Colors.BOLD}Total:   {total}{Colors.END}")

if failed == 0 and passed > 0:
    print(f"\n{Colors.GREEN}{Colors.BOLD}✅ ALL TESTS PASSED!{Colors.END}")
    print(f"\n{Colors.GREEN}🎉 Government Jobs API is working correctly!{Colors.END}")
    print(f"\n{Colors.BOLD}Next Steps:{Colors.END}")
    print("1. ✅ API endpoints working")
    print("2. Create sample jobs via Swagger UI: https://api.projectdevops.in/docs")
    print("3. Test with real data")
    print("4. Start frontend development using GOVT_JOBS_UI_GUIDE.md")
    exit(0)
elif passed > 0:
    print(f"\n{Colors.YELLOW}⚠️  Some tests failed. Please check the errors above.{Colors.END}")
    exit(1)
else:
    print(f"\n{Colors.RED}❌ All tests failed. API may not be deployed correctly.{Colors.END}")
    print(f"\n{Colors.BOLD}Troubleshooting:{Colors.END}")
    print("1. Check if server is running: curl https://api.projectdevops.in/docs")
    print("2. Verify MongoDB connection")
    print("3. Check server logs for errors")
    print("4. Ensure routes are registered in main.py")
    exit(1)
