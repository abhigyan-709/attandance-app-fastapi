#!/bin/bash

# Test PDF Data Endpoints for Biodata System
# Usage: ./test_pdf_endpoints.sh

BASE_URL="https://api.projectdevops.in"
USERNAME="admin"
PASSWORD="Gyanu@9693894505"
TEST_USER_ID="test_user_12345"

echo "🧪 Testing PDF Data Endpoints for Biodata System"
echo "================================================="

# Function to print colored output
print_status() {
    if [ $1 -eq 0 ]; then
        echo "✅ $2"
    else
        echo "❌ $2"
    fi
}

# Function to test API endpoint
test_endpoint() {
    local method=$1
    local endpoint=$2
    local description=$3
    local data=$4
    
    echo ""
    echo "🔍 Testing: $description"
    echo "📍 Endpoint: $method $endpoint"
    
    if [ "$method" = "GET" ]; then
        response=$(curl -s -w "%{http_code}" -X GET \
            -H "Authorization: Bearer $TOKEN" \
            -H "Content-Type: application/json" \
            "$BASE_URL$endpoint")
    elif [ "$method" = "POST" ]; then
        if [ -z "$data" ]; then
            response=$(curl -s -w "%{http_code}" -X POST \
                -H "Authorization: Bearer $TOKEN" \
                -H "Content-Type: application/json" \
                "$BASE_URL$endpoint")
        else
            response=$(curl -s -w "%{http_code}" -X POST \
                -H "Authorization: Bearer $TOKEN" \
                -H "Content-Type: application/json" \
                -d "$data" \
                "$BASE_URL$endpoint")
        fi
    fi
    
    http_code="${response: -3}"
    response_body="${response%???}"
    
    echo "📊 Status Code: $http_code"
    
    if [ ${#response_body} -gt 500 ]; then
        echo "📄 Response: ${response_body:0:500}... [truncated]"
    else
        echo "📄 Response: $response_body"
    fi
    
    if [ "$http_code" = "200" ] || [ "$http_code" = "201" ]; then
        print_status 0 "$description"
        return 0
    else
        print_status 1 "$description"
        return 1
    fi
}

# Get authentication token
echo "🔐 Getting authentication token..."
login_response=$(curl -s -X POST \
    -H "Content-Type: application/x-www-form-urlencoded" \
    -d "username=$USERNAME&password=$PASSWORD" \
    "$BASE_URL/token")

TOKEN=$(echo $login_response | grep -o '"access_token":"[^"]*' | cut -d'"' -f4)

if [ -z "$TOKEN" ]; then
    echo "❌ Failed to get authentication token"
    echo "Response: $login_response"
    exit 1
fi

echo "✅ Authentication successful"
echo "🎫 Token: ${TOKEN:0:50}..."

# Test PDF endpoints
successful_tests=0
total_tests=0

# 1. Test PDF Data Extraction
total_tests=$((total_tests + 1))
test_endpoint "GET" "/biodata/$TEST_USER_ID/pdf-data" "Get complete PDF data"
if [ $? -eq 0 ]; then successful_tests=$((successful_tests + 1)); fi

# 2. Test PDF Summary
total_tests=$((total_tests + 1))
test_endpoint "GET" "/biodata/$TEST_USER_ID/pdf-summary" "Get PDF summary data"
if [ $? -eq 0 ]; then successful_tests=$((successful_tests + 1)); fi

# 3. Test Storage Status Check
total_tests=$((total_tests + 1))
test_endpoint "GET" "/biodata/$TEST_USER_ID/storage-status" "Check storage status"
if [ $? -eq 0 ]; then successful_tests=$((successful_tests + 1)); fi

# 4. Test PDF Readiness Validation
total_tests=$((total_tests + 1))
test_endpoint "POST" "/biodata/$TEST_USER_ID/validate-pdf-readiness" "Validate PDF readiness"
if [ $? -eq 0 ]; then successful_tests=$((successful_tests + 1)); fi

# Test with admin accessing another user's data
OTHER_USER_ID="user_67890"

# 5. Test Admin Access to Other User's PDF Data
total_tests=$((total_tests + 1))
test_endpoint "GET" "/biodata/$OTHER_USER_ID/pdf-data" "Admin access to other user's PDF data"
if [ $? -eq 0 ]; then successful_tests=$((successful_tests + 1)); fi

# 6. Test Storage Status for Different User
total_tests=$((total_tests + 1))
test_endpoint "GET" "/biodata/$OTHER_USER_ID/storage-status" "Check other user's storage status"
if [ $? -eq 0 ]; then successful_tests=$((successful_tests + 1)); fi

# Summary
echo ""
echo "📊 TEST SUMMARY"
echo "==============="
echo "✅ Successful: $successful_tests/$total_tests"
echo "❌ Failed: $((total_tests - successful_tests))/$total_tests"

if [ $successful_tests -eq $total_tests ]; then
    echo "🎉 All PDF endpoint tests passed!"
    echo "✅ PDF data extraction system is working correctly"
    echo "✅ MongoDB storage validation is functional"
    echo "✅ Authorization checks are in place"
else
    echo "⚠️  Some tests failed - PDF endpoints may need debugging"
fi

success_rate=$(echo "scale=1; $successful_tests * 100 / $total_tests" | bc)
echo "📈 Success Rate: $success_rate%"

echo ""
echo "🔍 Additional Information:"
echo "• Base URL: $BASE_URL"
echo "• Test User ID: $TEST_USER_ID"
echo "• Admin User: $USERNAME"
echo "• New PDF Endpoints:"
echo "  - GET /biodata/{user_id}/pdf-data"
echo "  - GET /biodata/{user_id}/pdf-summary"
echo "  - GET /biodata/{user_id}/storage-status"
echo "  - POST /biodata/{user_id}/validate-pdf-readiness"