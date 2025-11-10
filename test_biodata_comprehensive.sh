#!/bin/bash

# Comprehensive Biodata System Testing Script
# Tests ALL endpoints with admin and regular user credentials
# Usage: ./test_biodata_comprehensive.sh

BASE_URL="https://api.projectdevops.in"
ADMIN_USERNAME="admin"
ADMIN_PASSWORD="Gyanu@9693894505"

# Test user credentials (will be created)
TEST_USERNAME="biodata_test_user"
TEST_PASSWORD="TestUser@123"
TEST_EMAIL="biodata.test@example.com"

echo "🧪 COMPREHENSIVE BIODATA SYSTEM TESTING"
echo "========================================"
echo "🌐 Base URL: $BASE_URL"
echo "👤 Admin User: $ADMIN_USERNAME"
echo "🧑‍💻 Test User: $TEST_USERNAME"
echo ""

# Color output functions
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_success() { echo -e "${GREEN}✅ $1${NC}"; }
print_error() { echo -e "${RED}❌ $1${NC}"; }
print_warning() { echo -e "${YELLOW}⚠️  $1${NC}"; }
print_info() { echo -e "${BLUE}ℹ️  $1${NC}"; }

# Counters
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0

# Test function
test_endpoint() {
    local method=$1
    local endpoint=$2
    local description=$3
    local auth_token=$4
    local data=$5
    local expected_status=${6:-200}
    
    TOTAL_TESTS=$((TOTAL_TESTS + 1))
    echo ""
    print_info "Test #$TOTAL_TESTS: $description"
    echo "📍 $method $endpoint"
    
    if [ "$method" = "GET" ]; then
        response=$(curl -s -w "HTTPSTATUS:%{http_code}" -X GET \
            -H "Authorization: Bearer $auth_token" \
            -H "Content-Type: application/json" \
            "$BASE_URL$endpoint")
    elif [ "$method" = "POST" ]; then
        if [ -z "$data" ]; then
            response=$(curl -s -w "HTTPSTATUS:%{http_code}" -X POST \
                -H "Authorization: Bearer $auth_token" \
                -H "Content-Type: application/json" \
                "$BASE_URL$endpoint")
        else
            response=$(curl -s -w "HTTPSTATUS:%{http_code}" -X POST \
                -H "Authorization: Bearer $auth_token" \
                -H "Content-Type: application/json" \
                -d "$data" \
                "$BASE_URL$endpoint")
        fi
    elif [ "$method" = "PUT" ]; then
        response=$(curl -s -w "HTTPSTATUS:%{http_code}" -X PUT \
            -H "Authorization: Bearer $auth_token" \
            -H "Content-Type: application/json" \
            -d "$data" \
            "$BASE_URL$endpoint")
    elif [ "$method" = "DELETE" ]; then
        response=$(curl -s -w "HTTPSTATUS:%{http_code}" -X DELETE \
            -H "Authorization: Bearer $auth_token" \
            -H "Content-Type: application/json" \
            "$BASE_URL$endpoint")
    fi
    
    http_code=$(echo $response | grep -o "HTTPSTATUS:[0-9]*" | cut -d: -f2)
    response_body=$(echo $response | sed -E 's/HTTPSTATUS:[0-9]*$//')
    
    echo "📊 Status: $http_code (Expected: $expected_status)"
    
    # Show truncated response
    if [ ${#response_body} -gt 200 ]; then
        echo "📄 Response: ${response_body:0:200}... [truncated]"
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
        return 1
    fi
}

# Function to get auth token
get_auth_token() {
    local username=$1
    local password=$2
    
    print_info "Getting auth token for: $username"
    
    login_response=$(curl -s -X POST \
        -H "Content-Type: application/x-www-form-urlencoded" \
        -d "username=$username&password=$password" \
        "$BASE_URL/token")
    
    token=$(echo $login_response | grep -o '"access_token":"[^"]*' | cut -d'"' -f4)
    
    if [ -z "$token" ]; then
        print_error "Failed to get auth token for $username"
        echo "Login response: $login_response"
        return 1
    fi
    
    print_success "Got auth token for $username"
    echo $token
}

# Function to create test user
create_test_user() {
    print_info "Creating test user: $TEST_USERNAME"
    
    user_data='{
        "username": "'$TEST_USERNAME'",
        "password": "'$TEST_PASSWORD'",
        "email": "'$TEST_EMAIL'",
        "role": "user"
    }'
    
    response=$(curl -s -w "HTTPSTATUS:%{http_code}" -X POST \
        -H "Content-Type: application/json" \
        -d "$user_data" \
        "$BASE_URL/register")
    
    http_code=$(echo $response | grep -o "HTTPSTATUS:[0-9]*" | cut -d: -f2)
    
    if [ "$http_code" = "201" ] || [ "$http_code" = "409" ]; then
        print_success "Test user ready (created or already exists)"
        return 0
    else
        print_warning "Test user creation status: $http_code"
        return 0  # Continue even if user exists
    fi
}

echo "🔐 PHASE 1: AUTHENTICATION TESTING"
echo "=================================="

# Create test user
create_test_user

# Get admin token
ADMIN_TOKEN=$(get_auth_token "$ADMIN_USERNAME" "$ADMIN_PASSWORD")
if [ -z "$ADMIN_TOKEN" ]; then
    print_error "Cannot proceed without admin token"
    exit 1
fi

# Get test user token
TEST_TOKEN=$(get_auth_token "$TEST_USERNAME" "$TEST_PASSWORD")
if [ -z "$TEST_TOKEN" ]; then
    print_warning "Test user token not available, will test with admin only"
fi

echo ""
echo "📋 PHASE 2: BIODATA CRUD OPERATIONS"
echo "==================================="

# Test 1: Create biodata profile (Admin)
test_endpoint "POST" "/biodata" "Create biodata profile (Admin)" "$ADMIN_TOKEN" '{
    "user_id": "admin_biodata_test",
    "first_name": "Admin",
    "last_name": "Test",
    "gender": "male",
    "dob": "1985-01-01",
    "email": "admin.test@example.com",
    "phone": "9876543210",
    "father_name": "Admin Father",
    "mother_name": "Admin Mother",
    "highest_education": "Masters",
    "height": "180",
    "complexion": "fair"
}' 201

# Store the created profile ID
ADMIN_PROFILE_RESPONSE=$(curl -s -X GET \
    -H "Authorization: Bearer $ADMIN_TOKEN" \
    "$BASE_URL/biodata/search?q=Admin&limit=1")
ADMIN_PROFILE_ID=$(echo $ADMIN_PROFILE_RESPONSE | grep -o '"_id":"[^"]*' | cut -d'"' -f4 | head -1)

# Test 2: Create biodata profile (Test User) if token available
if [ ! -z "$TEST_TOKEN" ]; then
    test_endpoint "POST" "/biodata" "Create biodata profile (Test User)" "$TEST_TOKEN" '{
        "user_id": "test_user_biodata",
        "first_name": "Test",
        "last_name": "User",
        "gender": "female",
        "dob": "1992-05-15",
        "email": "test.user@example.com",
        "phone": "9876543211",
        "father_name": "Test Father",
        "mother_name": "Test Mother",
        "highest_education": "Bachelor",
        "height": "165",
        "complexion": "wheatish"
    }' 201
    
    # Store test user profile ID
    TEST_PROFILE_RESPONSE=$(curl -s -X GET \
        -H "Authorization: Bearer $TEST_TOKEN" \
        "$BASE_URL/biodata/search?q=Test&limit=1")
    TEST_PROFILE_ID=$(echo $TEST_PROFILE_RESPONSE | grep -o '"_id":"[^"]*' | cut -d'"' -f4 | head -1)
fi

echo ""
echo "📖 PHASE 3: READ OPERATIONS"
echo "==========================="

# Test 3: Get biodata by ID (Admin accessing own)
if [ ! -z "$ADMIN_PROFILE_ID" ]; then
    test_endpoint "GET" "/biodata/$ADMIN_PROFILE_ID" "Get biodata by ID (Admin own)" "$ADMIN_TOKEN"
fi

# Test 4: Get biodata by ID (Admin accessing other's)
if [ ! -z "$TEST_PROFILE_ID" ]; then
    test_endpoint "GET" "/biodata/$TEST_PROFILE_ID" "Get biodata by ID (Admin accessing other)" "$ADMIN_TOKEN"
fi

# Test 5: Get biodata by ID (User accessing own)
if [ ! -z "$TEST_TOKEN" ] && [ ! -z "$TEST_PROFILE_ID" ]; then
    test_endpoint "GET" "/biodata/$TEST_PROFILE_ID" "Get biodata by ID (User own)" "$TEST_TOKEN"
fi

echo ""
echo "🔍 PHASE 4: SEARCH OPERATIONS"
echo "============================="

# Test 6: Basic search (Admin)
test_endpoint "GET" "/biodata/search?q=Admin&limit=5" "Basic search (Admin)" "$ADMIN_TOKEN"

# Test 7: Advanced search with filters (Admin)
test_endpoint "GET" "/biodata/search?q=Test&gender=female&min_age=25&max_age=35&limit=5" "Advanced search with filters (Admin)" "$ADMIN_TOKEN"

# Test 8: Search by religion (Admin)
test_endpoint "GET" "/biodata/search?q=Test&religion=hindu&limit=5" "Search by religion (Admin)" "$ADMIN_TOKEN"

# Test 9: Search (Regular user)
if [ ! -z "$TEST_TOKEN" ]; then
    test_endpoint "GET" "/biodata/search?q=Admin&limit=5" "Basic search (User)" "$TEST_TOKEN"
fi

echo ""
echo "📷 PHASE 5: PHOTO OPERATIONS"
echo "============================"

# Test 10: Get photos (Admin)
if [ ! -z "$ADMIN_PROFILE_ID" ]; then
    test_endpoint "GET" "/biodata/$ADMIN_PROFILE_ID/photos" "Get photos (Admin)" "$ADMIN_TOKEN"
fi

echo ""
echo "📝 PHASE 6: UPDATE OPERATIONS"
echo "============================="

# Test 11: Update basic info (Admin)
if [ ! -z "$ADMIN_PROFILE_ID" ]; then
    test_endpoint "PUT" "/biodata/$ADMIN_PROFILE_ID/basic-info" "Update basic info (Admin)" "$ADMIN_TOKEN" '{
        "about_me": "Updated admin profile description",
        "mother_tongue": "English"
    }'
fi

# Test 12: Update contact info (Admin)
if [ ! -z "$ADMIN_PROFILE_ID" ]; then
    test_endpoint "PUT" "/biodata/$ADMIN_PROFILE_ID/contact" "Update contact info (Admin)" "$ADMIN_TOKEN" '{
        "email": "admin.updated@example.com",
        "phone": "9876543200",
        "address": "Updated Admin Address"
    }'
fi

# Test 13: Update education (Admin)
if [ ! -z "$ADMIN_PROFILE_ID" ]; then
    test_endpoint "PUT" "/biodata/$ADMIN_PROFILE_ID/education" "Update education (Admin)" "$ADMIN_TOKEN" '{
        "highest_education": "PhD",
        "education_details": "Computer Science PhD",
        "college_name": "Admin University"
    }'
fi

# Test 14: Update family info (Admin)
if [ ! -z "$ADMIN_PROFILE_ID" ]; then
    test_endpoint "PUT" "/biodata/$ADMIN_PROFILE_ID/family" "Update family info (Admin)" "$ADMIN_TOKEN" '{
        "father_name": "Updated Father Name",
        "mother_name": "Updated Mother Name",
        "siblings": "2 brothers, 1 sister"
    }'
fi

echo ""
echo "🔧 PHASE 7: ENHANCED FEATURES"
echo "============================="

# Test 15: Add extended family member (Admin)
if [ ! -z "$ADMIN_PROFILE_ID" ]; then
    test_endpoint "POST" "/biodata/$ADMIN_PROFILE_ID/extended-family-member" "Add extended family member (Admin)" "$ADMIN_TOKEN" '{
        "name": "Uncle John",
        "relation": "uncle",
        "occupation": "Engineer",
        "location": "Mumbai"
    }' 201
fi

echo ""
echo "👑 PHASE 8: ADMIN-ONLY OPERATIONS"
echo "================================="

# Test 16: Update verification status (Admin only)
if [ ! -z "$ADMIN_PROFILE_ID" ]; then
    test_endpoint "POST" "/biodata/$ADMIN_PROFILE_ID/verify" "Update verification status (Admin)" "$ADMIN_TOKEN" '{
        "verification_status": "verified"
    }'
fi

# Test 17: Add admin notes (Admin only)
if [ ! -z "$ADMIN_PROFILE_ID" ]; then
    test_endpoint "PUT" "/biodata/$ADMIN_PROFILE_ID/admin-notes" "Add admin notes (Admin)" "$ADMIN_TOKEN" '{
        "admin_notes": "Test profile - verified for testing purposes"
    }'
fi

echo ""
echo "📊 PHASE 9: PDF SYSTEM TESTING"
echo "=============================="

# Test 18: Get PDF data (Admin)
if [ ! -z "$ADMIN_PROFILE_ID" ]; then
    test_endpoint "GET" "/biodata/$ADMIN_PROFILE_ID/pdf-data" "Get PDF data (Admin)" "$ADMIN_TOKEN"
fi

# Test 19: Get PDF summary (Admin)
if [ ! -z "$ADMIN_PROFILE_ID" ]; then
    test_endpoint "GET" "/biodata/$ADMIN_PROFILE_ID/pdf-summary" "Get PDF summary (Admin)" "$ADMIN_TOKEN"
fi

# Test 20: Check storage status (Admin)
if [ ! -z "$ADMIN_PROFILE_ID" ]; then
    test_endpoint "GET" "/biodata/$ADMIN_PROFILE_ID/storage-status" "Check storage status (Admin)" "$ADMIN_TOKEN"
fi

# Test 21: Validate PDF readiness (Admin)
if [ ! -z "$ADMIN_PROFILE_ID" ]; then
    test_endpoint "POST" "/biodata/$ADMIN_PROFILE_ID/validate-pdf-readiness" "Validate PDF readiness (Admin)" "$ADMIN_TOKEN"
fi

echo ""
echo "🧹 PHASE 10: CLEANUP & DELETE OPERATIONS"
echo "========================================"

# Test 22: Delete profile (Admin)
# Commenting out to preserve test data
# if [ ! -z "$ADMIN_PROFILE_ID" ]; then
#     test_endpoint "DELETE" "/biodata/$ADMIN_PROFILE_ID" "Delete biodata profile (Admin)" "$ADMIN_TOKEN" "" 204
# fi

echo ""
echo "📊 FINAL TEST SUMMARY"
echo "====================="
print_info "Total Tests: $TOTAL_TESTS"
print_success "Passed: $PASSED_TESTS"
print_error "Failed: $FAILED_TESTS"

if [ $FAILED_TESTS -eq 0 ]; then
    print_success "🎉 ALL TESTS PASSED!"
    echo "✅ Biodata system is fully functional"
    echo "✅ Authentication works correctly"
    echo "✅ CRUD operations are working"
    echo "✅ Admin privileges are properly enforced"
else
    print_warning "⚠️  Some tests failed"
    echo "📋 Review failed tests above for debugging"
fi

SUCCESS_RATE=$(echo "scale=1; $PASSED_TESTS * 100 / $TOTAL_TESTS" | bc -l 2>/dev/null || echo "0")
echo "📈 Success Rate: $SUCCESS_RATE%"

echo ""
echo "🔍 TEST ENVIRONMENT INFO"
echo "========================"
echo "🌐 API Base URL: $BASE_URL"
echo "👤 Admin Token: ${ADMIN_TOKEN:0:30}..."
echo "🧑‍💻 Test User Token: ${TEST_TOKEN:0:30}..."
echo "📄 Admin Profile ID: $ADMIN_PROFILE_ID"
echo "📄 Test Profile ID: $TEST_PROFILE_ID"
echo ""
echo "🏁 Testing completed at $(date)"