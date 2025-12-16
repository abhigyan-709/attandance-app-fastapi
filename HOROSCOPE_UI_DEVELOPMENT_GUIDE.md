# 🎨 Horoscope UI Development Guide
## Admin & Author Panel Implementation

Complete frontend development guide for the Daily Horoscope (राशि फल) management system.

---

## 📋 Table of Contents
- [Overview](#overview)
- [User Roles & Permissions](#user-roles--permissions)
- [Page Structure](#page-structure)
- [Admin Panel Features](#admin-panel-features)
- [Author Panel Features](#author-panel-features)
- [Component Library](#component-library)
- [API Integration](#api-integration)
- [Sample Implementations](#sample-implementations)
- [Styling Guidelines](#styling-guidelines)

---

## 🌟 Overview

### Technology Stack
- **Frontend Framework**: React/Vue/Next.js (your choice)
- **UI Library**: Material-UI, Ant Design, or Chakra UI
- **State Management**: Redux/Zustand/Pinia
- **API Client**: Axios/Fetch
- **Rich Text Editor**: Quill/TinyMCE/Draft.js (for Hindi input)
- **Date Picker**: react-datepicker/vue-datepicker
- **Authentication**: JWT Token stored in localStorage/cookies

---

## 👥 User Roles & Permissions

### Admin
✅ Can create/edit/delete ANY horoscope  
✅ Can publish/unpublish ANY horoscope  
✅ Can view ALL horoscopes  
✅ Can bulk delete horoscopes  
✅ Can view complete statistics  
✅ Can search/filter all horoscopes  

### Author
✅ Can create new horoscopes  
✅ Can edit OWN horoscopes  
✅ Can delete OWN horoscopes  
✅ Can publish/unpublish OWN horoscopes  
✅ Can view OWN horoscopes  
❌ Cannot bulk delete  
✅ Can view OWN statistics  

---

## 📱 Page Structure

### Admin Routes
```
/admin/horoscope                    → Dashboard (stats + quick actions)
/admin/horoscope/all                → All horoscopes list
/admin/horoscope/published          → Published horoscopes
/admin/horoscope/drafts             → Draft horoscopes
/admin/horoscope/create             → Create new horoscope
/admin/horoscope/edit/:id           → Edit existing horoscope
/admin/horoscope/search             → Search interface
/admin/horoscope/stats              → Detailed statistics
```

### Author Routes
```
/author/horoscope                   → Dashboard (my horoscopes + stats)
/author/horoscope/create            → Create new horoscope
/author/horoscope/edit/:id          → Edit my horoscope
/author/horoscope/drafts            → My drafts
/author/horoscope/published         → My published horoscopes
/author/horoscope/stats             → My statistics
```

---

## 🔐 Admin Panel Features

### 1. Dashboard Page (`/admin/horoscope`)

**Layout:**
```
┌─────────────────────────────────────────────────┐
│  राशि फल प्रबंधन (Horoscope Management)        │
├─────────────────────────────────────────────────┤
│  📊 Statistics Cards                             │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐        │
│  │  Total   │ │Published │ │  Drafts  │        │
│  │   100    │ │    85    │ │    15    │        │
│  └──────────┘ └──────────┘ └──────────┘        │
│                                                  │
│  ┌──────────┐ ┌──────────┐                     │
│  │  Views   │ │  Likes   │                     │
│  │  5,000   │ │  1,200   │                     │
│  └──────────┘ └──────────┘                     │
├─────────────────────────────────────────────────┤
│  🔥 Quick Actions                                │
│  [+ नया राशि फल] [📋 सभी देखें] [🔍 खोजें]    │
├─────────────────────────────────────────────────┤
│  📅 Recent Horoscopes (Last 5)                  │
│  ┌───────────────────────────────────────────┐ │
│  │ Date       │ Status    │ Views │ Actions  │ │
│  │ 2025-12-16 │ Published │ 250   │ [E][D]  │ │
│  │ 2025-12-15 │ Published │ 300   │ [E][D]  │ │
│  └───────────────────────────────────────────┘ │
└─────────────────────────────────────────────────┘
```

**API Calls:**
```javascript
GET /news/admin/horoscope/stats
GET /news/admin/horoscopes?page=1&limit=5
```

---

### 2. All Horoscopes List (`/admin/horoscope/all`)

**Features:**
- Pagination
- Filter by: Published/Draft, Author, Date Range
- Search by title/content
- Bulk selection for delete
- Quick actions: Edit, Delete, Publish/Unpublish

**Layout:**
```
┌─────────────────────────────────────────────────────────┐
│  सभी राशि फल (All Horoscopes)                           │
├─────────────────────────────────────────────────────────┤
│  Filters:                                                │
│  [Status ▼] [Author ▼] [Date Range] [Search...]        │
│  [+ नया जोड़ें]              [🗑️ Selected Delete]      │
├─────────────────────────────────────────────────────────┤
│  ☐ Date       │ Author  │ Status    │ Views │ Actions  │
│  ☐ 2025-12-16 │ admin   │ Published │ 250   │ [E][P][D]│
│  ☐ 2025-12-15 │ author1 │ Draft     │ 0     │ [E][P][D]│
│  ☐ 2025-12-14 │ admin   │ Published │ 300   │ [E][U][D]│
├─────────────────────────────────────────────────────────┤
│  « Previous  [1] [2] [3] [4] [5]  Next »               │
└─────────────────────────────────────────────────────────┘
```

**API Calls:**
```javascript
GET /news/admin/horoscopes?page=1&limit=10&published=true
GET /news/admin/horoscope/search?query=शुभ&page=1
GET /news/admin/horoscope/date-range?start_date=2025-12-01&end_date=2025-12-31
POST /news/admin/horoscope/bulk-delete (body: ["id1", "id2"])
```

---

### 3. Create/Edit Form (`/admin/horoscope/create` or `/edit/:id`)

**Form Structure:**

```
┌───────────────────────────────────────────────────┐
│  नया राशि फल बनाएं (Create New Horoscope)        │
├───────────────────────────────────────────────────┤
│                                                    │
│  शीर्षक (Title):                                  │
│  [राशि फल✡️🙏🏻                               ]    │
│                                                    │
│  तारीख (Date): *Required                          │
│  [📅 2025-12-16]                                  │
│                                                    │
│  ─────────────────────────────────────────────    │
│                                                    │
│  🐏 मेष राशि >> चू, चे, चो, ला, ली, लू, ले, लो, अ│
│  ┌─────────────────────────────────────────────┐ │
│  │ आज अपने काम के लिए दूसरों पर दबाव न डालें... │ │
│  │                                               │ │
│  │ (Hindi text editor - 5-6 lines)              │ │
│  │                                               │ │
│  └─────────────────────────────────────────────┘ │
│  [Expand/Collapse]                                │
│                                                    │
│  🐂 वृष राशि >> ई, उ, ए, ओ, वा, वी, वू, वे, वो   │
│  ┌─────────────────────────────────────────────┐ │
│  │ (Text editor for Vrishabh)                   │ │
│  └─────────────────────────────────────────────┘ │
│  [Expand/Collapse]                                │
│                                                    │
│  ... (All 12 zodiac signs)                        │
│                                                    │
│  ─────────────────────────────────────────────    │
│                                                    │
│  समापन संदेश (Closing Message):                  │
│  [☘️आपका दिन मंगलमय हो।☘️                    ]    │
│                                                    │
│  संपर्क जानकारी (Contact Info):                  │
│  ┌─────────────────────────────────────────────┐ │
│  │ 🕉️ कुण्डली विचार, भविष्य की जानकारी...     │ │
│  └─────────────────────────────────────────────┘ │
│                                                    │
│  [✓ Publish Immediately]                          │
│                                                    │
│  [💾 Save Draft]  [🚀 Publish]  [❌ Cancel]       │
└───────────────────────────────────────────────────┘
```

**Validation Rules:**
- ✅ Date is required and must be unique
- ✅ All 12 zodiac predictions must be filled
- ✅ Each prediction should be 3-10 lines
- ✅ Title defaults to "राशि फल✡️🙏🏻"
- ✅ Closing message defaults to "☘️आपका दिन मंगलमय हो।☘️"

**API Calls:**
```javascript
// Create
POST /news/admin/horoscope
{
  "title": "राशि फल✡️🙏🏻",
  "date": "2025-12-16",
  "zodiac_predictions": [...],
  "closing_message": "☘️आपका दिन मंगलमय हो।☘️",
  "contact_info": "...",
  "published": false
}

// Update
PUT /news/admin/horoscope/{id}
{...updated fields...}

// Quick Publish
POST /news/admin/horoscope/{id}/publish
```

---

### 4. Statistics Page (`/admin/horoscope/stats`)

**Layout:**
```
┌─────────────────────────────────────────────────┐
│  📊 Horoscope Statistics                         │
├─────────────────────────────────────────────────┤
│  Overview                                        │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐        │
│  │  Total   │ │Published │ │  Drafts  │        │
│  │   100    │ │    85    │ │    15    │        │
│  └──────────┘ └──────────┘ └──────────┘        │
│                                                  │
│  Engagement                                      │
│  ┌──────────┐ ┌──────────┐                     │
│  │Total Views│Total Likes│                     │
│  │  5,000   │ │  1,200   │                     │
│  └──────────┘ └──────────┘                     │
│                                                  │
│  📈 Most Viewed Horoscope                       │
│  Date: 2025-12-15 | Views: 500 | Likes: 120    │
│                                                  │
│  💙 Most Liked Horoscope                        │
│  Date: 2025-12-14 | Views: 450 | Likes: 150    │
│                                                  │
│  📊 Views by Date (Chart)                       │
│  [Line/Bar Chart showing last 30 days]         │
│                                                  │
│  👥 Author Performance                          │
│  ┌────────────────────────────────────────────┐│
│  │ Author   │ Posts │ Views │ Avg Views/Post │││
│  │ admin    │  50   │ 3000  │ 60             │││
│  │ author1  │  30   │ 1500  │ 50             │││
│  └────────────────────────────────────────────┘│
└─────────────────────────────────────────────────┘
```

**API Call:**
```javascript
GET /news/admin/horoscope/stats
```

---

## ✍️ Author Panel Features

### 1. Author Dashboard (`/author/horoscope`)

**Layout:**
```
┌─────────────────────────────────────────────────┐
│  मेरे राशि फल (My Horoscopes)                   │
├─────────────────────────────────────────────────┤
│  📊 My Statistics                                │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐        │
│  │My Total  │ │Published │ │  Drafts  │        │
│  │    50    │ │    45    │ │    5     │        │
│  └──────────┘ └──────────┘ └──────────┘        │
│                                                  │
│  ┌──────────┐ ┌──────────┐                     │
│  │My Views  │ │ My Likes │                     │
│  │  2,500   │ │   600    │                     │
│  └──────────┘ └──────────┘                     │
├─────────────────────────────────────────────────┤
│  🔥 Quick Actions                                │
│  [+ नया राशि फल बनाएं] [📝 मेरे ड्राफ्ट]      │
├─────────────────────────────────────────────────┤
│  📅 My Recent Horoscopes (Last 10)              │
│  ┌───────────────────────────────────────────┐ │
│  │ Date       │ Status    │ Views │ Actions  │ │
│  │ 2025-12-16 │ Published │ 50    │ [E][U]  │ │
│  │ 2025-12-15 │ Draft     │ 0     │ [E][P]  │ │
│  └───────────────────────────────────────────┘ │
└─────────────────────────────────────────────────┘
```

**API Calls:**
```javascript
GET /news/author/horoscope/stats
GET /news/author/horoscopes?page=1&limit=10
```

---

### 2. Author Create/Edit Form

**Same as Admin form but:**
- ❌ No bulk delete option
- ❌ Cannot edit other authors' horoscopes
- ✅ Can only manage own horoscopes
- ✅ Same validation rules

**API Calls:**
```javascript
POST /news/admin/horoscope (same endpoint for authors)
PUT /news/admin/horoscope/{id} (only if author owns it)
```

---

## 🧩 Component Library

### 1. ZodiacSignCard Component

**Props:**
```typescript
interface ZodiacSignCardProps {
  sign: string;          // "mesh", "vrishabh", etc.
  emoji: string;         // "🐏", "🐂", etc.
  hindiName: string;     // "मेष राशि", "वृष राशि"
  syllables: string;     // "चू, चे, चो, ला, ली, लू, ले, लो, अ"
  prediction: string;
  onChange: (value: string) => void;
  isExpanded: boolean;
  onToggle: () => void;
}
```

**React Example:**
```jsx
const ZodiacSignCard = ({
  emoji,
  hindiName,
  syllables,
  prediction,
  onChange,
  isExpanded,
  onToggle
}) => {
  return (
    <div className="zodiac-card">
      <div className="zodiac-header" onClick={onToggle}>
        <h3>
          {emoji} {hindiName} <span className="syllables">&gt;&gt; {syllables}</span>
        </h3>
        <button>{isExpanded ? '▼' : '▶'}</button>
      </div>
      
      {isExpanded && (
        <div className="zodiac-body">
          <textarea
            value={prediction}
            onChange={(e) => onChange(e.target.value)}
            placeholder="आज का भविष्यफल लिखें..."
            rows={6}
            className="hindi-input"
            dir="ltr"
          />
          <div className="char-count">{prediction.length} characters</div>
        </div>
      )}
    </div>
  );
};
```

---

### 2. HoroscopeForm Component

**React Example:**
```jsx
import { useState } from 'react';
import DatePicker from 'react-datepicker';
import ZodiacSignCard from './ZodiacSignCard';

const ZODIAC_SIGNS = [
  { sign: 'mesh', emoji: '🐏', name: 'मेष राशि', syllables: 'चू, चे, चो, ला, ली, लू, ले, लो, अ' },
  { sign: 'vrishabh', emoji: '🐂', name: 'वृष राशि', syllables: 'ई, उ, ए, ओ, वा, वी, वू, वे, वो' },
  { sign: 'mithun', emoji: '👭', name: 'मिथुन राशि', syllables: 'का, की, कु, घ, ड, छ, के, को, हा' },
  { sign: 'kark', emoji: '🦀', name: 'कर्क राशि', syllables: 'ही, हू, हे, हो, डा, डी, डू, डे, डो' },
  { sign: 'simha', emoji: '🐅', name: 'सिंह राशि', syllables: 'मा, मी, मू, मे, मो, टा, टी, टू, टे' },
  { sign: 'kanya', emoji: '🙎‍♀️', name: 'कन्या राशि', syllables: 'टो, पा, पी, पू, ष, ण, ठ, पे, पो' },
  { sign: 'tula', emoji: '⚖️', name: 'तुला राशि', syllables: 'रा, री, रु, रे, रो, ता, ती, तू, ते' },
  { sign: 'vrishchik', emoji: '🦂', name: 'वृश्चिक राशि', syllables: 'तो, ना, नी, नू, ने, नो, या, यी, यू' },
  { sign: 'dhanu', emoji: '🏹', name: 'धनु राशि', syllables: 'ये, यो, भा, भी, भू, ध, फ, ढ, भे' },
  { sign: 'makar', emoji: '🐊', name: 'मकर राशि', syllables: 'भो, जा, जी, खी, खू, खे, खो, गा, गी' },
  { sign: 'kumbh', emoji: '⚱️', name: 'कुम्भ राशि', syllables: 'गू, गे, गो, सा, सी, सू, से, सो, दा' },
  { sign: 'meen', emoji: '🐟', name: 'मीन राशि', syllables: 'दी, दू, थ, झ, ञ, दे, दो, चा, ची' },
];

const HoroscopeForm = ({ initialData, onSubmit, isEdit = false }) => {
  const [formData, setFormData] = useState({
    title: initialData?.title || 'राशि फल✡️🙏🏻',
    date: initialData?.date || new Date(),
    zodiac_predictions: initialData?.zodiac_predictions || ZODIAC_SIGNS.map(z => ({
      sign: z.sign,
      emoji: z.emoji,
      hindi_name: z.name,
      syllables: z.syllables,
      prediction: ''
    })),
    closing_message: initialData?.closing_message || '☘️आपका दिन मंगलमय हो।☘️',
    contact_info: initialData?.contact_info || '',
    published: initialData?.published || false
  });

  const [expandedCards, setExpandedCards] = useState([0]); // First card expanded by default
  const [errors, setErrors] = useState({});

  const toggleCard = (index) => {
    setExpandedCards(prev => 
      prev.includes(index) 
        ? prev.filter(i => i !== index)
        : [...prev, index]
    );
  };

  const updatePrediction = (index, value) => {
    const newPredictions = [...formData.zodiac_predictions];
    newPredictions[index].prediction = value;
    setFormData({ ...formData, zodiac_predictions: newPredictions });
  };

  const validate = () => {
    const newErrors = {};
    
    if (!formData.date) {
      newErrors.date = 'तारीख जरूरी है';
    }
    
    const emptyPredictions = formData.zodiac_predictions.filter(p => !p.prediction.trim());
    if (emptyPredictions.length > 0) {
      newErrors.predictions = `${emptyPredictions.length} राशियों का भविष्यफल खाली है`;
    }
    
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (publish = false) => {
    if (!validate()) {
      alert('कृपया सभी जरूरी फील्ड भरें');
      return;
    }
    
    const data = {
      ...formData,
      published: publish,
      date: formData.date.toISOString().split('T')[0]
    };
    
    await onSubmit(data);
  };

  return (
    <div className="horoscope-form">
      <h2>{isEdit ? 'राशि फल संपादित करें' : 'नया राशि फल बनाएं'}</h2>
      
      {/* Title */}
      <div className="form-group">
        <label>शीर्षक (Title)</label>
        <input
          type="text"
          value={formData.title}
          onChange={(e) => setFormData({...formData, title: e.target.value})}
          className="form-control"
        />
      </div>
      
      {/* Date */}
      <div className="form-group">
        <label>तारीख (Date) *</label>
        <DatePicker
          selected={formData.date}
          onChange={(date) => setFormData({...formData, date})}
          dateFormat="yyyy-MM-dd"
          className="form-control"
        />
        {errors.date && <span className="error">{errors.date}</span>}
      </div>
      
      <hr />
      
      {/* Zodiac Predictions */}
      <div className="zodiac-predictions">
        <h3>राशि भविष्यफल (Zodiac Predictions)</h3>
        {errors.predictions && (
          <div className="alert alert-warning">{errors.predictions}</div>
        )}
        
        <div className="expand-collapse-all">
          <button onClick={() => setExpandedCards(ZODIAC_SIGNS.map((_, i) => i))}>
            सभी खोलें
          </button>
          <button onClick={() => setExpandedCards([])}>
            सभी बंद करें
          </button>
        </div>
        
        {formData.zodiac_predictions.map((pred, index) => (
          <ZodiacSignCard
            key={pred.sign}
            emoji={pred.emoji}
            hindiName={pred.hindi_name}
            syllables={pred.syllables}
            prediction={pred.prediction}
            onChange={(value) => updatePrediction(index, value)}
            isExpanded={expandedCards.includes(index)}
            onToggle={() => toggleCard(index)}
          />
        ))}
      </div>
      
      <hr />
      
      {/* Closing Message */}
      <div className="form-group">
        <label>समापन संदेश (Closing Message)</label>
        <input
          type="text"
          value={formData.closing_message}
          onChange={(e) => setFormData({...formData, closing_message: e.target.value})}
          className="form-control"
        />
      </div>
      
      {/* Contact Info */}
      <div className="form-group">
        <label>संपर्क जानकारी (Contact Info)</label>
        <textarea
          value={formData.contact_info}
          onChange={(e) => setFormData({...formData, contact_info: e.target.value})}
          rows={3}
          className="form-control"
        />
      </div>
      
      {/* Actions */}
      <div className="form-actions">
        <button 
          className="btn btn-secondary"
          onClick={() => handleSubmit(false)}
        >
          💾 ड्राफ्ट के रूप में सहेजें
        </button>
        
        <button 
          className="btn btn-primary"
          onClick={() => handleSubmit(true)}
        >
          🚀 प्रकाशित करें
        </button>
        
        <button 
          className="btn btn-outline"
          onClick={() => window.history.back()}
        >
          ❌ रद्द करें
        </button>
      </div>
    </div>
  );
};

export default HoroscopeForm;
```

---

### 3. HoroscopeTable Component

**React Example:**
```jsx
import { useState } from 'react';
import { format } from 'date-fns';

const HoroscopeTable = ({ 
  horoscopes, 
  onEdit, 
  onDelete, 
  onPublish, 
  onUnpublish,
  showBulkActions = false 
}) => {
  const [selectedIds, setSelectedIds] = useState([]);
  
  const toggleSelect = (id) => {
    setSelectedIds(prev => 
      prev.includes(id) 
        ? prev.filter(i => i !== id)
        : [...prev, id]
    );
  };
  
  const toggleSelectAll = () => {
    setSelectedIds(
      selectedIds.length === horoscopes.length 
        ? [] 
        : horoscopes.map(h => h._id)
    );
  };
  
  return (
    <div className="horoscope-table">
      {showBulkActions && selectedIds.length > 0 && (
        <div className="bulk-actions">
          <span>{selectedIds.length} selected</span>
          <button onClick={() => onDelete(selectedIds)}>
            🗑️ Delete Selected
          </button>
        </div>
      )}
      
      <table>
        <thead>
          <tr>
            {showBulkActions && (
              <th>
                <input 
                  type="checkbox" 
                  checked={selectedIds.length === horoscopes.length}
                  onChange={toggleSelectAll}
                />
              </th>
            )}
            <th>तारीख</th>
            <th>लेखक</th>
            <th>स्थिति</th>
            <th>व्यू</th>
            <th>लाइक</th>
            <th>क्रियाएं</th>
          </tr>
        </thead>
        <tbody>
          {horoscopes.map(horoscope => (
            <tr key={horoscope._id}>
              {showBulkActions && (
                <td>
                  <input 
                    type="checkbox"
                    checked={selectedIds.includes(horoscope._id)}
                    onChange={() => toggleSelect(horoscope._id)}
                  />
                </td>
              )}
              <td>{format(new Date(horoscope.date), 'dd MMM yyyy')}</td>
              <td>{horoscope.author_username}</td>
              <td>
                <span className={`badge ${horoscope.published ? 'success' : 'warning'}`}>
                  {horoscope.published ? 'प्रकाशित' : 'ड्राफ्ट'}
                </span>
              </td>
              <td>{horoscope.views}</td>
              <td>{horoscope.likes}</td>
              <td className="actions">
                <button 
                  onClick={() => onEdit(horoscope._id)}
                  title="संपादित करें"
                >
                  ✏️
                </button>
                
                {horoscope.published ? (
                  <button 
                    onClick={() => onUnpublish(horoscope._id)}
                    title="अप्रकाशित करें"
                  >
                    📥
                  </button>
                ) : (
                  <button 
                    onClick={() => onPublish(horoscope._id)}
                    title="प्रकाशित करें"
                  >
                    🚀
                  </button>
                )}
                
                <button 
                  onClick={() => onDelete([horoscope._id])}
                  title="हटाएं"
                  className="danger"
                >
                  🗑️
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

export default HoroscopeTable;
```

---

## 🔌 API Integration

### API Service Class

**JavaScript/TypeScript:**
```javascript
// services/horoscopeApi.js
import axios from 'axios';

const API_BASE = 'https://api.projectdevops.in/news';

class HoroscopeAPI {
  constructor() {
    this.client = axios.create({
      baseURL: API_BASE,
      headers: {
        'Content-Type': 'application/json'
      }
    });
    
    // Add auth token to all requests
    this.client.interceptors.request.use(config => {
      const token = localStorage.getItem('authToken');
      if (token) {
        config.headers.Authorization = `Bearer ${token}`;
      }
      return config;
    });
  }
  
  // Admin/Author endpoints
  async getAllHoroscopes(page = 1, limit = 10, filters = {}) {
    const params = { page, limit, ...filters };
    const { data } = await this.client.get('/admin/horoscopes', { params });
    return data;
  }
  
  async getHoroscopeById(id) {
    const { data } = await this.client.get(`/admin/horoscope/${id}`);
    return data;
  }
  
  async createHoroscope(horoscopeData) {
    const { data } = await this.client.post('/admin/horoscope', horoscopeData);
    return data;
  }
  
  async updateHoroscope(id, horoscopeData) {
    const { data } = await this.client.put(`/admin/horoscope/${id}`, horoscopeData);
    return data;
  }
  
  async deleteHoroscope(id) {
    const { data } = await this.client.delete(`/admin/horoscope/${id}`);
    return data;
  }
  
  async publishHoroscope(id) {
    const { data } = await this.client.post(`/admin/horoscope/${id}/publish`);
    return data;
  }
  
  async unpublishHoroscope(id) {
    const { data } = await this.client.post(`/admin/horoscope/${id}/unpublish`);
    return data;
  }
  
  async getStats() {
    const { data } = await this.client.get('/admin/horoscope/stats');
    return data;
  }
  
  async getAuthorStats() {
    const { data } = await this.client.get('/author/horoscope/stats');
    return data;
  }
  
  async searchHoroscopes(query, page = 1) {
    const { data } = await this.client.get('/admin/horoscope/search', {
      params: { query, page }
    });
    return data;
  }
  
  async bulkDelete(ids) {
    const { data } = await this.client.post('/admin/horoscope/bulk-delete', ids);
    return data;
  }
  
  // Public endpoints
  async getTodayHoroscope() {
    const { data } = await this.client.get('/horoscope/today');
    return data;
  }
}

export default new HoroscopeAPI();
```

---

## 🎨 Styling Guidelines

### CSS Variables (Hindi-friendly design)
```css
:root {
  /* Colors */
  --primary-color: #FF6B35;      /* Saffron accent */
  --secondary-color: #004E89;
  --success-color: #28a745;
  --warning-color: #ffc107;
  --danger-color: #dc3545;
  
  /* Hindi Font */
  --hindi-font: 'Noto Sans Devanagari', 'Mukta', sans-serif;
  --english-font: 'Inter', 'Roboto', sans-serif;
  
  /* Spacing */
  --card-padding: 1.5rem;
  --form-gap: 1rem;
}

/* Hindi Text Support */
.hindi-text, .hindi-input {
  font-family: var(--hindi-font);
  font-size: 1.1rem;
  line-height: 1.8;
  direction: ltr;
}

/* Zodiac Card Styling */
.zodiac-card {
  border: 1px solid #ddd;
  border-radius: 8px;
  margin-bottom: 1rem;
  overflow: hidden;
  transition: box-shadow 0.3s;
}

.zodiac-card:hover {
  box-shadow: 0 4px 12px rgba(0,0,0,0.1);
}

.zodiac-header {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  padding: 1rem;
  cursor: pointer;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.zodiac-header h3 {
  margin: 0;
  font-size: 1.2rem;
}

.zodiac-header .syllables {
  font-size: 0.9rem;
  opacity: 0.9;
  margin-left: 0.5rem;
}

.zodiac-body {
  padding: 1rem;
}

.zodiac-body textarea {
  width: 100%;
  font-family: var(--hindi-font);
  border: 1px solid #ddd;
  border-radius: 4px;
  padding: 0.75rem;
  resize: vertical;
}

/* Table Styling */
.horoscope-table table {
  width: 100%;
  border-collapse: collapse;
}

.horoscope-table th {
  background: #f8f9fa;
  padding: 0.75rem;
  text-align: left;
  font-weight: 600;
}

.horoscope-table td {
  padding: 0.75rem;
  border-bottom: 1px solid #dee2e6;
}

.horoscope-table .badge {
  padding: 0.25rem 0.75rem;
  border-radius: 12px;
  font-size: 0.85rem;
}

.horoscope-table .badge.success {
  background: #d4edda;
  color: #155724;
}

.horoscope-table .badge.warning {
  background: #fff3cd;
  color: #856404;
}

/* Buttons */
.btn {
  padding: 0.5rem 1.5rem;
  border-radius: 6px;
  border: none;
  cursor: pointer;
  font-weight: 500;
  transition: all 0.3s;
}

.btn-primary {
  background: var(--primary-color);
  color: white;
}

.btn-primary:hover {
  background: #e55a2b;
  transform: translateY(-2px);
  box-shadow: 0 4px 8px rgba(0,0,0,0.2);
}

.btn-secondary {
  background: var(--secondary-color);
  color: white;
}

.btn-danger {
  background: var(--danger-color);
  color: white;
}
```

---

## 📱 Responsive Design

### Mobile-First Breakpoints
```css
/* Mobile (default) */
.horoscope-table {
  overflow-x: auto;
}

/* Tablet (768px+) */
@media (min-width: 768px) {
  .stats-cards {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 1rem;
  }
}

/* Desktop (1024px+) */
@media (min-width: 1024px) {
  .stats-cards {
    grid-template-columns: repeat(4, 1fr);
  }
  
  .form-actions {
    display: flex;
    justify-content: flex-end;
    gap: 1rem;
  }
}
```

---

## 🚀 Deployment Checklist

### Before Deployment
- [ ] Test all CRUD operations
- [ ] Verify Hindi input/display works correctly
- [ ] Test date picker with different formats
- [ ] Verify role-based permissions (admin vs author)
- [ ] Test bulk delete (admin only)
- [ ] Test search functionality
- [ ] Verify statistics calculations
- [ ] Test on mobile devices
- [ ] Check API error handling
- [ ] Verify authentication flow

### Performance Optimization
- [ ] Lazy load zodiac cards (expand on demand)
- [ ] Implement pagination for large lists
- [ ] Cache statistics data
- [ ] Optimize Hindi font loading
- [ ] Add loading states for API calls

---

## 🐛 Common Issues & Solutions

### Issue 1: Hindi characters not displaying
**Solution**: Add Hindi font in `index.html`
```html
<link href="https://fonts.googleapis.com/css2?family=Noto+Sans+Devanagari:wght@400;500;600&display=swap" rel="stylesheet">
```

### Issue 2: Date format mismatch
**Solution**: Always convert to ISO format (YYYY-MM-DD)
```javascript
const formattedDate = new Date(date).toISOString().split('T')[0];
```

### Issue 3: Textarea not preserving line breaks
**Solution**: Use `white-space: pre-wrap` in CSS
```css
.prediction-display {
  white-space: pre-wrap;
}
```

---

## 📚 Additional Resources

- [Hindi Typography Guide](https://fonts.google.com/knowledge/glossary/devanagari)
- [FastAPI Authentication](https://fastapi.tiangolo.com/tutorial/security/)
- [React Date Picker](https://reactdatepicker.com/)
- [Axios HTTP Client](https://axios-http.com/)

---

**Ready to build! 🎨✨**

For API endpoints reference, see [HOROSCOPE_API_GUIDE.md](HOROSCOPE_API_GUIDE.md)
