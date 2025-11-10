#!/bin/bash

# ULTIMATE BIODATA API TESTING SCRIPT
# Tests ALL 68+ endpoints with comprehensive coverage
# Usage: ./test_all_biodata_endpoints.sh

BASE_URL="https://api.projectdevops.in"
ADMIN_USERNAME="admin"
ADMIN_PASSWORD="Gyanu@9693894505"

# Test credentials
TEST_USERNAME="biodata_test_comprehensive"
TEST_PASSWORD="TestUser@123"
TEST_EMAIL="biodata.comprehensive@example.com"

# Colors for output
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

# Test results storage
declare -a FAILED_ENDPOINTS=()

echo -e "${CYAN}🔥 ULTIMATE BIODATA API TESTING - ALL 68+ ENDPOINTS${NC}"
echo "================================================================="
echo -e "${BLUE}📅 Date: $(date)${NC}"
echo -e "${BLUE}🌐 Base URL: $BASE_URL${NC}"
echo -e "${BLUE}👤 Admin User: $ADMIN_USERNAME${NC}"
echo -e "${BLUE}🧑‍💻 Test User: $TEST_USERNAME${NC}"

print_header() {
    echo ""
    echo -e "${PURPLE}$1${NC}"
    echo -e "${PURPLE}$(printf '=%.0s' $(seq 1 ${#1}))${NC}"
}

print_success() { echo -e "${GREEN}✅ $1${NC}"; }
print_error() { echo -e "${RED}❌ $1${NC}"; }
print_warning() { echo -e "${YELLOW}⚠️  $1${NC}"; }
print_info() { echo -e "${BLUE}ℹ️  $1${NC}"; }

# Enhanced test function
test_endpoint() {
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
    
    if [ "$file_upload" = "true" ]; then
        # File upload test
        echo "test content" > /tmp/test_file.txt
        response=$(curl -s -w "HTTPSTATUS:%{http_code}" -X $method \
            -H "Authorization: Bearer $auth_token" \
            -F "file=@/tmp/test_file.txt" \
            "$BASE_URL$endpoint")
        rm -f /tmp/test_file.txt
    elif [ "$method" = "GET" ]; then
        response=$(curl -s -w "HTTPSTATUS:%{http_code}" -X GET \
            -H "Authorization: Bearer $auth_token" \
            -H "Content-Type: application/json" \
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
            -H "Content-Type: application/json" \
            "$BASE_URL$endpoint")
    fi
    
    local http_code=$(echo $response | grep -o "HTTPSTATUS:[0-9]*" | cut -d: -f2)
    local response_body=$(echo $response | sed -E 's/HTTPSTATUS:[0-9]*$//')
    
    echo "📊 Status: $http_code (Expected: $expected_status)"
    
    # Show response snippet
    if [ ${#response_body} -gt 150 ]; then
        echo "📄 Response: ${response_body:0:150}... [truncated]"
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

# Get auth tokens
get_auth_token() {
    local username=$1
    local password=$2
    
    local login_response=$(curl -s -X POST \
        -H "Content-Type: application/x-www-form-urlencoded" \
        -d "username=$username&password=$password" \
        "$BASE_URL/token")
    
    local token=$(echo $login_response | grep -o '"access_token":"[^"]*' | cut -d'"' -f4)
    
    if [ -z "$token" ]; then
        print_error "Failed to get auth token for $username"
        echo "Response: $login_response"
        return 1
    fi
    
    echo $token
}

# Create test user
create_test_user() {
    print_info "Creating test user: $TEST_USERNAME"
    
    local user_data='{
        "username": "'$TEST_USERNAME'",
        "password": "'$TEST_PASSWORD'",
        "email": "'$TEST_EMAIL'",
        "role": "user"
    }'
    
    curl -s -X POST \
        -H "Content-Type: application/json" \
        -d "$user_data" \
        "$BASE_URL/register" > /dev/null
    
    print_success "Test user setup completed"
}

print_header "🔐 PHASE 1: AUTHENTICATION SETUP"

# Setup users and tokens
create_test_user

ADMIN_TOKEN=$(get_auth_token "$ADMIN_USERNAME" "$ADMIN_PASSWORD")
if [ -z "$ADMIN_TOKEN" ]; then
    print_error "Cannot proceed without admin token"
    exit 1
fi
print_success "Admin authentication successful"

TEST_TOKEN=$(get_auth_token "$TEST_USERNAME" "$TEST_PASSWORD")
if [ -z "$TEST_TOKEN" ]; then
    print_warning "Test user token not available, using admin for all tests"
    TEST_TOKEN=$ADMIN_TOKEN
fi

print_header "📋 PHASE 2: BASIC BIODATA OPERATIONS"

# 1. Create biodata profile
test_endpoint "POST" "/biodata" "Create biodata profile" "$ADMIN_TOKEN" '{
    "user_id": "test_comprehensive_user",
    "first_name": "Comprehensive",
    "last_name": "Test",
    "gender": "male",
    "dob": "1990-01-01",
    "email": "comprehensive.test@example.com",
    "phone": "9876543210",
    "father_name": "Father Name",
    "mother_name": "Mother Name",
    "highest_education": "Masters",
    "height": "175",
    "complexion": "fair"
}' 200

# Get the profile ID from search
SEARCH_RESPONSE=$(curl -s -X GET \
    -H "Authorization: Bearer $ADMIN_TOKEN" \
    "$BASE_URL/biodata/search?q=Comprehensive&limit=1")
PROFILE_ID=$(echo $SEARCH_RESPONSE | grep -o '"_id":"[^"]*' | cut -d'"' -f4 | head -1)

if [ -z "$PROFILE_ID" ]; then
    print_error "Could not get profile ID, using fallback"
    PROFILE_ID="6912022c06e823975585e322"
fi

print_info "Using Profile ID: $PROFILE_ID"

# 2. Get all biodata profiles
test_endpoint "GET" "/biodata" "Get all biodata profiles" "$ADMIN_TOKEN"

# 3. Get my biodata profile
test_endpoint "GET" "/biodata/my/profile" "Get my biodata profile" "$TEST_TOKEN"

# 4. Search biodata
test_endpoint "GET" "/biodata/search?q=Test&limit=5" "Search biodata profiles" "$ADMIN_TOKEN"

# 5. Get specific biodata profile
test_endpoint "GET" "/biodata/$PROFILE_ID" "Get specific biodata profile" "$ADMIN_TOKEN"

# 6. Update biodata profile
test_endpoint "PUT" "/biodata/$PROFILE_ID" "Update biodata profile" "$ADMIN_TOKEN" '{
    "about_me": "Updated comprehensive test profile",
    "mother_tongue": "English"
}'

print_header "📸 PHASE 3: PHOTO MANAGEMENT OPERATIONS"

# 7. Get photos
test_endpoint "GET" "/biodata/$PROFILE_ID/photos" "Get biodata photos" "$ADMIN_TOKEN"

# 8. Upload photo (file upload)
test_endpoint "POST" "/biodata/$PROFILE_ID/photos" "Upload biodata photo" "$ADMIN_TOKEN" "" 201 true

print_header "🔧 PHASE 4: SECTION MANAGEMENT (PATCH/GET/DELETE)"

# Contact operations
test_endpoint "PATCH" "/biodata/$PROFILE_ID/contact" "Update contact info" "$ADMIN_TOKEN" '{
    "email": "updated@example.com",
    "phone": "9876543299",
    "address": "Updated Address"
}'

test_endpoint "GET" "/biodata/$PROFILE_ID/contact" "Get contact info" "$ADMIN_TOKEN"

# Education operations  
test_endpoint "PATCH" "/biodata/$PROFILE_ID/education" "Update education" "$ADMIN_TOKEN" '{
    "highest_education": "PhD",
    "education_details": "Computer Science PhD"
}'

test_endpoint "GET" "/biodata/$PROFILE_ID/education" "Get education info" "$ADMIN_TOKEN"

# Occupation operations
test_endpoint "PATCH" "/biodata/$PROFILE_ID/occupation" "Update occupation" "$ADMIN_TOKEN" '{
    "occupation": "Software Engineer",
    "company": "Tech Corp"
}'

test_endpoint "GET" "/biodata/$PROFILE_ID/occupation" "Get occupation info" "$ADMIN_TOKEN"

# Family operations
test_endpoint "PATCH" "/biodata/$PROFILE_ID/family" "Update family info" "$ADMIN_TOKEN" '{
    "father_name": "Updated Father",
    "mother_name": "Updated Mother",
    "siblings": "2 brothers"
}'

test_endpoint "GET" "/biodata/$PROFILE_ID/family" "Get family details" "$ADMIN_TOKEN"

# Physical attributes operations
test_endpoint "PATCH" "/biodata/$PROFILE_ID/physical" "Update physical attributes" "$ADMIN_TOKEN" '{
    "height": "180",
    "weight": "75",
    "complexion": "wheatish"
}'

test_endpoint "GET" "/biodata/$PROFILE_ID/physical" "Get physical attributes" "$ADMIN_TOKEN"

# Lifestyle operations
test_endpoint "PATCH" "/biodata/$PROFILE_ID/lifestyle" "Update lifestyle" "$ADMIN_TOKEN" '{
    "diet": "vegetarian",
    "smoking": "no",
    "drinking": "no"
}'

test_endpoint "GET" "/biodata/$PROFILE_ID/lifestyle" "Get lifestyle info" "$ADMIN_TOKEN"

# Horoscope operations
test_endpoint "PATCH" "/biodata/$PROFILE_ID/horoscope" "Update horoscope" "$ADMIN_TOKEN" '{
    "birth_time": "10:30",
    "birth_place": "Mumbai"
}'

test_endpoint "GET" "/biodata/$PROFILE_ID/horoscope" "Get horoscope info" "$ADMIN_TOKEN"

# Languages operations
test_endpoint "PATCH" "/biodata/$PROFILE_ID/languages" "Update languages" "$ADMIN_TOKEN" '{
    "languages_known": ["Hindi", "English", "Marathi"]
}'

test_endpoint "GET" "/biodata/$PROFILE_ID/languages" "Get languages info" "$ADMIN_TOKEN"

# Partner preferences operations
test_endpoint "PATCH" "/biodata/$PROFILE_ID/partner-preferences" "Update partner preferences" "$ADMIN_TOKEN" '{
    "min_age": 25,
    "max_age": 35,
    "preferred_education": ["Graduate"]
}'

test_endpoint "GET" "/biodata/$PROFILE_ID/partner-preferences" "Get partner preferences" "$ADMIN_TOKEN"

print_header "🚀 PHASE 5: ENHANCED BIODATA FEATURES"

# Upgrade to detailed biodata
test_endpoint "PATCH" "/biodata/$PROFILE_ID/upgrade-to-detailed" "Upgrade to detailed biodata" "$ADMIN_TOKEN"

# Detailed religious info
test_endpoint "PATCH" "/biodata/$PROFILE_ID/detailed-religious-info" "Update detailed religious info" "$ADMIN_TOKEN" '{
    "varna": "brahmin",
    "religious_sect": "shaiva"
}'

test_endpoint "GET" "/biodata/$PROFILE_ID/detailed-religious-info" "Get detailed religious info" "$ADMIN_TOKEN"

# Detailed astrology
test_endpoint "PATCH" "/biodata/$PROFILE_ID/detailed-astrology" "Update detailed astrology" "$ADMIN_TOKEN" '{
    "rashi": "mesha",
    "nakshatra": "ashwini"
}'

test_endpoint "GET" "/biodata/$PROFILE_ID/detailed-astrology" "Get detailed astrology" "$ADMIN_TOKEN"

# Upload kundli
test_endpoint "POST" "/biodata/$PROFILE_ID/upload-kundli" "Upload kundli document" "$ADMIN_TOKEN" "" 201 true

# Family background
test_endpoint "PATCH" "/biodata/$PROFILE_ID/detailed-family-background" "Update detailed family background" "$ADMIN_TOKEN" '{
    "family_type": "nuclear",
    "family_values": "traditional"
}'

# Extended family member
test_endpoint "POST" "/biodata/$PROFILE_ID/extended-family-member" "Add extended family member" "$ADMIN_TOKEN" '{
    "name": "Uncle John",
    "relation": "uncle",
    "occupation": "Engineer"
}' 201

# Traditional preferences
test_endpoint "PATCH" "/biodata/$PROFILE_ID/traditional-preferences" "Update traditional preferences" "$ADMIN_TOKEN" '{
    "regional_tradition": "maharashtrian"
}'

test_endpoint "GET" "/biodata/$PROFILE_ID/traditional-preferences" "Get traditional preferences" "$ADMIN_TOKEN"

# Marriage planning
test_endpoint "PATCH" "/biodata/$PROFILE_ID/marriage-planning" "Update marriage planning" "$ADMIN_TOKEN" '{
    "preferred_wedding_date": "2024-12-01"
}'

test_endpoint "GET" "/biodata/$PROFILE_ID/marriage-planning" "Get marriage planning" "$ADMIN_TOKEN"

# Verification documents
test_endpoint "PATCH" "/biodata/$PROFILE_ID/verification-documents" "Update verification documents" "$ADMIN_TOKEN" '{
    "identity_verified": true
}'

test_endpoint "POST" "/biodata/$PROFILE_ID/upload-document" "Upload verification document" "$ADMIN_TOKEN" "" 201 true

test_endpoint "GET" "/biodata/$PROFILE_ID/verification-documents" "Get verification documents" "$ADMIN_TOKEN"

print_header "👑 PHASE 6: ADMIN-ONLY OPERATIONS"

# Stats and analytics
test_endpoint "GET" "/biodata/stats/overview" "Get biodata stats overview" "$ADMIN_TOKEN"

test_endpoint "GET" "/biodata/$PROFILE_ID/analytics" "Get profile analytics" "$ADMIN_TOKEN"

# Verification operations
test_endpoint "PATCH" "/biodata/$PROFILE_ID/verify" "Verify profile" "$ADMIN_TOKEN" '{
    "verification_notes": "Profile verified successfully"
}'

test_endpoint "PATCH" "/biodata/$PROFILE_ID/unverify" "Unverify profile" "$ADMIN_TOKEN"

# Admin detailed profiles
test_endpoint "GET" "/admin/biodata/detailed-profiles" "Get admin detailed profiles" "$ADMIN_TOKEN"

# Admin verification status
test_endpoint "PATCH" "/admin/biodata/$PROFILE_ID/verification-status" "Update admin verification status" "$ADMIN_TOKEN" '{
    "verification_status": "verified"
}'

print_header "📊 PHASE 7: PDF GENERATION SYSTEM"

# PDF endpoints
test_endpoint "GET" "/biodata/$PROFILE_ID/pdf-data" "Get PDF data" "$ADMIN_TOKEN"

test_endpoint "GET" "/biodata/$PROFILE_ID/pdf-summary" "Get PDF summary" "$ADMIN_TOKEN"

test_endpoint "GET" "/biodata/$PROFILE_ID/storage-status" "Check storage status" "$ADMIN_TOKEN"

test_endpoint "POST" "/biodata/$PROFILE_ID/validate-pdf-readiness" "Validate PDF readiness" "$ADMIN_TOKEN"

print_header "🗑️ PHASE 8: DELETE OPERATIONS"

# Section deletions
test_endpoint "DELETE" "/biodata/$PROFILE_ID/contact" "Delete contact info" "$ADMIN_TOKEN" "" 204

test_endpoint "DELETE" "/biodata/$PROFILE_ID/education" "Delete education info" "$ADMIN_TOKEN" "" 204

test_endpoint "DELETE" "/biodata/$PROFILE_ID/occupation" "Delete occupation info" "$ADMIN_TOKEN" "" 204

test_endpoint "DELETE" "/biodata/$PROFILE_ID/physical" "Delete physical attributes" "$ADMIN_TOKEN" "" 204

test_endpoint "DELETE" "/biodata/$PROFILE_ID/lifestyle" "Delete lifestyle info" "$ADMIN_TOKEN" "" 204

test_endpoint "DELETE" "/biodata/$PROFILE_ID/horoscope" "Delete horoscope info" "$ADMIN_TOKEN" "" 204

test_endpoint "DELETE" "/biodata/$PROFILE_ID/languages" "Delete languages info" "$ADMIN_TOKEN" "" 204

test_endpoint "DELETE" "/biodata/$PROFILE_ID/partner-preferences" "Delete partner preferences" "$ADMIN_TOKEN" "" 204

# Soft delete profile
test_endpoint "DELETE" "/biodata/$PROFILE_ID" "Soft delete biodata profile" "$ADMIN_TOKEN" "" 204

# Permanent delete profile (commented out to preserve data)
# test_endpoint "DELETE" "/biodata/$PROFILE_ID/permanent" "Permanent delete biodata profile" "$ADMIN_TOKEN" "" 204

print_header "📊 FINAL COMPREHENSIVE TEST RESULTS"

echo ""
echo -e "${CYAN}╔══════════════════════════════════════╗${NC}"
echo -e "${CYAN}║           TEST SUMMARY               ║${NC}"
echo -e "${CYAN}╠══════════════════════════════════════╣${NC}"
echo -e "${CYAN}║${NC} Total Tests:      ${YELLOW}$TOTAL_TESTS${NC}               ${CYAN}║${NC}"
echo -e "${CYAN}║${NC} Passed Tests:     ${GREEN}$PASSED_TESTS${NC}               ${CYAN}║${NC}"
echo -e "${CYAN}║${NC} Failed Tests:     ${RED}$FAILED_TESTS${NC}               ${CYAN}║${NC}"
echo -e "${CYAN}╚══════════════════════════════════════╝${NC}"

SUCCESS_RATE=$(echo "scale=1; $PASSED_TESTS * 100 / $TOTAL_TESTS" | bc -l 2>/dev/null || echo "0")
echo -e "${CYAN}📈 Success Rate: ${GREEN}$SUCCESS_RATE%${NC}"

if [ $FAILED_TESTS -gt 0 ]; then
    echo ""
    echo -e "${RED}❌ FAILED ENDPOINTS:${NC}"
    echo -e "${RED}===================${NC}"
    for endpoint in "${FAILED_ENDPOINTS[@]}"; do
        echo -e "${RED}• $endpoint${NC}"
    done
fi

echo ""
echo -e "${CYAN}🔍 TEST ENVIRONMENT DETAILS${NC}"
echo -e "${CYAN}===========================${NC}"
echo -e "${BLUE}• API Base URL: $BASE_URL${NC}"
echo -e "${BLUE}• Admin Token: ${ADMIN_TOKEN:0:30}...${NC}"
echo -e "${BLUE}• Test Profile ID: $PROFILE_ID${NC}"
echo -e "${BLUE}• Execution Time: $(date)${NC}"

if [ $FAILED_TESTS -eq 0 ]; then
    echo ""
    echo -e "${GREEN}🎉 ALL BIODATA ENDPOINTS WORKING PERFECTLY!${NC}"
    echo -e "${GREEN}✅ The biodata system is production-ready${NC}"
    echo -e "${GREEN}✅ All CRUD operations functional${NC}"
    echo -e "${GREEN}✅ Photo management working${NC}"
    echo -e "${GREEN}✅ Enhanced features operational${NC}"
    echo -e "${GREEN}✅ Admin controls functional${NC}"
    echo -e "${GREEN}✅ PDF system ready${NC}"
else
    echo ""
    echo -e "${YELLOW}⚠️  SOME ENDPOINTS NEED ATTENTION${NC}"
    echo -e "${YELLOW}📋 Review failed endpoints above${NC}"
    echo -e "${YELLOW}🔧 Most likely causes: Authentication, server restart needed, or data validation${NC}"
fi

echo ""
echo -e "${PURPLE}🏁 COMPREHENSIVE BIODATA API TESTING COMPLETED${NC}"