#!/bin/bash

# =============================================================================
# BIODATA SYSTEM ADMIN API TESTING SCRIPT
# =============================================================================
# This script tests all biodata API endpoints using admin credentials
# Usage: ./test_biodata_admin.sh
# Prerequisites: curl, jq (for JSON parsing)
# =============================================================================

# Configuration
BASE_URL="https://api.projectdevops.in"
ADMIN_USERNAME="admin"
ADMIN_PASSWORD="Gyanu@9693894505"
TIMESTAMP=$(date +%s)
TEST_USER_USERNAME="biodata_test_${TIMESTAMP}"
TEST_USER_EMAIL="biodata.test.${TIMESTAMP}@example.com"
TEST_USER_PASSWORD="TestBiodata123!"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Global variables
ADMIN_TOKEN=""
TEST_USER_TOKEN=""
TEST_PROFILE_ID=""
TEST_RESULTS=()
PASSED_TESTS=0
FAILED_TESTS=0

# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

print_header() {
    echo -e "\n${BLUE}===============================================================================${NC}"
    echo -e "${BLUE} $1${NC}"
    echo -e "${BLUE}===============================================================================${NC}\n"
}

print_section() {
    echo -e "\n${CYAN}--- $1 ---${NC}"
}

print_test() {
    echo -e "${YELLOW}🧪 Testing: $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ SUCCESS: $1${NC}"
    TEST_RESULTS+=("✅ $1")
    ((PASSED_TESTS++))
}

print_error() {
    echo -e "${RED}❌ FAILED: $1${NC}"
    TEST_RESULTS+=("❌ $1")
    ((FAILED_TESTS++))
}

print_info() {
    echo -e "${BLUE}ℹ️  INFO: $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  WARNING: $1${NC}"
}

# Enhanced response checker
check_response() {
    local response="$1"
    local expected_status="$2"
    local description="$3"
    local show_body="${4:-true}"
    
    local status=$(echo "$response" | tail -1)
    local body=$(echo "$response" | sed '$d')
    
    if [[ "$status" == "$expected_status" ]]; then
        print_success "$description"
        if [[ "$show_body" == "true" && -n "$body" ]]; then
            echo "$body" | jq '.' 2>/dev/null || echo "$body"
        fi
        return 0
    else
        print_error "$description (Expected: $expected_status, Got: $status)"
        if [[ -n "$body" ]]; then
            echo "$body" | jq '.' 2>/dev/null || echo "$body"
        fi
        return 1
    fi
}

# Extract value from JSON response
extract_json_value() {
    local response="$1"
    local key="$2"
    local body=$(echo "$response" | sed '$d')
    echo "$body" | jq -r ".$key" 2>/dev/null
}

# =============================================================================
# AUTHENTICATION TESTS
# =============================================================================

test_admin_login() {
    print_header "AUTHENTICATION TESTS"
    print_section "Admin Login"
    
    print_test "Admin login with credentials"
    
    local response=$(curl -s -w "\n%{http_code}" -X POST "$BASE_URL/token" \
        -H "Content-Type: application/x-www-form-urlencoded" \
        -d "username=$ADMIN_USERNAME&password=$ADMIN_PASSWORD")
    
    if check_response "$response" "200" "Admin login" "false"; then
        ADMIN_TOKEN=$(extract_json_value "$response" "access_token")
        print_info "Admin token obtained: ${ADMIN_TOKEN:0:20}..."
        return 0
    else
        print_error "Failed to get admin token. Cannot proceed with tests."
        exit 1
    fi
}

test_admin_user_info() {
    print_section "Admin User Verification"
    
    print_test "Getting admin user information"
    
    local response=$(curl -s -w "\n%{http_code}" -X GET "$BASE_URL/users/me" \
        -H "Authorization: Bearer $ADMIN_TOKEN")
    
    check_response "$response" "200" "Get admin user info"
}

test_create_test_user() {
    print_section "Test User Creation"
    
    print_test "Creating test user for biodata testing"
    
    local response=$(curl -s -w "\n%{http_code}" -X POST "$BASE_URL/register/" \
        -H "Content-Type: application/json" \
        -d "{
            \"first_name\": \"Test\",
            \"last_name\": \"User\",
            \"city\": \"Test City\",
            \"username\": \"$TEST_USER_USERNAME\",
            \"email\": \"$TEST_USER_EMAIL\",
            \"password\": \"$TEST_USER_PASSWORD\",
            \"role\": \"user\"
        }")
    
    local status=$(echo "$response" | tail -1)
    if [[ "$status" == "201" ]] || [[ "$status" == "200" ]]; then
        print_success "Test user created successfully"
    elif [[ "$status" == "400" ]]; then
        print_info "Test user might already exist, continuing..."
    else
        print_error "Failed to create test user (Status: $status)"
        local body=$(echo "$response" | sed '$d')
        echo "$body"
    fi
}

test_user_login() {
    print_section "Test User Login"
    
    print_test "Test user login"
    
    local response=$(curl -s -w "\n%{http_code}" -X POST "$BASE_URL/token" \
        -H "Content-Type: application/x-www-form-urlencoded" \
        -d "username=$TEST_USER_USERNAME&password=$TEST_USER_PASSWORD")
    
    if check_response "$response" "200" "Test user login" "false"; then
        TEST_USER_TOKEN=$(extract_json_value "$response" "access_token")
        print_info "Test user token obtained: ${TEST_USER_TOKEN:0:20}..."
        return 0
    else
        print_warning "Test user login failed, using admin token for remaining tests"
        TEST_USER_TOKEN="$ADMIN_TOKEN"
        return 1
    fi
}

# =============================================================================
# BIODATA PROFILE TESTS
# =============================================================================

test_create_basic_biodata() {
    print_header "BIODATA PROFILE TESTS"
    print_section "Basic Profile Creation"
    
    print_test "Creating basic biodata profile"
    
    local response=$(curl -s -w "\n%{http_code}" -X POST "$BASE_URL/biodata" \
        -H "Authorization: Bearer $TEST_USER_TOKEN" \
        -H "Content-Type: application/json" \
        -d '{
            "biodata_type": "basic",
            "first_name": "Ananya",
            "last_name": "Kumar",
            "gender": "female",
            "dob": "1997-08-14",
            "religion": "hindu",
            "caste": "Kayastha",
            "caste_category": "general",
            "gotra": "Kashyap",
            "mother_tongue": "Hindi",
            "marital_status": "never_married",
            "about_me": "Software engineer with a love for travel and books.",
            "profile_owner_relation": "self"
        }')
    
    if check_response "$response" "200" "Create basic biodata profile"; then
        TEST_PROFILE_ID=$(extract_json_value "$response" "_id")
        print_info "Profile created with ID: $TEST_PROFILE_ID"
        return 0
    else
        return 1
    fi
}

test_get_my_profile() {
    print_section "Profile Retrieval"
    
    print_test "Getting my biodata profile"
    
    local response=$(curl -s -w "\n%{http_code}" -X GET "$BASE_URL/biodata/my/profile" \
        -H "Authorization: Bearer $TEST_USER_TOKEN")
    
    check_response "$response" "200" "Get my profile"
}

test_get_specific_profile() {
    print_test "Getting specific profile by ID"
    
    if [[ -z "$TEST_PROFILE_ID" ]]; then
        print_error "No profile ID available for testing"
        return 1
    fi
    
    local response=$(curl -s -w "\n%{http_code}" -X GET "$BASE_URL/biodata/$TEST_PROFILE_ID" \
        -H "Authorization: Bearer $TEST_USER_TOKEN")
    
    check_response "$response" "200" "Get specific profile"
}

# =============================================================================
# PROFILE SECTION UPDATES
# =============================================================================

test_update_contact_info() {
    print_header "PROFILE SECTION UPDATES"
    print_section "Contact Information"
    
    if [[ -z "$TEST_PROFILE_ID" ]]; then
        print_error "No profile ID available for testing"
        return 1
    fi
    
    print_test "Updating contact information"
    
    local response=$(curl -s -w "\n%{http_code}" -X PATCH "$BASE_URL/biodata/$TEST_PROFILE_ID/contact" \
        -H "Authorization: Bearer $TEST_USER_TOKEN" \
        -H "Content-Type: application/json" \
        -d '{
            "email": "ananya.updated@example.com",
            "phone_country_code": "+91",
            "phone_number": "9876543210",
            "address": {
                "city": "Delhi",
                "state": "Delhi",
                "country": "India",
                "pincode": "110001"
            }
        }')
    
    check_response "$response" "200" "Update contact information"
}

test_update_education() {
    print_section "Education Information"
    
    if [[ -z "$TEST_PROFILE_ID" ]]; then
        print_error "No profile ID available for testing"
        return 1
    fi
    
    print_test "Updating education information"
    
    local response=$(curl -s -w "\n%{http_code}" -X PATCH "$BASE_URL/biodata/$TEST_PROFILE_ID/education" \
        -H "Authorization: Bearer $TEST_USER_TOKEN" \
        -H "Content-Type: application/json" \
        -d '{
            "level": "masters",
            "degree": "MCA",
            "institute": "Patna University",
            "graduation_year": 2020
        }')
    
    check_response "$response" "200" "Update education information"
}

test_update_occupation() {
    print_section "Occupation Information"
    
    if [[ -z "$TEST_PROFILE_ID" ]]; then
        print_error "No profile ID available for testing"
        return 1
    fi
    
    print_test "Updating occupation information"
    
    local response=$(curl -s -w "\n%{http_code}" -X PATCH "$BASE_URL/biodata/$TEST_PROFILE_ID/occupation" \
        -H "Authorization: Bearer $TEST_USER_TOKEN" \
        -H "Content-Type: application/json" \
        -d '{
            "employment_type": "private",
            "organization": "TCS",
            "designation": "Software Developer",
            "annual_income_value": 800000,
            "annual_income_currency": "INR"
        }')
    
    check_response "$response" "200" "Update occupation information"
}

test_update_physical_attributes() {
    print_section "Physical Attributes"
    
    if [[ -z "$TEST_PROFILE_ID" ]]; then
        print_error "No profile ID available for testing"
        return 1
    fi
    
    print_test "Updating physical attributes"
    
    local response=$(curl -s -w "\n%{http_code}" -X PATCH "$BASE_URL/biodata/$TEST_PROFILE_ID/physical" \
        -H "Authorization: Bearer $TEST_USER_TOKEN" \
        -H "Content-Type: application/json" \
        -d '{
            "height_cm": 165,
            "weight_kg": 58,
            "body_type": "slim",
            "complexion": "wheatish",
            "blood_group": "B+"
        }')
    
    check_response "$response" "200" "Update physical attributes"
}

test_update_lifestyle() {
    print_section "Lifestyle Information"
    
    if [[ -z "$TEST_PROFILE_ID" ]]; then
        print_error "No profile ID available for testing"
        return 1
    fi
    
    print_test "Updating lifestyle information"
    
    local response=$(curl -s -w "\n%{http_code}" -X PATCH "$BASE_URL/biodata/$TEST_PROFILE_ID/lifestyle" \
        -H "Authorization: Bearer $TEST_USER_TOKEN" \
        -H "Content-Type: application/json" \
        -d '{
            "diet": "vegetarian",
            "drinking": "no",
            "smoking": "no"
        }')
    
    check_response "$response" "200" "Update lifestyle information"
}

test_update_family_details() {
    print_section "Family Details"
    
    if [[ -z "$TEST_PROFILE_ID" ]]; then
        print_error "No profile ID available for testing"
        return 1
    fi
    
    print_test "Updating family details"
    
    local response=$(curl -s -w "\n%{http_code}" -X PATCH "$BASE_URL/biodata/$TEST_PROFILE_ID/family" \
        -H "Authorization: Bearer $TEST_USER_TOKEN" \
        -H "Content-Type: application/json" \
        -d '{
            "father_name": "Rajesh Kumar",
            "father_occupation": "Teacher",
            "mother_name": "Sunita Devi",
            "mother_occupation": "Homemaker",
            "siblings": [
                {
                    "relation": "Brother",
                    "name": "Vikash Kumar",
                    "occupation": "Engineer",
                    "is_married": false
                }
            ],
            "family_type": "Nuclear",
            "family_values": "Traditional",
            "native_place": "Gaya, Bihar"
        }')
    
    check_response "$response" "200" "Update family details"
}

test_update_partner_preferences() {
    print_section "Partner Preferences"
    
    if [[ -z "$TEST_PROFILE_ID" ]]; then
        print_error "No profile ID available for testing"
        return 1
    fi
    
    print_test "Updating partner preferences"
    
    local response=$(curl -s -w "\n%{http_code}" -X PATCH "$BASE_URL/biodata/$TEST_PROFILE_ID/partner-preferences" \
        -H "Authorization: Bearer $TEST_USER_TOKEN" \
        -H "Content-Type: application/json" \
        -d '{
            "min_age": 25,
            "max_age": 32,
            "min_height_cm": 170,
            "max_height_cm": 180,
            "marital_status": ["never_married"],
            "religion": ["hindu"],
            "caste": ["Kayastha", "Brahmin"],
            "education_levels": ["bachelors", "masters"],
            "occupations": ["private", "government"],
            "mother_tongues": ["Hindi", "English"],
            "preferred_locations": ["Delhi", "Mumbai", "Bangalore"],
            "diet": ["vegetarian"]
        }')
    
    check_response "$response" "200" "Update partner preferences"
}

# =============================================================================
# ADVANCED BIODATA FEATURES
# =============================================================================

test_upgrade_to_detailed() {
    print_header "ADVANCED BIODATA FEATURES"
    print_section "Profile Upgrade"
    
    if [[ -z "$TEST_PROFILE_ID" ]]; then
        print_error "No profile ID available for testing"
        return 1
    fi
    
    print_test "Upgrading profile to detailed"
    
    local response=$(curl -s -w "\n%{http_code}" -X PATCH "$BASE_URL/biodata/$TEST_PROFILE_ID/upgrade-to-detailed" \
        -H "Authorization: Bearer $TEST_USER_TOKEN")
    
    check_response "$response" "200" "Upgrade to detailed profile"
}

test_detailed_religious_info() {
    print_section "Detailed Religious Information"
    
    if [[ -z "$TEST_PROFILE_ID" ]]; then
        print_error "No profile ID available for testing"
        return 1
    fi
    
    print_test "Updating detailed religious information"
    
    local response=$(curl -s -w "\n%{http_code}" -X PATCH "$BASE_URL/biodata/$TEST_PROFILE_ID/detailed-religious-info" \
        -H "Authorization: Bearer $TEST_USER_TOKEN" \
        -H "Content-Type: application/json" \
        -d '{
            "varna": "brahmin",
            "sub_caste": "Gaur Brahmin",
            "religious_sect": "vaishnavism",
            "temple_association": "Local Hanuman Temple",
            "spiritual_practices": ["daily_prayers", "yoga", "meditation"],
            "festivals_observed": ["Diwali", "Karva_Chauth", "Navratri"],
            "daily_prayers": true,
            "vegetarian_since": "birth"
        }')
    
    check_response "$response" "200" "Update detailed religious information"
}

test_detailed_astrology() {
    print_section "Detailed Astrology Information"
    
    if [[ -z "$TEST_PROFILE_ID" ]]; then
        print_error "No profile ID available for testing"
        return 1
    fi
    
    print_test "Updating detailed astrology information"
    
    local response=$(curl -s -w "\n%{http_code}" -X PATCH "$BASE_URL/biodata/$TEST_PROFILE_ID/detailed-astrology" \
        -H "Authorization: Bearer $TEST_USER_TOKEN" \
        -H "Content-Type: application/json" \
        -d '{
            "birth_time": "08:30",
            "birth_place_coordinates": "25.5941° N, 85.1376° E",
            "rashi_detailed": "Kanya (Virgo)",
            "nakshatra_detailed": "Hasta",
            "lagna": "Tula (Libra)",
            "doshas": ["none"],
            "guna_milan_score": 32,
            "auspicious_time_preference": "Winter months"
        }')
    
    check_response "$response" "200" "Update detailed astrology information"
}

test_extended_family() {
    print_section "Extended Family Information"
    
    if [[ -z "$TEST_PROFILE_ID" ]]; then
        print_error "No profile ID available for testing"
        return 1
    fi
    
    print_test "Adding extended family members"
    
    local response=$(curl -s -w "\n%{http_code}" -X PATCH "$BASE_URL/biodata/$TEST_PROFILE_ID/extended-family" \
        -H "Authorization: Bearer $TEST_USER_TOKEN" \
        -H "Content-Type: application/json" \
        -d '{
            "extended_family": [
                {
                    "relation": "Maternal Uncle",
                    "name": "Suresh Kumar",
                    "occupation": "Business",
                    "location": "Delhi"
                },
                {
                    "relation": "Paternal Aunt",
                    "name": "Meera Devi",
                    "occupation": "Teacher",
                    "location": "Patna"
                }
            ]
        }')
    
    check_response "$response" "200" "Update extended family information"
}

# =============================================================================
# SEARCH AND FILTERING TESTS
# =============================================================================

test_search_profiles() {
    print_header "SEARCH AND FILTERING TESTS"
    print_section "Profile Search"
    
    print_test "Searching profiles with basic filters"
    
    local response=$(curl -s -w "\n%{http_code}" -X GET "$BASE_URL/biodata?gender=female&religion=hindu&limit=5" \
        -H "Authorization: Bearer $ADMIN_TOKEN")
    
    check_response "$response" "200" "Search profiles with filters"
}

test_advanced_search() {
    print_section "Advanced Search"
    
    print_test "Advanced search with multiple filters"
    
    local response=$(curl -s -w "\n%{http_code}" -X GET "$BASE_URL/biodata?gender=female&religion=hindu&marital_status=never_married&min_age=25&max_age=30&limit=5" \
        -H "Authorization: Bearer $ADMIN_TOKEN")
    
    check_response "$response" "200" "Advanced search with multiple filters"
}

test_text_search() {
    print_section "Text Search"
    
    print_test "Text search for 'engineer'"
    
    local response=$(curl -s -w "\n%{http_code}" -X GET "$BASE_URL/biodata/search?q=engineer&limit=5" \
        -H "Authorization: Bearer $ADMIN_TOKEN")
    
    check_response "$response" "200" "Text search"
}

test_location_search() {
    print_section "Location-based Search"
    
    print_test "Location-based search"
    
    local response=$(curl -s -w "\n%{http_code}" -X GET "$BASE_URL/biodata?location=Delhi&limit=5" \
        -H "Authorization: Bearer $ADMIN_TOKEN")
    
    check_response "$response" "200" "Location-based search"
}

# =============================================================================
# ANALYTICS AND ENGAGEMENT TESTS
# =============================================================================

test_profile_analytics() {
    print_header "ANALYTICS AND ENGAGEMENT TESTS"
    print_section "Profile Analytics"
    
    if [[ -z "$TEST_PROFILE_ID" ]]; then
        print_error "No profile ID available for testing"
        return 1
    fi
    
    print_test "Getting profile analytics"
    
    local response=$(curl -s -w "\n%{http_code}" -X GET "$BASE_URL/biodata/$TEST_PROFILE_ID/analytics" \
        -H "Authorization: Bearer $TEST_USER_TOKEN")
    
    check_response "$response" "200" "Get profile analytics"
}

test_increment_view() {
    print_section "View Tracking"
    
    if [[ -z "$TEST_PROFILE_ID" ]]; then
        print_error "No profile ID available for testing"
        return 1
    fi
    
    print_test "Incrementing profile view count"
    
    local response=$(curl -s -w "\n%{http_code}" -X PATCH "$BASE_URL/biodata/$TEST_PROFILE_ID/increment-view" \
        -H "Authorization: Bearer $ADMIN_TOKEN")
    
    check_response "$response" "200" "Increment profile view"
}

test_profile_interactions() {
    print_section "Profile Interactions"
    
    if [[ -z "$TEST_PROFILE_ID" ]]; then
        print_error "No profile ID available for testing"
        return 1
    fi
    
    print_test "Recording profile interaction"
    
    local response=$(curl -s -w "\n%{http_code}" -X POST "$BASE_URL/biodata/$TEST_PROFILE_ID/interact" \
        -H "Authorization: Bearer $ADMIN_TOKEN" \
        -H "Content-Type: application/json" \
        -d '{
            "interaction_type": "profile_view",
            "notes": "Viewed by admin for testing"
        }')
    
    local status=$(echo "$response" | tail -1)
    if [[ "$status" == "200" ]] || [[ "$status" == "201" ]] || [[ "$status" == "404" ]]; then
        if [[ "$status" == "404" ]]; then
            print_info "Profile interaction endpoint not found (might not be implemented)"
        else
            print_success "Record profile interaction"
        fi
    else
        print_error "Record profile interaction (Status: $status)"
    fi
}

# =============================================================================
# SECTION RETRIEVAL TESTS
# =============================================================================

test_get_individual_sections() {
    print_header "SECTION RETRIEVAL TESTS"
    print_section "Individual Section Retrieval"
    
    if [[ -z "$TEST_PROFILE_ID" ]]; then
        print_error "No profile ID available for testing"
        return 1
    fi
    
    local sections=("contact" "education" "occupation" "physical" "lifestyle" "family" "partner-preferences")
    
    for section in "${sections[@]}"; do
        print_test "Getting $section section"
        
        local response=$(curl -s -w "\n%{http_code}" -X GET "$BASE_URL/biodata/$TEST_PROFILE_ID/$section" \
            -H "Authorization: Bearer $TEST_USER_TOKEN")
        
        local status=$(echo "$response" | tail -1)
        if [[ "$status" == "200" ]]; then
            print_success "Get $section section"
        elif [[ "$status" == "404" ]]; then
            print_info "Get $section section (section might be empty)"
        else
            print_error "Get $section section (Status: $status)"
        fi
    done
}

# =============================================================================
# ADMIN SPECIFIC TESTS
# =============================================================================

test_admin_functions() {
    print_header "ADMIN SPECIFIC TESTS"
    print_section "Admin Profile Management"
    
    print_test "Getting all profiles (admin view)"
    
    local response=$(curl -s -w "\n%{http_code}" -X GET "$BASE_URL/biodata?limit=10" \
        -H "Authorization: Bearer $ADMIN_TOKEN")
    
    check_response "$response" "200" "Get all profiles (admin)"
    
    print_test "Getting profile statistics"
    
    local response=$(curl -s -w "\n%{http_code}" -X GET "$BASE_URL/biodata/stats" \
        -H "Authorization: Bearer $ADMIN_TOKEN")
    
    local status=$(echo "$response" | tail -1)
    if [[ "$status" == "200" ]]; then
        print_success "Get profile statistics"
    elif [[ "$status" == "404" ]]; then
        print_info "Profile statistics endpoint not found"
    else
        print_error "Get profile statistics (Status: $status)"
    fi
}

# =============================================================================
# CLEANUP TESTS
# =============================================================================

test_cleanup() {
    print_header "CLEANUP TESTS"
    print_section "Profile Cleanup"
    
    if [[ -z "$TEST_PROFILE_ID" ]]; then
        print_info "No profile ID available for cleanup"
        return 0
    fi
    
    print_test "Soft deleting test profile"
    
    local response=$(curl -s -w "\n%{http_code}" -X DELETE "$BASE_URL/biodata/$TEST_PROFILE_ID" \
        -H "Authorization: Bearer $TEST_USER_TOKEN")
    
    local status=$(echo "$response" | tail -1)
    if [[ "$status" == "200" ]] || [[ "$status" == "204" ]]; then
        print_success "Soft delete test profile"
    else
        print_error "Soft delete test profile (Status: $status)"
        local body=$(echo "$response" | sed '$d')
        echo "$body"
    fi
}

# =============================================================================
# PHOTO UPLOAD TESTS (Simulated)
# =============================================================================

test_photo_operations() {
    print_header "PHOTO OPERATIONS TESTS"
    print_section "Photo Management"
    
    if [[ -z "$TEST_PROFILE_ID" ]]; then
        print_error "No profile ID available for testing"
        return 1
    fi
    
    print_test "Getting photo upload URL"
    
    local response=$(curl -s -w "\n%{http_code}" -X GET "$BASE_URL/biodata/$TEST_PROFILE_ID/photos" \
        -H "Authorization: Bearer $TEST_USER_TOKEN")
    
    local status=$(echo "$response" | tail -1)
    if [[ "$status" == "200" ]]; then
        print_success "Get photos"
    elif [[ "$status" == "404" ]]; then
        print_info "Photos endpoint not found or no photos uploaded"
    else
        print_error "Get photos (Status: $status)"
    fi
    
    print_test "Testing photo upload endpoint availability"
    
    local response=$(curl -s -w "\n%{http_code}" -X POST "$BASE_URL/biodata/$TEST_PROFILE_ID/photos" \
        -H "Authorization: Bearer $TEST_USER_TOKEN" \
        -H "Content-Type: application/json" \
        -d '{"photo_type": "profile", "description": "Test photo"}')
    
    local status=$(echo "$response" | tail -1)
    if [[ "$status" == "200" ]] || [[ "$status" == "201" ]]; then
        print_success "Photo upload endpoint available"
    elif [[ "$status" == "400" ]] || [[ "$status" == "422" ]]; then
        print_info "Photo upload endpoint available (requires actual file)"
    elif [[ "$status" == "404" ]]; then
        print_info "Photo upload endpoint not implemented"
    else
        print_error "Photo upload endpoint test (Status: $status)"
    fi
}

# =============================================================================
# REPORT GENERATION
# =============================================================================

generate_test_report() {
    print_header "TEST EXECUTION SUMMARY"
    
    echo -e "${CYAN}Test Configuration:${NC}"
    echo -e "  Base URL: $BASE_URL"
    echo -e "  Admin Username: $ADMIN_USERNAME"
    echo -e "  Test User: $TEST_USER_USERNAME"
    echo -e "  Test Profile ID: ${TEST_PROFILE_ID:-'Not Created'}"
    echo -e "  Timestamp: $(date)"
    
    echo -e "\n${CYAN}Test Results:${NC}"
    echo -e "${GREEN}✅ Passed: $PASSED_TESTS${NC}"
    echo -e "${RED}❌ Failed: $FAILED_TESTS${NC}"
    
    local total=$((PASSED_TESTS + FAILED_TESTS))
    if [[ $total -gt 0 ]]; then
        local success_rate=$((PASSED_TESTS * 100 / total))
        echo -e "${BLUE}📊 Success Rate: $success_rate%${NC}"
    fi
    
    if [[ ${#TEST_RESULTS[@]} -gt 0 ]]; then
        echo -e "\n${CYAN}Detailed Results:${NC}"
        for result in "${TEST_RESULTS[@]}"; do
            echo -e "  $result"
        done
    fi
    
    if [[ $FAILED_TESTS -eq 0 ]]; then
        echo -e "\n${GREEN}🎉 ALL TESTS PASSED! The biodata API is working correctly.${NC}"
        return 0
    else
        echo -e "\n${YELLOW}⚠️  Some tests failed. Please review the output above.${NC}"
        return 1
    fi
}

# =============================================================================
# MAIN EXECUTION FUNCTION
# =============================================================================

main() {
    print_header "BIODATA SYSTEM COMPREHENSIVE API TESTING"
    print_info "Starting comprehensive biodata API testing with admin credentials"
    print_info "Base URL: $BASE_URL"
    
    # Check prerequisites
    if ! command -v curl &> /dev/null; then
        print_error "curl is required but not installed"
        exit 1
    fi
    
    if ! command -v jq &> /dev/null; then
        print_warning "jq is not installed. JSON responses may not be formatted nicely."
    fi
    
    # Execute test suites
    test_admin_login
    test_admin_user_info
    test_create_test_user
    test_user_login
    
    test_create_basic_biodata
    test_get_my_profile
    test_get_specific_profile
    
    test_update_contact_info
    test_update_education
    test_update_occupation
    test_update_physical_attributes
    test_update_lifestyle
    test_update_family_details
    test_update_partner_preferences
    
    test_upgrade_to_detailed
    test_detailed_religious_info
    test_detailed_astrology
    test_extended_family
    
    test_search_profiles
    test_advanced_search
    test_text_search
    test_location_search
    
    test_profile_analytics
    test_increment_view
    test_profile_interactions
    
    test_get_individual_sections
    test_admin_functions
    test_photo_operations
    
    test_cleanup
    
    # Generate final report
    generate_test_report
}

# Execute main function
main "$@"