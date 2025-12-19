# Horoscope Scheduling Fix - IST Timezone Issue

## Problem Description

The horoscope scheduling system had two critical issues:

1. **Scheduled horoscopes not auto-publishing**: Horoscopes scheduled for specific IST times (e.g., 12:10 AM) were not being automatically published at the scheduled time.

2. **Scheduling UI showing after publish**: After a scheduled horoscope was published, the UI still displayed scheduling options instead of showing it as published.

## Root Causes

### Issue 1: `scheduled_publish` Flag Not Cleared
When the background task `_process_scheduled_horoscopes()` auto-published a scheduled horoscope, it was setting:
- `published: True` ✓
- `published_at: <scheduled_time>` ✓

But it was **NOT** setting:
- `scheduled_publish: False` ✗

This caused the UI to think the horoscope was still in "scheduled" state even after it was published.

### Issue 2: Timezone Conversion (If Applicable)
The timezone conversion logic was already correct, but lacked debug logging to troubleshoot issues. The system properly:
- Accepts IST datetime input from frontend (format: `YYYY-MM-DDTHH:MM`)
- Converts to UTC for storage using `pytz`
- Compares UTC times for scheduling logic
- Converts back to IST for display in API responses

## Solution Applied

### 1. Clear `scheduled_publish` Flag on Auto-Publish
**File**: `routes/news.py` - Function: `_process_scheduled_horoscopes()`

**Before**:
```python
coll.update_one(
    {"_id": horoscope["_id"]},
    {
        "$set": {
            "published": True,
            "published_at": scheduled_time,
            "updated_at": datetime.utcnow()
        }
    }
)
```

**After**:
```python
coll.update_one(
    {"_id": horoscope["_id"]},
    {
        "$set": {
            "published": True,
            "published_at": scheduled_time,
            "updated_at": datetime.utcnow(),
            "scheduled_publish": False  # ✅ Clear scheduling flag after publishing
        }
    }
)
```

### 2. Enhanced Debug Logging
Added comprehensive logging to track timezone conversions and scheduling operations:

**In `_parse_ist_datetime_horoscope()`**:
```python
logger.info(f"[Timezone Conversion] Input IST: {datetime_str} -> Parsed IST: {ist_dt} -> UTC: {utc_dt}")
```

**In `_process_scheduled_horoscopes()`**:
```python
current_ist = _utc_to_ist_horoscope(current_utc)
logger.info(f"[Horoscope Scheduler] Current UTC: {current_utc}, IST: {current_ist}")

scheduled_ist = _utc_to_ist_horoscope(scheduled_time)
logger.info(f"[Horoscope Scheduler] Auto-publishing horoscope {horoscope['_id']} scheduled for UTC: {scheduled_time}, IST: {scheduled_ist}")
```

## How Scheduling Works

### 1. Creating a Scheduled Horoscope
```bash
POST /news/admin/horoscope
{
  "date": "2025-12-21",
  "scheduled_publish": true,
  "scheduled_at": "2025-12-21T00:10",  # IST time: 12:10 AM
  "published": false,
  "zodiac_predictions": [...]
}
```

**Backend Processing**:
1. Parse `"2025-12-21T00:10"` as IST (India Standard Time)
2. Convert to UTC: `2025-12-20T18:40:00` (5.5 hours behind)
3. Store in MongoDB:
   - `scheduled_at: 2025-12-20T18:40:00` (UTC)
   - `scheduled_publish: true`
   - `published: false`

### 2. Auto-Publishing Scheduled Horoscopes
The background task `_process_scheduled_horoscopes()` runs on every public horoscope API call:
- `/news/horoscope/today`
- `/news/horoscope/date/{date}`
- `/news/admin/horoscopes` (list)
- `/news/admin/horoscope/{id}` (get by ID)

**Logic**:
```python
current_utc = datetime.utcnow()  # e.g., 2025-12-20T18:45:00

# Find horoscopes where:
# - scheduled_publish = true
# - published = false
# - scheduled_at <= current_utc
scheduled_horoscopes = coll.find({
    "scheduled_publish": True,
    "published": False,
    "scheduled_at": {"$lte": current_utc}
})

# Auto-publish each one
for horoscope in scheduled_horoscopes:
    coll.update_one(
        {"_id": horoscope["_id"]},
        {"$set": {
            "published": True,
            "published_at": horoscope["scheduled_at"],
            "scheduled_publish": False,  # ✅ FIX: Clear scheduling flag
            "updated_at": datetime.utcnow()
        }}
    )
```

### 3. API Response Format
When returning horoscope data, the `_normalize_horoscope()` function adds IST times:

```json
{
  "_id": "676...",
  "date": "2025-12-21",
  "published": true,
  "scheduled_publish": false,  // ✅ Now correctly false after auto-publish
  
  // UTC times (for backend reference)
  "created_at": "2025-12-20T10:00:00",
  "published_at": "2025-12-20T18:40:00",
  "scheduled_at": "2025-12-20T18:40:00",
  
  // IST times (for display in UI)
  "created_at_ist": "2025-12-20T15:30:00",
  "published_at_ist": "2025-12-21T00:10:00",
  "scheduled_at_ist": "2025-12-21T00:10:00"
}
```

## Testing the Fix

### Prerequisites
1. Have admin/author JWT token ready
2. Server must be running with MongoDB connection

### Test Steps

#### Option 1: Automated Test Script
```bash
# Set your JWT token
export TOKEN="your_jwt_token_here"

# Run test script
./test_horoscope_scheduling_fix.sh
```

#### Option 2: Manual Testing
```bash
# 1. Get current IST time + 2 minutes
SCHEDULED_TIME=$(python3 -c "
from datetime import datetime, timedelta
import pytz
ist = pytz.timezone('Asia/Kolkata')
scheduled = datetime.now(ist) + timedelta(minutes=2)
print(scheduled.strftime('%Y-%m-%dT%H:%M'))
")

echo "Testing with scheduled time: $SCHEDULED_TIME"

# 2. Create scheduled horoscope
curl -X POST "https://api.projectdevops.in/news/admin/horoscope" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"title\": \"राशि फल✡️🙏🏻\",
    \"date\": \"2025-12-21\",
    \"zodiac_predictions\": [...],  # Include all 12 signs
    \"published\": false,
    \"scheduled_publish\": true,
    \"scheduled_at\": \"$SCHEDULED_TIME\"
  }"

# 3. Wait 2-3 minutes, then check if published
# Trigger the background task by calling any public endpoint
curl "https://api.projectdevops.in/news/horoscope/today"

# 4. Verify the horoscope is published and scheduled_publish is false
curl "https://api.projectdevops.in/news/admin/horoscope/{horoscope_id}" \
  -H "Authorization: Bearer $TOKEN"
```

### Expected Results
1. **Before scheduled time**:
   - `scheduled_publish: true`
   - `published: false`
   - `scheduled_at_ist` shows correct IST time

2. **After scheduled time** (when background task runs):
   - `scheduled_publish: false` ✅ (This was the bug - now fixed)
   - `published: true` ✅
   - `published_at_ist` shows the scheduled IST time ✅

3. **Server logs** should show:
   ```
   [Timezone Conversion] Input IST: 2025-12-21T00:10 -> Parsed IST: 2025-12-21 00:10:00+05:30 -> UTC: 2025-12-20 18:40:00
   [Horoscope Scheduler] Current UTC: 2025-12-20 18:42:00, IST: 2025-12-21 00:12:00
   [Horoscope Scheduler] Auto-publishing horoscope ... scheduled for UTC: 2025-12-20 18:40:00, IST: 2025-12-21 00:10:00
   Auto-published scheduled horoscope: ... for date 2025-12-21
   ```

## Timezone Reference

### IST (India Standard Time)
- UTC offset: **+05:30** (5 hours 30 minutes ahead)
- No daylight saving time

### Conversion Examples
| IST Time | UTC Time | Notes |
|----------|----------|-------|
| 00:10 AM (midnight) | 6:40 PM (previous day) | Scheduled horoscope example |
| 12:00 PM (noon) | 6:30 AM | |
| 11:59 PM | 6:29 PM | |

### Common Pitfalls to Avoid
1. ❌ **Never compare IST datetime with UTC datetime directly**
   ```python
   # WRONG
   if ist_time > utc_time:  # Comparing different timezones!
   ```

2. ✅ **Always convert to same timezone before comparison**
   ```python
   # CORRECT
   if ist_time.astimezone(pytz.UTC) > utc_time:
   ```

3. ❌ **Never store timezone-aware datetimes in MongoDB**
   ```python
   # WRONG
   doc["scheduled_at"] = ist_dt  # Has timezone info
   ```

4. ✅ **Always store naive UTC datetimes**
   ```python
   # CORRECT
   doc["scheduled_at"] = utc_dt.replace(tzinfo=None)
   ```

## Future Improvements

### 1. Dedicated Scheduler Service
Instead of running `_process_scheduled_horoscopes()` on every API call, consider:
- **APScheduler**: Run background task every 1-5 minutes
- **Celery**: Distributed task queue for production
- **AWS EventBridge**: Serverless scheduled tasks

### 2. Notification System
When a scheduled horoscope is auto-published:
- Send push notifications to subscribed users
- Trigger fresh news push via `/push/notify-fresh-news`
- Log publish events for analytics

### 3. UI/UX Enhancements
- Show countdown timer until scheduled publish time
- Display "Scheduled for <IST_TIME>" badge in admin UI
- Add "Cancel Schedule" button to revert to draft

### 4. Testing
- Add unit tests for timezone conversion functions
- Integration tests for scheduling workflow
- Mock datetime for predictable test results

## Related Files
- `routes/news.py`: Main horoscope endpoints and scheduling logic
- `models/news.py`: DailyHoroscope, CreateHoroscopeRequest models
- `test_horoscope_scheduling_fix.sh`: Automated test script

## Deployment Checklist
- [ ] Deploy updated `routes/news.py` to production
- [ ] Restart FastAPI server
- [ ] Monitor logs for timezone conversion messages
- [ ] Test with real scheduled horoscope (2-3 minutes in future)
- [ ] Verify existing scheduled horoscopes get auto-published correctly

## Support
For issues or questions:
1. Check server logs for `[Timezone Conversion]` and `[Horoscope Scheduler]` messages
2. Verify MongoDB documents have correct UTC times stored
3. Test timezone conversion manually with Python REPL:
   ```python
   from datetime import datetime
   import pytz
   
   IST = pytz.timezone('Asia/Kolkata')
   
   # Parse IST time
   naive_dt = datetime.strptime("2025-12-21T00:10", "%Y-%m-%dT%H:%M")
   ist_dt = IST.localize(naive_dt)
   
   # Convert to UTC
   utc_dt = ist_dt.astimezone(pytz.UTC).replace(tzinfo=None)
   
   print(f"IST: {ist_dt}")
   print(f"UTC: {utc_dt}")
   ```
