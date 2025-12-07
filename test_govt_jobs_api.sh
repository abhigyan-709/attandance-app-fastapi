#!/bin/bash

# Government Jobs API Testing Script
# Run after deployment to verify all endpoints work correctly

API_BASE="https://api.projectdevops.in/govt-jobs"
ADMIN_TOKEN="" # Add your admin JWT token here

echo "🧪 Testing Government Jobs API"
echo "================================"
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test counter
PASSED=0
FAILED=0

test_endpoint() {
    local name=$1
    local url=$2
    local method=${3:-GET}
    local auth=${4:-false}
    local data=${5:-}
    
    echo -n "Testing: $name ... "
    
    if [ "$auth" = "true" ]; then
        if [ -z "$ADMIN_TOKEN" ]; then
            echo -e "${YELLOW}SKIPPED${NC} (no admin token)"
            return
        fi
        headers="-H 'Authorization: Bearer $ADMIN_TOKEN'"
    else
        headers=""
    fi
    
    if [ -n "$data" ]; then
        response=$(eval curl -s -w "\n%{http_code}" -X $method "$url" $headers -H "Content-Type: application/json" -d "'$data'")
    else
        response=$(eval curl -s -w "\n%{http_code}" -X $method "$url" $headers)
    fi
    
    http_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | head -n-1)
    
    if [ "$http_code" -ge 200 ] && [ "$http_code" -lt 300 ]; then
        echo -e "${GREEN}✓ PASSED${NC} (HTTP $http_code)"
        ((PASSED++))
    else
        echo -e "${RED}✗ FAILED${NC} (HTTP $http_code)"
        echo "   Response: $body"
        ((FAILED++))
    fi
}

echo "📊 PUBLIC ENDPOINTS (No Authentication)"
echo "---------------------------------------"

test_endpoint "Dashboard Stats" "$API_BASE/stats/dashboard"
test_endpoint "List Jobs (default)" "$API_BASE/"
test_endpoint "List Jobs (with filters)" "$API_BASE/?status=Active&limit=10"
test_endpoint "Latest Jobs" "$API_BASE/latest/list?limit=5"
test_endpoint "Featured Jobs" "$API_BASE/featured/list?limit=5"
test_endpoint "Closing Soon Jobs" "$API_BASE/closing-soon/list?days=7"
test_endpoint "Get Categories" "$API_BASE/filter/categories"
test_endpoint "Get States" "$API_BASE/filter/states"
test_endpoint "Get Organizations" "$API_BASE/filter/organizations"

echo ""
echo "🔐 ADMIN ENDPOINTS (Authentication Required)"
echo "--------------------------------------------"

if [ -z "$ADMIN_TOKEN" ]; then
    echo -e "${YELLOW}⚠️  Skipping admin tests: No token provided${NC}"
    echo "To test admin endpoints:"
    echo "1. Login to get JWT token: curl -X POST https://api.projectdevops.in/login -d '{\"username\":\"admin\",\"password\":\"your_password\"}'"
    echo "2. Edit this script and add token to ADMIN_TOKEN variable"
    echo "3. Run script again"
else
    test_endpoint "Get All Jobs (Admin)" "$API_BASE/admin/all?page=1&limit=10" "GET" "true"
    test_endpoint "Check Slug Availability" "$API_BASE/admin/check-slug/test-slug" "GET" "true"
fi

echo ""
echo "📈 RESULTS"
echo "=========="
echo -e "Passed: ${GREEN}$PASSED${NC}"
echo -e "Failed: ${RED}$FAILED${NC}"
echo ""

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}✅ All tests passed!${NC}"
    echo ""
    echo "🎉 Government Jobs API is working correctly!"
    echo ""
    echo "Next Steps:"
    echo "1. Create MongoDB indexes (see GOVT_JOBS_SETUP_GUIDE.md)"
    echo "2. Create sample jobs using Swagger UI: https://api.projectdevops.in/docs"
    echo "3. Test job creation and listing"
    echo "4. Start frontend development using GOVT_JOBS_UI_GUIDE.md"
    exit 0
else
    echo -e "${RED}❌ Some tests failed. Please check the API deployment.${NC}"
    echo ""
    echo "Troubleshooting:"
    echo "1. Verify server is running: curl https://api.projectdevops.in/docs"
    echo "2. Check server logs for errors"
    echo "3. Ensure MongoDB connection is working"
    echo "4. Verify routes are registered in main.py"
    exit 1
fi
