# Grievance Redressal Mechanism - Implementation Guide

## 📋 Overview

Complete implementation of Grievance Redressal Mechanism for Gobar Sahi Times news portal, compliant with **IT Rules 2021** for digital media publishers in India.

## 🏛️ Regulatory Compliance

This system addresses the mandatory requirements under:
- **Information Technology (Intermediary Guidelines and Digital Media Ethics Code) Rules, 2021**
- Part III - Code of Ethics for Publishers of News and Current Affairs Content

### Required Components (Now Implemented)

✅ **A. Grievance Redressal Officer (GRO)**
- Name, designation, contact details
- Official email address
- Working hours and response timeline

✅ **B. Self Regulatory Body Membership**
- Name of the body (e.g., NBDA, NBSA)
- Membership number and details
- Contact information

✅ **C. News Editor(s) Details**
- Chief Editor information
- Editorial team details
- Contact information

---

## 🗂️ Database Collections

### 1. `grievance_info`
Stores grievance mechanism information (officers, editors, self-regulatory body)

```javascript
{
  "_id": ObjectId,
  "type": "officer" | "editor" | "self_regulatory_body",
  
  // For type: "officer"
  "name": "Rajesh Kumar",
  "designation": "Grievance Redressal Officer",
  "email": "grievance@gobarsahitimes.com",
  "phone": "+91-9876543210",
  "address": "Gobar Sahi Times Office, Patna, Bihar - 800001",
  "working_hours": "Monday to Friday, 10:00 AM - 6:00 PM IST",
  "is_active": true,
  "appointed_date": ISODate,
  "appointed_by": "admin",
  
  // For type: "editor"
  "name": "Dr. Priya Sharma",
  "designation": "Chief Editor",
  "email": "editor@gobarsahitimes.com",
  "phone": "+91-9876543211",
  "bio": "20+ years of journalism experience",
  "profile_image": "https://...",
  "is_chief_editor": true,
  "is_active": true,
  
  // For type: "self_regulatory_body"
  "body_name": "News Broadcasters & Digital Association",
  "membership_number": "NBDA-2024-12345",
  "registration_date": ISODate,
  "website_url": "https://www.nbda.in",
  "contact_email": "info@nbda.in",
  "is_active": true
}
```

### 2. `grievance_complaints`
Stores all grievance complaints submitted by users

```javascript
{
  "_id": ObjectId,
  "complaint_id": "GRV-2024-A1B2C3D4",
  "complainant_name": "John Doe",
  "complainant_email": "john@example.com",
  "complainant_phone": "+91-9876543210",
  "category": "factual_error",  // Enum
  "subject": "Incorrect election results",
  "description": "Detailed description...",
  "article_url": "https://gobarsahitimes.com/news/...",
  "article_id": "news123",
  "evidence_urls": ["https://..."],
  "preferred_resolution": "Correction and clarification",
  
  // Status tracking
  "status": "submitted",  // submitted, under_review, in_progress, resolved, rejected, closed
  "submitted_at": ISODate,
  "assigned_to": "editor_username",
  "resolved_at": ISODate,
  "resolved_by": "admin",
  "resolution_notes": "Article corrected...",
  
  // History
  "status_history": [
    {
      "status": "submitted",
      "timestamp": ISODate,
      "updated_by": "system",
      "notes": "Complaint submitted"
    }
  ],
  "internal_notes": [
    {
      "note": "Contacted author for fact-check",
      "added_by": "admin",
      "timestamp": ISODate
    }
  ]
}
```

---

## 🔌 API Endpoints

### Public Endpoints (No Authentication)

#### 1. Get Grievance Information
```http
GET /grievance/info
```

**Response:**
```json
{
  "grievance_officer": {
    "name": "Rajesh Kumar",
    "designation": "Grievance Redressal Officer",
    "email": "grievance@gobarsahitimes.com",
    "phone": "+91-9876543210",
    "address": "Gobar Sahi Times Office, Patna, Bihar - 800001",
    "working_hours": "Monday to Friday, 10:00 AM - 6:00 PM IST"
  },
  "self_regulatory_body": {
    "body_name": "News Broadcasters & Digital Association",
    "membership_number": "NBDA-2024-12345",
    "website_url": "https://www.nbda.in"
  },
  "news_editors": [
    {
      "name": "Dr. Priya Sharma",
      "designation": "Chief Editor",
      "email": "editor@gobarsahitimes.com",
      "is_chief_editor": true
    }
  ],
  "complaint_submission_url": "/grievance/submit",
  "last_updated": "2024-12-11T10:00:00Z"
}
```

#### 2. Submit Grievance Complaint
```http
POST /grievance/submit
Content-Type: application/json

{
  "complainant_name": "John Doe",
  "complainant_email": "john@example.com",
  "complainant_phone": "+91-9876543210",
  "category": "factual_error",
  "subject": "Incorrect information about election results",
  "description": "The article contains factually incorrect data...",
  "article_url": "https://gobarsahitimes.com/news/election-2024",
  "preferred_resolution": "Request correction with proper fact-checking"
}
```

**Response:**
```json
{
  "message": "Grievance complaint submitted successfully",
  "complaint_id": "GRV-2024-A1B2C3D4",
  "status": "submitted",
  "submitted_at": "2024-12-11T10:30:00Z",
  "acknowledgment": "You will receive an acknowledgment email shortly. We aim to resolve complaints within 15 days."
}
```

#### 3. Track Grievance Status
```http
GET /grievance/track/{complaint_id}
```

**Example:**
```bash
curl https://api.projectdevops.in/grievance/track/GRV-2024-A1B2C3D4
```

**Response:**
```json
{
  "complaint_id": "GRV-2024-A1B2C3D4",
  "status": "under_review",
  "submitted_at": "2024-12-11T10:30:00Z",
  "category": "factual_error",
  "subject": "Incorrect information about election results",
  "resolved_at": null,
  "resolution_notes": null,
  "status_history": [
    {
      "status": "submitted",
      "timestamp": "2024-12-11T10:30:00Z",
      "notes": "Complaint submitted"
    },
    {
      "status": "under_review",
      "timestamp": "2024-12-11T14:00:00Z",
      "notes": "Assigned to editorial team"
    }
  ]
}
```

### Admin Endpoints (Authentication Required)

#### 4. Get All Complaints
```http
GET /grievance/complaints?status=submitted&category=factual_error&skip=0&limit=50
Authorization: Bearer <admin_token>
```

#### 5. Get Complaint Details
```http
GET /grievance/complaints/{complaint_id}
Authorization: Bearer <admin_token>
```

#### 6. Update Complaint Status
```http
PATCH /grievance/complaints/{complaint_id}
Authorization: Bearer <admin_token>
Content-Type: application/json

{
  "status": "resolved",
  "resolution_notes": "Article has been corrected and a clarification published",
  "internal_notes": "Contacted author, verified facts from official sources"
}
```

#### 7. Get Statistics
```http
GET /grievance/statistics
Authorization: Bearer <admin_token>
```

**Response:**
```json
{
  "total_complaints": 45,
  "pending_complaints": 8,
  "resolved_complaints": 35,
  "rejected_complaints": 2,
  "avg_resolution_time_hours": 72.5,
  "complaints_by_category": {
    "factual_error": 20,
    "defamation": 5,
    "privacy_violation": 10,
    "offensive_content": 8,
    "other": 2
  },
  "complaints_this_month": 12,
  "resolution_rate_percentage": 77.78
}
```

#### 8. Set Grievance Officer
```http
POST /grievance/officer
Authorization: Bearer <admin_token>
Content-Type: application/json

{
  "name": "Rajesh Kumar",
  "designation": "Grievance Redressal Officer",
  "email": "grievance@gobarsahitimes.com",
  "phone": "+91-9876543210",
  "address": "Gobar Sahi Times Office, Patna, Bihar - 800001",
  "working_hours": "Monday to Friday, 10:00 AM - 6:00 PM IST"
}
```

#### 9. Set Self Regulatory Body
```http
POST /grievance/self-regulatory-body
Authorization: Bearer <admin_token>
Content-Type: application/json

{
  "body_name": "News Broadcasters & Digital Association",
  "membership_number": "NBDA-2024-12345",
  "website_url": "https://www.nbda.in",
  "contact_email": "info@nbda.in"
}
```

#### 10. Add News Editor
```http
POST /grievance/editor
Authorization: Bearer <admin_token>
Content-Type: application/json

{
  "name": "Dr. Priya Sharma",
  "designation": "Chief Editor",
  "email": "editor@gobarsahitimes.com",
  "phone": "+91-9876543211",
  "bio": "20+ years of journalism experience",
  "is_chief_editor": true
}
```

---

## 📧 Email Notifications

### 1. Acknowledgment Email
Sent automatically when complaint is submitted:
- Complaint ID
- Timeline (15 days)
- Tracking link
- Contact information

### 2. Resolution Email
Sent when complaint is resolved:
- Resolution details
- Feedback options
- Escalation information

---

## 🎨 Frontend Implementation

### 1. Grievance Information Page
Create `/grievance` or `/about/grievance-redressal` page:

```jsx
// grievance-info.tsx
import { useEffect, useState } from 'react';

interface GrievanceInfo {
  grievance_officer: {
    name: string;
    designation: string;
    email: string;
    phone: string;
    address: string;
    working_hours: string;
  };
  self_regulatory_body: {
    body_name: string;
    membership_number: string;
    website_url: string;
  };
  news_editors: Array<{
    name: string;
    designation: string;
    email: string;
    is_chief_editor: boolean;
  }>;
}

export default function GrievanceInfoPage() {
  const [info, setInfo] = useState<GrievanceInfo | null>(null);

  useEffect(() => {
    fetch('https://api.projectdevops.in/grievance/info')
      .then(res => res.json())
      .then(data => setInfo(data));
  }, []);

  if (!info) return <div>Loading...</div>;

  return (
    <div className="container mx-auto px-4 py-8">
      <h1 className="text-3xl font-bold mb-6">Grievance Redressal Mechanism</h1>
      
      {/* Grievance Officer Section */}
      <section className="mb-8 p-6 bg-white rounded-lg shadow">
        <h2 className="text-2xl font-semibold mb-4">A. Grievance Redressal Officer</h2>
        <div className="space-y-2">
          <p><strong>Name:</strong> {info.grievance_officer.name}</p>
          <p><strong>Designation:</strong> {info.grievance_officer.designation}</p>
          <p><strong>Email:</strong> <a href={`mailto:${info.grievance_officer.email}`} className="text-blue-600">{info.grievance_officer.email}</a></p>
          <p><strong>Phone:</strong> {info.grievance_officer.phone}</p>
          <p><strong>Address:</strong> {info.grievance_officer.address}</p>
          <p><strong>Working Hours:</strong> {info.grievance_officer.working_hours}</p>
        </div>
      </section>

      {/* Self Regulatory Body Section */}
      <section className="mb-8 p-6 bg-white rounded-lg shadow">
        <h2 className="text-2xl font-semibold mb-4">B. Self Regulatory Body</h2>
        <div className="space-y-2">
          <p><strong>Body Name:</strong> {info.self_regulatory_body.body_name}</p>
          <p><strong>Membership Number:</strong> {info.self_regulatory_body.membership_number}</p>
          <p><strong>Website:</strong> <a href={info.self_regulatory_body.website_url} target="_blank" className="text-blue-600">{info.self_regulatory_body.website_url}</a></p>
        </div>
      </section>

      {/* News Editors Section */}
      <section className="mb-8 p-6 bg-white rounded-lg shadow">
        <h2 className="text-2xl font-semibold mb-4">C. News Editor(s)</h2>
        <div className="space-y-4">
          {info.news_editors.map((editor, index) => (
            <div key={index} className="border-l-4 border-blue-500 pl-4">
              <p className="font-semibold">{editor.name}</p>
              <p className="text-sm text-gray-600">{editor.designation}</p>
              <p className="text-sm"><a href={`mailto:${editor.email}`} className="text-blue-600">{editor.email}</a></p>
            </div>
          ))}
        </div>
      </section>

      {/* Submit Complaint Button */}
      <div className="text-center">
        <a href="/grievance/submit" className="inline-block px-8 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition">
          Submit a Grievance
        </a>
      </div>
    </div>
  );
}
```

### 2. Grievance Submission Form
Create `/grievance/submit` page:

```jsx
// grievance-submit.tsx
import { useState } from 'react';

export default function GrievanceSubmitPage() {
  const [formData, setFormData] = useState({
    complainant_name: '',
    complainant_email: '',
    complainant_phone: '',
    category: 'factual_error',
    subject: '',
    description: '',
    article_url: '',
    preferred_resolution: ''
  });
  const [submitted, setSubmitted] = useState(false);
  const [complaintId, setComplaintId] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    const response = await fetch('https://api.projectdevops.in/grievance/submit', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(formData)
    });

    const data = await response.json();
    setComplaintId(data.complaint_id);
    setSubmitted(true);
  };

  if (submitted) {
    return (
      <div className="container mx-auto px-4 py-8 max-w-2xl">
        <div className="bg-green-50 border border-green-200 rounded-lg p-6 text-center">
          <h2 className="text-2xl font-bold text-green-800 mb-4">✅ Complaint Submitted Successfully</h2>
          <p className="text-lg mb-4">Your Complaint ID: <strong className="font-mono text-xl">{complaintId}</strong></p>
          <p className="text-gray-700 mb-6">You will receive an acknowledgment email shortly. We aim to resolve complaints within 15 days.</p>
          <a href={`/grievance/track/${complaintId}`} className="inline-block px-6 py-2 bg-blue-600 text-white rounded hover:bg-blue-700">
            Track Your Complaint
          </a>
        </div>
      </div>
    );
  }

  return (
    <div className="container mx-auto px-4 py-8 max-w-3xl">
      <h1 className="text-3xl font-bold mb-6">Submit a Grievance</h1>
      
      <form onSubmit={handleSubmit} className="space-y-6 bg-white p-6 rounded-lg shadow">
        <div>
          <label className="block text-sm font-medium mb-2">Your Name *</label>
          <input
            type="text"
            required
            value={formData.complainant_name}
            onChange={e => setFormData({...formData, complainant_name: e.target.value})}
            className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
          />
        </div>

        <div>
          <label className="block text-sm font-medium mb-2">Email Address *</label>
          <input
            type="email"
            required
            value={formData.complainant_email}
            onChange={e => setFormData({...formData, complainant_email: e.target.value})}
            className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
          />
        </div>

        <div>
          <label className="block text-sm font-medium mb-2">Phone Number</label>
          <input
            type="tel"
            value={formData.complainant_phone}
            onChange={e => setFormData({...formData, complainant_phone: e.target.value})}
            className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
          />
        </div>

        <div>
          <label className="block text-sm font-medium mb-2">Category *</label>
          <select
            required
            value={formData.category}
            onChange={e => setFormData({...formData, category: e.target.value})}
            className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
          >
            <option value="factual_error">Factual Error</option>
            <option value="defamation">Defamation</option>
            <option value="copyright">Copyright Violation</option>
            <option value="privacy_violation">Privacy Violation</option>
            <option value="offensive_content">Offensive Content</option>
            <option value="misinformation">Misinformation</option>
            <option value="other">Other</option>
          </select>
        </div>

        <div>
          <label className="block text-sm font-medium mb-2">Subject *</label>
          <input
            type="text"
            required
            minLength={10}
            value={formData.subject}
            onChange={e => setFormData({...formData, subject: e.target.value})}
            className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
            placeholder="Brief summary of the issue"
          />
        </div>

        <div>
          <label className="block text-sm font-medium mb-2">Detailed Description *</label>
          <textarea
            required
            minLength={50}
            rows={6}
            value={formData.description}
            onChange={e => setFormData({...formData, description: e.target.value})}
            className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
            placeholder="Provide detailed information about your grievance..."
          />
        </div>

        <div>
          <label className="block text-sm font-medium mb-2">Article/News URL</label>
          <input
            type="url"
            value={formData.article_url}
            onChange={e => setFormData({...formData, article_url: e.target.value})}
            className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
            placeholder="https://gobarsahitimes.com/news/..."
          />
        </div>

        <div>
          <label className="block text-sm font-medium mb-2">Preferred Resolution</label>
          <textarea
            rows={3}
            value={formData.preferred_resolution}
            onChange={e => setFormData({...formData, preferred_resolution: e.target.value})}
            className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
            placeholder="What resolution are you seeking?"
          />
        </div>

        <button
          type="submit"
          className="w-full py-3 px-6 bg-blue-600 text-white font-semibold rounded-lg hover:bg-blue-700 transition"
        >
          Submit Grievance
        </button>
      </form>
    </div>
  );
}
```

### 3. Complaint Tracking Page
Create `/grievance/track/[id]` page

### 4. Admin Dashboard
Add grievance management section to admin dashboard with:
- List of all complaints
- Filter by status/category
- Quick actions (assign, update status, resolve)
- Statistics dashboard

---

## 🔧 Testing

### Test with cURL:

```bash
# 1. Get grievance info
curl https://api.projectdevops.in/grievance/info

# 2. Submit a complaint
curl -X POST https://api.projectdevops.in/grievance/submit \
  -H "Content-Type: application/json" \
  -d '{
    "complainant_name": "Test User",
    "complainant_email": "test@example.com",
    "category": "factual_error",
    "subject": "Test complaint",
    "description": "This is a test complaint with detailed description of the issue that needs to be addressed by the editorial team."
  }'

# 3. Track complaint
curl https://api.projectdevops.in/grievance/track/GRV-2024-12345678

# 4. Admin: Get all complaints
curl https://api.projectdevops.in/grievance/complaints \
  -H "Authorization: Bearer $ADMIN_TOKEN"

# 5. Admin: Update complaint
curl -X PATCH https://api.projectdevops.in/grievance/complaints/GRV-2024-12345678 \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "status": "resolved",
    "resolution_notes": "Issue has been addressed and article corrected"
  }'
```

---

## 📊 Compliance Checklist

- [x] Grievance Redressal Officer appointed with contact details
- [x] Self Regulatory Body membership disclosed
- [x] News Editor(s) information provided
- [x] Public grievance submission mechanism
- [x] Complaint tracking system
- [x] 15-day resolution timeline
- [x] Email notifications (acknowledgment & resolution)
- [x] Admin management interface
- [x] Statistics and reporting

---

## 🚀 Deployment Steps

1. ✅ Backend already deployed (routes registered in main.py)
2. 📧 Update email configuration in send_email.py
3. 🎨 Create frontend pages (grievance info, submit, track)
4. 👤 Set up Grievance Officer via admin API
5. 🏛️ Add Self Regulatory Body information
6. 📝 Add News Editor details
7. 🔗 Add link in footer: "Grievance Redressal"
8. 📄 Update About/Contact pages

---

## 📞 Support

For questions about this implementation:
- **Email:** connect@projectdevops.in
- **Technical Support:** Abhigyan (abhigyan709@gmail.com)

---

**Status:** ✅ Backend Implementation Complete
**Next:** Frontend UI Integration
