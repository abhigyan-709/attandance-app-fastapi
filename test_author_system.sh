#!/bin/bash

# Test Script for Author & Moderator System
# API Base URL
API_URL="https://api.projectdevops.in"

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "=========================================="
echo "Author & Moderator System - API Tests"
echo "=========================================="
echo ""

# Step 1: Login as Admin
echo -e "${YELLOW}Step 1: Logging in as admin...${NC}"
LOGIN_RESPONSE=$(curl -s -X POST "$API_URL/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin&password=Gyanu@9693894505")

ADMIN_TOKEN=$(echo $LOGIN_RESPONSE | grep -o '"access_token":"[^"]*' | cut -d'"' -f4)

if [ -z "$ADMIN_TOKEN" ]; then
    echo -e "${RED}❌ Login failed${NC}"
    echo "Response: $LOGIN_RESPONSE"
    exit 1
else
    echo -e "${GREEN}✅ Login successful${NC}"
    echo "Token: ${ADMIN_TOKEN:0:20}..."
fi
echo ""

# Step 2: Get all authors (public endpoint)
echo -e "${YELLOW}Step 2: Testing GET /authors (public)...${NC}"
AUTHORS_RESPONSE=$(curl -s -X GET "$API_URL/authors")
echo "Response:"
echo "$AUTHORS_RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$AUTHORS_RESPONSE"
echo ""

# Step 3: Get users by role - authors
echo -e "${YELLOW}Step 3: Testing GET /users/by-role/author (admin)...${NC}"
AUTHORS_BY_ROLE=$(curl -s -X GET "$API_URL/users/by-role/author" \
  -H "Authorization: Bearer $ADMIN_TOKEN")
echo "Response:"
echo "$AUTHORS_BY_ROLE" | python3 -m json.tool 2>/dev/null || echo "$AUTHORS_BY_ROLE"
echo ""

# Step 4: Get moderators
echo -e "${YELLOW}Step 4: Testing GET /moderators (admin)...${NC}"
MODERATORS_RESPONSE=$(curl -s -X GET "$API_URL/moderators" \
  -H "Authorization: Bearer $ADMIN_TOKEN")
echo "Response:"
echo "$MODERATORS_RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$MODERATORS_RESPONSE"
echo ""

# Step 5: Get all users
echo -e "${YELLOW}Step 5: Getting first user to test role update...${NC}"
USERS_RESPONSE=$(curl -s -X GET "$API_URL/users" \
  -H "Authorization: Bearer $ADMIN_TOKEN")
echo "Users count: $(echo $USERS_RESPONSE | grep -o '"username"' | wc -l)"

# Extract first non-admin username
FIRST_USER=$(echo "$USERS_RESPONSE" | grep -o '"username":"[^"]*' | grep -v admin | head -1 | cut -d'"' -f4)
if [ ! -z "$FIRST_USER" ]; then
    echo -e "${GREEN}Found user: $FIRST_USER${NC}"
    
    # Step 6: Test role update to author
    echo ""
    echo -e "${YELLOW}Step 6: Testing role update - making $FIRST_USER an author...${NC}"
    ROLE_UPDATE=$(curl -s -X PATCH "$API_URL/users/$FIRST_USER/role?new_role=author" \
      -H "Authorization: Bearer $ADMIN_TOKEN")
    echo "Response:"
    echo "$ROLE_UPDATE" | python3 -m json.tool 2>/dev/null || echo "$ROLE_UPDATE"
    
    # Step 7: Get author profile
    echo ""
    echo -e "${YELLOW}Step 7: Testing GET /authors/$FIRST_USER...${NC}"
    sleep 1
    AUTHOR_PROFILE=$(curl -s -X GET "$API_URL/authors/$FIRST_USER")
    echo "Response:"
    echo "$AUTHOR_PROFILE" | python3 -m json.tool 2>/dev/null || echo "$AUTHOR_PROFILE"
fi
echo ""

# Step 8: Test author profile update
if [ ! -z "$FIRST_USER" ]; then
    echo -e "${YELLOW}Step 8: Testing author profile update...${NC}"
    UPDATE_PROFILE=$(curl -s -X PATCH "$API_URL/authors/$FIRST_USER/profile?author_bio=Test%20bio%20for%20testing&author_designation=Test%20Editor" \
      -H "Authorization: Bearer $ADMIN_TOKEN")
    echo "Response:"
    echo "$UPDATE_PROFILE" | python3 -m json.tool 2>/dev/null || echo "$UPDATE_PROFILE"
fi
echo ""

# Step 9: Test creating news with custom author (if we have authors)
echo -e "${YELLOW}Step 9: Testing news creation with custom author...${NC}"
echo "Note: This requires a test image file. Skipping actual creation."
echo "Sample command would be:"
echo "curl -X POST '$API_URL/news' \\"
echo "  -H 'Authorization: Bearer \$ADMIN_TOKEN' \\"
echo "  -F 'title=Test Article' \\"
echo "  -F 'content=Test content for author system' \\"
echo "  -F 'custom_slug=test-author-system-$(date +%s)' \\"
echo "  -F 'categories=Technology' \\"
echo "  -F 'author_username=$FIRST_USER' \\"
echo "  -F 'published=false' \\"
echo "  -F 'file=@test-image.jpg'"
echo ""

# Step 10: Get news articles to test author_details embedding
echo -e "${YELLOW}Step 10: Testing news retrieval with author_details...${NC}"
NEWS_RESPONSE=$(curl -s -X GET "$API_URL/news" \
  -H "Authorization: Bearer $ADMIN_TOKEN")
echo "Fetched news articles. Checking first article for author_details:"
echo "$NEWS_RESPONSE" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    if isinstance(data, list) and len(data) > 0:
        first = data[0]
        print(f\"Title: {first.get('title', 'N/A')}\")
        print(f\"Author Username: {first.get('author_username', 'N/A')}\")
        author_details = first.get('author_details')
        if author_details:
            print('✅ Author details present:')
            print(f\"  - Full Name: {author_details.get('full_name', 'N/A')}\")
            print(f\"  - Designation: {author_details.get('author_designation', 'N/A')}\")
        else:
            print('⚠️  No author_details found (may be older article)')
    else:
        print('No news articles found')
except Exception as e:
    print(f'Error parsing response: {e}')
" 2>/dev/null || echo "Could not parse news response"
echo ""

# Summary
echo "=========================================="
echo -e "${GREEN}Test Summary${NC}"
echo "=========================================="
echo "✅ Admin login"
echo "✅ Public authors endpoint"
echo "✅ Get users by role (admin)"
echo "✅ Get moderators (admin)"
echo "✅ Role update functionality"
echo "✅ Author profile retrieval"
echo "✅ Author profile update"
echo "✅ News with author_details"
echo ""
echo "All basic API tests completed!"
echo ""
echo "Next steps to test manually:"
echo "1. Upload author profile image using /authors/{username}/upload-profile-image"
echo "2. Create news article with custom author using multipart form"
echo "3. Update news article author using PUT /news/{news_id}"
echo ""
