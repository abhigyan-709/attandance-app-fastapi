# Horoscope Scheduling System Guide

## Overview
The horoscope system now supports **IST (Indian Standard Time) timezone-based scheduled publishing**, identical to the news system. Horoscopes can be scheduled for future publication, and will automatically publish when the scheduled time is reached.

## Key Features

### 1. **IST Timezone Support**
- Frontend sends datetime in IST format: `"2025-12-16T14:30"` (YYYY-MM-DDTHH:MM)
- Backend converts to UTC and stores in MongoDB
- API responses include both UTC and IST times for frontend display

### 2. **Scheduled Publishing Flow**
```
Create Horoscope → Set Schedule → Auto-Publish at Scheduled Time
```

### 3. **Auto-Publish Mechanism**
- Every public horoscope endpoint call triggers `_process_scheduled_horoscopes()`
- Scans for horoscopes with `scheduled_publish=true` and `scheduled_at <= current_utc`
- Automatically sets `published=true` and `published_at=scheduled_at`
- Changes `scheduled_publish` to `false` after publishing

## Database Schema Changes

### DailyHoroscope Model
```python
class DailyHoroscope(BaseModel):
    # ... existing fields ...
    scheduled_publish: bool = False              # Is this scheduled for future?
    scheduled_at: Optional[datetime] = None      # UTC datetime for scheduled publish
    published_at: Optional[datetime] = None      # When it was published
```

### Request Models
```python
class CreateHoroscopeRequest(BaseModel):
    # ... existing fields ...
    scheduled_publish: bool = False
    scheduled_at: Optional[str] = None  # IST format: "YYYY-MM-DDTHH:MM"

class UpdateHoroscopeRequest(BaseModel):
    # ... existing fields ...
    scheduled_publish: Optional[bool] = None
    scheduled_at: Optional[str] = None  # IST format: "YYYY-MM-DDTHH:MM"
```

## API Usage

### Create Scheduled Horoscope

**Endpoint:** `POST /admin/horoscope`

**Example 1: Schedule for Future (12:00 PM IST on Dec 16, 2025)**
```json
{
  "date": "2025-12-16",
  "title": "राशि फल✡️🙏🏻",
  "zodiac_predictions": [
    {
      "sign": "mesh",
      "hindi_name": "मेष",
      "syllables": "चू, चे, चो, ला, ली, लू, ले, लो, आ",
      "prediction": "आज आपके जीवन में..."
    }
    // ... all 12 zodiac signs
  ],
  "closing_text": "🙏सभी मित्रों को जय श्री राम🙏",
  "contact_info": "📞 संपर्क करें: 7894561230",
  "published": false,                    // Ignored when scheduling
  "scheduled_publish": true,             // Enable scheduling
  "scheduled_at": "2025-12-16T12:00"    // IST datetime
}
```

**Response:**
```json
{
  "_id": "676...",
  "date": "2025-12-16",
  "published": false,                    // Will be false until scheduled time
  "scheduled_publish": true,
  "scheduled_at": "2025-12-16T06:30:00", // Stored in UTC (IST - 5:30)
  "scheduled_at_ist": "2025-12-16T12:00:00",  // Display in IST
  "created_at": "2025-12-15T10:00:00",
  // ... other fields
}
```

**Example 2: Publish Immediately**
```json
{
  "date": "2025-12-15",
  "title": "राशि फल✡️🙏🏻",
  "zodiac_predictions": [...],
  "closing_text": "🙏सभी मित्रों को जय श्री राम🙏",
  "contact_info": "📞 संपर्क करें: 7894561230",
  "published": true,
  "scheduled_publish": false,   // No scheduling
  "scheduled_at": null          // Ignored
}
```

### Update Schedule

**Endpoint:** `PUT /admin/horoscope/{horoscope_id}`

**Example 1: Change Schedule Time**
```json
{
  "scheduled_publish": true,
  "scheduled_at": "2025-12-16T18:00"  // New IST time
}
```

**Example 2: Disable Scheduling (Manual Publish)**
```json
{
  "published": true,           // Publish now
  "scheduled_publish": false   // Clear schedule
}
```

**Example 3: Cancel Schedule, Keep as Draft**
```json
{
  "scheduled_publish": false,  // Disable scheduling
  "published": false           // Keep as draft
}
```

## Validation Rules

### Create Horoscope
1. **Scheduled time must be in the future**
   - Error if `scheduled_at <= current_utc`
   - Returns user-friendly IST time in error message

2. **scheduled_at required when scheduled_publish=true**
   - Error if `scheduled_publish=true` but `scheduled_at=null`

3. **published flag overridden**
   - If `scheduled_publish=true`, backend forces `published=false`
   - Horoscope will auto-publish at scheduled time

### Update Horoscope
1. **Same validation as create** for scheduled_at

2. **Manual publish clears schedule**
   - Setting `published=true` automatically sets:
     - `scheduled_publish=false`
     - `scheduled_at=null`

3. **Scheduled time updates**
   - Can change `scheduled_at` while keeping `scheduled_publish=true`
   - New time must still be in the future

## Auto-Publish Process

### Trigger Points
Auto-publish runs on **every public endpoint call**:
- `GET /horoscope/today`
- `GET /horoscope/date/{date}`
- `GET /horoscope/zodiac/{zodiac_sign}`
- `GET /horoscope/archive`

### Process Logic
```python
def _process_scheduled_horoscopes(db_client: MongoClient):
    current_utc = datetime.utcnow()
    
    # Find horoscopes ready to publish
    scheduled_horoscopes = db_client[db.db_name][HOROSCOPE_COLL].find({
        "scheduled_publish": True,
        "published": False,
        "scheduled_at": {"$lte": current_utc}
    })
    
    for horoscope in scheduled_horoscopes:
        # Publish using scheduled time as published_at
        db_client[db.db_name][HOROSCOPE_COLL].update_one(
            {"_id": horoscope["_id"]},
            {"$set": {
                "published": True,
                "published_at": horoscope["scheduled_at"],  # Use scheduled time
                "scheduled_publish": False,
                "updated_at": current_utc
            }}
        )
```

## IST Helper Functions

### 1. Parse IST to UTC
```python
def _parse_ist_datetime_horoscope(datetime_str: str) -> datetime:
    """
    Converts IST string to UTC datetime
    Input: "2025-12-16T14:30" (IST)
    Output: datetime(2025, 12, 16, 9, 0) (UTC)
    """
```

### 2. Convert UTC to IST
```python
def _utc_to_ist_horoscope(utc_dt: datetime) -> datetime:
    """
    Converts UTC datetime to IST datetime
    Input: datetime(2025, 12, 16, 9, 0) (UTC)
    Output: datetime(2025, 12, 16, 14, 30) (IST)
    """
```

### 3. Check if Scheduled Time Reached
```python
def _is_scheduled_horoscope_ready(scheduled_at: datetime) -> bool:
    """
    Returns True if current UTC time >= scheduled_at
    """
```

### 4. Normalize Horoscope Response
```python
def _normalize_horoscope(doc: Dict[str, Any]) -> Dict[str, Any]:
    """
    Adds scheduled_at_ist field for frontend display
    Converts scheduled_at (UTC) to IST datetime
    """
```

## Frontend Integration

### Display Scheduled Time
API response includes both UTC and IST:
```json
{
  "scheduled_at": "2025-12-16T06:30:00",      // UTC (for backend)
  "scheduled_at_ist": "2025-12-16T12:00:00"   // IST (for display)
}
```

**Display to User:**
```javascript
// React/Next.js example
{horoscope.scheduled_publish && (
  <div className="scheduled-badge">
    Scheduled for: {formatDateTime(horoscope.scheduled_at_ist)}
  </div>
)}
```

### Schedule Picker
```javascript
// Send IST datetime to backend
const scheduleTime = "2025-12-16T14:30";  // From datetime-local input

await fetch('/admin/horoscope', {
  method: 'POST',
  body: JSON.stringify({
    // ... horoscope data ...
    scheduled_publish: true,
    scheduled_at: scheduleTime  // Backend handles UTC conversion
  })
});
```

### Status Indicators
```javascript
function getHoroscopeStatus(horoscope) {
  if (horoscope.published) {
    return "Published";
  } else if (horoscope.scheduled_publish) {
    return `Scheduled (${horoscope.scheduled_at_ist})`;
  } else {
    return "Draft";
  }
}
```

## Admin Dashboard Features

### Filter by Status
```javascript
// GET /admin/horoscopes?published=false
// Shows drafts AND scheduled horoscopes

// GET /admin/horoscopes?published=true
// Shows only published horoscopes
```

### Upcoming Scheduled Horoscopes
Query MongoDB directly or create custom endpoint:
```python
@news_router.get("/admin/horoscopes/scheduled")
async def get_scheduled_horoscopes(
    db_client: MongoClient = Depends(db.get_client)
):
    scheduled = list(
        db_client[db.db_name][HOROSCOPE_COLL]
        .find({
            "scheduled_publish": True,
            "published": False
        })
        .sort("scheduled_at", ASCENDING)
    )
    return [_normalize_horoscope(h) for h in scheduled]
```

## Error Handling

### Common Errors

1. **Past Scheduled Time**
```json
{
  "detail": "Scheduled time must be in the future. Current IST time: 2025-12-15 10:30"
}
```

2. **Missing scheduled_at**
```json
{
  "detail": "scheduled_at is required when scheduled_publish is true. Provide datetime in format: YYYY-MM-DDTHH:MM (IST)"
}
```

3. **Invalid Date Format**
```python
# Frontend should send: "2025-12-16T14:30"
# NOT: "2025-12-16 14:30" or "16-12-2025T14:30"
```

## Testing Schedule Feature

### Manual Test Script
```bash
#!/bin/bash

# 1. Create scheduled horoscope (30 seconds in future)
FUTURE_TIME=$(date -u -v+30S "+%Y-%m-%dT%H:%M")  # macOS
# FUTURE_TIME=$(date -u -d "+30 seconds" "+%Y-%m-%dT%H:%M")  # Linux

curl -X POST "https://api.projectdevops.in/admin/horoscope" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"date\": \"$(date +%Y-%m-%d)\",
    \"title\": \"राशि फल✡️🙏🏻\",
    \"zodiac_predictions\": [...],
    \"closing_text\": \"🙏जय श्री राम🙏\",
    \"contact_info\": \"📞 7894561230\",
    \"scheduled_publish\": true,
    \"scheduled_at\": \"$FUTURE_TIME\"
  }"

# 2. Check horoscope is unpublished
HOROSCOPE_ID="<id_from_response>"
curl "https://api.projectdevops.in/admin/horoscope/$HOROSCOPE_ID" \
  -H "Authorization: Bearer $ADMIN_TOKEN"

# 3. Wait 35 seconds
sleep 35

# 4. Access public endpoint (triggers auto-publish)
curl "https://api.projectdevops.in/horoscope/today"

# 5. Verify horoscope is now published
curl "https://api.projectdevops.in/admin/horoscope/$HOROSCOPE_ID" \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

## Best Practices

1. **Always Schedule in IST**
   - Users think in IST timezone
   - Backend handles UTC conversion automatically

2. **Validate Before Scheduling**
   - Check all 12 zodiac signs present
   - Verify future datetime before submission

3. **Show Status Clearly**
   - Use badges/indicators for scheduled posts
   - Display countdown to scheduled time

4. **Handle Failed Auto-Publish**
   - If server down at scheduled time, horoscope publishes on next request
   - No manual intervention needed

5. **Update Schedules Carefully**
   - Changing schedule clears old time completely
   - To cancel schedule, set `scheduled_publish=false`

## Production Deployment

### Environment Variables
Ensure `.env` includes:
```bash
# Timezone handling
TZ=UTC  # Server should run in UTC

# MongoDB connection
MONGO_URI=mongodb://...

# AWS secrets for MongoDB URI
AWS_REGION=ap-south-1
```

### System Timezone
Server must run in UTC for correct scheduling:
```bash
# Check server timezone
timedatectl

# Set to UTC if needed
sudo timedatectl set-timezone UTC
```

### Monitoring
Watch for:
- Horoscopes stuck in "scheduled" state
- Large time drift between server and actual time
- Failed auto-publish attempts (check logs)

## Comparison with News System

Both horoscope and news systems use **identical scheduling logic**:

| Feature | News | Horoscope |
|---------|------|-----------|
| IST Input | ✅ | ✅ |
| UTC Storage | ✅ | ✅ |
| Auto-Publish | ✅ | ✅ |
| Future Validation | ✅ | ✅ |
| Manual Override | ✅ | ✅ |
| IST Display | ✅ | ✅ |

**Helper Functions:**
- News: `_parse_ist_datetime()`, `_utc_to_ist()`, `_process_scheduled_posts()`
- Horoscope: `_parse_ist_datetime_horoscope()`, `_utc_to_ist_horoscope()`, `_process_scheduled_horoscopes()`

## Troubleshooting

### Scheduled Horoscope Not Publishing

**Check 1: Server Time**
```bash
date -u  # Should show correct UTC time
```

**Check 2: MongoDB Data**
```javascript
db.daily_horoscopes.find({
  scheduled_publish: true,
  published: false
})
```

**Check 3: scheduled_at Format**
```javascript
// Correct UTC storage
"scheduled_at": ISODate("2025-12-16T06:30:00Z")

// Wrong (string instead of datetime)
"scheduled_at": "2025-12-16T06:30:00"
```

**Check 4: Public Endpoint Called**
```bash
# Trigger auto-publish manually
curl "https://api.projectdevops.in/horoscope/today"
```

### Wrong Timezone Display

**Frontend shows wrong time:**
- Backend returns both `scheduled_at` (UTC) and `scheduled_at_ist` (IST)
- Use `scheduled_at_ist` for display to users
- Use `scheduled_at` for backend logic only

**User enters wrong timezone:**
- Always show "IST" label near datetime picker
- Example: "Schedule Time (IST): [datetime-local input]"

## Related Files

- **Models:** `models/news.py` (Lines 88-175)
- **Routes:** `routes/news.py` (Lines 2170-2290, 2515-3170)
- **Helper Functions:** `routes/news.py` (Lines 2171-2268)
- **CLI Script:** `create_horoscope.py` (needs scheduling update)

## Next Steps

1. **Update CLI Script**
   - Add `--schedule` flag to `create_horoscope.py`
   - Example: `python3 create_horoscope.py 2025-12-16 admin --schedule "2025-12-16T12:00"`

2. **Create Scheduled Endpoint**
   - Add `GET /admin/horoscopes/scheduled` for dashboard
   - Returns upcoming scheduled horoscopes

3. **Add Notifications**
   - Send email/push notification when horoscope auto-publishes
   - Alert admins if auto-publish fails

4. **Scheduling Analytics**
   - Track scheduled vs immediate publishes
   - Monitor average schedule-to-publish time
