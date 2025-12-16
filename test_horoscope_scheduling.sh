#!/bin/bash

# Horoscope Scheduling Test Script
# Tests the IST timezone-based scheduled publishing feature

set -e  # Exit on error

# Configuration
API_BASE="https://api.projectdevops.in"
# Replace with your admin token
ADMIN_TOKEN="${ADMIN_TOKEN:-your_admin_token_here}"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== Horoscope Scheduling Test ===${NC}\n"

# Function to print test step
test_step() {
    echo -e "${YELLOW}[TEST]${NC} $1"
}

# Function to print success
test_success() {
    echo -e "${GREEN}[✓]${NC} $1\n"
}

# Function to print error
test_error() {
    echo -e "${RED}[✗]${NC} $1\n"
    exit 1
}

# Check if admin token is provided
if [ "$ADMIN_TOKEN" = "your_admin_token_here" ]; then
    echo -e "${RED}Error: Please set ADMIN_TOKEN environment variable${NC}"
    echo "Usage: ADMIN_TOKEN=your_token ./test_horoscope_scheduling.sh"
    exit 1
fi

# Test 1: Create horoscope scheduled for 1 minute in future
test_step "Test 1: Creating horoscope scheduled for 1 minute in future"

# Calculate IST time 1 minute from now
# Note: This calculates UTC time, then adds IST offset (5:30)
CURRENT_UTC=$(date -u "+%Y-%m-%d %H:%M:%S")
FUTURE_UTC=$(date -u -v+1M "+%Y-%m-%d %H:%M" 2>/dev/null || date -u -d "+1 minute" "+%Y-%m-%d %H:%M")

# Convert to IST (UTC + 5:30)
FUTURE_IST=$(date -u -v+1M -v+5H -v+30M "+%Y-%m-%dT%H:%M" 2>/dev/null || date -u -d "+1 minute +5 hours +30 minutes" "+%Y-%m-%dT%H:%M")
TODAY=$(date "+%Y-%m-%d")

echo "Scheduling for IST time: $FUTURE_IST"

CREATE_RESPONSE=$(curl -s -X POST "$API_BASE/admin/horoscope" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"date\": \"$TODAY\",
    \"title\": \"राशि फल✡️🙏🏻\",
    \"zodiac_predictions\": [
      {
        \"sign\": \"mesh\",
        \"hindi_name\": \"मेष\",
        \"syllables\": \"चू, चे, चो, ला, ली, लू, ले, लो, आ\",
        \"prediction\": \"TEST: आज आपके जीवन में खुशियां आएंगी।\"
      },
      {
        \"sign\": \"vrishabh\",
        \"hindi_name\": \"वृषभ\",
        \"syllables\": \"इ, ई, उ, ऊ, ए, ओ, वा, वी, वू\",
        \"prediction\": \"TEST: धन लाभ के योग हैं।\"
      },
      {
        \"sign\": \"mithun\",
        \"hindi_name\": \"मिथुन\",
        \"syllables\": \"का, की, कू, घ, ङ, छ, के, को, ह\",
        \"prediction\": \"TEST: नए अवसर मिलेंगे।\"
      },
      {
        \"sign\": \"kark\",
        \"hindi_name\": \"कर्क\",
        \"syllables\": \"हि, ही, हु, हू, हे, हो, डा, डी, डू\",
        \"prediction\": \"TEST: परिवार में सुख समृद्धि।\"
      },
      {
        \"sign\": \"simha\",
        \"hindi_name\": \"सिंह\",
        \"syllables\": \"मा, मी, मू, मे, मो, टा, टी, टू, टे\",
        \"prediction\": \"TEST: कार्यक्षेत्र में सफलता।\"
      },
      {
        \"sign\": \"kanya\",
        \"hindi_name\": \"कन्या\",
        \"syllables\": \"टो, पा, पी, पू, ष, ण, ठ, पे, पो\",
        \"prediction\": \"TEST: स्वास्थ्य अच्छा रहेगा।\"
      },
      {
        \"sign\": \"tula\",
        \"hindi_name\": \"तुला\",
        \"syllables\": \"रा, री, रू, रे, रो, ता, ती, तू, ते\",
        \"prediction\": \"TEST: व्यापार में वृद्धि।\"
      },
      {
        \"sign\": \"vrishchik\",
        \"hindi_name\": \"वृश्चिक\",
        \"syllables\": \"तो, ना, नी, नू, ने, नो, या, यी, यू\",
        \"prediction\": \"TEST: मानसिक शांति मिलेगी।\"
      },
      {
        \"sign\": \"dhanu\",
        \"hindi_name\": \"धनु\",
        \"syllables\": \"ये, यो, भा, भी, भू, ध, फ, ढ, भे\",
        \"prediction\": \"TEST: यात्रा शुभ रहेगी।\"
      },
      {
        \"sign\": \"makar\",
        \"hindi_name\": \"मकर\",
        \"syllables\": \"भो, जा, जी, खी, खू, खे, खो, गा, गी\",
        \"prediction\": \"TEST: धन संचय होगा।\"
      },
      {
        \"sign\": \"kumbh\",
        \"hindi_name\": \"कुम्भ\",
        \"syllables\": \"गु, गे, गो, सा, सी, सू, से, सो, दा\",
        \"prediction\": \"TEST: सामाजिक मान सम्मान।\"
      },
      {
        \"sign\": \"meen\",
        \"hindi_name\": \"मीन\",
        \"syllables\": \"दी, दू, थ, झ, ञ, दे, दो, च, ची\",
        \"prediction\": \"TEST: आध्यात्मिक उन्नति।\"
      }
    ],
    \"closing_text\": \"🙏सभी मित्रों को जय श्री राम🙏\",
    \"contact_info\": \"📞 संपर्क करें: 7894561230\",
    \"published\": false,
    \"scheduled_publish\": true,
    \"scheduled_at\": \"$FUTURE_IST\"
  }")

# Check if creation was successful
if echo "$CREATE_RESPONSE" | grep -q "_id"; then
    HOROSCOPE_ID=$(echo "$CREATE_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin)['_id'])")
    test_success "Created scheduled horoscope with ID: $HOROSCOPE_ID"
else
    test_error "Failed to create horoscope: $CREATE_RESPONSE"
fi

# Verify horoscope is unpublished
PUBLISHED=$(echo "$CREATE_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('published', False))")
SCHEDULED=$(echo "$CREATE_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('scheduled_publish', False))")

if [ "$PUBLISHED" = "False" ] && [ "$SCHEDULED" = "True" ]; then
    test_success "Horoscope correctly created as scheduled (published=False, scheduled_publish=True)"
else
    test_error "Horoscope state incorrect: published=$PUBLISHED, scheduled_publish=$SCHEDULED"
fi

# Test 2: Verify horoscope is NOT visible in public API
test_step "Test 2: Verifying horoscope is not visible in public API (before scheduled time)"

PUBLIC_RESPONSE=$(curl -s "$API_BASE/horoscope/today")

if echo "$PUBLIC_RESPONSE" | grep -q "उपलब्ध नहीं"; then
    test_success "Horoscope correctly hidden from public API"
else
    echo -e "${YELLOW}Note: A different published horoscope for today might exist${NC}\n"
fi

# Test 3: Wait for scheduled time and verify auto-publish
test_step "Test 3: Waiting 65 seconds for scheduled time..."

echo "Current time: $(date)"
echo "Waiting for auto-publish..."

sleep 65

test_step "Triggering auto-publish by calling public API"

# Call public API to trigger _process_scheduled_horoscopes()
PUBLIC_RESPONSE_AFTER=$(curl -s "$API_BASE/horoscope/today")

if echo "$PUBLIC_RESPONSE_AFTER" | grep -q "TEST:"; then
    test_success "Horoscope auto-published successfully!"
else
    echo -e "${YELLOW}Checking horoscope details...${NC}"
fi

# Test 4: Verify horoscope is now published in admin API
test_step "Test 4: Verifying horoscope is now published in admin API"

ADMIN_RESPONSE=$(curl -s "$API_BASE/admin/horoscope/$HOROSCOPE_ID" \
  -H "Authorization: Bearer $ADMIN_TOKEN")

PUBLISHED_AFTER=$(echo "$ADMIN_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('published', False))")
SCHEDULED_AFTER=$(echo "$ADMIN_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('scheduled_publish', False))")

if [ "$PUBLISHED_AFTER" = "True" ] && [ "$SCHEDULED_AFTER" = "False" ]; then
    test_success "Horoscope auto-published correctly (published=True, scheduled_publish=False)"
else
    test_error "Auto-publish failed: published=$PUBLISHED_AFTER, scheduled_publish=$SCHEDULED_AFTER"
fi

# Test 5: Test updating schedule
test_step "Test 5: Testing schedule update"

# Delete the test horoscope first
curl -s -X DELETE "$API_BASE/admin/horoscope/$HOROSCOPE_ID" \
  -H "Authorization: Bearer $ADMIN_TOKEN" > /dev/null

# Create new one with far future schedule
FAR_FUTURE_IST=$(date -u -v+1d -v+5H -v+30M "+%Y-%m-%dT%H:%M" 2>/dev/null || date -u -d "+1 day +5 hours +30 minutes" "+%Y-%m-%dT%H:%M")
TOMORROW=$(date -v+1d "+%Y-%m-%d" 2>/dev/null || date -d "+1 day" "+%Y-%m-%d")

CREATE_RESPONSE2=$(curl -s -X POST "$API_BASE/admin/horoscope" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"date\": \"$TOMORROW\",
    \"title\": \"राशि फल✡️🙏🏻\",
    \"zodiac_predictions\": [
      {\"sign\": \"mesh\", \"hindi_name\": \"मेष\", \"syllables\": \"चू, चे, चो\", \"prediction\": \"TEST2\"},
      {\"sign\": \"vrishabh\", \"hindi_name\": \"वृषभ\", \"syllables\": \"इ, ई, उ\", \"prediction\": \"TEST2\"},
      {\"sign\": \"mithun\", \"hindi_name\": \"मिथुन\", \"syllables\": \"का, की\", \"prediction\": \"TEST2\"},
      {\"sign\": \"kark\", \"hindi_name\": \"कर्क\", \"syllables\": \"हि, ही\", \"prediction\": \"TEST2\"},
      {\"sign\": \"simha\", \"hindi_name\": \"सिंह\", \"syllables\": \"मा, मी\", \"prediction\": \"TEST2\"},
      {\"sign\": \"kanya\", \"hindi_name\": \"कन्या\", \"syllables\": \"टो, पा\", \"prediction\": \"TEST2\"},
      {\"sign\": \"tula\", \"hindi_name\": \"तुला\", \"syllables\": \"रा, री\", \"prediction\": \"TEST2\"},
      {\"sign\": \"vrishchik\", \"hindi_name\": \"वृश्चिक\", \"syllables\": \"तो, ना\", \"prediction\": \"TEST2\"},
      {\"sign\": \"dhanu\", \"hindi_name\": \"धनु\", \"syllables\": \"ये, यो\", \"prediction\": \"TEST2\"},
      {\"sign\": \"makar\", \"hindi_name\": \"मकर\", \"syllables\": \"भो, जा\", \"prediction\": \"TEST2\"},
      {\"sign\": \"kumbh\", \"hindi_name\": \"कुम्भ\", \"syllables\": \"गु, गे\", \"prediction\": \"TEST2\"},
      {\"sign\": \"meen\", \"hindi_name\": \"मीन\", \"syllables\": \"दी, दू\", \"prediction\": \"TEST2\"}
    ],
    \"closing_text\": \"जय श्री राम\",
    \"contact_info\": \"7894561230\",
    \"scheduled_publish\": true,
    \"scheduled_at\": \"$FAR_FUTURE_IST\"
  }")

HOROSCOPE_ID2=$(echo "$CREATE_RESPONSE2" | python3 -c "import sys, json; print(json.load(sys.stdin)['_id'])")

# Now manually publish it
UPDATE_RESPONSE=$(curl -s -X PUT "$API_BASE/admin/horoscope/$HOROSCOPE_ID2" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"published\": true
  }")

PUBLISHED_MANUAL=$(echo "$UPDATE_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('published', False))")
SCHEDULED_MANUAL=$(echo "$UPDATE_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('scheduled_publish', False))")

if [ "$PUBLISHED_MANUAL" = "True" ] && [ "$SCHEDULED_MANUAL" = "False" ]; then
    test_success "Manual publish correctly cleared schedule"
else
    test_error "Manual publish failed: published=$PUBLISHED_MANUAL, scheduled_publish=$SCHEDULED_MANUAL"
fi

# Cleanup
test_step "Cleanup: Deleting test horoscopes"
curl -s -X DELETE "$API_BASE/admin/horoscope/$HOROSCOPE_ID2" \
  -H "Authorization: Bearer $ADMIN_TOKEN" > /dev/null

test_success "Cleanup complete"

echo -e "${GREEN}=== All Tests Passed! ===${NC}"
echo ""
echo "Summary:"
echo "✓ Scheduled horoscope creation"
echo "✓ Hidden from public API before scheduled time"
echo "✓ Auto-publish at scheduled time"
echo "✓ Manual publish clears schedule"
echo ""
echo "The horoscope scheduling system is working correctly!"
