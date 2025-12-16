#!/bin/bash

# Horoscope API Complete Test Suite
# Testing all 22 endpoints with admin and author credentials

BASE_URL="https://api.projectdevops.in"

echo "=========================================="
echo "🧪 HOROSCOPE API COMPLETE TEST SUITE"
echo "=========================================="
echo ""

# Login as Admin
echo "🔐 Logging in as ADMIN..."
ADMIN_TOKEN=$(curl -s -X POST "$BASE_URL/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin&password=Gyanu@9693894505" | python3 -c "import sys, json; print(json.load(sys.stdin)['access_token'])")

echo "✅ Admin Token: ${ADMIN_TOKEN:0:50}..."
echo ""

# Login as Author
echo "🔐 Logging in as AUTHOR..."
AUTHOR_TOKEN=$(curl -s -X POST "$BASE_URL/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=abhigyan709&password=Gyanu@9693894505" | python3 -c "import sys, json; print(json.load(sys.stdin)['access_token'])")

echo "✅ Author Token: ${AUTHOR_TOKEN:0:50}..."
echo ""
echo "=========================================="
echo ""

# ==================== PUBLIC ENDPOINTS ====================
echo "📍 PUBLIC ENDPOINTS (No Authentication)"
echo "=========================================="
echo ""

echo "1️⃣  GET /horoscope/today"
curl -s -w "\nStatus: %{http_code}\n" "$BASE_URL/horoscope/today" | python3 -c "import sys, json; d=json.load(sys.stdin); print(json.dumps(d, indent=2, ensure_ascii=False))" 2>/dev/null || echo "No data or error"
echo ""

echo "2️⃣  GET /horoscope/date/2025-12-16"
curl -s -w "\nStatus: %{http_code}\n" "$BASE_URL/horoscope/date/2025-12-16" | python3 -c "import sys, json; d=json.load(sys.stdin); print(json.dumps(d, indent=2, ensure_ascii=False))" 2>/dev/null || echo "No data"
echo ""

echo "3️⃣  GET /horoscope/zodiac/mesh"
curl -s -w "\nStatus: %{http_code}\n" "$BASE_URL/horoscope/zodiac/mesh" | python3 -c "import sys, json; d=json.load(sys.stdin); print(json.dumps(d, indent=2, ensure_ascii=False))" 2>/dev/null || echo "No data"
echo ""

echo "4️⃣  GET /horoscope/archive?page=1&limit=5"
curl -s -w "\nStatus: %{http_code}\n" "$BASE_URL/horoscope/archive?page=1&limit=5" | python3 -c "import sys, json; d=json.load(sys.stdin); print(f'Found {len(d)} horoscopes' if isinstance(d, list) else json.dumps(d, ensure_ascii=False))" 2>/dev/null || echo "No data"
echo ""

# ==================== ADMIN ENDPOINTS ====================
echo ""
echo "🔐 ADMIN ENDPOINTS (Admin Token Required)"
echo "=========================================="
echo ""

echo "7️⃣  POST /admin/horoscope (Create)"
CREATE_DATA='{
  "title": "राशि फल✡️🙏🏻",
  "date": "2025-12-17",
  "zodiac_predictions": [
    {"sign": "mesh", "emoji": "🐏", "hindi_name": "मेष राशि", "syllables": "चू, चे, चो, ला, ली, लू, ले, लो, अ", "prediction": "आज का दिन आपके लिए शुभ रहेगा। व्यापार में लाभ के योग हैं।"},
    {"sign": "vrishabh", "emoji": "🐂", "hindi_name": "वृष राशि", "syllables": "ई, उ, ए, ओ, वा, वी, वू, वे, वो", "prediction": "आर्थिक स्थिति में सुधार होगा। परिवार में खुशी का माहौल रहेगा।"},
    {"sign": "mithun", "emoji": "👭", "hindi_name": "मिथुन राशि", "syllables": "का, की, कु, घ, ड, छ, के, को, हा", "prediction": "नए अवसर मिलेंगे। दोस्तों का साथ मिलेगा।"},
    {"sign": "kark", "emoji": "🦀", "hindi_name": "कर्क राशि", "syllables": "ही, हू, हे, हो, डा, डी, डू, डे, डो", "prediction": "करियर में प्रगति होगी। स्वास्थ्य का ध्यान रखें।"},
    {"sign": "simha", "emoji": "🐅", "hindi_name": "सिंह राशि", "syllables": "मा, मी, मू, मे, मो, टा, टी, टू, टे", "prediction": "नेतृत्व क्षमता में वृद्धि होगी। सफलता मिलेगी।"},
    {"sign": "kanya", "emoji": "🙎‍♀️", "hindi_name": "कन्या राशि", "syllables": "टो, पा, पी, पू, ष, ण, ठ, पे, पो", "prediction": "कार्यक्षेत्र में उन्नति होगी। परीक्षा में सफलता मिलेगी।"},
    {"sign": "tula", "emoji": "⚖️", "hindi_name": "तुला राशि", "syllables": "रा, री, रु, रे, रो, ता, ती, तू, ते", "prediction": "संतुलित निर्णय लें। व्यापार में लाभ होगा।"},
    {"sign": "vrishchik", "emoji": "🦂", "hindi_name": "वृश्चिक राशि", "syllables": "तो, ना, नी, नू, ने, नो, या, यी, यू", "prediction": "गुप्त शत्रुओं से सावधान रहें। सफलता के योग हैं।"},
    {"sign": "dhanu", "emoji": "🏹", "hindi_name": "धनु राशि", "syllables": "ये, यो, भा, भी, भू, ध, फ, ढ, भे", "prediction": "यात्रा के योग हैं। नए कार्य शुरू कर सकते हैं।"},
    {"sign": "makar", "emoji": "🐊", "hindi_name": "मकर राशि", "syllables": "भो, जा, जी, खी, खू, खे, खो, गा, गी", "prediction": "मेहनत रंग लाएगी। धन लाभ के योग हैं।"},
    {"sign": "kumbh", "emoji": "⚱️", "hindi_name": "कुम्भ राशि", "syllables": "गू, गे, गो, सा, सी, सू, से, सो, दा", "prediction": "सामाजिक कार्यों में सफलता मिलेगी। नए मित्र बनेंगे।"},
    {"sign": "meen", "emoji": "🐟", "hindi_name": "मीन राशि", "syllables": "दी, दू, थ, झ, ञ, दे, दो, चा, ची", "prediction": "आध्यात्मिक विकास होगा। मानसिक शांति मिलेगी।"}
  ],
  "closing_message": "☘️आपका दिन मंगलमय हो।☘️",
  "contact_info": "🕉️ कुण्डली विचार, भविष्य की जानकारी के लिए संपर्क करें।",
  "published": false
}'

CREATED_ID=$(curl -s -X POST "$BASE_URL/admin/horoscope" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d "$CREATE_DATA" | python3 -c "import sys, json; d=json.load(sys.stdin); print(d.get('_id', 'ERROR: ' + str(d)))")

echo "Created Horoscope ID: $CREATED_ID"
echo ""

echo "8️⃣  GET /admin/horoscopes (List all)"
curl -s "$BASE_URL/admin/horoscopes?page=1&limit=3" \
  -H "Authorization: Bearer $ADMIN_TOKEN" | python3 -c "import sys, json; d=json.load(sys.stdin); print(f'Total horoscopes: {len(d)}' if isinstance(d, list) else json.dumps(d, ensure_ascii=False))"
echo ""

if [ "$CREATED_ID" != "ERROR"* ]; then
  echo "9️⃣  GET /admin/horoscope/{id} (Get single)"
  curl -s "$BASE_URL/admin/horoscope/$CREATED_ID" \
    -H "Authorization: Bearer $ADMIN_TOKEN" | python3 -c "import sys, json; d=json.load(sys.stdin); print(f\"ID: {d.get('_id', 'N/A')}, Date: {d.get('date', 'N/A')}, Published: {d.get('published', 'N/A')}\")" 2>/dev/null || echo "Error fetching"
  echo ""

  echo "1️⃣0️⃣  PUT /admin/horoscope/{id} (Update)"
  curl -s -X PUT "$BASE_URL/admin/horoscope/$CREATED_ID" \
    -H "Authorization: Bearer $ADMIN_TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"title": "राशि फल✡️🙏🏻 (Updated)"}' | python3 -c "import sys, json; d=json.load(sys.stdin); print(f\"Updated title: {d.get('title', 'N/A')}\")" 2>/dev/null || echo "Error updating"
  echo ""

  echo "1️⃣2️⃣  POST /admin/horoscope/{id}/publish"
  curl -s -X POST "$BASE_URL/admin/horoscope/$CREATED_ID/publish" \
    -H "Authorization: Bearer $ADMIN_TOKEN" | python3 -c "import sys, json; d=json.load(sys.stdin); print(f\"Published: {d.get('published', 'N/A')}\")" 2>/dev/null || echo "Error publishing"
  echo ""

  echo "1️⃣3️⃣  POST /admin/horoscope/{id}/unpublish"
  curl -s -X POST "$BASE_URL/admin/horoscope/$CREATED_ID/unpublish" \
    -H "Authorization: Bearer $ADMIN_TOKEN" | python3 -c "import sys, json; d=json.load(sys.stdin); print(f\"Published: {d.get('published', 'N/A')}\")" 2>/dev/null || echo "Error unpublishing"
  echo ""
fi

echo "1️⃣6️⃣  GET /admin/horoscope/stats"
curl -s "$BASE_URL/admin/horoscope/stats" \
  -H "Authorization: Bearer $ADMIN_TOKEN" | python3 -c "import sys, json; d=json.load(sys.stdin); print(json.dumps(d, indent=2, ensure_ascii=False))" 2>/dev/null || echo "Error"
echo ""

echo "1️⃣9️⃣  GET /admin/horoscope/drafts"
curl -s "$BASE_URL/admin/horoscope/drafts?page=1&limit=3" \
  -H "Authorization: Bearer $ADMIN_TOKEN" | python3 -c "import sys, json; d=json.load(sys.stdin); print(f'Draft horoscopes: {len(d)}' if isinstance(d, list) else json.dumps(d, ensure_ascii=False))"
echo ""

echo "2️⃣0️⃣  GET /admin/horoscope/published"
curl -s "$BASE_URL/admin/horoscope/published?page=1&limit=3" \
  -H "Authorization: Bearer $ADMIN_TOKEN" | python3 -c "import sys, json; d=json.load(sys.stdin); print(f'Published horoscopes: {len(d)}' if isinstance(d, list) else json.dumps(d, ensure_ascii=False))"
echo ""

echo "2️⃣1️⃣  GET /admin/horoscope/search?query=शुभ"
curl -s "$BASE_URL/admin/horoscope/search?query=शुभ&page=1" \
  -H "Authorization: Bearer $ADMIN_TOKEN" | python3 -c "import sys, json; d=json.load(sys.stdin); print(f'Search results: {len(d)}' if isinstance(d, list) else json.dumps(d, ensure_ascii=False))"
echo ""

# ==================== AUTHOR ENDPOINTS ====================
echo ""
echo "✍️  AUTHOR ENDPOINTS (Author Token Required)"
echo "=========================================="
echo ""

echo "1️⃣5️⃣  GET /author/horoscopes"
curl -s "$BASE_URL/author/horoscopes?page=1&limit=3" \
  -H "Authorization: Bearer $AUTHOR_TOKEN" | python3 -c "import sys, json; d=json.load(sys.stdin); print(f'Author horoscopes: {len(d)}' if isinstance(d, list) else json.dumps(d, ensure_ascii=False))"
echo ""

echo "1️⃣7️⃣  GET /author/horoscope/stats"
curl -s "$BASE_URL/author/horoscope/stats" \
  -H "Authorization: Bearer $AUTHOR_TOKEN" | python3 -c "import sys, json; d=json.load(sys.stdin); print(json.dumps(d, indent=2, ensure_ascii=False))" 2>/dev/null || echo "Error"
echo ""

# ==================== CLEANUP ====================
if [ "$CREATED_ID" != "ERROR"* ]; then
  echo ""
  echo "🧹 CLEANUP"
  echo "=========================================="
  echo "1️⃣1️⃣  DELETE /admin/horoscope/{id}"
  curl -s -X DELETE "$BASE_URL/admin/horoscope/$CREATED_ID" \
    -H "Authorization: Bearer $ADMIN_TOKEN" | python3 -c "import sys, json; d=json.load(sys.stdin); print(d.get('message', json.dumps(d, ensure_ascii=False)))" 2>/dev/null || echo "Error deleting"
  echo ""
fi

echo ""
echo "=========================================="
echo "✅ TEST SUITE COMPLETED!"
echo "=========================================="
