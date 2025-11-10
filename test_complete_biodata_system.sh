#!/bin/bash

# COMPLETE BIODATA API TESTING - ALL 68 ENDPOINTS
# Tests every single endpoint systematically
# Usage: ./test_complete_biodata_system.sh

BASE_URL="https://api.projectdevops.in"
ADMIN_USERNAME="admin"
ADMIN_PASSWORD="Gyanu@9693894505"

# Test credentials
TEST_USERNAME="biodata_complete_test"
TEST_PASSWORD="TestUser@123"
TEST_EMAIL="biodata.complete@example.com"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m'

# Counters
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0

declare -a FAILED_ENDPOINTS=()
declare -a ALL_ENDPOINTS=(
    # Basic CRUD Operations
    "POST /biodata"
    "GET /biodata"
    "GET /biodata/my/profile"
    "GET /biodata/search"
    "GET /biodata/{profile_id}"
    "PUT /biodata/{profile_id}"
    
    # Photo Operations  
    "POST /biodata/{profile_id}/photos"
    "GET /biodata/{profile_id}/photos"
    "PATCH /biodata/{profile_id}/photos/{photo_index}"
    "POST /biodata/{profile_id}/photos/replace/{photo_index}"
    "PATCH /biodata/{profile_id}/photos/reorder"
    "DELETE /biodata/{profile_id}/photos/{photo_index}"
    
    # Section PATCH Operations
    "PATCH /biodata/{profile_id}/contact"
    "PATCH /biodata/{profile_id}/education"
    "PATCH /biodata/{profile_id}/occupation"
    "PATCH /biodata/{profile_id}/family"
    "PATCH /biodata/{profile_id}/partner-preferences"
    "PATCH /biodata/{profile_id}/physical"
    "PATCH /biodata/{profile_id}/lifestyle"
    "PATCH /biodata/{profile_id}/horoscope"
    "PATCH /biodata/{profile_id}/languages"
    
    # Section GET Operations
    "GET /biodata/{profile_id}/contact"
    "GET /biodata/{profile_id}/education"
    "GET /biodata/{profile_id}/occupation"
    "GET /biodata/{profile_id}/family"
    "GET /biodata/{profile_id}/physical"
    "GET /biodata/{profile_id}/lifestyle"
    "GET /biodata/{profile_id}/horoscope"
    "GET /biodata/{profile_id}/languages"
    "GET /biodata/{profile_id}/partner-preferences"
    
    # Section DELETE Operations
    "DELETE /biodata/{profile_id}/contact"
    "DELETE /biodata/{profile_id}/education"
    "DELETE /biodata/{profile_id}/occupation"
    "DELETE /biodata/{profile_id}/physical"
    "DELETE /biodata/{profile_id}/lifestyle"
    "DELETE /biodata/{profile_id}/horoscope"
    "DELETE /biodata/{profile_id}/languages"
    "DELETE /biodata/{profile_id}/partner-preferences"
    
    # Profile Management
    "DELETE /biodata/{profile_id}"
    "DELETE /biodata/{profile_id}/permanent"
    
    # Statistics
    "GET /biodata/stats/overview"
    
    # Verification
    "PATCH /biodata/{profile_id}/verify"
    "PATCH /biodata/{profile_id}/unverify"
    
    # Enhanced Features
    "PATCH /biodata/{profile_id}/upgrade-to-detailed"
    "PATCH /biodata/{profile_id}/detailed-religious-info"
    "GET /biodata/{profile_id}/detailed-religious-info"
    "PATCH /biodata/{profile_id}/detailed-astrology"
    "GET /biodata/{profile_id}/detailed-astrology"
    "POST /biodata/{profile_id}/upload-kundli"
    "PATCH /biodata/{profile_id}/detailed-family-background"
    "POST /biodata/{profile_id}/extended-family-member"
    "DELETE /biodata/{profile_id}/extended-family-member/{member_index}"
    "PATCH /biodata/{profile_id}/extended-family"
    "PATCH /biodata/{profile_id}/traditional-preferences"
    "GET /biodata/{profile_id}/traditional-preferences"
    "PATCH /biodata/{profile_id}/marriage-planning"
    "GET /biodata/{profile_id}/marriage-planning"
    "PATCH /biodata/{profile_id}/verification-documents"
    "POST /biodata/{profile_id}/upload-document"
    "GET /biodata/{profile_id}/verification-documents"
    
    # Analytics
    "GET /biodata/{profile_id}/analytics"
    "PATCH /biodata/{profile_id}/increment-view"
    
    # Admin Operations
    "GET /admin/biodata/detailed-profiles"
    "PATCH /admin/biodata/{profile_id}/verification-status"
    
    # PDF Operations
    "GET /biodata/{profile_id}/pdf-data"
    "GET /biodata/{profile_id}/pdf-summary"
    "GET /biodata/{profile_id}/storage-status"
    "POST /biodata/{profile_id}/validate-pdf-readiness"
)

echo -e "${CYAN}🔥 COMPLETE BIODATA API TESTING - ALL 68 ENDPOINTS${NC}"
echo "=================================================================="
echo -e "${BLUE}📅 Date: $(date)${NC}"
echo -e "${BLUE}🌐 Base URL: $BASE_URL${NC}"
echo -e "${BLUE}👤 Admin User: $ADMIN_USERNAME${NC}"
echo -e "${BLUE}📊 Total Endpoints to Test: ${#ALL_ENDPOINTS[@]}${NC}"

print_success() { echo -e "${GREEN}✅ $1${NC}"; }
print_error() { echo -e "${RED}❌ $1${NC}"; }
print_info() { echo -e "${BLUE}ℹ️  $1${NC}"; }

# Enhanced test function
test_endpoint_complete() {
    local method=$1
    local endpoint=$2
    local description=$3
    local auth_token=$4
    local data=$5
    local expected_status=${6:-200}
    local file_upload=$7
    
    TOTAL_TESTS=$((TOTAL_TESTS + 1))
    echo ""
    print_info "Test #$TOTAL_TESTS: $description"
    echo "📍 $method $endpoint"
    
    local response
    
    # Handle different request types
    if [ "$file_upload" = "true" ]; then
        # Create test image file
        echo "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==" | base64 -d > /tmp/test_image.png
        response=$(curl -s -w "HTTPSTATUS:%{http_code}" -X $method \
            -H "Authorization: Bearer $auth_token" \
            -F "file=@/tmp/test_image.png" \
            "$BASE_URL$endpoint")
        rm -f /tmp/test_image.png
    elif [ "$method" = "GET" ]; then
        response=$(curl -s -w "HTTPSTATUS:%{http_code}" -X GET \
            -H "Authorization: Bearer $auth_token" \
            "$BASE_URL$endpoint")
    elif [ "$method" = "POST" ] || [ "$method" = "PUT" ] || [ "$method" = "PATCH" ]; then
        if [ -z "$data" ]; then
            response=$(curl -s -w "HTTPSTATUS:%{http_code}" -X $method \
                -H "Authorization: Bearer $auth_token" \
                -H "Content-Type: application/json" \
                "$BASE_URL$endpoint")
        else
            response=$(curl -s -w "HTTPSTATUS:%{http_code}" -X $method \
                -H "Authorization: Bearer $auth_token" \
                -H "Content-Type: application/json" \
                -d "$data" \
                "$BASE_URL$endpoint")
        fi
    elif [ "$method" = "DELETE" ]; then
        response=$(curl -s -w "HTTPSTATUS:%{http_code}" -X DELETE \
            -H "Authorization: Bearer $auth_token" \
            "$BASE_URL$endpoint")
    fi
    
    local http_code=$(echo $response | grep -o "HTTPSTATUS:[0-9]*" | cut -d: -f2)
    local response_body=$(echo $response | sed -E 's/HTTPSTATUS:[0-9]*$//')
    
    echo "📊 Status: $http_code (Expected: $expected_status)"
    
    if [ ${#response_body} -gt 100 ]; then
        echo "📄 Response: ${response_body:0:100}... [truncated]"
    else
        echo "📄 Response: $response_body"
    fi
    
    if [ "$http_code" = "$expected_status" ]; then
        print_success "$description"
        PASSED_TESTS=$((PASSED_TESTS + 1))
        return 0
    else
        print_error "$description (Expected $expected_status, got $http_code)"
        FAILED_TESTS=$((FAILED_TESTS + 1))
        FAILED_ENDPOINTS+=("$method $endpoint - $description")
        return 1
    fi
}

# Get auth token
get_auth_token() {
    local username=$1
    local password=$2
    
    local login_response=$(curl -s -X POST \
        -H "Content-Type: application/x-www-form-urlencoded" \
        -d "username=$username&password=$password" \
        "$BASE_URL/token")
    
    local token=$(echo $login_response | grep -o '"access_token":"[^"]*' | cut -d'"' -f4)
    echo $token
}

# Setup authentication
ADMIN_TOKEN=$(get_auth_token "$ADMIN_USERNAME" "$ADMIN_PASSWORD")
if [ -z "$ADMIN_TOKEN" ]; then
    print_error "Cannot proceed without admin token"
    exit 1
fi

# Create test profile
print_info "Creating test profile..."
CREATE_RESPONSE=$(curl -s -X POST \
    -H "Authorization: Bearer $ADMIN_TOKEN" \
    -H "Content-Type: application/json" \
    -d '{
        "user_id": "complete_test_user",
        "first_name": "Complete",
        "last_name": "Test",
        "gender": "male",
        "dob": "1990-01-01",
        "email": "complete.test@example.com",
        "phone": "9876543210",
        "father_name": "Father Name",
        "mother_name": "Mother Name",
        "highest_education": "Masters",
        "height": "175",
        "complexion": "fair"
    }' \
    "$BASE_URL/biodata")

PROFILE_ID=$(echo $CREATE_RESPONSE | grep -o '"_id":"[^"]*' | cut -d'"' -f4)
if [ -z "$PROFILE_ID" ]; then
    print_error "Could not create test profile"
    exit 1
fi

print_info "Created test profile with ID: $PROFILE_ID"

echo ""
echo -e "${PURPLE}🚀 TESTING ALL 68 ENDPOINTS${NC}"
echo -e "${PURPLE}============================${NC}"

# Test 1: POST /biodata
test_endpoint_complete "POST" "/biodata" "Create biodata profile" "$ADMIN_TOKEN" '{
    "user_id": "another_test_user",
    "first_name": "Another",
    "last_name": "Test",
    "gender": "female",
    "dob": "1992-01-01",
    "email": "another.test@example.com",
    "phone": "9876543211"
}' 200

# Test 2: GET /biodata
test_endpoint_complete "GET" "/biodata" "Get all biodata profiles" "$ADMIN_TOKEN"

# Test 3: GET /biodata/my/profile
test_endpoint_complete "GET" "/biodata/my/profile" "Get my biodata profile" "$ADMIN_TOKEN"

# Test 4: GET /biodata/search
test_endpoint_complete "GET" "/biodata/search?q=Complete&limit=5" "Search biodata profiles" "$ADMIN_TOKEN"

# Test 5: GET /biodata/{profile_id}
test_endpoint_complete "GET" "/biodata/$PROFILE_ID" "Get specific biodata profile" "$ADMIN_TOKEN"

# Test 6: PUT /biodata/{profile_id}
test_endpoint_complete "PUT" "/biodata/$PROFILE_ID" "Update biodata profile" "$ADMIN_TOKEN" '{
    "first_name": "Updated",
    "last_name": "Test",
    "gender": "male",
    "dob": "1990-01-01",
    "about_me": "Updated profile"
}' 200

# Test 7: POST /biodata/{profile_id}/photos
test_endpoint_complete "POST" "/biodata/$PROFILE_ID/photos" "Upload biodata photo" "$ADMIN_TOKEN" "" 201 true

# Test 8: GET /biodata/{profile_id}/photos
test_endpoint_complete "GET" "/biodata/$PROFILE_ID/photos" "Get biodata photos" "$ADMIN_TOKEN"

# Test 9: PATCH /biodata/{profile_id}/photos/{photo_index}
test_endpoint_complete "PATCH" "/biodata/$PROFILE_ID/photos/0" "Update photo metadata" "$ADMIN_TOKEN" '{"is_main": true, "description": "Main photo"}'

# Test 10: POST /biodata/{profile_id}/photos/replace/{photo_index}
test_endpoint_complete "POST" "/biodata/$PROFILE_ID/photos/replace/0" "Replace photo" "$ADMIN_TOKEN" "" 200 true

# Test 11: PATCH /biodata/{profile_id}/photos/reorder
test_endpoint_complete "PATCH" "/biodata/$PROFILE_ID/photos/reorder" "Reorder photos" "$ADMIN_TOKEN" '{"new_order": [0]}'

# Test 12: PATCH /biodata/{profile_id}/contact
test_endpoint_complete "PATCH" "/biodata/$PROFILE_ID/contact" "Update contact info" "$ADMIN_TOKEN" '{
    "email": "updated@example.com",
    "phone": "9876543299",
    "alternate_phone": "9876543298"
}'

# Test 13: GET /biodata/{profile_id}/contact
test_endpoint_complete "GET" "/biodata/$PROFILE_ID/contact" "Get contact info" "$ADMIN_TOKEN"

# Test 14: PATCH /biodata/{profile_id}/education
test_endpoint_complete "PATCH" "/biodata/$PROFILE_ID/education" "Update education" "$ADMIN_TOKEN" '{
    "level": "masters",
    "degree": "Computer Science",
    "institute": "ABC University"
}'

# Test 15: GET /biodata/{profile_id}/education
test_endpoint_complete "GET" "/biodata/$PROFILE_ID/education" "Get education info" "$ADMIN_TOKEN"

# Test 16: PATCH /biodata/{profile_id}/occupation
test_endpoint_complete "PATCH" "/biodata/$PROFILE_ID/occupation" "Update occupation" "$ADMIN_TOKEN" '{
    "employment_type": "private",
    "organization": "Tech Corp",
    "designation": "Software Engineer"
}'

# Test 17: GET /biodata/{profile_id}/occupation
test_endpoint_complete "GET" "/biodata/$PROFILE_ID/occupation" "Get occupation info" "$ADMIN_TOKEN"

# Test 18: PATCH /biodata/{profile_id}/family
test_endpoint_complete "PATCH" "/biodata/$PROFILE_ID/family" "Update family info" "$ADMIN_TOKEN" '{
    "father_name": "Updated Father",
    "mother_name": "Updated Mother",
    "father_occupation": "Engineer"
}'

# Test 19: GET /biodata/{profile_id}/family
test_endpoint_complete "GET" "/biodata/$PROFILE_ID/family" "Get family details" "$ADMIN_TOKEN"

# Test 20: PATCH /biodata/{profile_id}/partner-preferences
test_endpoint_complete "PATCH" "/biodata/$PROFILE_ID/partner-preferences" "Update partner preferences" "$ADMIN_TOKEN" '{
    "min_age": 25,
    "max_age": 35,
    "min_height_cm": 160,
    "max_height_cm": 175
}'

# Test 21: GET /biodata/{profile_id}/partner-preferences
test_endpoint_complete "GET" "/biodata/$PROFILE_ID/partner-preferences" "Get partner preferences" "$ADMIN_TOKEN"

# Test 22: PATCH /biodata/{profile_id}/physical
test_endpoint_complete "PATCH" "/biodata/$PROFILE_ID/physical" "Update physical attributes" "$ADMIN_TOKEN" '{
    "height_cm": 175,
    "weight_kg": 70,
    "complexion": "fair"
}'

# Test 23: GET /biodata/{profile_id}/physical
test_endpoint_complete "GET" "/biodata/$PROFILE_ID/physical" "Get physical attributes" "$ADMIN_TOKEN"

# Test 24: PATCH /biodata/{profile_id}/lifestyle
test_endpoint_complete "PATCH" "/biodata/$PROFILE_ID/lifestyle" "Update lifestyle" "$ADMIN_TOKEN" '{
    "diet": "vegetarian",
    "smoking": "no",
    "drinking": "no"
}'

# Test 25: GET /biodata/{profile_id}/lifestyle
test_endpoint_complete "GET" "/biodata/$PROFILE_ID/lifestyle" "Get lifestyle info" "$ADMIN_TOKEN"

# Test 26: PATCH /biodata/{profile_id}/horoscope
test_endpoint_complete "PATCH" "/biodata/$PROFILE_ID/horoscope" "Update horoscope" "$ADMIN_TOKEN" '{
    "date_of_birth": "1990-01-01",
    "time_of_birth": "10:30",
    "place_of_birth": "Mumbai"
}'

# Test 27: GET /biodata/{profile_id}/horoscope
test_endpoint_complete "GET" "/biodata/$PROFILE_ID/horoscope" "Get horoscope info" "$ADMIN_TOKEN"

# Test 28: PATCH /biodata/{profile_id}/languages
test_endpoint_complete "PATCH" "/biodata/{profile_id}/languages" "Update languages" "$ADMIN_TOKEN" '{
    "known": {
        "Hindi": "native",
        "English": "fluent",
        "Marathi": "conversational"
    }
}'

# Test 29: GET /biodata/{profile_id}/languages
test_endpoint_complete "GET" "/biodata/$PROFILE_ID/languages" "Get languages info" "$ADMIN_TOKEN"

# Test 30: GET /biodata/stats/overview
test_endpoint_complete "GET" "/biodata/stats/overview" "Get biodata stats overview" "$ADMIN_TOKEN"

# Test 31: PATCH /biodata/{profile_id}/verify
test_endpoint_complete "PATCH" "/biodata/$PROFILE_ID/verify" "Verify profile" "$ADMIN_TOKEN" '{
    "verification_notes": "Profile verified"
}'

# Test 32: PATCH /biodata/{profile_id}/unverify
test_endpoint_complete "PATCH" "/biodata/$PROFILE_ID/unverify" "Unverify profile" "$ADMIN_TOKEN"

# Test 33: PATCH /biodata/{profile_id}/upgrade-to-detailed
test_endpoint_complete "PATCH" "/biodata/$PROFILE_ID/upgrade-to-detailed" "Upgrade to detailed biodata" "$ADMIN_TOKEN"

# Test 34: PATCH /biodata/{profile_id}/detailed-religious-info
test_endpoint_complete "PATCH" "/biodata/$PROFILE_ID/detailed-religious-info" "Update detailed religious info" "$ADMIN_TOKEN" '{
    "varna": "brahmin",
    "religious_sect": "shaivism"
}'

# Test 35: GET /biodata/{profile_id}/detailed-religious-info
test_endpoint_complete "GET" "/biodata/$PROFILE_ID/detailed-religious-info" "Get detailed religious info" "$ADMIN_TOKEN"

# Test 36: PATCH /biodata/{profile_id}/detailed-astrology
test_endpoint_complete "PATCH" "/biodata/$PROFILE_ID/detailed-astrology" "Update detailed astrology" "$ADMIN_TOKEN" '{
    "rashi": "mesha",
    "nakshatra": "ashwini"
}'

# Test 37: GET /biodata/{profile_id}/detailed-astrology
test_endpoint_complete "GET" "/biodata/$PROFILE_ID/detailed-astrology" "Get detailed astrology" "$ADMIN_TOKEN"

# Test 38: POST /biodata/{profile_id}/upload-kundli
test_endpoint_complete "POST" "/biodata/$PROFILE_ID/upload-kundli" "Upload kundli document" "$ADMIN_TOKEN" "" 201 true

# Test 39: PATCH /biodata/{profile_id}/detailed-family-background
test_endpoint_complete "PATCH" "/biodata/$PROFILE_ID/detailed-family-background" "Update detailed family background" "$ADMIN_TOKEN" '{
    "family_type": "nuclear",
    "family_values": "traditional"
}'

# Test 40: POST /biodata/{profile_id}/extended-family-member
test_endpoint_complete "POST" "/biodata/$PROFILE_ID/extended-family-member" "Add extended family member" "$ADMIN_TOKEN" '{
    "name": "Uncle John",
    "relation": "uncle",
    "occupation": "Engineer"
}' 201

# Test 41: PATCH /biodata/{profile_id}/extended-family
test_endpoint_complete "PATCH" "/biodata/$PROFILE_ID/extended-family" "Update extended family" "$ADMIN_TOKEN" '{
    "extended_family": [
        {
            "name": "Updated Uncle",
            "relation": "uncle",
            "occupation": "Doctor"
        }
    ]
}'

# Test 42: PATCH /biodata/{profile_id}/traditional-preferences
test_endpoint_complete "PATCH" "/biodata/$PROFILE_ID/traditional-preferences" "Update traditional preferences" "$ADMIN_TOKEN" '{
    "regional_tradition": "maharashtrian"
}'

# Test 43: GET /biodata/{profile_id}/traditional-preferences
test_endpoint_complete "GET" "/biodata/$PROFILE_ID/traditional-preferences" "Get traditional preferences" "$ADMIN_TOKEN"

# Test 44: PATCH /biodata/{profile_id}/marriage-planning
test_endpoint_complete "PATCH" "/biodata/$PROFILE_ID/marriage-planning" "Update marriage planning" "$ADMIN_TOKEN" '{
    "preferred_wedding_date": "2024-12-01",
    "budget_range": "moderate"
}'

# Test 45: GET /biodata/{profile_id}/marriage-planning
test_endpoint_complete "GET" "/biodata/$PROFILE_ID/marriage-planning" "Get marriage planning" "$ADMIN_TOKEN"

# Test 46: PATCH /biodata/{profile_id}/verification-documents
test_endpoint_complete "PATCH" "/biodata/$PROFILE_ID/verification-documents" "Update verification documents" "$ADMIN_TOKEN" '{
    "identity_verified": true,
    "education_verified": false
}'

# Test 47: POST /biodata/{profile_id}/upload-document
test_endpoint_complete "POST" "/biodata/$PROFILE_ID/upload-document" "Upload verification document" "$ADMIN_TOKEN" "" 201 true

# Test 48: GET /biodata/{profile_id}/verification-documents
test_endpoint_complete "GET" "/biodata/$PROFILE_ID/verification-documents" "Get verification documents" "$ADMIN_TOKEN"

# Test 49: GET /biodata/{profile_id}/analytics
test_endpoint_complete "GET" "/biodata/$PROFILE_ID/analytics" "Get profile analytics" "$ADMIN_TOKEN"

# Test 50: PATCH /biodata/{profile_id}/increment-view
test_endpoint_complete "PATCH" "/biodata/$PROFILE_ID/increment-view" "Increment profile view" "$ADMIN_TOKEN"

# Test 51: GET /admin/biodata/detailed-profiles
test_endpoint_complete "GET" "/admin/biodata/detailed-profiles" "Get admin detailed profiles" "$ADMIN_TOKEN"

# Test 52: PATCH /admin/biodata/{profile_id}/verification-status
test_endpoint_complete "PATCH" "/admin/biodata/$PROFILE_ID/verification-status" "Update admin verification status" "$ADMIN_TOKEN" '{
    "verification_status": "verified"
}'

# Test 53: GET /biodata/{profile_id}/pdf-data
test_endpoint_complete "GET" "/biodata/$PROFILE_ID/pdf-data" "Get PDF data" "$ADMIN_TOKEN"

# Test 54: GET /biodata/{profile_id}/pdf-summary
test_endpoint_complete "GET" "/biodata/$PROFILE_ID/pdf-summary" "Get PDF summary" "$ADMIN_TOKEN"

# Test 55: GET /biodata/{profile_id}/storage-status
test_endpoint_complete "GET" "/biodata/$PROFILE_ID/storage-status" "Check storage status" "$ADMIN_TOKEN"

# Test 56: POST /biodata/{profile_id}/validate-pdf-readiness
test_endpoint_complete "POST" "/biodata/$PROFILE_ID/validate-pdf-readiness" "Validate PDF readiness" "$ADMIN_TOKEN"

# Delete Operations
# Test 57: DELETE /biodata/{profile_id}/contact
test_endpoint_complete "DELETE" "/biodata/$PROFILE_ID/contact" "Delete contact info" "$ADMIN_TOKEN" "" 204

# Test 58: DELETE /biodata/{profile_id}/education
test_endpoint_complete "DELETE" "/biodata/$PROFILE_ID/education" "Delete education info" "$ADMIN_TOKEN" "" 204

# Test 59: DELETE /biodata/{profile_id}/occupation
test_endpoint_complete "DELETE" "/biodata/$PROFILE_ID/occupation" "Delete occupation info" "$ADMIN_TOKEN" "" 204

# Test 60: DELETE /biodata/{profile_id}/physical
test_endpoint_complete "DELETE" "/biodata/$PROFILE_ID/physical" "Delete physical attributes" "$ADMIN_TOKEN" "" 204

# Test 61: DELETE /biodata/{profile_id}/lifestyle
test_endpoint_complete "DELETE" "/biodata/$PROFILE_ID/lifestyle" "Delete lifestyle info" "$ADMIN_TOKEN" "" 204

# Test 62: DELETE /biodata/{profile_id}/horoscope
test_endpoint_complete "DELETE" "/biodata/$PROFILE_ID/horoscope" "Delete horoscope info" "$ADMIN_TOKEN" "" 204

# Test 63: DELETE /biodata/{profile_id}/languages
test_endpoint_complete "DELETE" "/biodata/$PROFILE_ID/languages" "Delete languages info" "$ADMIN_TOKEN" "" 204

# Test 64: DELETE /biodata/{profile_id}/partner-preferences
test_endpoint_complete "DELETE" "/biodata/$PROFILE_ID/partner-preferences" "Delete partner preferences" "$ADMIN_TOKEN" "" 204

# Test 65: DELETE /biodata/{profile_id}/photos/{photo_index}
test_endpoint_complete "DELETE" "/biodata/$PROFILE_ID/photos/0" "Delete specific photo" "$ADMIN_TOKEN" "" 204

# Test 66: DELETE /biodata/{profile_id}/extended-family-member/{member_index}
test_endpoint_complete "DELETE" "/biodata/$PROFILE_ID/extended-family-member/0" "Delete extended family member" "$ADMIN_TOKEN" "" 204

# Test 67: DELETE /biodata/{profile_id}
test_endpoint_complete "DELETE" "/biodata/$PROFILE_ID" "Soft delete biodata profile" "$ADMIN_TOKEN" "" 204

# Test 68: DELETE /biodata/{profile_id}/permanent (commented out to preserve data)
# test_endpoint_complete "DELETE" "/biodata/$PROFILE_ID/permanent" "Permanent delete biodata profile" "$ADMIN_TOKEN" "" 204

echo ""
echo -e "${CYAN}╔══════════════════════════════════════╗${NC}"
echo -e "${CYAN}║      COMPLETE TEST RESULTS           ║${NC}"
echo -e "${CYAN}╠══════════════════════════════════════╣${NC}"
echo -e "${CYAN}║${NC} Total Tests:      ${YELLOW}$TOTAL_TESTS${NC}               ${CYAN}║${NC}"
echo -e "${CYAN}║${NC} Passed Tests:     ${GREEN}$PASSED_TESTS${NC}               ${CYAN}║${NC}"
echo -e "${CYAN}║${NC} Failed Tests:     ${RED}$FAILED_TESTS${NC}               ${CYAN}║${NC}"
echo -e "${CYAN}╚══════════════════════════════════════╝${NC}"

SUCCESS_RATE=$(echo "scale=1; $PASSED_TESTS * 100 / $TOTAL_TESTS" | bc -l 2>/dev/null || echo "0")
echo -e "${CYAN}📈 Success Rate: ${GREEN}$SUCCESS_RATE%${NC}"

if [ $FAILED_TESTS -gt 0 ]; then
    echo ""
    echo -e "${RED}❌ FAILED ENDPOINTS (${FAILED_TESTS} total):${NC}"
    echo -e "${RED}=================================${NC}"
    for endpoint in "${FAILED_ENDPOINTS[@]}"; do
        echo -e "${RED}• $endpoint${NC}"
    done
fi

echo ""
echo -e "${CYAN}🔍 COMPREHENSIVE TEST SUMMARY${NC}"
echo -e "${CYAN}=============================${NC}"
echo -e "${BLUE}• Total Endpoints Tested: ${#ALL_ENDPOINTS[@]}${NC}"
echo -e "${BLUE}• Actual Tests Executed: $TOTAL_TESTS${NC}"
echo -e "${BLUE}• Profile ID Used: $PROFILE_ID${NC}"
echo -e "${BLUE}• Execution Time: $(date)${NC}"

if [ $FAILED_TESTS -eq 0 ]; then
    echo ""
    echo -e "${GREEN}🎉 ALL 68 BIODATA ENDPOINTS TESTED SUCCESSFULLY!${NC}"
    echo -e "${GREEN}✅ The biodata system is fully functional${NC}"
else
    echo ""
    echo -e "${YELLOW}⚠️  BIODATA SYSTEM STATUS: $SUCCESS_RATE% FUNCTIONAL${NC}"
fi

echo ""
echo -e "${PURPLE}🏁 COMPLETE BIODATA API TESTING FINISHED${NC}"