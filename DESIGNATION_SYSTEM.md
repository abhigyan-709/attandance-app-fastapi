# Author Designation System - Implementation Guide

## 📋 Overview

Complete designation management system for authors with automatic grievance role assignment based on designation hierarchy.

## 🎯 Features

✅ **Predefined Designations** with hierarchy levels
✅ **Grievance Role Mapping** - Auto-assign based on designation
✅ **Public API** for UI dropdowns
✅ **Admin Management** - CRUD operations
✅ **User Sync** - Automatically sync user grievance roles
✅ **Validation** - Ensure only valid designations

---

## 📊 Designation Hierarchy

### Executive Level
- **CEO** - Chief Executive Officer
- **CTO** - Chief Technology Officer
- **CFO** - Chief Financial Officer

### Chief Level
- **Chief Editor** - Overall editorial responsibility ✅ Auto-assign grievances
- **Managing Editor** - Day-to-day editorial management ✅ Auto-assign grievances

### Senior Level
- **Regional Editor** - Regional content management ✅ Auto-assign grievances
- **Senior Staff Editor** - Senior editorial position ✅ Auto-assign grievances

### Mid Level
- **Staff Editor** - Regular editorial duties ✅ Can handle grievances
- **Associate Editor** - Mid-level editorial position ✅ Can handle grievances
- **Copy Editor** - Content review and editing
- **Senior Reporter** - Experienced reporting
- **Correspondent** - Special assignment coverage

### Junior Level
- **Assistant Editor** - Entry-level editorial position
- **Reporter** - Field reporting
- **Contributor** - External content contributor

---

## 🔌 API Endpoints

### Public Endpoints (No Auth)

#### 1. Get All Designations
```http
GET /designations?active_only=true
```

**Response:**
```json
[
  {
    "id": "65a1b2c3d4e5f6g7h8i9j0k1",
    "name": "Chief Editor",
    "level": "chief",
    "can_handle_grievances": true,
    "auto_assign_grievances": true,
    "display_order": 1,
    "is_active": true,
    "description": "Chief Editor - Overall editorial responsibility",
    "created_at": "2024-12-11T10:00:00Z"
  },
  {
    "id": "65a1b2c3d4e5f6g7h8i9j0k2",
    "name": "Regional Editor",
    "level": "senior",
    "can_handle_grievances": true,
    "auto_assign_grievances": true,
    "display_order": 2,
    "is_active": true,
    "description": "Regional Editor - Regional content management"
  }
]
```

#### 2. Get Grievance Handler Designations
```http
GET /designations/grievance-handlers
```

**Response:**
```json
[
  {
    "id": "65a1b2c3d4e5f6g7h8i9j0k1",
    "name": "Chief Editor",
    "level": "chief",
    "auto_assign": true
  },
  {
    "id": "65a1b2c3d4e5f6g7h8i9j0k2",
    "name": "Regional Editor",
    "level": "senior",
    "auto_assign": true
  }
]
```

### Admin Endpoints (Auth Required)

#### 3. Initialize Default Designations
```bash
# One-time setup
curl -X POST https://api.projectdevops.in/designations/initialize \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

**Response:**
```json
{
  "message": "Default designations initialized successfully",
  "count": 15,
  "designations": [
    "Chief Editor",
    "Regional Editor",
    "Staff Editor",
    "Senior Staff Editor",
    "CEO",
    "CTO",
    "CFO",
    "Managing Editor",
    "Associate Editor",
    "Assistant Editor",
    "Copy Editor",
    "Reporter",
    "Senior Reporter",
    "Contributor",
    "Correspondent"
  ]
}
```

#### 4. Create Custom Designation
```bash
curl -X POST https://api.projectdevops.in/designations \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Digital Editor",
    "level": "mid",
    "can_handle_grievances": true,
    "auto_assign_grievances": false,
    "display_order": 20,
    "description": "Digital Editor - Online content management"
  }'
```

#### 5. Update Designation
```bash
curl -X PUT https://api.projectdevops.in/designations/{designation_id} \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Senior Digital Editor",
    "level": "senior",
    "can_handle_grievances": true,
    "auto_assign_grievances": true,
    "display_order": 15,
    "description": "Senior Digital Editor"
  }'
```

#### 6. Deactivate Designation
```bash
curl -X DELETE https://api.projectdevops.in/designations/{designation_id} \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

#### 7. Sync User Designations
```bash
# Updates all existing users with grievance roles based on their designations
curl -X POST https://api.projectdevops.in/designations/sync-users \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

**Response:**
```json
{
  "message": "User designations synced successfully",
  "updated": 25,
  "invalid": 2,
  "total_valid_designations": 15
}
```

#### 8. Get Users by Designation
```bash
curl https://api.projectdevops.in/designations/users-by-designation?can_handle_grievances=true \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

**Response:**
```json
{
  "total_users": 15,
  "designations_count": 5,
  "users_by_designation": {
    "Chief Editor": [
      {
        "_id": "65a1b2c3d4e5f6g7h8i9j0k1",
        "username": "john_doe",
        "first_name": "John",
        "last_name": "Doe",
        "email": "john@gobarsahitimes.com",
        "author_designation": "Chief Editor",
        "author_designation_level": "chief",
        "can_handle_grievances": true
      }
    ],
    "Regional Editor": [...]
  }
}
```

---

## 🔄 Integration with User Update

When updating a user's `author_designation`, the system **automatically**:

1. ✅ **Validates** designation exists and is active
2. ✅ **Syncs** `author_designation_level` (chief, senior, mid, junior)
3. ✅ **Sets** `can_handle_grievances` flag
4. ✅ **Records** `author_designation_synced_at` timestamp

### Example User Update with Designation
```bash
curl -X PUT https://api.projectdevops.in/users/john_doe \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "author_designation": "Chief Editor",
    "author_bio": "20+ years in journalism"
  }'
```

**Automatic Updates:**
```json
{
  "author_designation": "Chief Editor",
  "author_designation_level": "chief",
  "can_handle_grievances": true,
  "author_designation_synced_at": "2024-12-11T15:30:00Z",
  "author_bio": "20+ years in journalism"
}
```

---

## 🎯 Grievance Auto-Assignment Logic

When a grievance is submitted:

1. **Find Eligible Handlers:**
   - Role: `author` or `admin`
   - Status: `is_active = true`
   - Capability: `can_handle_grievances = true`
   - Designation: Must have `author_designation`

2. **Prioritize by Level:**
   - Sort by `author_designation_level` (highest first)
   - Executive → Chief → Senior → Mid → Junior

3. **Auto-Assign:**
   - Assign to first eligible handler
   - Record in `status_history`

### Example Auto-Assignment Flow

```
New Grievance Submitted
         ↓
Find Handlers: can_handle_grievances=true
         ↓
Sort by Level: Chief Editor (level=chief) → Regional Editor (level=senior)
         ↓
Assign to: Chief Editor
         ↓
Notification Sent
```

---

## 🎨 Frontend Implementation

### 1. Designation Dropdown in Author Profile

```jsx
// AuthorProfileForm.tsx
import { useEffect, useState } from 'react';

interface Designation {
  id: string;
  name: string;
  level: string;
  description: string;
}

export default function AuthorProfileForm() {
  const [designations, setDesignations] = useState<Designation[]>([]);
  const [selectedDesignation, setSelectedDesignation] = useState('');

  useEffect(() => {
    // Fetch designations
    fetch('https://api.projectdevops.in/designations')
      .then(res => res.json())
      .then(data => setDesignations(data));
  }, []);

  const handleUpdate = async () => {
    await fetch(`https://api.projectdevops.in/users/${username}`, {
      method: 'PUT',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        author_designation: selectedDesignation
      })
    });
  };

  return (
    <div>
      <label className="block text-sm font-medium mb-2">
        Designation *
      </label>
      <select
        value={selectedDesignation}
        onChange={e => setSelectedDesignation(e.target.value)}
        className="w-full px-4 py-2 border rounded-lg"
      >
        <option value="">Select Designation</option>
        {designations.map(des => (
          <option key={des.id} value={des.name}>
            {des.name} {des.description && `- ${des.description}`}
          </option>
        ))}
      </select>
      
      <button onClick={handleUpdate} className="mt-4 px-6 py-2 bg-blue-600 text-white rounded">
        Update Profile
      </button>
    </div>
  );
}
```

### 2. Admin Designation Management Page

```jsx
// DesignationManagement.tsx
export default function DesignationManagement() {
  const [designations, setDesignations] = useState([]);

  const initialize = async () => {
    const res = await fetch(
      'https://api.projectdevops.in/designations/initialize',
      {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${adminToken}` }
      }
    );
    const data = await res.json();
    alert(data.message);
  };

  const syncUsers = async () => {
    const res = await fetch(
      'https://api.projectdevops.in/designations/sync-users',
      {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${adminToken}` }
      }
    );
    const data = await res.json();
    alert(`Synced ${data.updated} users, ${data.invalid} invalid`);
  };

  return (
    <div className="container mx-auto p-6">
      <h1 className="text-3xl font-bold mb-6">Designation Management</h1>
      
      <div className="flex gap-4 mb-6">
        <button
          onClick={initialize}
          className="px-6 py-2 bg-green-600 text-white rounded"
        >
          Initialize Default Designations
        </button>
        
        <button
          onClick={syncUsers}
          className="px-6 py-2 bg-blue-600 text-white rounded"
        >
          Sync User Designations
        </button>
      </div>

      {/* Designation List */}
      <div className="bg-white rounded-lg shadow">
        <table className="w-full">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left">Designation</th>
              <th className="px-6 py-3 text-left">Level</th>
              <th className="px-6 py-3 text-left">Can Handle Grievances</th>
              <th className="px-6 py-3 text-left">Auto-Assign</th>
              <th className="px-6 py-3 text-left">Actions</th>
            </tr>
          </thead>
          <tbody>
            {designations.map(des => (
              <tr key={des.id} className="border-t">
                <td className="px-6 py-4">{des.name}</td>
                <td className="px-6 py-4">
                  <span className="px-2 py-1 bg-blue-100 text-blue-800 rounded text-xs">
                    {des.level}
                  </span>
                </td>
                <td className="px-6 py-4">
                  {des.can_handle_grievances ? '✅' : '❌'}
                </td>
                <td className="px-6 py-4">
                  {des.auto_assign_grievances ? '✅' : '❌'}
                </td>
                <td className="px-6 py-4">
                  <button className="text-blue-600 hover:underline">Edit</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
```

---

## 🗄️ Database Schema

### `designations` Collection
```javascript
{
  "_id": ObjectId,
  "name": "Chief Editor",
  "level": "chief",  // executive, chief, senior, mid, junior
  "can_handle_grievances": true,
  "auto_assign_grievances": true,
  "display_order": 1,
  "is_active": true,
  "description": "Chief Editor - Overall editorial responsibility",
  "created_at": ISODate,
  "created_by": "admin",
  "updated_at": ISODate,
  "updated_by": "admin"
}
```

### `user` Collection (Extended Fields)
```javascript
{
  "_id": ObjectId,
  "username": "john_doe",
  "author_designation": "Chief Editor",
  
  // Auto-populated by designation sync
  "author_designation_level": "chief",
  "can_handle_grievances": true,
  "author_designation_synced_at": ISODate
}
```

---

## 🚀 Deployment Steps

### Step 1: Initialize Designations
```bash
# Login as admin and initialize
curl -X POST https://api.projectdevops.in/designations/initialize \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

### Step 2: Sync Existing Users
```bash
# Sync all existing authors with grievance roles
curl -X POST https://api.projectdevops.in/designations/sync-users \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

### Step 3: Update Frontend
- Add designation dropdown to author profile forms
- Fetch designations from `/designations` endpoint
- Display designation in author cards/profiles

### Step 4: Test Grievance Auto-Assignment
1. Submit a test grievance
2. Verify auto-assignment to Chief Editor/Regional Editor
3. Check assignment in admin dashboard

---

## ✅ Benefits

1. **Standardized Designations** - Consistent across platform
2. **Automatic Role Assignment** - No manual configuration
3. **Hierarchical Management** - Clear chain of command
4. **Grievance Efficiency** - Auto-route to right person
5. **Easy Maintenance** - Centralized designation management
6. **Validation** - Prevent invalid designations
7. **Audit Trail** - Track designation changes

---

## 📊 Designation vs Grievance Role Matrix

| Designation | Level | Can Handle | Auto-Assign | Priority |
|-------------|-------|------------|-------------|----------|
| CEO | Executive | ✅ | ❌ | 5 |
| CTO | Executive | ❌ | ❌ | - |
| CFO | Executive | ❌ | ❌ | - |
| Chief Editor | Chief | ✅ | ✅ | 1 |
| Managing Editor | Chief | ✅ | ✅ | 2 |
| Regional Editor | Senior | ✅ | ✅ | 3 |
| Senior Staff Editor | Senior | ✅ | ✅ | 4 |
| Staff Editor | Mid | ✅ | ❌ | 6 |
| Associate Editor | Mid | ✅ | ❌ | 7 |
| Copy Editor | Mid | ❌ | ❌ | - |
| Senior Reporter | Mid | ❌ | ❌ | - |
| Assistant Editor | Junior | ❌ | ❌ | - |
| Reporter | Junior | ❌ | ❌ | - |
| Contributor | Junior | ❌ | ❌ | - |
| Correspondent | Mid | ❌ | ❌ | - |

---

## 🔧 Testing

```bash
# 1. Get all designations
curl https://api.projectdevops.in/designations

# 2. Initialize (first time)
curl -X POST https://api.projectdevops.in/designations/initialize \
  -H "Authorization: Bearer $ADMIN_TOKEN"

# 3. Update user designation
curl -X PUT https://api.projectdevops.in/users/john_doe \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"author_designation": "Chief Editor"}'

# 4. Verify user fields updated
curl https://api.projectdevops.in/users/john_doe \
  -H "Authorization: Bearer $TOKEN"

# 5. Submit grievance and check auto-assignment
curl -X POST https://api.projectdevops.in/grievance/submit \
  -H "Content-Type: application/json" \
  -d '{
    "complainant_name": "Test User",
    "complainant_email": "test@example.com",
    "category": "factual_error",
    "subject": "Test complaint",
    "description": "This is a test to verify auto-assignment works correctly"
  }'

# Response should include: "assigned_to": "john_doe"
```

---

**Status:** ✅ Complete Implementation
**Next:** Initialize designations and sync users
