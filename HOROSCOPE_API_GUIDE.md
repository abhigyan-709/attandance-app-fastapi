# 🔮 Horoscope API Guide

Complete API documentation for the Daily Horoscope system (राशि फल).

## 📋 Table of Contents
- [Overview](#overview)
- [Models](#models)
- [Public Endpoints](#public-endpoints)
- [Admin/Author CRUD Operations](#adminauthor-crud-operations)
- [Statistics & Analytics](#statistics--analytics)
- [UI Implementation Guide](#ui-implementation-guide)

---

## 🌟 Overview

The horoscope system provides daily predictions for all 12 zodiac signs in Hindi with:
- ✨ Emojis for each zodiac sign
- 📝 Sanskrit syllables (अक्षर)
- 🔮 Daily predictions in Hindi
- 📊 View and like tracking
- 👥 Admin/Author management

**Collection**: `daily_horoscopes`

---

## 📦 Models

### ZodiacSign (Enum)
```python
mesh        # मेष (Aries) 🐏
vrishabh    # वृषभ (Taurus) 🐂
mithun      # मिथुन (Gemini) 👭
kark        # कर्क (Cancer) 🦀
simha       # सिंह (Leo) 🐅
kanya       # कन्या (Virgo) 🙎‍♀️
tula        # तुला (Libra) ⚖️
vrishchik   # वृश्चिक (Scorpio) 🦂
dhanu       # धनु (Sagittarius) 🏹
makar       # मकर (Capricorn) 🐊
kumbh       # कुम्भ (Aquarius) ⚱️
meen        # मीन (Pisces) 🐟
```

### ZodiacPrediction
```json
{
  "sign": "mesh",
  "emoji": "🐏",
  "hindi_name": "मेष राशि",
  "syllables": "चू, चे, चो, ला, ली, लू, ले, लो, अ",
  "prediction": "आज अपने काम के लिए दूसरों पर दबाव न डालें..."
}
```

### DailyHoroscope
```json
{
  "_id": "string",
  "title": "राशि फल✡️🙏🏻",
  "date": "2025-12-16",
  "zodiac_predictions": [...],  // Array of 12 ZodiacPrediction
  "closing_message": "☘️आपका दिन मंगलमय हो।☘️",
  "contact_info": "🕉️ कुण्डली विचार...",
  "author_username": "admin",
  "published": true,
  "views": 0,
  "likes": 0,
  "created_at": "2025-12-16T10:00:00Z",
  "published_at": "2025-12-16T10:00:00Z"
}
```

---

## 🌍 Public Endpoints

### 1. Get Today's Horoscope
```http
GET /news/horoscope/today
```
**Response**: Full horoscope with all 12 zodiac predictions

**Example**:
```bash
curl https://api.projectdevops.in/news/horoscope/today
```

---

### 2. Get Horoscope by Date
```http
GET /news/horoscope/date/{target_date}
```
**Parameters**:
- `target_date`: Date in YYYY-MM-DD format

**Example**:
```bash
curl https://api.projectdevops.in/news/horoscope/date/2025-12-16
```

---

### 3. Get Specific Zodiac Prediction (Today)
```http
GET /news/horoscope/zodiac/{zodiac_sign}
```
**Parameters**:
- `zodiac_sign`: One of the ZodiacSign enum values (mesh, vrishabh, etc.)

**Example**:
```bash
curl https://api.projectdevops.in/news/horoscope/zodiac/mesh
```

---

### 4. Get Horoscope Archive
```http
GET /news/horoscope/archive?page=1&limit=10
```
**Query Parameters**:
- `page`: Page number (default: 1)
- `limit`: Items per page (max: 50, default: 10)

**Example**:
```bash
curl "https://api.projectdevops.in/news/horoscope/archive?page=1&limit=20"
```

---

### 5. Increment Views
```http
POST /news/horoscope/{horoscope_id}/views
```
**Description**: Track horoscope views (IP-based deduplication)

---

### 6. Increment Likes
```http
POST /news/horoscope/{horoscope_id}/likes
```
**Description**: Track horoscope likes (IP-based deduplication)

---

## 🔐 Admin/Author CRUD Operations

### Authentication Required
All admin/author endpoints require:
```http
Authorization: Bearer <JWT_TOKEN>
```
**Roles**: `admin` or `author`

---

### 1. Create Horoscope
```http
POST /news/admin/horoscope
Authorization: Bearer <TOKEN>
Content-Type: application/json
```

**Request Body**:
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
      "prediction": "आज का दिन शुभ रहेगा..."
    }
    // ... all 12 zodiac signs required
  ],
  "closing_message": "☘️आपका दिन मंगलमय हो।☘️",
  "contact_info": "कुण्डली विचार हेतु सम्पर्क करें",
  "published": false  // Save as draft
}
```

**Validation**:
- All 12 zodiac signs must be present
- Date must be unique (one horoscope per day)

---

### 2. Get All Horoscopes (Admin View)
```http
GET /news/admin/horoscopes?page=1&limit=10&published=true
Authorization: Bearer <TOKEN>
```

**Query Parameters**:
- `page`: Page number
- `limit`: Items per page (max: 100)
- `published`: Filter by status (true/false/null for all)

---

### 3. Get Horoscope by ID (Admin)
```http
GET /news/admin/horoscope/{horoscope_id}
Authorization: Bearer <TOKEN>
```
**Description**: Get single horoscope (includes unpublished)

---

### 4. Get Horoscope by Date (Admin)
```http
GET /news/admin/horoscope/date/{target_date}
Authorization: Bearer <TOKEN>
```
**Description**: Get horoscope for specific date (includes unpublished)

---

### 5. Update Horoscope
```http
PUT /news/admin/horoscope/{horoscope_id}
Authorization: Bearer <TOKEN>
Content-Type: application/json
```

**Request Body** (all fields optional):
```json
{
  "title": "Updated Title",
  "zodiac_predictions": [...],
  "closing_message": "Updated message",
  "published": true
}
```

---

### 6. Delete Horoscope
```http
DELETE /news/admin/horoscope/{horoscope_id}
Authorization: Bearer <TOKEN>
```

---

### 7. Publish Horoscope
```http
POST /news/admin/horoscope/{horoscope_id}/publish
Authorization: Bearer <TOKEN>
```
**Description**: Publish a draft horoscope

---

### 8. Unpublish Horoscope
```http
POST /news/admin/horoscope/{horoscope_id}/unpublish
Authorization: Bearer <TOKEN>
```
**Description**: Convert published horoscope to draft

---

### 9. Get Author's Horoscopes
```http
GET /news/author/horoscopes?page=1&limit=10&published=true
Authorization: Bearer <TOKEN>
```
**Description**: Get horoscopes created by current author

---

### 10. Get Draft Horoscopes
```http
GET /news/admin/horoscope/drafts?page=1&limit=10
Authorization: Bearer <TOKEN>
```
**Description**: Get all unpublished horoscopes

---

### 11. Get Published Horoscopes (Admin)
```http
GET /news/admin/horoscope/published?page=1&limit=10&author=username
Authorization: Bearer <TOKEN>
```

**Query Parameters**:
- `author`: Filter by author username (optional)

---

### 12. Search Horoscopes
```http
GET /news/admin/horoscope/search?query=शुभ&page=1&limit=10
Authorization: Bearer <TOKEN>
```
**Description**: Search by title, predictions, or closing message

---

### 13. Get Horoscopes by Date Range
```http
GET /news/admin/horoscope/date-range?start_date=2025-12-01&end_date=2025-12-31&published=true
Authorization: Bearer <TOKEN>
```

**Query Parameters**:
- `start_date`: Start date (required)
- `end_date`: End date (required)
- `published`: Filter by status (optional)

---

### 14. Bulk Delete Horoscopes (Admin Only)
```http
POST /news/admin/horoscope/bulk-delete
Authorization: Bearer <TOKEN>
Content-Type: application/json
```

**Request Body**:
```json
["horoscope_id_1", "horoscope_id_2", "horoscope_id_3"]
```

**Requires**: `admin` role

---

## 📊 Statistics & Analytics

### 1. Get Admin Statistics
```http
GET /news/admin/horoscope/stats
Authorization: Bearer <TOKEN>
```

**Response**:
```json
{
  "total_horoscopes": 100,
  "published_horoscopes": 85,
  "draft_horoscopes": 15,
  "total_views": 5000,
  "total_likes": 1200,
  "most_viewed": {...},
  "most_liked": {...}
}
```

---

### 2. Get Author Statistics
```http
GET /news/author/horoscope/stats
Authorization: Bearer <TOKEN>
```

**Response**:
```json
{
  "author": "username",
  "total_horoscopes": 50,
  "published_horoscopes": 45,
  "draft_horoscopes": 5,
  "total_views": 2500,
  "total_likes": 600
}
```

---

## 🎨 UI Implementation Guide

### Frontend Structure

#### 1. Public Pages
```
/rashifal                    → Today's horoscope
/rashifal/{date}             → Specific date
/rashifal/{zodiac}           → Specific zodiac
/rashifal/archive            → Archive with date picker
```

#### 2. Admin Panel
```
/admin/rashifal              → Dashboard with stats
/admin/rashifal/create       → Create new horoscope
/admin/rashifal/edit/{id}    → Edit horoscope
/admin/rashifal/drafts       → Draft list
/admin/rashifal/published    → Published list
```

#### 3. Author Panel
```
/author/rashifal             → Author's horoscopes
/author/rashifal/create      → Create new
/author/rashifal/stats       → Author stats
```

---

### Display Format (Public)

```
राशि फल✡️🙏🏻

🐏 मेष राशि >> चू, चे, चो, ला, ली, लू, ले, लो, अ
[Prediction text here...]

🐂 वृष राशि >> ई, उ, ए, ओ, वा, वी, वू, वे, वो
[Prediction text here...]

[Continue for all 12 signs...]

☘️आपका दिन मंगलमय हो।☘️

🕉️ कुण्डली विचार, भविष्य की जानकारी, प्रश्न कुण्डली विचार हेतु सम्पर्क कर सकते हैं
```

---

### Admin Form Fields

1. **Title** (text input)
2. **Date** (date picker) - Required, unique
3. **Published** (toggle switch)
4. **Zodiac Predictions** (12 expandable sections):
   - Sign (auto-filled)
   - Emoji (auto-filled)
   - Hindi Name (auto-filled)
   - Syllables (auto-filled)
   - Prediction (textarea, Hindi input)
5. **Closing Message** (text input)
6. **Contact Info** (textarea, optional)

---

### Sample React Component

```jsx
// Create Horoscope Form
const CreateHoroscope = () => {
  const zodiacSigns = [
    { sign: 'mesh', emoji: '🐏', name: 'मेष राशि', syllables: 'चू, चे, चो, ला, ली, लू, ले, लो, अ' },
    { sign: 'vrishabh', emoji: '🐂', name: 'वृष राशि', syllables: 'ई, उ, ए, ओ, वा, वी, वू, वे, वो' },
    // ... all 12 signs
  ];

  const [formData, setFormData] = useState({
    title: 'राशि फल✡️🙏🏻',
    date: new Date().toISOString().split('T')[0],
    zodiac_predictions: zodiacSigns.map(z => ({...z, prediction: ''})),
    closing_message: '☘️आपका दिन मंगलमय हो।☘️',
    contact_info: '',
    published: false
  });

  // Handle form submission...
};
```

---

### Sample Vue Component

```vue
<template>
  <div class="horoscope-form">
    <h2>राशि फल बनाएं</h2>
    
    <input v-model="formData.title" />
    <input type="date" v-model="formData.date" />
    
    <div v-for="(pred, index) in formData.zodiac_predictions" :key="pred.sign">
      <h3>{{ pred.emoji }} {{ pred.hindi_name }}</h3>
      <p class="syllables">{{ pred.syllables }}</p>
      <textarea 
        v-model="pred.prediction" 
        rows="6"
        placeholder="आज का भविष्यफल लिखें..."
      ></textarea>
    </div>
    
    <textarea v-model="formData.closing_message"></textarea>
    <button @click="submitHoroscope">सबमिट करें</button>
  </div>
</template>
```

---

## 🔧 Helper Script

Use the provided script to create daily horoscopes:

```bash
python3 create_horoscope.py 2025-12-16 admin
```

**Script**: [create_horoscope.py](create_horoscope.py)

---

## 📝 Notes

1. **Date Uniqueness**: Only one horoscope per date allowed
2. **All 12 Signs Required**: Must provide predictions for all zodiac signs
3. **IP-Based Tracking**: Views and likes deduplicated by IP
4. **Author Restrictions**: Authors can only manage their own horoscopes
5. **Admin Override**: Admins can manage all horoscopes
6. **Draft Mode**: Save horoscopes without publishing for review

---

## 🐛 Error Responses

```json
// 404 - Not Found
{
  "detail": "आज के लिए राशिफल उपलब्ध नहीं है"
}

// 400 - Validation Error
{
  "detail": "सभी 12 राशियों के भविष्यफल जरूरी हैं"
}

// 403 - Forbidden
{
  "detail": "Admin or Author access required"
}
```

---

## 🚀 Production URLs

- **API Base**: `https://api.projectdevops.in/news`
- **Frontend**: `https://gtnews18.in/rashifal`
- **Swagger Docs**: `https://api.projectdevops.in/docs`

---

**Happy Coding! 🔮✨**
