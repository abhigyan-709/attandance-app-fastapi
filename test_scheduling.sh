#!/bin/bash

# Test News Scheduling Feature
# Testing with live API: api.projectdevops.in

TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VybmFtZSI6ImFkbWluIiwic3ViIjoiYWRtaW4iLCJleHAiOjE3NjQ4ODIwMDN9.hylKPr-GwYIK9zGTtguUE7QsYM9f_d_lOlJd5koPs9E"
API_URL="https://api.projectdevops.in"

# Create test file
echo "test" > /tmp/test.txt

echo "════════════════════════════════════════════════════════════"
echo "  Testing News Draft & Scheduling Feature"
echo "════════════════════════════════════════════════════════════"
echo ""

# Test 1: Create Draft Post
echo "📝 Test 1: Creating Draft Post..."
echo "───────────────────────────────────────────────────────────"
DRAFT_RESPONSE=$(curl -s -X POST "$API_URL/news" \
  -H "Authorization: Bearer $TOKEN" \
  -F "title=Draft Test - Dec 5" \
  -F "summary=This is a draft post" \
  -F "content=<p>Draft content - should not be public</p>" \
  -F "slug=draft-test-dec5" \
  -F "published=false" \
  -F "scheduled_publish=false" \
  -F "categories=Test" \
  -F "file=@/tmp/test.txt")

DRAFT_ID=$(echo "$DRAFT_RESPONSE" | python3 -c "import sys, json; d=json.load(sys.stdin); print(d.get('_id', 'ERROR'))" 2>/dev/null)
DRAFT_PUBLISHED=$(echo "$DRAFT_RESPONSE" | python3 -c "import sys, json; d=json.load(sys.stdin); print(d.get('published', 'ERROR'))" 2>/dev/null)

if [ "$DRAFT_ID" != "ERROR" ]; then
    echo "✅ Draft created successfully!"
    echo "   ID: $DRAFT_ID"
    echo "   Published: $DRAFT_PUBLISHED"
else
    echo "❌ Failed to create draft"
    echo "$DRAFT_RESPONSE"
fi
echo ""

# Test 2: Create Scheduled Post (5 minutes from now)
echo "🕒 Test 2: Creating Scheduled Post..."
echo "───────────────────────────────────────────────────────────"
FUTURE_TIME=$(python3 -c "from datetime import datetime, timedelta; import pytz; ist = pytz.timezone('Asia/Kolkata'); future = datetime.now(ist) + timedelta(minutes=5); print(future.strftime('%Y-%m-%dT%H:%M'))")
echo "   Scheduled for: $FUTURE_TIME IST"

SCHEDULED_RESPONSE=$(curl -s -X POST "$API_URL/news" \
  -H "Authorization: Bearer $TOKEN" \
  -F "title=Scheduled Test - Dec 5" \
  -F "summary=This post is scheduled" \
  -F "content=<p>Scheduled content - will publish at scheduled time</p>" \
  -F "slug=scheduled-test-dec5" \
  -F "published=false" \
  -F "scheduled_publish=true" \
  -F "scheduled_at=$FUTURE_TIME" \
  -F "categories=Test" \
  -F "file=@/tmp/test.txt")

SCHEDULED_ID=$(echo "$SCHEDULED_RESPONSE" | python3 -c "import sys, json; d=json.load(sys.stdin); print(d.get('_id', 'ERROR'))" 2>/dev/null)
SCHEDULED_AT=$(echo "$SCHEDULED_RESPONSE" | python3 -c "import sys, json; d=json.load(sys.stdin); print(d.get('scheduled_at', 'ERROR'))" 2>/dev/null)
SCHEDULED_PUBLISH=$(echo "$SCHEDULED_RESPONSE" | python3 -c "import sys, json; d=json.load(sys.stdin); print(d.get('scheduled_publish', 'ERROR'))" 2>/dev/null)

if [ "$SCHEDULED_ID" != "ERROR" ]; then
    echo "✅ Scheduled post created!"
    echo "   ID: $SCHEDULED_ID"
    echo "   Scheduled At (UTC): $SCHEDULED_AT"
    echo "   Scheduled Publish: $SCHEDULED_PUBLISH"
else
    echo "❌ Failed to create scheduled post"
    echo "$SCHEDULED_RESPONSE"
fi
echo ""

# Test 3: Get Scheduled Posts List
echo "📋 Test 3: Getting Scheduled Posts..."
echo "───────────────────────────────────────────────────────────"
SCHEDULED_LIST=$(curl -s -X GET "$API_URL/news/scheduled" \
  -H "Authorization: Bearer $TOKEN")

SCHEDULED_COUNT=$(echo "$SCHEDULED_LIST" | python3 -c "import sys, json; d=json.load(sys.stdin); print(len(d))" 2>/dev/null)

if [ "$SCHEDULED_COUNT" != "" ]; then
    echo "✅ Retrieved scheduled posts"
    echo "   Total scheduled: $SCHEDULED_COUNT"
    echo "$SCHEDULED_LIST" | python3 -c "import sys, json; posts=json.load(sys.stdin); [print(f\"   - {p['title']} (ID: {p['_id']})\") for p in posts[:3]]" 2>/dev/null
else
    echo "❌ Failed to get scheduled posts"
fi
echo ""

# Test 4: Verify Draft Not Public
echo "🔒 Test 4: Verifying Draft Not Public..."
echo "───────────────────────────────────────────────────────────"
PUBLIC_LIST=$(curl -s -X GET "$API_URL/news" | python3 -c "import sys, json; posts=json.load(sys.stdin); print([p['_id'] for p in posts if p.get('_id') == '$DRAFT_ID'])" 2>/dev/null)

if [ "$PUBLIC_LIST" == "[]" ]; then
    echo "✅ Draft not visible in public list"
else
    echo "⚠️  Draft may be visible in public list"
fi
echo ""

# Test 5: Update Scheduled Time
if [ "$SCHEDULED_ID" != "ERROR" ]; then
    echo "🔄 Test 5: Updating Scheduled Time..."
    echo "───────────────────────────────────────────────────────────"
    NEW_TIME=$(python3 -c "from datetime import datetime, timedelta; import pytz; ist = pytz.timezone('Asia/Kolkata'); future = datetime.now(ist) + timedelta(minutes=10); print(future.strftime('%Y-%m-%dT%H:%M'))")
    echo "   New time: $NEW_TIME IST"
    
    UPDATE_RESPONSE=$(curl -s -X PUT "$API_URL/news/$SCHEDULED_ID" \
      -H "Authorization: Bearer $TOKEN" \
      -F "scheduled_at=$NEW_TIME")
    
    NEW_SCHEDULED_AT=$(echo "$UPDATE_RESPONSE" | python3 -c "import sys, json; d=json.load(sys.stdin); print(d.get('scheduled_at', 'ERROR'))" 2>/dev/null)
    
    if [ "$NEW_SCHEDULED_AT" != "ERROR" ]; then
        echo "✅ Scheduled time updated"
        echo "   New time (UTC): $NEW_SCHEDULED_AT"
    else
        echo "❌ Failed to update scheduled time"
    fi
    echo ""
fi

# Test 6: Publish Now (Cancel Scheduling)
if [ "$SCHEDULED_ID" != "ERROR" ]; then
    echo "🚀 Test 6: Publishing Scheduled Post Now..."
    echo "───────────────────────────────────────────────────────────"
    
    PUBLISH_RESPONSE=$(curl -s -X PUT "$API_URL/news/$SCHEDULED_ID" \
      -H "Authorization: Bearer $TOKEN" \
      -F "scheduled_publish=false" \
      -F "published=true")
    
    IS_PUBLISHED=$(echo "$PUBLISH_RESPONSE" | python3 -c "import sys, json; d=json.load(sys.stdin); print(d.get('published', 'ERROR'))" 2>/dev/null)
    IS_SCHEDULED=$(echo "$PUBLISH_RESPONSE" | python3 -c "import sys, json; d=json.load(sys.stdin); print(d.get('scheduled_publish', 'ERROR'))" 2>/dev/null)
    
    if [ "$IS_PUBLISHED" == "True" ] && [ "$IS_SCHEDULED" == "False" ]; then
        echo "✅ Post published successfully"
        echo "   Published: $IS_PUBLISHED"
        echo "   Scheduled: $IS_SCHEDULED"
    else
        echo "⚠️  Unexpected state"
        echo "   Published: $IS_PUBLISHED"
        echo "   Scheduled: $IS_SCHEDULED"
    fi
    echo ""
fi

# Test 7: Test Past Time Validation
echo "⏰ Test 7: Testing Past Time Validation..."
echo "───────────────────────────────────────────────────────────"
PAST_TIME=$(python3 -c "from datetime import datetime, timedelta; import pytz; ist = pytz.timezone('Asia/Kolkata'); past = datetime.now(ist) - timedelta(minutes=10); print(past.strftime('%Y-%m-%dT%H:%M'))")

PAST_RESPONSE=$(curl -s -X POST "$API_URL/news" \
  -H "Authorization: Bearer $TOKEN" \
  -F "title=Past Time Test" \
  -F "summary=Should fail" \
  -F "content=<p>Test</p>" \
  -F "slug=past-time-test-dec5" \
  -F "scheduled_publish=true" \
  -F "scheduled_at=$PAST_TIME" \
  -F "categories=Test" \
  -F "file=@/tmp/test.txt")

PAST_ERROR=$(echo "$PAST_RESPONSE" | python3 -c "import sys, json; d=json.load(sys.stdin); print(d.get('detail', 'NO_ERROR'))" 2>/dev/null)

if [[ "$PAST_ERROR" == *"future"* ]]; then
    echo "✅ Past time correctly rejected"
    echo "   Error: ${PAST_ERROR:0:80}..."
else
    echo "⚠️  Expected validation error"
    echo "   Response: $PAST_ERROR"
fi
echo ""

# Summary
echo "════════════════════════════════════════════════════════════"
echo "  Test Summary"
echo "════════════════════════════════════════════════════════════"
echo ""
echo "✅ Tested Features:"
echo "   1. Draft post creation"
echo "   2. Scheduled post creation"
echo "   3. Scheduled posts list endpoint"
echo "   4. Draft visibility (not public)"
echo "   5. Update scheduled time"
echo "   6. Publish now (cancel scheduling)"
echo "   7. Past time validation"
echo ""
echo "🎯 Post IDs for manual verification:"
echo "   Draft: $DRAFT_ID"
echo "   Scheduled: $SCHEDULED_ID"
echo ""
echo "🌐 Test URLs:"
echo "   - Draft: $API_URL/news/$DRAFT_ID"
echo "   - Scheduled: $API_URL/news/$SCHEDULED_ID"
echo "   - Scheduled List: $API_URL/news/scheduled"
echo ""
echo "════════════════════════════════════════════════════════════"
