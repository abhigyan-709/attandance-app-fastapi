#!/bin/bash

# =============================================================================
# BIODATA SYSTEM API TESTING SCRIPT
# =============================================================================
# This script tests all major biodata API endpoints on the live server
# Usage: ./test_biodata_api.sh
# Prerequisites: curl, jq (for JSON parsing)
# =============================================================================

# Configuration
BASE_URL="https://api.projectdevops.in"
TIMESTAMP=$(date +%s)
TEST_USERNAME="biodata_test_${TIMESTAMP}"
TEST_EMAIL="biodata.test.${TIMESTAMP}@example.com"
TEST_PASSWORD="TestBiodata123!"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Global variables
ACCESS_TOKEN=""
PROFILE_ID=""

# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

print_header() {
    echo -e "\n${BLUE}==============================================================================${NC}"
    echo -e "${BLUE} $1${NC}"
    echo -e "${BLUE}==============================================================================${NC}\n"
}

print_test() {
    echo -e "${YELLOW}Testing: $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ SUCCESS: $1${NC}"
}

print_error() {
    echo -e "${RED}❌ ERROR: $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  INFO: $1${NC}"
}

check_response() {
    local response="$1"
    local expected_status="$2"
    local description="$3"
    
    local status=$(echo "$response" | tail -1)
    local body=$(echo "$response" | sed '$d')
    
    if [[ "$status" == "$expected_status" ]]; then
        print_success "$description"
        echo "$body"
        return 0
    else
        print_error "$description (Expected: $expected_status, Got: $status)"
        echo "$body"
        return 1
    fi
}

# =============================================================================
# AUTHENTICATION TESTS
# =============================================================================

test_user_registration() {
    print_header "TESTING USER REGISTRATION"
    
    print_test "Registering new test user: $TEST_USERNAME"
    
    response=$(curl -s -w "\n%{http_code}" -L -X POST "$BASE_URL/register" \
        -H "Content-Type: application/json" \
        -d "{
            \"first_name\": \"Test\",
            \"last_name\": \"User\",
            \"city\": \"Test City\",
            \"username\": \"$TEST_USERNAME\",
            \"email\": \"$TEST_EMAIL\",
            \"password\": \"$TEST_PASSWORD\",
            \"role\": \"user\"
        }")
    
    if check_response "$response" "201" "User registration"; then
        print_info "User registered successfully: $TEST_USERNAME"
        return 0
    else
        # Check if user already exists
        local status=$(echo "$response" | tail -n1)
        if [[ "$status" == "400" ]]; then
            print_info "User might already exist, continuing with login test..."
            return 0
        else
            return 1
        fi
    fi
}

test_user_login() {
    print_header "TESTING USER LOGIN"
    
    print_test "Logging in user: $TEST_USERNAME"
    
    response=$(curl -s -w "\n%{http_code}" -L -X POST "$BASE_URL/token" \
        -H "Content-Type: application/x-www-form-urlencoded" \
        -d "username=$TEST_USERNAME&password=$TEST_PASSWORD")
    
    if check_response "$response" "200" "User login"; then
        local body=$(echo "$response" | sed '$d')
        ACCESS_TOKEN=$(echo "$body" | jq -r '.access_token')
        print_info "Access token obtained: ${ACCESS_TOKEN:0:20}..."
        return 0
    else
        return 1
    fi
}

test_get_current_user() {
    print_header "TESTING GET CURRENT USER"
    
    print_test "Getting current user info"
    
    response=$(curl -s -w "\n%{http_code}" -L -X GET "$BASE_URL/users/me" \
        -H "Authorization: Bearer $ACCESS_TOKEN")
    
    check_response "$response" "200" "Get current user"
}

# =============================================================================
# BIODATA PROFILE TESTS
# =============================================================================

test_create_basic_profile() {
    print_header "TESTING BASIC BIODATA CREATION"
    
    print_test "Creating basic biodata profile"
    
    response=$(curl -s -w "\n%{http_code}" -L -X POST "$BASE_URL/biodata" \
        -H "Authorization: Bearer $ACCESS_TOKEN" \
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
        local body=$(echo "$response" | sed '$d')
        PROFILE_ID=$(echo "$body" | jq -r '._id')
        print_info "Profile created with ID: $PROFILE_ID"
        return 0
    else
        return 1
    fi
}

test_get_my_profile() {
    print_header "TESTING GET MY PROFILE"
    
    print_test "Getting my biodata profile"
    
    response=$(curl -s -w "\n%{http_code}" -L -X GET "$BASE_URL/biodata/my/profile" \
        -H "Authorization: Bearer $ACCESS_TOKEN")
    
    check_response "$response" "200" "Get my profile"
}

test_get_specific_profile() {
    print_header "TESTING GET SPECIFIC PROFILE"
    
    if [[ -z "$PROFILE_ID" ]]; then
        print_error "No profile ID available for testing"
        return 1
    fi
    
    print_test "Getting specific profile: $PROFILE_ID"
    
    response=$(curl -s -w "\n%{http_code}" -L -X GET "$BASE_URL/biodata/$PROFILE_ID" \
        -H "Authorization: Bearer $ACCESS_TOKEN")
    
    check_response "$response" "200" "Get specific profile"
}

# =============================================================================
# SECTION UPDATE TESTS
# =============================================================================

test_update_contact_info() {
    print_header "TESTING CONTACT INFO UPDATE"
    
    if [[ -z "$PROFILE_ID" ]]; then
        print_error "No profile ID available for testing"
        return 1
    fi
    
    print_test "Updating contact information"
    
    response=$(curl -s -w "\n%{http_code}" -L -X PATCH "$BASE_URL/biodata/$PROFILE_ID/contact" \
        -H "Authorization: Bearer $ACCESS_TOKEN" \
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
    print_header "TESTING EDUCATION UPDATE"
    
    if [[ -z "$PROFILE_ID" ]]; then
        print_error "No profile ID available for testing"
        return 1
    fi
    
    print_test "Updating education information"
    
    response=$(curl -s -w "\n%{http_code}" -L -X PATCH "$BASE_URL/biodata/$PROFILE_ID/education" \
        -H "Authorization: Bearer $ACCESS_TOKEN" \
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
    print_header "TESTING OCCUPATION UPDATE"
    
    if [[ -z "$PROFILE_ID" ]]; then
        print_error "No profile ID available for testing"
        return 1
    fi
    
    print_test "Updating occupation information"
    
    response=$(curl -s -w "\n%{http_code}" -L -X PATCH "$BASE_URL/biodata/$PROFILE_ID/occupation" \
        -H "Authorization: Bearer $ACCESS_TOKEN" \
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
    print_header "TESTING PHYSICAL ATTRIBUTES UPDATE"
    
    if [[ -z "$PROFILE_ID" ]]; then
        print_error "No profile ID available for testing"
        return 1
    fi
    
    print_test "Updating physical attributes"
    
    response=$(curl -s -w "\n%{http_code}" -L -X PATCH "$BASE_URL/biodata/$PROFILE_ID/physical" \
        -H "Authorization: Bearer $ACCESS_TOKEN" \
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
    print_header "TESTING LIFESTYLE UPDATE"
    
    if [[ -z "$PROFILE_ID" ]]; then
        print_error "No profile ID available for testing"
        return 1
    fi
    
    print_test "Updating lifestyle information"
    
    response=$(curl -s -w "\n%{http_code}" -L -X PATCH "$BASE_URL/biodata/$PROFILE_ID/lifestyle" \
        -H "Authorization: Bearer $ACCESS_TOKEN" \
        -H "Content-Type: application/json" \
        -d '{
            "diet": "vegetarian",
            "drinking": "no",
            "smoking": "no"
        }')
    
    check_response "$response" "200" "Update lifestyle information"
}

test_update_family_details() {
    print_header "TESTING FAMILY DETAILS UPDATE"
    
    if [[ -z "$PROFILE_ID" ]]; then
        print_error "No profile ID available for testing"
        return 1
    fi
    
    print_test "Updating family details"
    
    response=$(curl -s -w "\n%{http_code}" -L -X PATCH "$BASE_URL/biodata/$PROFILE_ID/family" \
        -H "Authorization: Bearer $ACCESS_TOKEN" \
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
    print_header "TESTING PARTNER PREFERENCES UPDATE"
    
    if [[ -z "$PROFILE_ID" ]]; then
        print_error "No profile ID available for testing"
        return 1
    fi
    
    print_test "Updating partner preferences"
    
    response=$(curl -s -w "\n%{http_code}" -L -X PATCH "$BASE_URL/biodata/$PROFILE_ID/partner-preferences" \
        -H "Authorization: Bearer $ACCESS_TOKEN" \
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
# SEARCH TESTS
# =============================================================================

test_search_profiles() {
    print_header "TESTING PROFILE SEARCH"
    
    print_test "Searching profiles with filters"
    
    response=$(curl -s -w "\n%{http_code}" -L -X GET "$BASE_URL/biodata?gender=female&religion=hindu&limit=5" \
        -H "Authorization: Bearer $ACCESS_TOKEN")
    
    check_response "$response" "200" "Search profiles with filters"
}

test_text_search() {
    print_header "TESTING TEXT SEARCH"
    
    print_test "Text search for 'engineer'"
    
    response=$(curl -s -w "\n%{http_code}" -L -X GET "$BASE_URL/biodata/search?q=engineer&limit=5" \
        -H "Authorization: Bearer $ACCESS_TOKEN")
    
    check_response "$response" "200" "Text search"
}

# =============================================================================
# ADVANCED FEATURES TESTS
# =============================================================================

test_upgrade_to_detailed() {
    print_header "TESTING PROFILE UPGRADE"
    
    if [[ -z "$PROFILE_ID" ]]; then
        print_error "No profile ID available for testing"
        return 1
    fi
    
    print_test "Upgrading profile to detailed"
    
    response=$(curl -s -w "\n%{http_code}" -L -X PATCH "$BASE_URL/biodata/$PROFILE_ID/upgrade-to-detailed" \
        -H "Authorization: Bearer $ACCESS_TOKEN")
    
    check_response "$response" "200" "Upgrade to detailed profile"
}

test_detailed_religious_info() {
    print_header "TESTING DETAILED RELIGIOUS INFO"
    
    if [[ -z "$PROFILE_ID" ]]; then
        print_error "No profile ID available for testing"
        return 1
    fi
    
    print_test "Updating detailed religious information"
    
    response=$(curl -s -w "\n%{http_code}" -L -X PATCH "$BASE_URL/biodata/$PROFILE_ID/detailed-religious-info" \
        -H "Authorization: Bearer $ACCESS_TOKEN" \
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
    print_header "TESTING DETAILED ASTROLOGY"
    
    if [[ -z "$PROFILE_ID" ]]; then
        print_error "No profile ID available for testing"
        return 1
    fi
    
    print_test "Updating detailed astrology information"
    
    response=$(curl -s -w "\n%{http_code}" -L -X PATCH "$BASE_URL/biodata/$PROFILE_ID/detailed-astrology" \
        -H "Authorization: Bearer $ACCESS_TOKEN" \
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

# =============================================================================
# RETRIEVAL TESTS
# =============================================================================

test_get_sections() {
    print_header "TESTING SECTION RETRIEVAL"
    
    if [[ -z "$PROFILE_ID" ]]; then
        print_error "No profile ID available for testing"
        return 1
    fi
    
    # Test getting individual sections
    sections=("contact" "education" "occupation" "physical" "lifestyle" "family" "partner-preferences")
    
    for section in "${sections[@]}"; do
        print_test "Getting $section section"
        
        response=$(curl -s -w "\n%{http_code}" -L -X GET "$BASE_URL/biodata/$PROFILE_ID/$section" \
            -H "Authorization: Bearer $ACCESS_TOKEN")
        
        local status=$(echo "$response" | tail -n1)
        if [[ "$status" == "200" ]]; then
            print_success "Get $section section"
        else
            print_info "Get $section section (might be empty): Status $status"
        fi
    done
}

# =============================================================================
# ANALYTICS TESTS
# =============================================================================

test_profile_analytics() {
    print_header "TESTING PROFILE ANALYTICS"
    
    if [[ -z "$PROFILE_ID" ]]; then
        print_error "No profile ID available for testing"
        return 1
    fi
    
    print_test "Getting profile analytics"
    
    response=$(curl -s -w "\n%{http_code}" -L -X GET "$BASE_URL/biodata/$PROFILE_ID/analytics" \
        -H "Authorization: Bearer $ACCESS_TOKEN")
    
    check_response "$response" "200" "Get profile analytics"
}

test_increment_view() {
    print_header "TESTING VIEW INCREMENT"
    
    if [[ -z "$PROFILE_ID" ]]; then
        print_error "No profile ID available for testing"
        return 1
    fi
    
    print_test "Incrementing profile view"
    
    response=$(curl -s -w "\n%{http_code}" -L -X PATCH "$BASE_URL/biodata/$PROFILE_ID/increment-view" \
        -H "Authorization: Bearer $ACCESS_TOKEN")
    
    check_response "$response" "200" "Increment profile view"
}

# =============================================================================
# CLEANUP TESTS
# =============================================================================

test_cleanup() {
    print_header "TESTING CLEANUP"
    
    if [[ -z "$PROFILE_ID" ]]; then
        print_error "No profile ID available for cleanup"
        return 1
    fi
    
    print_test "Deleting test profile (soft delete)"
    
    response=$(curl -s -w "\n%{http_code}" -L -X DELETE "$BASE_URL/biodata/$PROFILE_ID" \
        -H "Authorization: Bearer $ACCESS_TOKEN")
    
    check_response "$response" "200" "Delete test profile"
}

# =============================================================================
# MAIN EXECUTION
# =============================================================================

main() {
    print_header "BIODATA SYSTEM API TESTING"
    print_info "Base URL: $BASE_URL"
    print_info "Test User: $TEST_USERNAME"
    print_info "Test Email: $TEST_EMAIL"
    
    # Check prerequisites
    if ! command -v curl &> /dev/null; then
        print_error "curl is required but not installed"
        exit 1
    fi
    
    if ! command -v jq &> /dev/null; then
        print_error "jq is required but not installed"
        exit 1
    fi
    
    # Track test results
    local passed=0
    local failed=0
    
    # Authentication Tests
    if test_user_registration; then ((passed++)); else ((failed++)); fi
    if test_user_login; then ((passed++)); else ((failed++)); fi
    if test_get_current_user; then ((passed++)); else ((failed++)); fi
    
    # Core Profile Tests
    if test_create_basic_profile; then ((passed++)); else ((failed++)); fi
    if test_get_my_profile; then ((passed++)); else ((failed++)); fi
    if test_get_specific_profile; then ((passed++)); else ((failed++)); fi
    
    # Section Update Tests
    if test_update_contact_info; then ((passed++)); else ((failed++)); fi
    if test_update_education; then ((passed++)); else ((failed++)); fi
    if test_update_occupation; then ((passed++)); else ((failed++)); fi
    if test_update_physical_attributes; then ((passed++)); else ((failed++)); fi
    if test_update_lifestyle; then ((passed++)); else ((failed++)); fi
    if test_update_family_details; then ((passed++)); else ((failed++)); fi
    if test_update_partner_preferences; then ((passed++)); else ((failed++)); fi
    
    # Search Tests
    if test_search_profiles; then ((passed++)); else ((failed++)); fi
    if test_text_search; then ((passed++)); else ((failed++)); fi
    
    # Advanced Features Tests
    if test_upgrade_to_detailed; then ((passed++)); else ((failed++)); fi
    if test_detailed_religious_info; then ((passed++)); else ((failed++)); fi
    if test_detailed_astrology; then ((passed++)); else ((failed++)); fi
    
    # Retrieval Tests
    if test_get_sections; then ((passed++)); else ((failed++)); fi
    
    # Analytics Tests
    if test_profile_analytics; then ((passed++)); else ((failed++)); fi
    if test_increment_view; then ((passed++)); else ((failed++)); fi
    
    # Cleanup
    if test_cleanup; then ((passed++)); else ((failed++)); fi
    
    # Final Results
    print_header "TEST RESULTS SUMMARY"
    echo -e "${GREEN}✅ Passed: $passed${NC}"
    echo -e "${RED}❌ Failed: $failed${NC}"
    
    local total=$((passed + failed))
    if [[ $total -gt 0 ]]; then
        local success_rate=$((passed * 100 / total))
        echo -e "${BLUE}📊 Success Rate: $success_rate%${NC}"
    fi
    
    if [[ $failed -eq 0 ]]; then
        echo -e "\n${GREEN}🎉 ALL TESTS PASSED! The biodata API is working correctly.${NC}"
        exit 0
    else
        echo -e "\n${YELLOW}⚠️  Some tests failed. Please review the output above.${NC}"
        exit 1
    fi
}

# Execute main function
main "$@"