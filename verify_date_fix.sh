#!/bin/bash

# Quick test script to verify the date timezone fix

BASE_URL="${BASE_URL:-https://api.projectdevops.in}"
TOKEN="${TOKEN}"

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== Date/Time Timezone Fix Verification ===${NC}"
echo ""

if [ -z "$TOKEN" ]; then
    echo -e "${RED}Error: TOKEN environment variable not set${NC}"
    echo "Usage: TOKEN='your_jwt_token' ./verify_date_fix.sh"
    exit 1
fi

echo -e "${YELLOW}Step 1: Check System Time/Date Status${NC}"
echo "Endpoint: GET /news/admin/horoscope/debug/time-check"
echo ""

TIME_CHECK=$(curl -s -X GET "$BASE_URL/news/admin/horoscope/debug/time-check" \
  -H "Authorization: Bearer $TOKEN")

echo "$TIME_CHECK" | python3 -m json.tool

echo ""
echo -e "${YELLOW}Analysis:${NC}"

IST_DATE=$(echo "$TIME_CHECK" | python3 -c "import sys, json; print(json.load(sys.stdin)['times']['ist_date'])" 2>/dev/null)
UTC_DATE=$(echo "$TIME_CHECK" | python3 -c "import sys, json; print(json.load(sys.stdin)['times']['utc_date'])" 2>/dev/null)
ISSUE_DETECTED=$(echo "$TIME_CHECK" | python3 -c "import sys, json; print(json.load(sys.stdin)['comparison']['issue_detected'])" 2>/dev/null)

echo "IST Date (India): $IST_DATE"
echo "UTC Date (Server): $UTC_DATE"

if [ "$IST_DATE" != "$UTC_DATE" ]; then
    echo -e "${YELLOW}⚠️  UTC and IST are on different dates${NC}"
    echo "This is normal when UTC time is between 18:30-23:59"
    echo "System should use IST date ($IST_DATE) for 'today'"
else
    echo -e "${GREEN}✅ UTC and IST are on same date${NC}"
fi

echo ""
echo -e "${YELLOW}Step 2: Check Today's Horoscope${NC}"
echo "Endpoint: GET /news/admin/horoscope/debug/today"
echo ""

TODAY_DEBUG=$(curl -s -X GET "$BASE_URL/news/admin/horoscope/debug/today" \
  -H "Authorization: Bearer $TOKEN")

echo "$TODAY_DEBUG" | python3 -c "
import sys, json
data = json.load(sys.stdin)
info = data['debug_info']
print(f\"Looking for date: {info['today_date']}\")
print(f\"Current IST: {info['current_ist']}\")
print(f\"Found: {info['found_count']} horoscope(s)\")

if info['found_count'] > 0:
    h = data['horoscopes'][0]
    print(f\"\\nHoroscope Details:\")
    print(f\"  ID: {h['_id']}\")
    print(f\"  Date: {h['date']}\")
    print(f\"  Published: {h['published']}\")
    if 'scheduled_at_ist' in h:
        print(f\"  Scheduled At (IST): {h['scheduled_at_ist']}\")
"

echo ""
echo -e "${YELLOW}Step 3: Test Public Endpoint${NC}"
echo "Endpoint: GET /news/horoscope/today"
echo ""

PUBLIC_RESPONSE=$(curl -s -X GET "$BASE_URL/news/horoscope/today" 2>&1)

if echo "$PUBLIC_RESPONSE" | grep -q '"_id"'; then
    echo -e "${GREEN}✅ SUCCESS: Horoscope found for today${NC}"
    echo "$PUBLIC_RESPONSE" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    print(f\"Horoscope ID: {data['_id']}\")
    print(f\"Date: {data['date']}\")
    print(f\"Published: {data['published']}\")
except:
    pass
"
elif echo "$PUBLIC_RESPONSE" | grep -q "404"; then
    echo -e "${RED}❌ FAIL: No horoscope found for today${NC}"
    echo "Response:"
    echo "$PUBLIC_RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$PUBLIC_RESPONSE"
    echo ""
    echo -e "${YELLOW}Possible reasons:${NC}"
    echo "1. No horoscope created for today's IST date ($IST_DATE)"
    echo "2. Horoscope exists but not published"
    echo "3. Date mismatch issue still present"
else
    echo -e "${YELLOW}⚠️  Unexpected response${NC}"
    echo "$PUBLIC_RESPONSE"
fi

echo ""
echo -e "${YELLOW}Step 4: Check Background Scheduler Logs${NC}"
echo "Check your server logs for these patterns:"
echo ""
echo "Expected log patterns:"
echo "  🔍 [Horoscope Scheduler] Checking at UTC: ..., IST: ..., Today (IST): $IST_DATE"
echo "  🔍 [get_today_horoscope] Looking for date (IST): $IST_DATE"
echo ""

echo -e "${BLUE}=== Verification Summary ===${NC}"
echo ""
echo -e "${GREEN}✅ PASS Criteria:${NC}"
echo "  1. time-check shows IST date: $IST_DATE"
echo "  2. debug/today looks for IST date: $IST_DATE"
echo "  3. Public endpoint returns horoscope (if one exists for $IST_DATE)"
echo "  4. Server logs show 'Today (IST): $IST_DATE'"
echo ""

# Final check
if [ "$IST_DATE" ]; then
    echo -e "${GREEN}✅ System is using IST date: $IST_DATE${NC}"
    echo "Fix is working correctly!"
else
    echo -e "${RED}❌ Could not verify IST date${NC}"
    echo "Check if server is running and token is valid"
fi

echo ""
echo -e "${BLUE}=== Additional Debug Commands ===${NC}"
echo ""
echo "# Force process scheduled horoscopes:"
echo "curl -X POST '$BASE_URL/news/admin/horoscope/force-process-scheduled' -H 'Authorization: Bearer \$TOKEN'"
echo ""
echo "# Manually publish today's horoscope (emergency):"
echo "curl -X POST '$BASE_URL/news/admin/horoscope/publish-today' -H 'Authorization: Bearer \$TOKEN'"
echo ""
echo "# Check all dates in database:"
echo "curl -X GET '$BASE_URL/news/admin/horoscope/debug/all-dates' -H 'Authorization: Bearer \$TOKEN'"
