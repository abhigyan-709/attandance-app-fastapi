# Religious Content Scheduling UI Implementation Guide - Next.js

## 🎯 **Project Overview**

This guide provides complete instructions for implementing a religious content scheduling UI system in Next.js that integrates with the existing FastAPI news backend. The implementation is **completely non-destructive** and enhances the existing news system without breaking any current functionality.

## 🔒 **Safety Guarantees**

### ✅ **What This UI Addition Will NOT Break:**
- ✅ Existing news CRUD operations
- ✅ Current news listing and filtering
- ✅ Existing user authentication
- ✅ Blog/news commenting system
- ✅ Search functionality
- ✅ SEO optimizations
- ✅ File upload systems
- ✅ Any current admin panels

### ✅ **How We Ensure Safety:**
- All new endpoints use `/religious-content/*` prefix (separate from `/news/*`)
- New database collections (won't modify existing news collection)
- Additive-only changes to existing models
- Separate UI components and routes
- Independent scheduling system

## 📚 **Backend API Endpoints Reference**

### **Base URL:** `http://localhost:8000`

### **Authentication Headers:**
```javascript
const headers = {
  'Authorization': `Bearer ${accessToken}`,
  'Content-Type': 'application/json'
};
```

### **1. Content Templates API**

#### Create Template
```javascript
// POST /religious-content/templates
const createTemplate = async (templateData) => {
  const response = await fetch('/api/religious-content/templates', {
    method: 'POST',
    headers,
    body: JSON.stringify({
      name: "Daily Rashifal Template",
      content_type: "rashifal", // rashifal|panchang|editorial|this_day_history|festival|mantra|aarti|vrat_kathas|spiritual_guru
      template_content: "आज {{date}} का राशिफल:\n🌟 {{rashi}}: {{prediction}}",
      default_variables: {
        date: "{{date}}",
        rashi: "मेष",
        prediction: "आज आपका दिन शुभ रहेगा"
      },
      is_active: true
    })
  });
  return response.json();
};
```

#### Get Templates
```javascript
// GET /religious-content/templates?content_type=rashifal&active_only=true
const getTemplates = async (contentType = null, activeOnly = true) => {
  const params = new URLSearchParams();
  if (contentType) params.append('content_type', contentType);
  if (activeOnly) params.append('active_only', 'true');
  
  const response = await fetch(`/api/religious-content/templates?${params}`, {
    headers
  });
  return response.json();
};
```

### **2. Content Scheduling API**

#### Schedule Single Content
```javascript
// POST /religious-content/schedule
const scheduleContent = async (contentData) => {
  const response = await fetch('/api/religious-content/schedule', {
    method: 'POST',
    headers,
    body: JSON.stringify({
      content_type: "rashifal",
      title: "आज का राशिफल - 5 अक्टूबर 2025",
      content: "<p>सभी 12 राशियों का विस्तृत राशिफल...</p>",
      schedule_date: "2025-10-06T06:00:00Z",
      tags: ["rashifal", "daily", "astrology"],
      auto_publish: true,
      is_recurring: false,
      rashifal_data: [
        {
          rashi: "mesh", // mesh|vrishabh|mithun|kark|singh|kanya|tula|vrishchik|dhanu|makar|kumbh|meen
          prediction: "आज आपका दिन बेहतरीन रहेगा",
          lucky_number: 7,
          lucky_color: "#FF6B6B",
          lucky_time: "10:00-12:00",
          advice: "नए काम की शुरुआत करें",
          rating: 4 // 1-5 stars
        }
        // ... up to 12 zodiac signs
      ]
    })
  });
  return response.json();
};
```

#### Get Scheduled Content
```javascript
// GET /religious-content/scheduled
const getScheduledContent = async (filters = {}) => {
  const params = new URLSearchParams();
  if (filters.content_type) params.append('content_type', filters.content_type);
  if (filters.status) params.append('status', filters.status);
  if (filters.start_date) params.append('start_date', filters.start_date);
  if (filters.end_date) params.append('end_date', filters.end_date);
  params.append('page', filters.page || 1);
  params.append('limit', filters.limit || 20);
  
  const response = await fetch(`/api/religious-content/scheduled?${params}`, {
    headers
  });
  return response.json();
};
```

#### Bulk Schedule
```javascript
// POST /religious-content/bulk-schedule
const bulkSchedule = async (bulkData) => {
  const response = await fetch('/api/religious-content/bulk-schedule', {
    method: 'POST',
    headers,
    body: JSON.stringify({
      content_type: "rashifal",
      start_date: "2025-10-06",
      end_date: "2025-10-12",
      schedule_time: "06:00",
      template_id: "template_id_here",
      tags: ["rashifal", "weekly"]
    })
  });
  return response.json();
};
```

#### Publish Content Manually
```javascript
// POST /religious-content/publish/{content_id}
const publishContent = async (contentId) => {
  const response = await fetch(`/api/religious-content/publish/${contentId}`, {
    method: 'POST',
    headers
  });
  return response.json();
};
```

### **3. Hindu Calendar API**

#### Get Festivals
```javascript
// GET /religious-content/calendar/festivals
const getFestivals = async (month = null, year = null) => {
  const params = new URLSearchParams();
  if (month) params.append('month', month);
  if (year) params.append('year', year);
  
  const response = await fetch(`/api/religious-content/calendar/festivals?${params}`, {
    headers
  });
  return response.json();
};
```

#### Get Daily Panchang
```javascript
// GET /religious-content/calendar/panchang
const getPanchang = async (date = null) => {
  const params = new URLSearchParams();
  if (date) params.append('date_requested', date);
  
  const response = await fetch(`/api/religious-content/calendar/panchang?${params}`, {
    headers
  });
  return response.json();
};
```

#### Get Auspicious Dates
```javascript
// GET /religious-content/calendar/auspicious-dates
const getAuspiciousDates = async (startDate = null, daysAhead = 30) => {
  const params = new URLSearchParams();
  if (startDate) params.append('start_date', startDate);
  params.append('days_ahead', daysAhead);
  
  const response = await fetch(`/api/religious-content/calendar/auspicious-dates?${params}`, {
    headers
  });
  return response.json();
};
```

### **4. Admin Dashboard API**

#### Get Dashboard Stats
```javascript
// GET /religious-content/dashboard
const getDashboardStats = async () => {
  const response = await fetch('/api/religious-content/dashboard', {
    headers
  });
  return response.json();
};
```

#### Get Admin Overview
```javascript
// GET /admin/religious-content/overview
const getAdminOverview = async () => {
  const response = await fetch('/api/admin/religious-content/overview', {
    headers
  });
  return response.json();
};
```

#### Bulk Actions
```javascript
// POST /admin/religious-content/bulk-actions
const bulkActions = async (action, contentIds, newScheduleDate = null) => {
  const response = await fetch('/api/admin/religious-content/bulk-actions', {
    method: 'POST',
    headers,
    body: JSON.stringify({
      action, // "publish" | "delete" | "reschedule"
      content_ids: contentIds,
      new_schedule_date: newScheduleDate
    })
  });
  return response.json();
};
```

### **5. Quick Actions API**

#### Quick Schedule
```javascript
// POST /religious-content/quick-schedule
const quickSchedule = async (contentType, daysAhead = 7, timeSlot = "06:00") => {
  const response = await fetch('/api/religious-content/quick-schedule', {
    method: 'POST',
    headers,
    body: JSON.stringify({
      content_type: contentType,
      days_ahead: daysAhead,
      time_slot: timeSlot
    })
  });
  return response.json();
};
```

## 🎨 **Zodiac Signs Configuration**

### **Zodiac Data with SVG Support**
```javascript
// constants/zodiacSigns.js
export const ZODIAC_SIGNS = [
  {
    rashi: "mesh",
    english: "Aries",
    hindi: "मेष",
    symbol: "♈",
    color: "#FF6B6B",
    gradient: "linear-gradient(135deg, #FF6B6B, #FF8787)",
    svg_path: "/icons/zodiac/aries.svg",
    element: "Fire",
    ruling_planet: "Mars",
    description: "साहसी और नेतृत्व करने वाले"
  },
  {
    rashi: "vrishabh",
    english: "Taurus", 
    hindi: "वृषभ",
    symbol: "♉",
    color: "#4ECDC4",
    gradient: "linear-gradient(135deg, #4ECDC4, #6BCFCF)",
    svg_path: "/icons/zodiac/taurus.svg",
    element: "Earth",
    ruling_planet: "Venus",
    description: "धैर्यवान और विश्वसनीय"
  },
  {
    rashi: "mithun",
    english: "Gemini",
    hindi: "मिथुन",
    symbol: "♊",
    color: "#45B7D1",
    gradient: "linear-gradient(135deg, #45B7D1, #5BC0DE)",
    svg_path: "/icons/zodiac/gemini.svg",
    element: "Air",
    ruling_planet: "Mercury",
    description: "बुद्धिमान और संवादप्रिय"
  },
  {
    rashi: "kark",
    english: "Cancer",
    hindi: "कर्क",
    symbol: "♋",
    color: "#96CEB4",
    gradient: "linear-gradient(135deg, #96CEB4, #A8D5BA)",
    svg_path: "/icons/zodiac/cancer.svg",
    element: "Water",
    ruling_planet: "Moon",
    description: "भावनात्मक और देखभाल करने वाले"
  },
  {
    rashi: "singh",
    english: "Leo",
    hindi: "सिंह",
    symbol: "♌",
    color: "#FECA57",
    gradient: "linear-gradient(135deg, #FECA57, #FFD32A)",
    svg_path: "/icons/zodiac/leo.svg",
    element: "Fire",
    ruling_planet: "Sun",
    description: "गर्वीले और आकर्षक"
  },
  {
    rashi: "kanya",
    english: "Virgo",
    hindi: "कन्या",
    symbol: "♍",
    color: "#6C5CE7",
    gradient: "linear-gradient(135deg, #6C5CE7, #8269E8)",
    svg_path: "/icons/zodiac/virgo.svg",
    element: "Earth",
    ruling_planet: "Mercury",
    description: "व्यवस्थित और विश्लेषणात्मक"
  },
  {
    rashi: "tula",
    english: "Libra",
    hindi: "तुला",
    symbol: "♎",
    color: "#FD79A8",
    gradient: "linear-gradient(135deg, #FD79A8, #FF8BB5)",
    svg_path: "/icons/zodiac/libra.svg",
    element: "Air",
    ruling_planet: "Venus",
    description: "संतुलित और न्यायप्रिय"
  },
  {
    rashi: "vrishchik",
    english: "Scorpio",
    hindi: "वृश्चिक",
    symbol: "♏",
    color: "#E17055",
    gradient: "linear-gradient(135deg, #E17055, #E67E50)",
    svg_path: "/icons/zodiac/scorpio.svg",
    element: "Water",
    ruling_planet: "Mars",
    description: "रहस्यमय और भावुक"
  },
  {
    rashi: "dhanu",
    english: "Sagittarius",
    hindi: "धनु",
    symbol: "♐",
    color: "#00B894",
    gradient: "linear-gradient(135deg, #00B894, #00CCA3)",
    svg_path: "/icons/zodiac/sagittarius.svg",
    element: "Fire",
    ruling_planet: "Jupiter",
    description: "साहसिक और दार्शनिक"
  },
  {
    rashi: "makar",
    english: "Capricorn",
    hindi: "मकर",
    symbol: "♑",
    color: "#2D3436",
    gradient: "linear-gradient(135deg, #2D3436, #5A6268)",
    svg_path: "/icons/zodiac/capricorn.svg",
    element: "Earth",
    ruling_planet: "Saturn",
    description: "महत्वाकांक्षी और अनुशासित"
  },
  {
    rashi: "kumbh",
    english: "Aquarius",
    hindi: "कुम्भ",
    symbol: "♒",
    color: "#0984E3",
    gradient: "linear-gradient(135deg, #0984E3, #2196F3)",
    svg_path: "/icons/zodiac/aquarius.svg",
    element: "Air",
    ruling_planet: "Uranus",
    description: "नवाचार और स्वतंत्रता प्रिय"
  },
  {
    rashi: "meen",
    english: "Pisces",
    hindi: "मीन",
    symbol: "♓",
    color: "#A29BFE",
    gradient: "linear-gradient(135deg, #A29BFE, #B19CD9)",
    svg_path: "/icons/zodiac/pisces.svg",
    element: "Water",
    ruling_planet: "Neptune",
    description: "कलात्मक और सहानुभूतिशील"
  }
];

export const getZodiacByRashi = (rashi) => {
  return ZODIAC_SIGNS.find(sign => sign.rashi === rashi);
};

export const getZodiacColors = () => {
  return ZODIAC_SIGNS.reduce((acc, sign) => {
    acc[sign.rashi] = sign.color;
    return acc;
  }, {});
};
```

### **Content Types Configuration**
```javascript
// constants/contentTypes.js
export const RELIGIOUS_CONTENT_TYPES = [
  {
    value: "rashifal",
    label: "राशिफल",
    english: "Horoscope",
    icon: "🌟",
    color: "#FF6B6B",
    description: "दैनिक और साप्ताहिक राशिफल"
  },
  {
    value: "panchang",
    label: "पंचांग",
    english: "Panchang",
    icon: "📅",
    color: "#4ECDC4",
    description: "तिथि, नक्षत्र, योग, करण"
  },
  {
    value: "this_day_history",
    label: "आज का इतिहास",
    english: "This Day in History",
    icon: "📜",
    color: "#45B7D1",
    description: "ऐतिहासिक घटनाएं और महत्वपूर्ण दिन"
  },
  {
    value: "editorial",
    label: "संपादकीय",
    english: "Editorial",
    icon: "✍️",
    color: "#96CEB4",
    description: "धार्मिक विचार और मार्गदर्शन"
  },
  {
    value: "festival",
    label: "त्योहार",
    english: "Festival",
    icon: "🎉",
    color: "#FECA57",
    description: "त्योहारों की जानकारी और महत्व"
  },
  {
    value: "mantra",
    label: "मंत्र",
    english: "Mantra",
    icon: "🕉️",
    color: "#6C5CE7",
    description: "दैनिक मंत्र और स्तोत्र"
  },
  {
    value: "aarti",
    label: "आरती",
    english: "Aarti",
    icon: "🪔",
    color: "#FD79A8",
    description: "भजन, आरती और प्रार्थनाएं"
  },
  {
    value: "vrat_kathas",
    label: "व्रत कथाएं",
    english: "Vrat Kathas",
    icon: "📖",
    color: "#E17055",
    description: "व्रत की कथाएं और विधि"
  },
  {
    value: "spiritual_guru",
    label: "आध्यात्मिक गुरु",
    english: "Spiritual Guru",
    icon: "🧘",
    color: "#00B894",
    description: "गुरुओं के उपदेश और शिक्षाएं"
  }
];
```

## 🏗️ **Next.js Project Structure**

```
pages/
├── admin/
│   ├── religious-content/
│   │   ├── index.js              // Dashboard
│   │   ├── schedule.js           // Scheduling Interface
│   │   ├── templates.js          // Template Management
│   │   ├── calendar.js           // Hindu Calendar
│   │   └── analytics.js          // Performance Analytics
│   └── index.js                  // Main Admin Dashboard
├── api/
│   └── religious-content/        // API proxy to FastAPI
│       ├── templates.js
│       ├── schedule.js
│       ├── calendar/
│       │   ├── festivals.js
│       │   ├── panchang.js
│       │   └── auspicious-dates.js
│       └── dashboard.js
└── religious-content/            // Public pages (if needed)
    ├── rashifal.js
    └── panchang.js

components/
├── religious/
│   ├── SchedulingForm.js         // Main scheduling form
│   ├── RashifalEditor.js         // Zodiac-specific editor
│   ├── BulkScheduler.js          // Bulk scheduling component
│   ├── TemplateEditor.js         // Template creation/editing
│   ├── FestivalCalendar.js       // Hindu calendar component
│   ├── PanchangWidget.js         // Daily panchang display
│   ├── ZodiacCard.js            // Zodiac sign card with SVG
│   ├── ContentTypeSelector.js    // Content type picker
│   └── ScheduledContentTable.js  // Scheduled content listing
├── ui/
│   ├── DateTimePicker.js         // Custom date/time picker
│   ├── ColorPicker.js            // Color selection for zodiac
│   └── RichTextEditor.js         // Content editor
└── charts/
    ├── DashboardCharts.js        // Analytics charts
    └── PerformanceMetrics.js     // Performance visualization

hooks/
├── useReligiousContent.js        // Religious content operations
├── useHinduCalendar.js          // Calendar operations
├── useTemplates.js              // Template operations
└── useScheduling.js             // Scheduling operations

utils/
├── api/
│   ├── religiousContent.js       // API client for religious content
│   └── hinduCalendar.js         // Calendar API client
├── helpers/
│   ├── dateUtils.js             // Date/time utilities
│   ├── zodiacUtils.js           // Zodiac-related utilities
│   └── templateUtils.js         // Template processing
└── constants/
    ├── zodiacSigns.js           // Zodiac configuration
    └── contentTypes.js          // Content type definitions

styles/
├── religious-content.css        // Religious content specific styles
└── zodiac-themes.css           // Zodiac color themes
```

## 🚀 **Implementation Steps**

### **Step 1: Setup API Proxy (No Backend Changes)**

Create API proxy in Next.js to avoid CORS issues:

```javascript
// pages/api/religious-content/[...slug].js
export default async function handler(req, res) {
  const { slug } = req.query;
  const path = Array.isArray(slug) ? slug.join('/') : slug;
  
  const backendUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
  const url = `${backendUrl}/religious-content/${path}`;
  
  const response = await fetch(url, {
    method: req.method,
    headers: {
      'Content-Type': 'application/json',
      'Authorization': req.headers.authorization || '',
    },
    body: req.method !== 'GET' ? JSON.stringify(req.body) : undefined,
  });
  
  const data = await response.json();
  res.status(response.status).json(data);
}
```

### **Step 2: Create Main Scheduling Component**

```javascript
// components/religious/SchedulingForm.js
import { useState, useEffect } from 'react';
import { ZODIAC_SIGNS } from '../../utils/constants/zodiacSigns';
import { RELIGIOUS_CONTENT_TYPES } from '../../utils/constants/contentTypes';

const SchedulingForm = () => {
  const [formData, setFormData] = useState({
    content_type: 'rashifal',
    title: '',
    content: '',
    schedule_date: '',
    auto_publish: true,
    is_recurring: false,
    tags: [],
    rashifal_data: []
  });

  const [selectedZodiac, setSelectedZodiac] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    try {
      const response = await fetch('/api/religious-content/schedule', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        },
        body: JSON.stringify(formData)
      });
      
      if (response.ok) {
        alert('Content scheduled successfully!');
        // Reset form or redirect
      }
    } catch (error) {
      console.error('Error scheduling content:', error);
    }
  };

  return (
    <div className="max-w-4xl mx-auto p-6 bg-white rounded-lg shadow-lg">
      <h2 className="text-2xl font-bold mb-6 text-gray-800">धार्मिक सामग्री शेड्यूल करें</h2>
      
      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Content Type Selector */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            सामग्री का प्रकार
          </label>
          <div className="grid grid-cols-3 gap-4">
            {RELIGIOUS_CONTENT_TYPES.map(type => (
              <div
                key={type.value}
                className={`p-4 border-2 rounded-lg cursor-pointer transition-colors ${
                  formData.content_type === type.value
                    ? 'border-blue-500 bg-blue-50'
                    : 'border-gray-200 hover:border-gray-300'
                }`}
                onClick={() => setFormData({...formData, content_type: type.value})}
              >
                <div className="text-2xl mb-2">{type.icon}</div>
                <div className="font-medium">{type.label}</div>
                <div className="text-sm text-gray-500">{type.description}</div>
              </div>
            ))}
          </div>
        </div>

        {/* Title Input */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            शीर्षक
          </label>
          <input
            type="text"
            value={formData.title}
            onChange={(e) => setFormData({...formData, title: e.target.value})}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            placeholder="जैसे: आज का राशिफल - 5 अक्टूबर 2025"
          />
        </div>

        {/* Schedule Date/Time */}
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              तारीख
            </label>
            <input
              type="date"
              value={formData.schedule_date.split('T')[0]}
              onChange={(e) => setFormData({
                ...formData, 
                schedule_date: e.target.value + 'T06:00:00Z'
              })}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              समय
            </label>
            <input
              type="time"
              value={formData.schedule_date.split('T')[1]?.split(':').slice(0,2).join(':') || '06:00'}
              onChange={(e) => {
                const date = formData.schedule_date.split('T')[0] || new Date().toISOString().split('T')[0];
                setFormData({
                  ...formData, 
                  schedule_date: `${date}T${e.target.value}:00Z`
                });
              }}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
        </div>

        {/* Zodiac Signs Grid (for Rashifal) */}
        {formData.content_type === 'rashifal' && (
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-4">
              राशिफल जानकारी
            </label>
            <div className="grid grid-cols-4 gap-4">
              {ZODIAC_SIGNS.map(sign => (
                <div
                  key={sign.rashi}
                  className="p-4 border rounded-lg hover:shadow-md transition-shadow"
                  style={{ borderColor: sign.color }}
                >
                  <div className="flex items-center mb-2">
                    <img 
                      src={sign.svg_path} 
                      alt={sign.hindi}
                      className="w-8 h-8 mr-2"
                      style={{ filter: `drop-shadow(0 0 3px ${sign.color})` }}
                    />
                    <span className="font-medium" style={{ color: sign.color }}>
                      {sign.hindi}
                    </span>
                  </div>
                  <textarea
                    placeholder={`${sign.hindi} का राशिफल...`}
                    className="w-full h-20 text-sm p-2 border border-gray-200 rounded resize-none"
                    onChange={(e) => {
                      const newRashifalData = [...formData.rashifal_data];
                      const existingIndex = newRashifalData.findIndex(r => r.rashi === sign.rashi);
                      
                      if (existingIndex >= 0) {
                        newRashifalData[existingIndex].prediction = e.target.value;
                      } else {
                        newRashifalData.push({
                          rashi: sign.rashi,
                          prediction: e.target.value,
                          lucky_color: sign.color,
                          rating: 3
                        });
                      }
                      
                      setFormData({...formData, rashifal_data: newRashifalData});
                    }}
                  />
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Content Editor */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            मुख्य सामग्री
          </label>
          <textarea
            value={formData.content}
            onChange={(e) => setFormData({...formData, content: e.target.value})}
            rows={8}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            placeholder="यहाँ अपनी सामग्री लिखें..."
          />
        </div>

        {/* Options */}
        <div className="flex items-center space-x-6">
          <label className="flex items-center">
            <input
              type="checkbox"
              checked={formData.auto_publish}
              onChange={(e) => setFormData({...formData, auto_publish: e.target.checked})}
              className="mr-2"
            />
            स्वचालित प्रकाशन
          </label>
          
          <label className="flex items-center">
            <input
              type="checkbox"
              checked={formData.is_recurring}
              onChange={(e) => setFormData({...formData, is_recurring: e.target.checked})}
              className="mr-2"
            />
            दोहराना (दैनिक)
          </label>
        </div>

        {/* Submit Button */}
        <button
          type="submit"
          className="w-full bg-blue-600 text-white py-3 px-4 rounded-md hover:bg-blue-700 transition-colors font-medium"
        >
          सामग्री शेड्यूल करें
        </button>
      </form>
    </div>
  );
};

export default SchedulingForm;
```

### **Step 3: Create Dashboard Component**

```javascript
// components/religious/Dashboard.js
import { useState, useEffect } from 'react';
import { Bar, Pie, Line } from 'react-chartjs-2';

const ReligiousDashboard = () => {
  const [dashboardData, setDashboardData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchDashboardData();
  }, []);

  const fetchDashboardData = async () => {
    try {
      const response = await fetch('/api/religious-content/dashboard', {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        }
      });
      const data = await response.json();
      setDashboardData(data);
    } catch (error) {
      console.error('Error fetching dashboard data:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) return <div>Loading...</div>;

  return (
    <div className="p-6 space-y-6">
      <h1 className="text-3xl font-bold text-gray-800">धार्मिक सामग्री डैशबोर्ड</h1>
      
      {/* Stats Cards */}
      <div className="grid grid-cols-4 gap-6">
        <div className="bg-white p-6 rounded-lg shadow-lg">
          <div className="text-2xl font-bold text-blue-600">
            {dashboardData.total_scheduled}
          </div>
          <div className="text-gray-600">कुल शेड्यूल्ड</div>
        </div>
        
        <div className="bg-white p-6 rounded-lg shadow-lg">
          <div className="text-2xl font-bold text-green-600">
            {dashboardData.published_today}
          </div>
          <div className="text-gray-600">आज प्रकाशित</div>
        </div>
        
        <div className="bg-white p-6 rounded-lg shadow-lg">
          <div className="text-2xl font-bold text-orange-600">
            {dashboardData.pending_approval}
          </div>
          <div className="text-gray-600">अनुमोदन बाकी</div>
        </div>
        
        <div className="bg-white p-6 rounded-lg shadow-lg">
          <div className="text-2xl font-bold text-red-600">
            {dashboardData.failed_publications}
          </div>
          <div className="text-gray-600">विफल प्रकाशन</div>
        </div>
      </div>

      {/* Content Type Breakdown */}
      <div className="grid grid-cols-2 gap-6">
        <div className="bg-white p-6 rounded-lg shadow-lg">
          <h3 className="text-lg font-medium mb-4">सामग्री प्रकार विभाजन</h3>
          <Pie
            data={{
              labels: Object.keys(dashboardData.content_type_breakdown),
              datasets: [{
                data: Object.values(dashboardData.content_type_breakdown),
                backgroundColor: [
                  '#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4',
                  '#FECA57', '#6C5CE7', '#FD79A8', '#E17055'
                ]
              }]
            }}
          />
        </div>
        
        <div className="bg-white p-6 rounded-lg shadow-lg">
          <h3 className="text-lg font-medium mb-4">आगामी शेड्यूल</h3>
          <div className="space-y-2">
            {dashboardData.upcoming_schedules.slice(0, 5).map(schedule => (
              <div key={schedule._id} className="flex justify-between items-center p-2 border-b">
                <div>
                  <div className="font-medium">{schedule.title}</div>
                  <div className="text-sm text-gray-600">{schedule.content_type}</div>
                </div>
                <div className="text-sm text-gray-500">
                  {new Date(schedule.schedule_date).toLocaleDateString('hi-IN')}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};

export default ReligiousDashboard;
```

### **Step 4: Create Bulk Scheduler Component**

```javascript
// components/religious/BulkScheduler.js
import { useState } from 'react';
import { RELIGIOUS_CONTENT_TYPES } from '../../utils/constants/contentTypes';

const BulkScheduler = () => {
  const [bulkData, setBulkData] = useState({
    content_type: 'rashifal',
    start_date: '',
    end_date: '',
    schedule_time: '06:00',
    template_id: '',
    tags: []
  });

  const handleBulkSchedule = async (e) => {
    e.preventDefault();
    
    try {
      const response = await fetch('/api/religious-content/bulk-schedule', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        },
        body: JSON.stringify(bulkData)
      });
      
      if (response.ok) {
        const result = await response.json();
        alert(`Successfully scheduled ${result.scheduled_count} items`);
      }
    } catch (error) {
      console.error('Error in bulk scheduling:', error);
    }
  };

  return (
    <div className="max-w-2xl mx-auto p-6 bg-white rounded-lg shadow-lg">
      <h2 className="text-2xl font-bold mb-6 text-gray-800">बल्क शेड्यूलिंग</h2>
      
      <form onSubmit={handleBulkSchedule} className="space-y-6">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            सामग्री का प्रकार
          </label>
          <select
            value={bulkData.content_type}
            onChange={(e) => setBulkData({...bulkData, content_type: e.target.value})}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            {RELIGIOUS_CONTENT_TYPES.map(type => (
              <option key={type.value} value={type.value}>
                {type.icon} {type.label}
              </option>
            ))}
          </select>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              शुरुआती तारीख
            </label>
            <input
              type="date"
              value={bulkData.start_date}
              onChange={(e) => setBulkData({...bulkData, start_date: e.target.value})}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              अंतिम तारीख
            </label>
            <input
              type="date"
              value={bulkData.end_date}
              onChange={(e) => setBulkData({...bulkData, end_date: e.target.value})}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            प्रकाशन समय
          </label>
          <input
            type="time"
            value={bulkData.schedule_time}
            onChange={(e) => setBulkData({...bulkData, schedule_time: e.target.value})}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>

        <button
          type="submit"
          className="w-full bg-green-600 text-white py-3 px-4 rounded-md hover:bg-green-700 transition-colors font-medium"
        >
          बल्क शेड्यूल करें
        </button>
      </form>
    </div>
  );
};

export default BulkScheduler;
```

### **Step 5: Create Hindu Calendar Component**

```javascript
// components/religious/FestivalCalendar.js
import { useState, useEffect } from 'react';
import Calendar from 'react-calendar';

const FestivalCalendar = () => {
  const [festivals, setFestivals] = useState([]);
  const [selectedDate, setSelectedDate] = useState(new Date());
  const [panchang, setPanchang] = useState(null);

  useEffect(() => {
    fetchFestivals();
    fetchPanchang(selectedDate);
  }, [selectedDate]);

  const fetchFestivals = async () => {
    try {
      const month = selectedDate.getMonth() + 1;
      const year = selectedDate.getFullYear();
      
      const response = await fetch(`/api/religious-content/calendar/festivals?month=${month}&year=${year}`, {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        }
      });
      const data = await response.json();
      setFestivals(data.festivals || []);
    } catch (error) {
      console.error('Error fetching festivals:', error);
    }
  };

  const fetchPanchang = async (date) => {
    try {
      const dateStr = date.toISOString().split('T')[0];
      const response = await fetch(`/api/religious-content/calendar/panchang?date_requested=${dateStr}`, {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        }
      });
      const data = await response.json();
      setPanchang(data);
    } catch (error) {
      console.error('Error fetching panchang:', error);
    }
  };

  const tileContent = ({ date, view }) => {
    if (view === 'month') {
      const festival = festivals.find(f => 
        new Date(f.date).toDateString() === date.toDateString()
      );
      
      if (festival) {
        return (
          <div className="festival-marker">
            <div className={`w-2 h-2 rounded-full mx-auto ${
              festival.is_major ? 'bg-red-500' : 'bg-blue-500'
            }`}></div>
          </div>
        );
      }
    }
    return null;
  };

  return (
    <div className="max-w-6xl mx-auto p-6">
      <h2 className="text-2xl font-bold mb-6 text-gray-800">हिंदू कैलेंडर</h2>
      
      <div className="grid grid-cols-3 gap-6">
        {/* Calendar */}
        <div className="col-span-2 bg-white p-6 rounded-lg shadow-lg">
          <Calendar
            onChange={setSelectedDate}
            value={selectedDate}
            tileContent={tileContent}
            className="w-full"
          />
        </div>
        
        {/* Panchang Info */}
        <div className="bg-white p-6 rounded-lg shadow-lg">
          <h3 className="text-lg font-bold mb-4">आज का पंचांग</h3>
          {panchang && (
            <div className="space-y-2">
              <div><strong>तिथि:</strong> {panchang.tithi}</div>
              <div><strong>नक्षत्र:</strong> {panchang.nakshatra}</div>
              <div><strong>योग:</strong> {panchang.yoga}</div>
              <div><strong>करण:</strong> {panchang.karana}</div>
              <div><strong>सूर्योदय:</strong> {panchang.sunrise}</div>
              <div><strong>सूर्यास्त:</strong> {panchang.sunset}</div>
              <div><strong>शुभ समय:</strong> {panchang.auspicious_time}</div>
              <div><strong>राहु काल:</strong> {panchang.inauspicious_time}</div>
            </div>
          )}
        </div>
      </div>
      
      {/* Festival List */}
      <div className="mt-6 bg-white p-6 rounded-lg shadow-lg">
        <h3 className="text-lg font-bold mb-4">इस महीने के त्योहार</h3>
        <div className="grid grid-cols-2 gap-4">
          {festivals.map(festival => (
            <div key={festival.name} className="p-4 border rounded-lg">
              <div className="font-medium text-lg">{festival.hindi_name}</div>
              <div className="text-sm text-gray-600">{festival.date}</div>
              <div className="text-sm mt-2">{festival.significance}</div>
              <button
                onClick={() => {
                  // Navigate to content scheduling with festival pre-filled
                  window.location.href = `/admin/religious-content/schedule?festival=${festival.name}&date=${festival.date}`;
                }}
                className="mt-2 text-xs bg-blue-100 text-blue-800 px-2 py-1 rounded"
              >
                सामग्री शेड्यूल करें
              </button>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default FestivalCalendar;
```

## 🔧 **Integration with Existing News System**

### **Step 6: Safe Navigation Integration**

```javascript
// components/layout/AdminSidebar.js (Modify existing sidebar)
const AdminSidebar = () => {
  return (
    <div className="w-64 bg-gray-800 text-white h-screen">
      {/* Existing news navigation */}
      <div className="p-4">
        <h2 className="text-xl font-bold">Admin Panel</h2>
      </div>
      
      <nav className="mt-8">
        {/* Existing News Menu Items */}
        <div className="px-4 py-2">
          <h3 className="text-sm font-semibold text-gray-400 uppercase tracking-wider">
            News Management
          </h3>
          <ul className="mt-2 space-y-1">
            <li><a href="/admin/news">All News</a></li>
            <li><a href="/admin/news/create">Create News</a></li>
            <li><a href="/admin/categories">Categories</a></li>
          </ul>
        </div>
        
        {/* NEW: Religious Content Menu (Separate Section) */}
        <div className="px-4 py-2 mt-6">
          <h3 className="text-sm font-semibold text-gray-400 uppercase tracking-wider">
            Religious Content
          </h3>
          <ul className="mt-2 space-y-1">
            <li><a href="/admin/religious-content">Dashboard</a></li>
            <li><a href="/admin/religious-content/schedule">Schedule Content</a></li>
            <li><a href="/admin/religious-content/calendar">Hindu Calendar</a></li>
            <li><a href="/admin/religious-content/templates">Templates</a></li>
            <li><a href="/admin/religious-content/analytics">Analytics</a></li>
          </ul>
        </div>
      </nav>
    </div>
  );
};
```

### **Step 7: Environment Configuration**

```javascript
// .env.local
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_APP_URL=http://localhost:3000
```

## 📱 **Mobile Responsive Design**

```css
/* styles/religious-content.css */
.zodiac-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 1rem;
  margin: 1rem 0;
}

@media (max-width: 768px) {
  .zodiac-grid {
    grid-template-columns: 1fr;
  }
  
  .festival-calendar {
    grid-template-columns: 1fr;
  }
  
  .dashboard-stats {
    grid-template-columns: repeat(2, 1fr);
  }
}

.zodiac-card {
  transition: transform 0.2s, box-shadow 0.2s;
}

.zodiac-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

.festival-marker {
  position: absolute;
  top: 2px;
  right: 2px;
}
```

## 🚀 **Deployment Instructions**

1. **Install Dependencies:**
```bash
npm install react-calendar react-chartjs-2 chart.js date-fns
```

2. **Add to package.json:**
```json
{
  "dependencies": {
    "react-calendar": "^4.6.0",
    "react-chartjs-2": "^5.2.0",
    "chart.js": "^4.4.0",
    "date-fns": "^2.30.0"
  }
}
```

3. **Create SVG Assets:**
   - Add zodiac SVG files in `/public/icons/zodiac/`
   - Each file named as: `aries.svg`, `taurus.svg`, etc.

4. **Test Integration:**
   - Start FastAPI backend: `uvicorn main:app --reload`
   - Start Next.js frontend: `npm run dev`
   - Navigate to `/admin/religious-content`

## ✅ **Final Safety Checklist**

- ✅ All new routes use `/admin/religious-content/*` prefix
- ✅ API calls use `/api/religious-content/*` proxy
- ✅ No modifications to existing news components
- ✅ Separate database collections for scheduling
- ✅ Backward-compatible model extensions
- ✅ Independent authentication flow
- ✅ Separate CSS classes and styles
- ✅ Optional features that can be disabled

This implementation guide provides a complete, safe, and non-destructive way to add religious content scheduling to your existing news system. The UI will be modern, responsive, and culturally appropriate for Hindu religious content.