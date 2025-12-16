# 🔗 Horoscope API Endpoints Reference
## Complete Backend Endpoint List for UI Integration

**Base URL**: `https://api.projectdevops.in`

---

## 📍 Public Endpoints (No Authentication)

### 1. Get Today's Horoscope
```
GET /news/horoscope/today
```
**Response**: Single `DailyHoroscope` object with all 12 zodiac predictions

---

### 2. Get Horoscope by Date
```
GET /news/horoscope/date/{target_date}
```
**Path Parameter**: `target_date` (format: `YYYY-MM-DD`, example: `2025-12-16`)  
**Response**: Single `DailyHoroscope` object

---

### 3. Get Single Zodiac Prediction
```
GET /news/horoscope/zodiac/{zodiac_sign}
```
**Path Parameter**: `zodiac_sign` (one of: `mesh`, `vrishabh`, `mithun`, `kark`, `simha`, `kanya`, `tula`, `vrishchik`, `dhanu`, `makar`, `kumbh`, `meen`)  
**Query Parameter**: `date` (optional, format: `YYYY-MM-DD`)  
**Response**: Single `ZodiacPrediction` object

**Example**: `/news/horoscope/zodiac/mesh?date=2025-12-16`

---

### 4. Get Horoscope Archive
```
GET /news/horoscope/archive
```
**Query Parameters**:
- `page` (default: 1)
- `limit` (default: 10, max: 100)

**Response**: List of `DailyHoroscope` objects

---

### 5. Increment Views
```
POST /news/horoscope/{horoscope_id}/views
```
**Path Parameter**: `horoscope_id` (MongoDB ObjectId)  
**Headers**: `X-Forwarded-For` or client IP for deduplication  
**Response**: `{ "views": 123, "message": "व्यू जोड़ा गया" }`

---

### 6. Increment Likes
```
POST /news/horoscope/{horoscope_id}/likes
```
**Path Parameter**: `horoscope_id` (MongoDB ObjectId)  
**Headers**: `X-Forwarded-For` or client IP for deduplication  
**Response**: `{ "likes": 45, "message": "लाइक जोड़ा गया" }`

---

## 🔐 Admin/Author Endpoints (JWT Authentication Required)

### 7. Create Horoscope
```
POST /news/admin/horoscope
```
**Headers**: `Authorization: Bearer <jwt_token>`  
**Body**:
```json
{
  "title": "राशि फल✡️🙏🏻",
  "date": "2025-12-16",
  "zodiac_predictions": [
    {
      "sign": "mesh",
      "emoji": "🐏",
      "hindi_name": "मेष राशि",
      "syllables": "चू, चे, चो, ला, ली, लू, ले, लो, अ",
      "prediction": "आज का दिन आपके लिए शुभ रहेगा..."
    }
    // ... all 12 zodiac signs
  ],
  "closing_message": "☘️आपका दिन मंगलमय हो।☘️",
  "contact_info": "संपर्क करें...",
  "published": false
}
```
**Response**: Created `DailyHoroscope` object

---

### 8. Get All Horoscopes (Paginated)
```
GET /news/admin/horoscopes
```
**Headers**: `Authorization: Bearer <jwt_token>`  
**Query Parameters**:
- `page` (default: 1)
- `limit` (default: 10, max: 100)

**Response**: List of `DailyHoroscope` objects

---

### 9. Get Single Horoscope by ID
```
GET /news/admin/horoscope/{horoscope_id}
```
**Headers**: `Authorization: Bearer <jwt_token>`  
**Path Parameter**: `horoscope_id` (MongoDB ObjectId)  
**Response**: Single `DailyHoroscope` object

---

### 10. Update Horoscope
```
PUT /news/admin/horoscope/{horoscope_id}
```
**Headers**: `Authorization: Bearer <jwt_token>`  
**Path Parameter**: `horoscope_id` (MongoDB ObjectId)  
**Body**: Same as create (partial updates supported)
```json
{
  "title": "Updated title",
  "zodiac_predictions": [...],
  "published": true
}
```
**Response**: Updated `DailyHoroscope` object

---

### 11. Delete Horoscope
```
DELETE /news/admin/horoscope/{horoscope_id}
```
**Headers**: `Authorization: Bearer <jwt_token>`  
**Path Parameter**: `horoscope_id` (MongoDB ObjectId)  
**Response**: `{ "message": "राशिफल सफलतापूर्वक डिलीट किया गया" }`

---

### 12. Publish Horoscope
```
POST /news/admin/horoscope/{horoscope_id}/publish
```
**Headers**: `Authorization: Bearer <jwt_token>`  
**Path Parameter**: `horoscope_id` (MongoDB ObjectId)  
**Response**: Updated `DailyHoroscope` object with `published: true`

---

### 13. Unpublish Horoscope
```
POST /news/admin/horoscope/{horoscope_id}/unpublish
```
**Headers**: `Authorization: Bearer <jwt_token>`  
**Path Parameter**: `horoscope_id` (MongoDB ObjectId)  
**Response**: Updated `DailyHoroscope` object with `published: false`

---

### 14. Get Horoscope by Date (Admin)
```
GET /news/admin/horoscope/date/{target_date}
```
**Headers**: `Authorization: Bearer <jwt_token>`  
**Path Parameter**: `target_date` (format: `YYYY-MM-DD`)  
**Note**: Returns both published and unpublished horoscopes  
**Response**: Single `DailyHoroscope` object

---

### 15. Get Author's Horoscopes
```
GET /news/author/horoscopes
```
**Headers**: `Authorization: Bearer <jwt_token>`  
**Query Parameters**:
- `page` (default: 1)
- `limit` (default: 10, max: 100)
- `published` (optional: true/false)

**Response**: List of current author's `DailyHoroscope` objects

---

### 16. Get All Statistics (Admin)
```
GET /news/admin/horoscope/stats
```
**Headers**: `Authorization: Bearer <jwt_token>`  
**Response**:
```json
{
  "total_horoscopes": 100,
  "published_horoscopes": 85,
  "draft_horoscopes": 15,
  "total_views": 5000,
  "total_likes": 1200,
  "most_viewed": { /* DailyHoroscope object */ },
  "most_liked": { /* DailyHoroscope object */ }
}
```

---

### 17. Get Author Statistics
```
GET /news/author/horoscope/stats
```
**Headers**: `Authorization: Bearer <jwt_token>`  
**Response**:
```json
{
  "author": "author_username",
  "total_horoscopes": 50,
  "published_horoscopes": 45,
  "draft_horoscopes": 5,
  "total_views": 2500,
  "total_likes": 600
}
```

---

### 18. Bulk Delete Horoscopes (Admin Only)
```
POST /news/admin/horoscope/bulk-delete
```
**Headers**: `Authorization: Bearer <jwt_token>`  
**Role Required**: `admin`  
**Body**:
```json
["horoscope_id_1", "horoscope_id_2", "horoscope_id_3"]
```
**Response**:
```json
{
  "message": "3 राशिफल सफलतापूर्वक डिलीट किए गए",
  "deleted_count": 3
}
```

---

### 19. Get Draft Horoscopes
```
GET /news/admin/horoscope/drafts
```
**Headers**: `Authorization: Bearer <jwt_token>`  
**Query Parameters**:
- `page` (default: 1)
- `limit` (default: 10, max: 100)

**Note**: Admin sees all drafts, Author sees only own drafts  
**Response**: List of unpublished `DailyHoroscope` objects

---

### 20. Get Published Horoscopes (Admin)
```
GET /news/admin/horoscope/published
```
**Headers**: `Authorization: Bearer <jwt_token>`  
**Query Parameters**:
- `page` (default: 1)
- `limit` (default: 10, max: 100)
- `author` (optional: filter by author username)

**Response**: List of published `DailyHoroscope` objects

---

### 21. Search Horoscopes
```
GET /news/admin/horoscope/search
```
**Headers**: `Authorization: Bearer <jwt_token>`  
**Query Parameters**:
- `query` (required: search term)
- `page` (default: 1)
- `limit` (default: 10, max: 100)

**Searches in**: title, predictions, closing_message  
**Response**: List of matching `DailyHoroscope` objects

**Example**: `/news/admin/horoscope/search?query=शुभ&page=1`

---

### 22. Get Horoscopes by Date Range
```
GET /news/admin/horoscope/date-range
```
**Headers**: `Authorization: Bearer <jwt_token>`  
**Query Parameters**:
- `start_date` (required: format `YYYY-MM-DD`)
- `end_date` (required: format `YYYY-MM-DD`)
- `published` (optional: true/false)

**Response**: List of `DailyHoroscope` objects within date range

**Example**: `/news/admin/horoscope/date-range?start_date=2025-12-01&end_date=2025-12-31&published=true`

---

## 📦 Data Models

### DailyHoroscope
```typescript
{
  _id: string;                        // MongoDB ObjectId
  title: string;                      // "राशि फल✡️🙏🏻"
  date: string;                       // "2025-12-16" (ISO date)
  zodiac_predictions: ZodiacPrediction[];  // All 12 signs
  closing_message: string;            // "☘️आपका दिन मंगलमय हो।☘️"
  contact_info?: string;              // Optional contact text
  published: boolean;
  views: number;
  likes: number;
  author_username: string;
  created_at: string;                 // ISO datetime
  updated_at: string;                 // ISO datetime
  published_at?: string;              // ISO datetime (if published)
}
```

### ZodiacPrediction
```typescript
{
  sign: string;                       // "mesh", "vrishabh", etc.
  emoji: string;                      // "🐏", "🐂", etc.
  hindi_name: string;                 // "मेष राशि", "वृष राशि"
  syllables: string;                  // "चू, चे, चो, ला, ली, लू, ले, लो, अ"
  prediction: string;                 // Full Hindi prediction text
}
```

---

## 🔑 Authentication

All admin/author endpoints require JWT token in header:
```
Authorization: Bearer <your_jwt_token>
```

**Get JWT Token**:
```
POST /login
Body: { "username": "your_username", "password": "your_password" }
Response: { "access_token": "<jwt_token>", "token_type": "bearer" }
```

---

## 🚨 Common Error Responses

### 401 Unauthorized
```json
{ "detail": "Not authenticated" }
```

### 403 Forbidden
```json
{ "detail": "Admin access required" }
```

### 404 Not Found
```json
{ "detail": "राशिफल नहीं मिला" }
```

### 400 Bad Request
```json
{ "detail": "All 12 zodiac predictions are required" }
```

---

## 💡 UI Integration Tips

### For Admin Panel

**Dashboard Page**:
```javascript
// Get statistics
const stats = await fetch('/news/admin/horoscope/stats', {
  headers: { 'Authorization': `Bearer ${token}` }
});

// Get recent horoscopes
const recent = await fetch('/news/admin/horoscopes?page=1&limit=5', {
  headers: { 'Authorization': `Bearer ${token}` }
});
```

**Create Form**:
```javascript
// Create new horoscope
const response = await fetch('/news/admin/horoscope', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify(horoscopeData)
});
```

**Edit Form**:
```javascript
// Get horoscope to edit
const horoscope = await fetch(`/news/admin/horoscope/${id}`, {
  headers: { 'Authorization': `Bearer ${token}` }
});

// Update horoscope
const updated = await fetch(`/news/admin/horoscope/${id}`, {
  method: 'PUT',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify(updatedData)
});
```

**Quick Actions**:
```javascript
// Publish
await fetch(`/news/admin/horoscope/${id}/publish`, {
  method: 'POST',
  headers: { 'Authorization': `Bearer ${token}` }
});

// Unpublish
await fetch(`/news/admin/horoscope/${id}/unpublish`, {
  method: 'POST',
  headers: { 'Authorization': `Bearer ${token}` }
});

// Delete
await fetch(`/news/admin/horoscope/${id}`, {
  method: 'DELETE',
  headers: { 'Authorization': `Bearer ${token}` }
});
```

### For Author Panel

**Dashboard**:
```javascript
// Get author's stats
const stats = await fetch('/news/author/horoscope/stats', {
  headers: { 'Authorization': `Bearer ${token}` }
});

// Get author's horoscopes
const myHoroscopes = await fetch('/news/author/horoscopes?page=1', {
  headers: { 'Authorization': `Bearer ${token}` }
});
```

### For Public Pages

**Today's Horoscope**:
```javascript
// No auth required
const today = await fetch('/news/horoscope/today');
```

**Increment Views**:
```javascript
// Track views (automatic IP deduplication)
await fetch(`/news/horoscope/${id}/views`, {
  method: 'POST'
});
```

---

## 🧪 Testing with cURL

### Test Authentication
```bash
# Login
curl -X POST "https://api.projectdevops.in/login" \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"your_password"}'

# Use token
TOKEN="your_jwt_token"
curl -X GET "https://api.projectdevops.in/news/admin/horoscopes" \
  -H "Authorization: Bearer $TOKEN"
```

### Test Public Endpoints
```bash
# Get today's horoscope
curl "https://api.projectdevops.in/news/horoscope/today"

# Get by date
curl "https://api.projectdevops.in/news/horoscope/date/2025-12-16"

# Get single zodiac
curl "https://api.projectdevops.in/news/horoscope/zodiac/mesh?date=2025-12-16"
```

---

**Need help?** Check [HOROSCOPE_API_GUIDE.md](HOROSCOPE_API_GUIDE.md) for detailed examples and [HOROSCOPE_UI_DEVELOPMENT_GUIDE.md](HOROSCOPE_UI_DEVELOPMENT_GUIDE.md) for UI implementation.
