#!/bin/bash

# Test Script for Scheduled Post Publication Time Fix
API_URL="https://api.projectdevops.in"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo "=========================================="
echo "Scheduled Post Publication Time - Test"
echo "=========================================="
echo ""

# Login as admin
echo -e "${YELLOW}Step 1: Logging in as admin...${NC}"
LOGIN_RESPONSE=$(curl -s -X POST "$API_URL/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin&password=Gyanu@9693894505")

ADMIN_TOKEN=$(echo $LOGIN_RESPONSE | grep -o '"access_token":"[^"]*' | cut -d'"' -f4)

if [ -z "$ADMIN_TOKEN" ]; then
    echo -e "${RED}❌ Login failed${NC}"
    exit 1
else
    echo -e "${GREEN}✅ Login successful${NC}"
fi
echo ""

# Create a scheduled post for 2 minutes from now
echo -e "${YELLOW}Step 2: Creating a scheduled post...${NC}"
echo "Scheduling post for 2 minutes from now..."

# Calculate scheduled time (2 minutes from now in IST)
# Get current UTC time, convert to IST (+5:30), add 2 minutes
SCHEDULED_TIME=$(python3 -c "
from datetime import datetime, timedelta
import pytz

utc_now = datetime.utcnow()
ist_tz = pytz.timezone('Asia/Kolkata')
ist_now = utc_now.replace(tzinfo=pytz.UTC).astimezone(ist_tz)
scheduled_ist = ist_now + timedelta(minutes=2)
print(scheduled_ist.strftime('%Y-%m-%dT%H:%M'))
")

echo "Scheduled time (IST): $SCHEDULED_TIME"
echo ""

# Create test image
echo "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==" | base64 -d > /tmp/test-scheduled.png

# Create the scheduled post
CREATE_RESPONSE=$(curl -s -X POST "$API_URL/news" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -F "title=Test Scheduled Post - $(date +%s)" \
  -F "content=This is a test scheduled post. It should appear as the latest post when published at scheduled time." \
  -F "custom_slug=test-scheduled-$(date +%s)" \
  -F "categories=Test" \
  -F "scheduled_publish=true" \
  -F "scheduled_at=$SCHEDULED_TIME" \
  -F "published=false" \
  -F "file=@/tmp/test-scheduled.png")

NEWS_ID=$(echo "$CREATE_RESPONSE" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('_id', ''))" 2>/dev/null)

if [ -z "$NEWS_ID" ]; then
    echo -e "${RED}❌ Failed to create scheduled post${NC}"
    echo "Response: $CREATE_RESPONSE"
    exit 1
else
    echo -e "${GREEN}✅ Scheduled post created${NC}"
    echo "News ID: $NEWS_ID"
    echo "Scheduled for: $SCHEDULED_TIME (IST)"
fi
echo ""

# Get the original created_at timestamp
ORIGINAL_CREATED=$(echo "$CREATE_RESPONSE" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('created_at', ''))" 2>/dev/null)
echo "Original created_at: $ORIGINAL_CREATED"
echo ""

echo -e "${YELLOW}Step 3: Waiting for scheduled publication...${NC}"
echo "Post will be auto-published in ~2 minutes"
echo "Checking every 15 seconds..."
echo ""

# Wait and check for publication
MAX_ATTEMPTS=12  # 12 * 15 seconds = 3 minutes
ATTEMPT=0

while [ $ATTEMPT -lt $MAX_ATTEMPTS ]; do
    ATTEMPT=$((ATTEMPT + 1))
    echo "Attempt $ATTEMPT/$MAX_ATTEMPTS - Checking status..."
    
    # Get the post details
    POST_RESPONSE=$(curl -s -X GET "$API_URL/news/$NEWS_ID" \
      -H "Authorization: Bearer $ADMIN_TOKEN")
    
    PUBLISHED=$(echo "$POST_RESPONSE" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('published', False))" 2>/dev/null)
    CREATED_AT=$(echo "$POST_RESPONSE" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('created_at', ''))" 2>/dev/null)
    
    if [ "$PUBLISHED" = "True" ]; then
        echo -e "${GREEN}✅ Post has been auto-published!${NC}"
        echo ""
        echo "Results:"
        echo "-------"
        echo "Original created_at: $ORIGINAL_CREATED"
        echo "Updated created_at:  $CREATED_AT"
        echo ""
        
        # Check if created_at was updated
        if [ "$ORIGINAL_CREATED" != "$CREATED_AT" ]; then
            echo -e "${GREEN}✅ SUCCESS: created_at was updated to scheduled time!${NC}"
            echo "The post will now appear as the latest post."
        else
            echo -e "${RED}❌ ISSUE: created_at was NOT updated${NC}"
            echo "The post will appear in chronological order of original creation."
        fi
        
        # Get latest news to verify ordering
        echo ""
        echo "Verifying post appears as latest..."
        LATEST_NEWS=$(curl -s -X GET "$API_URL/news?limit=1" \
          -H "Authorization: Bearer $ADMIN_TOKEN")
        
        LATEST_ID=$(echo "$LATEST_NEWS" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data[0].get('_id', '') if isinstance(data, list) and len(data) > 0 else '')" 2>/dev/null)
        
        if [ "$LATEST_ID" = "$NEWS_ID" ]; then
            echo -e "${GREEN}✅ Post appears as the latest news!${NC}"
        else
            echo -e "${YELLOW}⚠️  Post is not the latest (might be other newer posts)${NC}"
            echo "Latest post ID: $LATEST_ID"
            echo "Our post ID: $NEWS_ID"
        fi
        
        break
    else
        echo "Still scheduled... (published: $PUBLISHED)"
        sleep 15
    fi
done

if [ $ATTEMPT -eq $MAX_ATTEMPTS ]; then
    echo -e "${RED}❌ Post was not auto-published within 3 minutes${NC}"
    echo "This might be a server issue or the scheduled time hasn't arrived yet."
fi

# Cleanup
rm -f /tmp/test-scheduled.png

echo ""
echo "=========================================="
echo "Test Complete"
echo "=========================================="
