# Horoscope Scheduling System - Complete Implementation Guide

## ✅ What Was Fixed

### Critical Issue #1: No Continuous Background Scheduler ⚠️
**Problem**: `_process_scheduled_horoscopes()` only ran when API endpoints were called, not continuously.

**Solution**: Added a background thread that runs every 60 seconds to check and publish scheduled horoscopes automatically.

### Critical Issue #2: Incomplete Date Logic
**Problem**: Scheduler only looked for explicitly scheduled horoscopes, missing today's horoscopes that should auto-publish.

**Solution**: Enhanced query to handle both:
- Explicitly scheduled horoscopes (with `scheduled_publish: true` and future time)
- Today's horoscopes that should auto-publish when date matches

### Critical Issue #3: Missing Debug Tools
**Problem**: No way to troubleshoot what's happening with scheduled horoscopes.

**Solution**: Added 5 debug endpoints to inspect system state.

## 🚀 Implementation Changes

### 1. Background Scheduler (`main.py`)

**Added**:
```python
import threading
import time
from contextlib import asynccontextmanager

# Background scheduler function
def scheduled_horoscope_publisher():
    """Runs every 60 seconds in background thread"""
    from pymongo import MongoClient
    from routes.news import _process_scheduled_horoscopes
    from database.db import get_mongo_uri
    
    MONGODB_URI = get_mongo_uri()
    logger.info("🚀 [Horoscope Scheduler] Background thread started")
    
    while True:
        try:
            client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=5000)
            _process_scheduled_horoscopes(client)
            client.close()
        except Exception as e:
            logger.error(f"❌ [Horoscope Scheduler Error]: {str(e)}")
        
        time.sleep(60)  # Check every 1 minute

# Lifespan manager to start scheduler on app startup
@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler_thread = threading.Thread(
        target=scheduled_horoscope_publisher,
        daemon=True,
        name="HoroscopeScheduler"
    )
    scheduler_thread.start()
    logger.info("✅ [Horoscope Scheduler] Background scheduler initialized")
    yield
    logger.info("🛑 [Horoscope Scheduler] Shutting down")

# Updated FastAPI app with lifespan
app = FastAPI(
    title="OpenSource Enterprise API",
    lifespan=lifespan,  # ✅ Added this
    ...
)
```

### 2. Improved Scheduler Logic (`routes/news.py`)

**Before**:
```python
# Only found explicitly scheduled horoscopes
scheduled_horoscopes = coll.find({
    "scheduled_publish": True,
    "published": False,
    "scheduled_at": {"$lte": current_utc}
})
```

**After**:
```python
# Finds BOTH:
# 1. Explicitly scheduled horoscopes that are due
# 2. Today's horoscopes that should auto-publish
scheduled_horoscopes = list(coll.find({
    "published": False,
    "$or": [
        # Explicitly scheduled
        {
            "scheduled_publish": True,
            "scheduled_at": {"$lte": current_utc}
        },
        # Today's horoscope (auto-publish if date matches)
        {
            "date": today_date,
            "$or": [
                {"scheduled_publish": {"$ne": True}},
                {"scheduled_publish": True, "scheduled_at": {"$lte": current_utc}}
            ]
        }
    ]
}))
```

### 3. Enhanced Logging

All scheduler operations now log with emojis for easy visual scanning:
- 🔍 "Checking at UTC/IST"
- 📋 "Found X horoscopes to process"
- 📤 "Publishing horoscope..."
- ✅ "Auto-published X horoscopes"
- ❌ "Scheduler Error"
- ⚠️ "No published horoscope found"

### 4. New Debug Endpoints

#### GET `/admin/horoscope/debug/today`
**Purpose**: See what's stored for today's date
**Returns**:
```json
{
  "debug_info": {
    "today_date": "2025-12-20",
    "current_utc": "2025-12-20T14:30:00",
    "current_ist": "2025-12-20T20:00:00",
    "found_count": 1
  },
  "horoscopes": [...]
}
```

#### POST `/admin/horoscope/force-process-scheduled`
**Purpose**: Manually trigger scheduler (don't wait 1 minute)
**Use**: When you schedule a horoscope and want to test immediately

#### GET `/admin/horoscope/debug/all-dates`
**Purpose**: See all horoscope dates in database
**Returns**: List of all horoscopes with date, published status, scheduling info

#### POST `/admin/horoscope/publish-today`
**Purpose**: Emergency quick-fix to manually publish today's horoscope
**Use**: If scheduler isn't working and you need to publish NOW

#### GET `/admin/horoscope/debug/scheduled`
**Purpose**: See all scheduled horoscopes and whether they're due
**Returns**:
```json
{
  "debug_info": {
    "current_utc": "2025-12-20T14:30:00",
    "current_ist": "2025-12-20T20:00:00",
    "total_scheduled": 2
  },
  "scheduled_horoscopes": [
    {
      "_id": "...",
      "date": "2025-12-21",
      "published": false,
      "scheduled_at_ist": "2025-12-21T00:10:00",
      "is_due": false,
      "should_be_published": false
    }
  ]
}
```

### 5. Database Helper (`database/db.py`)

**Added**:
```python
def get_mongo_uri():
    """Get MongoDB URI for background tasks"""
    return db.get_mongo_uri()
```

This allows the background thread to get MongoDB credentials from AWS Secrets Manager.

## 📋 Testing Checklist

### Step 1: Verify Background Scheduler Started
```bash
# After deploying, check server logs for:
grep "Horoscope Scheduler" /path/to/logs

# Should see:
# 🚀 [Horoscope Scheduler] Background thread started
# ✅ [Horoscope Scheduler] Background scheduler initialized
```

### Step 2: Test Immediate Scheduling (2 minutes from now)
```bash
# Set your admin token
export TOKEN="your_admin_jwt_token"

# Calculate IST time 2 minutes from now
SCHEDULED_TIME=$(python3 -c "
from datetime import datetime, timedelta
import pytz
ist = pytz.timezone('Asia/Kolkata')
scheduled = datetime.now(ist) + timedelta(minutes=2)
print(scheduled.strftime('%Y-%m-%dT%H:%M'))
")

echo "Scheduling for IST: $SCHEDULED_TIME"

# Create scheduled horoscope
curl -X POST "https://api.projectdevops.in/news/admin/horoscope" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"title\": \"राशि फल✡️🙏🏻\",
    \"date\": \"2025-12-21\",
    \"zodiac_predictions\": [
      {\"sign\": \"mesh\", \"hindi_name\": \"मेष राशि\", \"syllables\": \"चू, चे, चो, ला\", \"prediction\": \"Test\"},
      {\"sign\": \"vrishabh\", \"hindi_name\": \"वृषभ राशि\", \"syllables\": \"ई, उ, ए, ओ\", \"prediction\": \"Test\"},
      {\"sign\": \"mithun\", \"hindi_name\": \"मिथुन राशि\", \"syllables\": \"का, की, कु\", \"prediction\": \"Test\"},
      {\"sign\": \"kark\", \"hindi_name\": \"कर्क राशि\", \"syllables\": \"ही, हू, हे\", \"prediction\": \"Test\"},
      {\"sign\": \"simha\", \"hindi_name\": \"सिंह राशि\", \"syllables\": \"मा, मी, मू\", \"prediction\": \"Test\"},
      {\"sign\": \"kanya\", \"hindi_name\": \"कन्या राशि\", \"syllables\": \"पा, पी, पू\", \"prediction\": \"Test\"},
      {\"sign\": \"tula\", \"hindi_name\": \"तुला राशि\", \"syllables\": \"रा, री, रू\", \"prediction\": \"Test\"},
      {\"sign\": \"vrishchik\", \"hindi_name\": \"वृश्चिक राशि\", \"syllables\": \"ना, नी, नू\", \"prediction\": \"Test\"},
      {\"sign\": \"dhanu\", \"hindi_name\": \"धनु राशि\", \"syllables\": \"या, यी, यू\", \"prediction\": \"Test\"},
      {\"sign\": \"makar\", \"hindi_name\": \"मकर राशि\", \"syllables\": \"का, की, कु\", \"prediction\": \"Test\"},
      {\"sign\": \"kumbh\", \"hindi_name\": \"कुम्भ राशि\", \"syllables\": \"गा, गी, गू\", \"prediction\": \"Test\"},
      {\"sign\": \"meen\", \"hindi_name\": \"मीन राशि\", \"syllables\": \"दा, दी, दू\", \"prediction\": \"Test\"}
    ],
    \"closing_message\": \"☘️आपका दिन मंगलमय हो।☘️\",
    \"published\": false,
    \"scheduled_publish\": true,
    \"scheduled_at\": \"$SCHEDULED_TIME\"
  }" | python3 -m json.tool

# Get the horoscope ID from response
HOROSCOPE_ID="paste_id_here"
```

### Step 3: Verify Scheduling Status
```bash
# Check debug endpoint
curl -X GET "https://api.projectdevops.in/news/admin/horoscope/debug/scheduled" \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool

# Should show:
# - scheduled_at_ist: your scheduled time
# - is_due: false (before time)
# - should_be_published: false
```

### Step 4: Wait 2-3 Minutes, Then Check

**Option A**: Wait for background scheduler (runs every 60 seconds)
```bash
# Wait 3 minutes, then check if published
curl -X GET "https://api.projectdevops.in/news/admin/horoscope/$HOROSCOPE_ID" \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool

# Check fields:
# - published: should be true
# - scheduled_publish: should be false (cleared)
```

**Option B**: Force immediate check (don't wait)
```bash
# Manually trigger scheduler
curl -X POST "https://api.projectdevops.in/news/admin/horoscope/force-process-scheduled" \
  -H "Authorization: Bearer $TOKEN"

# Then check horoscope
curl -X GET "https://api.projectdevops.in/news/admin/horoscope/$HOROSCOPE_ID" \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool
```

### Step 5: Check Server Logs
```bash
# Look for scheduler logs (every 60 seconds)
tail -f /path/to/server.log | grep "Horoscope Scheduler"

# Expected output:
# 🔍 [Horoscope Scheduler] Checking at UTC: ..., IST: ..., Today: 2025-12-20
# 📋 [Horoscope Scheduler] Found 1 horoscopes to process
# 📤 [Horoscope Scheduler] Publishing horoscope ... for date 2025-12-21
# ✅ [Horoscope Scheduler] Auto-published 1 horoscopes
```

## 🐛 Troubleshooting

### Problem: "No horoscope found for today"

**Diagnosis**:
```bash
# 1. Check what's in database for today
curl -X GET "https://api.projectdevops.in/news/admin/horoscope/debug/today" \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool

# Check response:
# - found_count: 0 → No horoscope created for today
# - found_count: 1 and published: false → Horoscope exists but unpublished
```

**Solution**:
```bash
# If unpublished, use quick-fix endpoint
curl -X POST "https://api.projectdevops.in/news/admin/horoscope/publish-today" \
  -H "Authorization: Bearer $TOKEN"
```

### Problem: Scheduled horoscope not auto-publishing

**Diagnosis**:
```bash
# 1. Check scheduled horoscopes status
curl -X GET "https://api.projectdevops.in/news/admin/horoscope/debug/scheduled" \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool

# Look at response:
# - is_due: true but published: false → Scheduler should have published it
# - is_due: false → Time hasn't arrived yet
```

**Solution**:
```bash
# 1. Manually trigger scheduler
curl -X POST "https://api.projectdevops.in/news/admin/horoscope/force-process-scheduled" \
  -H "Authorization: Bearer $TOKEN"

# 2. If still not working, check server logs for errors
grep "❌ \[Horoscope Scheduler Error\]" /path/to/logs

# 3. Verify background thread is running
ps aux | grep HoroscopeScheduler
```

### Problem: Background scheduler not running

**Diagnosis**:
```bash
# Check server logs on startup
grep "Horoscope Scheduler" /path/to/logs | head -5

# Should see:
# 🚀 [Horoscope Scheduler] Background thread started
# ✅ [Horoscope Scheduler] Background scheduler initialized

# If missing, scheduler didn't start
```

**Solution**:
1. Verify FastAPI app has `lifespan=lifespan` parameter
2. Restart FastAPI server
3. Check for Python threading issues in logs

### Problem: Timezone confusion (IST vs UTC)

**Diagnosis**:
```bash
# Check current times
curl -X GET "https://api.projectdevops.in/news/admin/horoscope/debug/today" \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool

# Compare:
# - current_utc: "2025-12-20T14:30:00"
# - current_ist: "2025-12-20T20:00:00"
# IST should be UTC + 5:30 hours
```

**Solution**: Times are stored in UTC, displayed in IST. Always use IST when scheduling from frontend.

## 📊 Monitoring Production

### Health Check Script
```bash
#!/bin/bash
# monitor_horoscope_scheduler.sh

TOKEN="your_admin_token"
API="https://api.projectdevops.in"

echo "=== Horoscope Scheduler Health Check ==="
echo ""

# 1. Check scheduled horoscopes
echo "📋 Scheduled Horoscopes:"
curl -s -X GET "$API/news/admin/horoscope/debug/scheduled" \
  -H "Authorization: Bearer $TOKEN" | python3 -c "
import sys, json
data = json.load(sys.stdin)
print(f\"Total scheduled: {data['debug_info']['total_scheduled']}\")
for h in data['scheduled_horoscopes']:
    if h['should_be_published']:
        print(f\"⚠️  OVERDUE: {h['date']} (ID: {h['_id']})\")
"

# 2. Check today's horoscope
echo ""
echo "📅 Today's Horoscope:"
curl -s -X GET "$API/news/admin/horoscope/debug/today" \
  -H "Authorization: Bearer $TOKEN" | python3 -c "
import sys, json
data = json.load(sys.stdin)
if data['debug_info']['found_count'] == 0:
    print('❌ No horoscope for today')
else:
    h = data['horoscopes'][0]
    status = '✅ Published' if h['published'] else '⚠️  Unpublished'
    print(f\"{status}: {h['date']}\")
"

# 3. Check recent logs (if accessible)
echo ""
echo "📝 Recent Scheduler Logs:"
# Adjust path to your server logs
tail -20 /path/to/server.log | grep "Horoscope Scheduler" || echo "No recent logs"

echo ""
echo "=== Health Check Complete ==="
```

### Cron Job for Daily Check
```bash
# Add to crontab: Check every hour
0 * * * * /path/to/monitor_horoscope_scheduler.sh >> /var/log/horoscope_monitor.log 2>&1
```

## 🚢 Deployment Steps

### 1. Pre-Deployment Checks
```bash
# Verify all files changed
git status

# Should show:
# - main.py (added lifespan manager)
# - routes/news.py (improved scheduler + debug endpoints)
# - database/db.py (added get_mongo_uri helper)
```

### 2. Deploy to Server
```bash
# Pull latest code
cd /path/to/attandance-app-fastapi
git pull origin main

# Restart FastAPI server
# (Method depends on your deployment: systemd, pm2, docker, etc.)

# systemd example:
sudo systemctl restart fastapi

# pm2 example:
pm2 restart fastapi-app

# docker example:
docker-compose restart api
```

### 3. Post-Deployment Verification
```bash
# 1. Check server started successfully
curl -s https://api.projectdevops.in/docs | grep "Swagger" && echo "✅ Server running"

# 2. Check background scheduler started
# Look in logs for:
grep "Horoscope Scheduler" /path/to/logs | tail -5

# Should see:
# 🚀 [Horoscope Scheduler] Background thread started
# ✅ [Horoscope Scheduler] Background scheduler initialized

# 3. Test debug endpoint
curl -X GET "https://api.projectdevops.in/news/admin/horoscope/debug/today" \
  -H "Authorization: Bearer $TOKEN"

# Should return JSON (not 404 or 500)
```

### 4. Create Test Scheduled Horoscope
```bash
# Use test script from Step 2 of Testing Checklist
# Schedule for 2 minutes from now, verify it auto-publishes
```

## 📚 API Reference

### Debug Endpoints Summary

| Endpoint | Method | Purpose | Auth |
|----------|--------|---------|------|
| `/admin/horoscope/debug/today` | GET | Check today's horoscopes | Admin/Author |
| `/admin/horoscope/debug/all-dates` | GET | List all horoscope dates | Admin/Author |
| `/admin/horoscope/debug/scheduled` | GET | Check scheduled horoscopes | Admin/Author |
| `/admin/horoscope/force-process-scheduled` | POST | Manually run scheduler | Admin/Author |
| `/admin/horoscope/publish-today` | POST | Emergency publish today | Admin only |

### Scheduler Behavior

| Scenario | Behavior |
|----------|----------|
| Horoscope scheduled for future IST time | Waits until UTC equivalent time, then auto-publishes |
| Today's horoscope created without scheduling | Auto-publishes when date matches today |
| Horoscope scheduled for past time | Error: "Scheduled time must be in the future" |
| Manually publish before scheduled time | Clears scheduling, publishes immediately |

## 🎯 Next Steps

1. **Monitor for 24 hours**: Check logs every few hours to ensure scheduler is working
2. **Test edge cases**: 
   - Schedule for midnight (00:10 IST)
   - Schedule for multiple dates
   - Update scheduled time
3. **Set up alerting** (optional):
   - Alert if scheduler errors increase
   - Alert if today's horoscope unpublished after 6 AM IST
4. **Document for team**: Share this guide with other developers

## 📞 Support

If issues persist:
1. Check server logs: `grep "Horoscope Scheduler" /path/to/logs`
2. Use debug endpoints to inspect state
3. Verify MongoDB connection is stable
4. Check if background thread is running: `ps aux | grep HoroscopeScheduler`

---

**Last Updated**: December 20, 2025
**Version**: 2.0 (with background scheduler)
