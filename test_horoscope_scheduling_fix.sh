#!/bin/bash

# Test script for horoscope scheduling fix
# This script tests the scheduled publishing with proper IST timezone handling

BASE_URL="https://api.projectdevops.in"
# For local testing, use: BASE_URL="http://localhost:8000"

# Color output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}=== Horoscope Scheduling Fix Test ===${NC}"
echo "Testing IST timezone conversion and scheduled_publish flag clearing"
echo ""

# Check if TOKEN is set
if [ -z "$TOKEN" ]; then
    echo -e "${RED}Error: TOKEN environment variable not set${NC}"
    echo "Usage: TOKEN='your_jwt_token' ./test_horoscope_scheduling_fix.sh"
    exit 1
fi

# Generate a test date (tomorrow)
TOMORROW=$(date -v+1d +%Y-%m-%d 2>/dev/null || date -d "+1 day" +%Y-%m-%d)

# Generate a scheduled time (5 minutes from now in IST)
# First get current IST time and add 5 minutes
SCHEDULED_TIME=$(python3 -c "
from datetime import datetime, timedelta
import pytz
ist = pytz.timezone('Asia/Kolkata')
now_ist = datetime.now(ist)
scheduled = now_ist + timedelta(minutes=5)
print(scheduled.strftime('%Y-%m-%dT%H:%M'))
")

echo -e "${YELLOW}Test Parameters:${NC}"
echo "Date: $TOMORROW"
echo "Scheduled Time (IST): $SCHEDULED_TIME"
echo ""

# Create test horoscope with scheduling
echo -e "${YELLOW}Step 1: Creating scheduled horoscope...${NC}"
CREATE_RESPONSE=$(curl -s -X POST "$BASE_URL/news/admin/horoscope" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"title\": \"राशि फल✡️🙏🏻\",
    \"date\": \"$TOMORROW\",
    \"zodiac_predictions\": [
      {\"sign\": \"mesh\", \"hindi_name\": \"मेष राशि\", \"syllables\": \"चू, चे, चो, ला\", \"prediction\": \"Test prediction for Mesh\"},
      {\"sign\": \"vrishabh\", \"hindi_name\": \"वृषभ राशि\", \"syllables\": \"ई, उ, ए, ओ\", \"prediction\": \"Test prediction\"},
      {\"sign\": \"mithun\", \"hindi_name\": \"मिथुन राशि\", \"syllables\": \"का, की, कु\", \"prediction\": \"Test prediction\"},
      {\"sign\": \"kark\", \"hindi_name\": \"कर्क राशि\", \"syllables\": \"ही, हू, हे\", \"prediction\": \"Test prediction\"},
      {\"sign\": \"simha\", \"hindi_name\": \"सिंह राशि\", \"syllables\": \"मा, मी, मू\", \"prediction\": \"Test prediction\"},
      {\"sign\": \"kanya\", \"hindi_name\": \"कन्या राशि\", \"syllables\": \"पा, पी, पू\", \"prediction\": \"Test prediction\"},
      {\"sign\": \"tula\", \"hindi_name\": \"तुला राशि\", \"syllables\": \"रा, री, रू\", \"prediction\": \"Test prediction\"},
      {\"sign\": \"vrishchik\", \"hindi_name\": \"वृश्चिक राशि\", \"syllables\": \"ना, नी, नू\", \"prediction\": \"Test prediction\"},
      {\"sign\": \"dhanu\", \"hindi_name\": \"धनु राशि\", \"syllables\": \"या, यी, यू\", \"prediction\": \"Test prediction\"},
      {\"sign\": \"makar\", \"hindi_name\": \"मकर राशि\", \"syllables\": \"का, की, कु\", \"prediction\": \"Test prediction\"},
      {\"sign\": \"kumbh\", \"hindi_name\": \"कुम्भ राशि\", \"syllables\": \"गा, गी, गू\", \"prediction\": \"Test prediction\"},
      {\"sign\": \"meen\", \"hindi_name\": \"मीन राशि\", \"syllables\": \"दा, दी, दू\", \"prediction\": \"Test prediction\"}
    ],
    \"closing_message\": \"☘️आपका दिन मंगलमय हो।☘️\",
    \"published\": false,
    \"scheduled_publish\": true,
    \"scheduled_at\": \"$SCHEDULED_TIME\"
  }")

echo "$CREATE_RESPONSE" | python3 -m json.tool

HOROSCOPE_ID=$(echo "$CREATE_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('_id', ''))" 2>/dev/null)

if [ -z "$HOROSCOPE_ID" ]; then
    echo -e "${RED}Failed to create horoscope${NC}"
    exit 1
fi

echo -e "${GREEN}Horoscope created with ID: $HOROSCOPE_ID${NC}"
echo ""

# Check if scheduled correctly
echo -e "${YELLOW}Step 2: Verifying horoscope is scheduled...${NC}"
GET_RESPONSE=$(curl -s -X GET "$BASE_URL/news/admin/horoscope/$HOROSCOPE_ID" \
  -H "Authorization: Bearer $TOKEN")

echo "$GET_RESPONSE" | python3 -m json.tool

SCHEDULED_PUBLISH=$(echo "$GET_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('scheduled_publish', False))" 2>/dev/null)
PUBLISHED=$(echo "$GET_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('published', False))" 2>/dev/null)
SCHEDULED_AT_IST=$(echo "$GET_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('scheduled_at_ist', 'N/A'))" 2>/dev/null)

echo ""
echo -e "${YELLOW}Status Check:${NC}"
echo "scheduled_publish: $SCHEDULED_PUBLISH"
echo "published: $PUBLISHED"
echo "scheduled_at_ist: $SCHEDULED_AT_IST"

if [ "$SCHEDULED_PUBLISH" = "True" ] && [ "$PUBLISHED" = "False" ]; then
    echo -e "${GREEN}✓ Horoscope is correctly scheduled (unpublished)${NC}"
else
    echo -e "${RED}✗ Unexpected state: scheduled_publish=$SCHEDULED_PUBLISH, published=$PUBLISHED${NC}"
fi

echo ""
echo -e "${YELLOW}Step 3: Wait for scheduled time and check auto-publish...${NC}"
echo "Waiting 5 minutes for auto-publish to trigger..."
echo "You can manually trigger it by calling any public horoscope endpoint:"
echo "curl -X GET '$BASE_URL/news/horoscope/today'"
echo ""
echo -e "${YELLOW}After the scheduled time passes, verify:${NC}"
echo "1. The horoscope should be published (published: true)"
echo "2. The scheduled_publish flag should be cleared (scheduled_publish: false)"
echo "3. Check server logs for timezone conversion logs"
echo ""
echo -e "${GREEN}Test setup complete!${NC}"
echo ""
echo "Clean up command:"
echo "curl -X DELETE '$BASE_URL/news/admin/horoscope/$HOROSCOPE_ID' -H 'Authorization: Bearer $TOKEN'"
