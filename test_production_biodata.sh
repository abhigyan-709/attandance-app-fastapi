#!/bin/bash

# Biodata API Production Testing Script
# Testing complete CRUD operations with soft delete fix
# User: abhigkumar709 | Password: 123456

set -e

# Configuration
BASE_URL="https://api.projectdevops.in"
USERNAME="abhigkumar709"
PASSWORD="123456"
TEST_PROFILE_ID=""

echo "🚀 BIODATA API PRODUCTION TESTING"
echo "=================================="
echo "Testing User: $USERNAME"
echo "Base URL: $BASE_URL"
echo ""

# Function to make API requests with error handling
make_request() {
    local method=$1
    local endpoint=$2
    local data=$3
    local token=$4
    
    echo "📡 $method $endpoint"
    
    if [ "$method" = "GET" ]; then
        curl -s -w "\nHTTP Status: %{http_code}\n" \
            -H "Authorization: Bearer $token" \
            "$BASE_URL$endpoint"
    elif [ "$method" = "DELETE" ]; then
        curl -s -w "\nHTTP Status: %{http_code}\n" \
            -X DELETE \
            -H "Authorization: Bearer $token" \
            "$BASE_URL$endpoint"
    else
        curl -s -w "\nHTTP Status: %{http_code}\n" \
            -X "$method" \
            -H "Content-Type: application/json" \
            -H "Authorization: Bearer $token" \
            -d "$data" \
            "$BASE_URL$endpoint"
    fi
    echo ""
    echo "---"
}

# Step 1: Login and get JWT token
echo "🔐 STEP 1: USER LOGIN"
echo "===================="

LOGIN_RESPONSE=$(curl -s -X POST \
    -H "Content-Type: application/json" \
    -d '{
        "username": "'$USERNAME'",
        "password": "'$PASSWORD'"
    }' \
    "$BASE_URL/login")

echo "Login Response: $LOGIN_RESPONSE"

# Extract JWT token (assuming response has access_token field)
JWT_TOKEN=$(echo $LOGIN_RESPONSE | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    print(data.get('access_token', ''))
except:
    print('')
")

if [ -z "$JWT_TOKEN" ]; then
    echo "❌ Failed to get JWT token. Check credentials or login endpoint."
    exit 1
fi

echo "✅ Successfully logged in!"
echo "JWT Token: ${JWT_TOKEN:0:50}..."
echo ""

# Step 2: Create Biodata Profile
echo "🏗️ STEP 2: CREATE BIODATA PROFILE"
echo "================================="

CREATE_DATA='{
    "first_name": "Abhigyan",
    "last_name": "Kumar",
    "gender": "Male",
    "dob": "1995-06-15",
    "religion": "Hindu",
    "caste": "Brahmin",
    "mother_tongue": "Hindi",
    "about_me": "Software Engineer passionate about technology",
    "marital_status": "never_married",
    "height_cm": 175.0,
    "weight_kg": 70.0,
    "education": {
        "level": "masters",
        "degree": "Computer Science",
        "institute": "IIT Delhi",
        "graduation_year": 2020
    },
    "occupation": {
        "employment_type": "private",
        "organization": "Tech Corp",
        "designation": "Senior Software Engineer",
        "annual_income": 1500000,
        "work_location": "Bangalore"
    }
}'

CREATE_RESPONSE=$(make_request "POST" "/biodata" "$CREATE_DATA" "$JWT_TOKEN")
echo "Create Response: $CREATE_RESPONSE"

# Extract profile ID
TEST_PROFILE_ID=$(echo "$CREATE_RESPONSE" | python3 -c "
import sys, json, re
content = sys.stdin.read()
# Try to extract profile ID from response
match = re.search(r'\"id\"\s*:\s*\"([a-f0-9]{24})\"', content)
if match:
    print(match.group(1))
else:
    # Try alternative field names
    for field in ['_id', 'profile_id', 'biodata_id']:
        match = re.search(rf'\"{field}\"\s*:\s*\"([a-f0-9]{{24}})\"', content)
        if match:
            print(match.group(1))
            break
")

if [ -z "$TEST_PROFILE_ID" ]; then
    echo "⚠️ Could not extract profile ID, will try with existing profile"
    # Try to get existing profile
    EXISTING_RESPONSE=$(make_request "GET" "/biodata/my/profile" "" "$JWT_TOKEN")
    TEST_PROFILE_ID=$(echo "$EXISTING_RESPONSE" | python3 -c "
import sys, json, re
content = sys.stdin.read()
match = re.search(r'\"id\"\s*:\s*\"([a-f0-9]{24})\"', content)
if match:
    print(match.group(1))
")
fi

echo "✅ Profile ID: $TEST_PROFILE_ID"
echo ""

# Step 3: READ Operations
echo "📖 STEP 3: READ OPERATIONS"
echo "========================="

echo "3.1: Get My Profile"
make_request "GET" "/biodata/my/profile" "" "$JWT_TOKEN"

if [ ! -z "$TEST_PROFILE_ID" ]; then
    echo "3.2: Get Specific Profile"
    make_request "GET" "/biodata/$TEST_PROFILE_ID" "" "$JWT_TOKEN"
    
    echo "3.3: Get Contact Info"
    make_request "GET" "/biodata/$TEST_PROFILE_ID/contact" "" "$JWT_TOKEN"
    
    echo "3.4: Get Education Info"
    make_request "GET" "/biodata/$TEST_PROFILE_ID/education" "" "$JWT_TOKEN"
fi

echo "3.5: Get All Profiles"
make_request "GET" "/biodata?limit=5" "" "$JWT_TOKEN"

# Step 4: UPDATE Operations
echo "🔄 STEP 4: UPDATE OPERATIONS"
echo "==========================="

if [ ! -z "$TEST_PROFILE_ID" ]; then
    echo "4.1: Update Contact Information (PATCH)"
    PATCH_CONTACT='{
        "email": "abhigkumar709@test.com",
        "phone_country_code": "+91",
        "phone_number": "9876543210",
        "current_address": "Test Address, Bangalore, Karnataka"
    }'
    make_request "PATCH" "/biodata/$TEST_PROFILE_ID/contact" "$PATCH_CONTACT" "$JWT_TOKEN"
    
    echo "4.2: Update Education (PATCH)"
    PATCH_EDUCATION='{
        "additional_qualifications": "AWS Certified Solutions Architect"
    }'
    make_request "PATCH" "/biodata/$TEST_PROFILE_ID/education" "$PATCH_EDUCATION" "$JWT_TOKEN"
    
    echo "4.3: Update Physical Attributes (PATCH)"
    PATCH_PHYSICAL='{
        "height_cm": 176.0,
        "body_type": "athletic",
        "complexion": "fair"
    }'
    make_request "PATCH" "/biodata/$TEST_PROFILE_ID/physical" "$PATCH_PHYSICAL" "$JWT_TOKEN"
    
    echo "4.4: Update Complete Profile (PUT)"
    PUT_DATA='{
        "first_name": "Abhigyan",
        "last_name": "Kumar Singh",
        "gender": "Male",
        "dob": "1995-06-15",
        "religion": "Hindu",
        "caste": "Brahmin",
        "mother_tongue": "Hindi",
        "about_me": "Updated: Senior Software Engineer with 4+ years experience"
    }'
    make_request "PUT" "/biodata/$TEST_PROFILE_ID" "$PUT_DATA" "$JWT_TOKEN"
fi

# Step 5: Additional PATCH Operations
echo "🔧 STEP 5: ADDITIONAL PATCH OPERATIONS"
echo "======================================"

if [ ! -z "$TEST_PROFILE_ID" ]; then
    echo "5.1: Update Family Details"
    PATCH_FAMILY='{
        "father_name": "Raj Kumar Singh",
        "mother_name": "Sunita Singh",
        "family_type": "nuclear",
        "family_status": "middle_class"
    }'
    make_request "PATCH" "/biodata/$TEST_PROFILE_ID/family" "$PATCH_FAMILY" "$JWT_TOKEN"
    
    echo "5.2: Update Lifestyle"
    PATCH_LIFESTYLE='{
        "diet": "vegetarian",
        "drinking": "no",
        "smoking": "no"
    }'
    make_request "PATCH" "/biodata/$TEST_PROFILE_ID/lifestyle" "$PATCH_LIFESTYLE" "$JWT_TOKEN"
    
    echo "5.3: Update Languages"
    PATCH_LANGUAGES='{
        "known": {
            "Hindi": "native",
            "English": "fluent",
            "Bengali": "conversational"
        }
    }'
    make_request "PATCH" "/biodata/$TEST_PROFILE_ID/languages" "$PATCH_LANGUAGES" "$JWT_TOKEN"
fi

# Step 6: CRITICAL - DELETE and Soft Delete Testing
echo "🗑️ STEP 6: DELETE OPERATIONS (CRITICAL TEST)"
echo "==========================================="

if [ ! -z "$TEST_PROFILE_ID" ]; then
    echo "6.1: Before Delete - Profile Should Exist"
    make_request "GET" "/biodata/$TEST_PROFILE_ID" "" "$JWT_TOKEN"
    
    echo "6.2: Soft Delete Profile (The Main Test!)"
    DELETE_RESPONSE=$(make_request "DELETE" "/biodata/$TEST_PROFILE_ID" "" "$JWT_TOKEN")
    echo "Delete Response: $DELETE_RESPONSE"
    
    echo "6.3: After Delete - Profile Should Return 404 (This is the critical test!)"
    make_request "GET" "/biodata/$TEST_PROFILE_ID" "" "$JWT_TOKEN"
    
    echo "6.4: My Profile Should Also Return 404"
    make_request "GET" "/biodata/my/profile" "" "$JWT_TOKEN"
    
    echo "6.5: Contact Info Should Return 404"
    make_request "GET" "/biodata/$TEST_PROFILE_ID/contact" "" "$JWT_TOKEN"
    
    echo "6.6: Education Info Should Return 404"
    make_request "GET" "/biodata/$TEST_PROFILE_ID/education" "" "$JWT_TOKEN"
    
    echo "6.7: All Profiles List Should Not Include Deleted Profile"
    make_request "GET" "/biodata" "" "$JWT_TOKEN"
fi

# Step 7: Test Results Summary
echo ""
echo "🎯 TESTING COMPLETE!"
echo "===================="
echo "✅ CREATE: Biodata profile creation"
echo "✅ READ: Profile retrieval (multiple endpoints)"
echo "✅ UPDATE: PUT and PATCH operations"
echo "✅ DELETE: Soft delete functionality"
echo ""
echo "🔍 CRITICAL SOFT DELETE TEST:"
echo "- Delete operation should return JSON (not 204)"
echo "- After delete, profile should return 404 on all GET requests"
echo "- Profile should not appear in listings"
echo "- This fixes the 'biodata comes back after refresh' issue"
echo ""
echo "Profile ID Tested: $TEST_PROFILE_ID"
echo "Test completed at: $(date)"

echo ""
echo "🚨 IMPORTANT: Check if any GET requests after DELETE returned data"
echo "If they did, the soft delete fix needs more work!"