# Religious Content Scheduling System - Implementation Guide

## Overview

This document outlines the comprehensive religious content scheduling system for posting articles related to religion like **rashifal**, **editorial**, **this day in history**, **panchang**, and other spiritual content that can be scheduled for future publication.

## 🚀 Features Implemented

### 1. **Religious Content Types**
- **Rashifal (राशिफल)** - Daily/weekly horoscope for all 12 zodiac signs
- **Editorial** - Religious opinion pieces and spiritual guidance
- **This Day in History** - Historical religious events and significance
- **Panchang (पंचांग)** - Daily Hindu calendar with tithi, nakshatra, yoga, karana
- **Festival Content** - Festival information, rituals, and celebrations
- **Mantra** - Daily mantras and spiritual practices
- **Aarti** - Devotional songs and prayers
- **Vrat Kathas** - Fasting stories and religious narratives
- **Spiritual Guru Content** - Teachings and wisdom from spiritual leaders

### 2. **Scheduling System**
- **Future Scheduling** - Schedule content for any future date and time
- **Recurring Content** - Set up daily, weekly, or monthly recurring publications
- **Bulk Scheduling** - Schedule multiple items at once (e.g., daily rashifal for a week)
- **Auto-Publishing** - Automatic publication at scheduled time
- **Template System** - Reusable content templates for recurring publications
- **Timezone Support** - IST (Asia/Kolkata) timezone handling

### 3. **Hindu Calendar Integration**
- **Festival Calendar** - Complete Hindu festival calendar with dates
- **Panchang Calculation** - Daily tithi, nakshatra, yoga, karana
- **Auspicious Timing** - Muhurat and Rahu Kaal calculations
- **Content Recommendations** - AI-suggested content types based on calendar

## 📊 Database Collections

### 1. **scheduled_religious_content**
```javascript
{
  "_id": ObjectId,
  "content_type": "rashifal|editorial|this_day_history|panchang|festival|mantra|aarti|vrat_kathas|spiritual_guru",
  "title": "Article title",
  "content": "Article content (HTML/Markdown)",
  "schedule_date": ISODate,
  "schedule_status": "scheduled|published|draft|expired",
  "author_username": "username",
  "categories": "धर्म",
  "tags": ["rashifal", "daily"],
  "auto_publish": true,
  "timezone": "Asia/Kolkata",
  "is_recurring": false,
  "recurrence_pattern": "daily|weekly|monthly",
  "next_schedule_date": ISODate,
  "template_id": ObjectId,
  "rashifal_data": [...],  // Type-specific data
  "panchang_data": {...},
  "created_at": ISODate,
  "updated_at": ISODate,
  "published_at": ISODate,
  "published_news_id": ObjectId
}
```

### 2. **religious_content_templates**
```javascript
{
  "_id": ObjectId,
  "name": "Template name",
  "content_type": "rashifal|panchang|etc",
  "template_content": "Content with {{placeholders}}",
  "default_variables": {...},
  "is_active": true,
  "created_by": "username",
  "created_at": ISODate
}
```

## 🔧 API Endpoints

### **Content Templates**
- `POST /religious-content/templates` - Create content template
- `GET /religious-content/templates` - Get all templates
- `PUT /religious-content/templates/{id}` - Update template
- `DELETE /religious-content/templates/{id}` - Delete template

### **Scheduling**
- `POST /religious-content/schedule` - Schedule single content
- `POST /religious-content/bulk-schedule` - Bulk schedule multiple dates
- `GET /religious-content/scheduled` - Get scheduled content with filters
- `PUT /religious-content/scheduled/{id}` - Update scheduled content
- `DELETE /religious-content/scheduled/{id}` - Delete scheduled content
- `POST /religious-content/publish/{id}` - Manually publish content

### **Hindu Calendar**
- `GET /religious-content/calendar/festivals` - Get Hindu festivals
- `GET /religious-content/calendar/panchang` - Get daily panchang
- `GET /religious-content/calendar/auspicious-dates` - Get auspicious dates for scheduling
- `GET /religious-content/calendar/monthly-overview` - Complete monthly calendar

### **Admin Dashboard**
- `GET /religious-content/dashboard` - Dashboard statistics
- `GET /admin/religious-content/overview` - Admin overview
- `GET /admin/religious-content/authors` - Author statistics
- `POST /admin/religious-content/bulk-actions` - Bulk operations
- `GET /admin/religious-content/performance` - Performance metrics

### **Quick Actions**
- `POST /religious-content/quick-schedule` - Quick schedule daily content
- `GET /religious-content/template-suggestions` - Get template suggestions

## 🎯 Backend Implementation

### **1. Pydantic Models** (`models/news.py`)
```python
class ReligiousContentType(str, Enum):
    RASHIFAL = "rashifal"
    EDITORIAL = "editorial"
    THIS_DAY_HISTORY = "this_day_history"
    PANCHANG = "panchang"
    FESTIVAL = "festival"

class ScheduledContent(BaseModel):
    content_type: ReligiousContentType
    title: str
    content: str
    schedule_date: datetime
    auto_publish: bool = True
    is_recurring: bool = False
    # ... other fields
```

### **2. Background Scheduler** (`services/scheduler.py`)
```python
class ReligiousContentScheduler:
    def start(self):
        # Start background thread for auto-publishing
    
    def _process_scheduled_content(self):
        # Check for content ready to publish
        # Automatically publish at scheduled time
    
    def _handle_recurring_content(self):
        # Create next instances of recurring content
```

### **3. Hindu Calendar Service** (`services/hindu_calendar.py`)
```python
class HinduCalendarService:
    def generate_daily_panchang(self, date):
        # Calculate tithi, nakshatra, yoga, karana
        
    def get_festivals_for_month(self, month, year):
        # Return festivals for specific month
        
    def get_auspicious_dates_for_content_scheduling(self, start, end):
        # Return best dates for religious content
```

## 🖥️ UI Backend Support

### **Dashboard Overview**
```javascript
// GET /religious-content/dashboard
{
  "total_scheduled": 150,
  "published_today": 5,
  "pending_approval": 12,
  "failed_publications": 2,
  "content_type_breakdown": {
    "rashifal": 45,
    "panchang": 30,
    "editorial": 25
  },
  "upcoming_schedules": [...] 
}
```

### **Monthly Calendar View**
```javascript
// GET /religious-content/calendar/monthly-overview?month=10&year=2024
{
  "month": 10,
  "year": 2024,
  "festivals": [...],
  "auspicious_dates": [...],
  "daily_panchang": [...],
  "scheduled_content": [...],
  "content_scheduling_suggestions": [...]
}
```

### **Quick Scheduling**
```javascript
// POST /religious-content/quick-schedule
{
  "content_type": "rashifal",
  "days_ahead": 7,
  "time_slot": "06:00"
}
```

## 📱 UI Implementation Strategy

### **1. Admin Dashboard**
- **Content Calendar View** - Monthly calendar showing scheduled content
- **Festival Integration** - Highlight festivals and suggest related content
- **Bulk Operations** - Schedule multiple items, bulk publish/delete
- **Performance Metrics** - Views, likes, engagement for religious content

### **2. Content Scheduling Interface**
- **Date/Time Picker** with timezone support
- **Content Type Selector** with templates
- **Recurring Schedule Options** (daily, weekly, monthly)
- **Template Editor** with variable placeholders
- **Preview Function** before scheduling

### **3. Hindu Calendar Integration**
- **Festival Calendar** - Interactive calendar with festivals
- **Panchang Display** - Daily panchang information
- **Auspicious Date Highlighter** - Best dates for content publication
- **Automatic Suggestions** - AI-suggested content based on calendar

### **4. Content Templates**
- **Template Library** - Pre-built templates for each content type
- **Variable System** - {{date}}, {{rashi}}, {{festival}} placeholders
- **Template Preview** - Live preview with sample data
- **Template Analytics** - Performance of template-based content

## 🔄 Auto-Publishing Workflow

```
1. Content Scheduled → stored in "scheduled_religious_content"
2. Background Scheduler checks every minute
3. If schedule_date <= current_time AND auto_publish = true:
   a. Create NewsPost in "news" collection
   b. Update scheduled content status to "published"
   c. Send notifications (optional)
   d. Handle recurring content (create next instance)
```

## 🚀 Advanced Features

### **1. Content Personalization**
- Location-based panchang (sunrise/sunset times)
- Regional festival variations
- Language preferences (Hindi/English)

### **2. AI Content Generation**
- Auto-generate daily rashifal content
- Historical event lookup for "this day in history"
- Festival description automation

### **3. Social Media Integration**
- Auto-post to social media when published
- Generate social media-friendly content snippets
- Hashtag suggestions based on content type

### **4. Analytics & Optimization**
- Best time analysis for publishing
- Content type performance tracking
- Audience engagement patterns
- A/B testing for content variations

## 📋 Usage Examples

### **Scheduling Daily Rashifal**
```bash
# Schedule rashifal for next 7 days at 6 AM
POST /religious-content/quick-schedule
{
  "content_type": "rashifal",
  "days_ahead": 7,
  "time_slot": "06:00"
}
```

### **Creating Festival Content Template**
```bash
POST /religious-content/templates
{
  "name": "Festival Celebration Template",
  "content_type": "festival",
  "template_content": "आज {{festival_name}} का पावन दिन है। {{significance}} के साथ मनाएं।",
  "default_variables": {
    "festival_name": "दिवाली",
    "significance": "रोशनी का त्योहार"
  }
}
```

### **Bulk Scheduling for Navratri**
```bash
POST /religious-content/bulk-schedule
{
  "content_type": "festival",
  "start_date": "2024-10-15",
  "end_date": "2024-10-24",
  "template_id": "festival_template_id"
}
```

This comprehensive system provides a complete solution for managing religious content with intelligent scheduling, Hindu calendar integration, and automated publishing capabilities.