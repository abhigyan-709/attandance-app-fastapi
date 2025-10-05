# 📋 Biodata API Endpoints Reference

## 🔐 Authentication & Authorization Levels

### **Authentication Requirements:**
- **🟢 USER LOGIN**: Requires valid JWT token (role: "user" or "admin")  
- **🔴 ADMIN ONLY**: Requires valid JWT token with role: "admin"
- **🟡 PUBLIC**: No authentication required

### **Access Control Logic:**
- **Profile Owner**: User whose `username` matches the biodata's `user_id` field
- **Admin**: User with `role: "admin"` 
- **Public Access**: Any authenticated user can view active profiles
- **Owner + Admin**: Either the profile owner OR an admin can perform the action

---

## 📊 Complete API Endpoints

### **🔵 BASIC BIODATA MANAGEMENT**

#### **🟢 USER LOGIN REQUIRED**

| Method | Endpoint | Description | Who Can Access |
|--------|----------|-------------|----------------|
| `POST` | `/biodata` | Create new biodata profile | Any logged-in user (becomes owner) |
| `GET` | `/biodata` | List biodata profiles with filters | Any logged-in user (shows active profiles) |
| `GET` | `/biodata/{profile_id}` | Get specific biodata profile | Any logged-in user (if profile is active) |
| `GET` | `/biodata/my/profile` | Get current user's biodata | Profile owner only |
| `PUT` | `/biodata/{profile_id}` | Update entire biodata profile | Profile owner + Admin |
| `DELETE` | `/biodata/{profile_id}` | Soft delete biodata profile | Profile owner + Admin |
| `GET` | `/biodata/search` | Search biodata profiles | Any logged-in user (shows active profiles) |

---

### **🔵 PHOTO MANAGEMENT**

#### **🟢 USER LOGIN REQUIRED**

| Method | Endpoint | Description | Who Can Access |
|--------|----------|-------------|----------------|
| `POST` | `/biodata/{profile_id}/photos` | Upload photo to profile | Profile owner + Admin |
| `GET` | `/biodata/{profile_id}/photos` | Get all photos for profile | Any logged-in user |
| `PATCH` | `/biodata/{profile_id}/photos/{photo_index}` | Update photo metadata | Profile owner + Admin |
| `POST` | `/biodata/{profile_id}/photos/replace/{photo_index}` | Replace existing photo | Profile owner + Admin |
| `PATCH` | `/biodata/{profile_id}/photos/reorder` | Reorder photos | Profile owner + Admin |
| `DELETE` | `/biodata/{profile_id}/photos/{photo_index}` | Delete specific photo | Profile owner + Admin |

---

### **🔵 CONTACT INFORMATION**

#### **🟢 USER LOGIN REQUIRED**

| Method | Endpoint | Description | Who Can Access |
|--------|----------|-------------|----------------|
| `PATCH` | `/biodata/{profile_id}/contact` | Update contact information | Profile owner + Admin |
| `GET` | `/biodata/{profile_id}/contact` | Get contact information | Any logged-in user |
| `DELETE` | `/biodata/{profile_id}/contact` | Delete contact information | Profile owner + Admin |

---

### **🔵 EDUCATION INFORMATION**

#### **🟢 USER LOGIN REQUIRED**

| Method | Endpoint | Description | Who Can Access |
|--------|----------|-------------|----------------|
| `PATCH` | `/biodata/{profile_id}/education` | Update education info | Profile owner + Admin |
| `GET` | `/biodata/{profile_id}/education` | Get education info | Any logged-in user |
| `DELETE` | `/biodata/{profile_id}/education` | Delete education info | Profile owner + Admin |

---

### **🔵 OCCUPATION INFORMATION**

#### **🟢 USER LOGIN REQUIRED**

| Method | Endpoint | Description | Who Can Access |
|--------|----------|-------------|----------------|
| `PATCH` | `/biodata/{profile_id}/occupation` | Update occupation info | Profile owner + Admin |
| `GET` | `/biodata/{profile_id}/occupation` | Get occupation info | Any logged-in user |
| `DELETE` | `/biodata/{profile_id}/occupation` | Delete occupation info | Profile owner + Admin |

---

### **🔵 FAMILY DETAILS**

#### **🟢 USER LOGIN REQUIRED**

| Method | Endpoint | Description | Who Can Access |
|--------|----------|-------------|----------------|
| `PATCH` | `/biodata/{profile_id}/family` | Update family details | Profile owner + Admin |
| `GET` | `/biodata/{profile_id}/family` | Get family details | Any logged-in user |

---

### **🔵 PARTNER PREFERENCES**

#### **🟢 USER LOGIN REQUIRED**

| Method | Endpoint | Description | Who Can Access |
|--------|----------|-------------|----------------|
| `PATCH` | `/biodata/{profile_id}/partner-preferences` | Update partner preferences | Profile owner + Admin |
| `GET` | `/biodata/{profile_id}/partner-preferences` | Get partner preferences | Any logged-in user |
| `DELETE` | `/biodata/{profile_id}/partner-preferences` | Delete partner preferences | Profile owner + Admin |

---

### **🔵 PHYSICAL ATTRIBUTES**

#### **🟢 USER LOGIN REQUIRED**

| Method | Endpoint | Description | Who Can Access |
|--------|----------|-------------|----------------|
| `PATCH` | `/biodata/{profile_id}/physical` | Update physical attributes | Profile owner + Admin |
| `GET` | `/biodata/{profile_id}/physical` | Get physical attributes | Any logged-in user |
| `DELETE` | `/biodata/{profile_id}/physical` | Delete physical attributes | Profile owner + Admin |

---

### **🔵 LIFESTYLE INFORMATION**

#### **🟢 USER LOGIN REQUIRED**

| Method | Endpoint | Description | Who Can Access |
|--------|----------|-------------|----------------|
| `PATCH` | `/biodata/{profile_id}/lifestyle` | Update lifestyle info | Profile owner + Admin |
| `GET` | `/biodata/{profile_id}/lifestyle` | Get lifestyle info | Any logged-in user |
| `DELETE` | `/biodata/{profile_id}/lifestyle` | Delete lifestyle info | Profile owner + Admin |

---

### **🔵 HOROSCOPE INFORMATION**

#### **🟢 USER LOGIN REQUIRED**

| Method | Endpoint | Description | Who Can Access |
|--------|----------|-------------|----------------|
| `PATCH` | `/biodata/{profile_id}/horoscope` | Update horoscope info | Profile owner + Admin |
| `GET` | `/biodata/{profile_id}/horoscope` | Get horoscope info | Any logged-in user |
| `DELETE` | `/biodata/{profile_id}/horoscope` | Delete horoscope info | Profile owner + Admin |

---

### **🔵 LANGUAGES INFORMATION**

#### **🟢 USER LOGIN REQUIRED**

| Method | Endpoint | Description | Who Can Access |
|--------|----------|-------------|----------------|
| `PATCH` | `/biodata/{profile_id}/languages` | Update languages info | Profile owner + Admin |
| `GET` | `/biodata/{profile_id}/languages` | Get languages info | Any logged-in user |
| `DELETE` | `/biodata/{profile_id}/languages` | Delete languages info | Profile owner + Admin |

---

## 🕕 **ENHANCED HINDU MATRIMONIAL FEATURES**

### **🔵 BIODATA TYPE MANAGEMENT**

#### **🟢 USER LOGIN REQUIRED**

| Method | Endpoint | Description | Who Can Access |
|--------|----------|-------------|----------------|
| `PATCH` | `/biodata/{profile_id}/upgrade-to-detailed` | Upgrade to detailed biodata | Profile owner + Admin |

---

### **🔵 DETAILED RELIGIOUS INFORMATION**

#### **🟢 USER LOGIN REQUIRED**

| Method | Endpoint | Description | Who Can Access | Notes |
|--------|----------|-------------|----------------|-------|
| `PATCH` | `/biodata/{profile_id}/detailed-religious-info` | Update detailed religious info | Profile owner + Admin | Requires detailed biodata type |
| `GET` | `/biodata/{profile_id}/detailed-religious-info` | Get detailed religious info | Any logged-in user | Public if profile active |

---

### **🔵 DETAILED ASTROLOGY**

#### **🟢 USER LOGIN REQUIRED**

| Method | Endpoint | Description | Who Can Access | Notes |
|--------|----------|-------------|----------------|-------|
| `PATCH` | `/biodata/{profile_id}/detailed-astrology` | Update detailed astrology | Profile owner + Admin | Requires detailed biodata type |
| `GET` | `/biodata/{profile_id}/detailed-astrology` | Get detailed astrology | Any logged-in user | Public if profile active |
| `POST` | `/biodata/{profile_id}/upload-kundli` | Upload Kundli PDF | Profile owner + Admin | S3 upload |

---

### **🔵 DETAILED FAMILY BACKGROUND**

#### **🟢 USER LOGIN REQUIRED**

| Method | Endpoint | Description | Who Can Access | Notes |
|--------|----------|-------------|----------------|-------|
| `PATCH` | `/biodata/{profile_id}/detailed-family-background` | Update detailed family background | Profile owner + Admin | Requires detailed biodata type |
| `POST` | `/biodata/{profile_id}/extended-family-member` | Add extended family member | Profile owner + Admin | Add to family list |
| `DELETE` | `/biodata/{profile_id}/extended-family-member/{member_index}` | Remove extended family member | Profile owner + Admin | Remove by index |

---

### **🔵 TRADITIONAL PREFERENCES**

#### **🟢 USER LOGIN REQUIRED**

| Method | Endpoint | Description | Who Can Access | Notes |
|--------|----------|-------------|----------------|-------|
| `PATCH` | `/biodata/{profile_id}/traditional-preferences` | Update traditional preferences | Profile owner + Admin | Requires detailed biodata type |
| `GET` | `/biodata/{profile_id}/traditional-preferences` | Get traditional preferences | Any logged-in user | Public if profile active |

---

### **🔵 MARRIAGE PLANNING**

#### **🟢 USER LOGIN REQUIRED**

| Method | Endpoint | Description | Who Can Access | Notes |
|--------|----------|-------------|----------------|-------|
| `PATCH` | `/biodata/{profile_id}/marriage-planning` | Update marriage planning | Profile owner + Admin | Requires detailed biodata type |
| `GET` | `/biodata/{profile_id}/marriage-planning` | Get marriage planning | Any logged-in user | Public if profile active |

---

### **🔵 DOCUMENT VERIFICATION**

#### **🟢 USER LOGIN REQUIRED**

| Method | Endpoint | Description | Who Can Access | Notes |
|--------|----------|-------------|----------------|-------|
| `PATCH` | `/biodata/{profile_id}/verification-documents` | Update verification documents | Profile owner + Admin | Sensitive data |
| `POST` | `/biodata/{profile_id}/upload-document` | Upload verification document | Profile owner + Admin | S3 upload to documents folder |
| `GET` | `/biodata/{profile_id}/verification-documents` | Get verification documents | Profile owner + Admin only | Private data only |

---

### **🔵 PROFILE ANALYTICS**

#### **🟢 USER LOGIN REQUIRED**

| Method | Endpoint | Description | Who Can Access | Notes |
|--------|----------|-------------|----------------|-------|
| `GET` | `/biodata/{profile_id}/analytics` | Get profile analytics | Profile owner only | Private analytics data |

#### **🟡 PUBLIC (NO AUTH)**

| Method | Endpoint | Description | Who Can Access | Notes |
|--------|----------|-------------|----------------|-------|
| `PATCH` | `/biodata/{profile_id}/increment-view` | Increment profile view | Anyone | Public analytics tracking |

---

## 🔴 **ADMIN-ONLY ENDPOINTS**

### **🔵 PROFILE VERIFICATION**

| Method | Endpoint | Description | Who Can Access |
|--------|----------|-------------|----------------|
| `PATCH` | `/biodata/{profile_id}/verify` | Verify profile | Admin only (`role: "admin"`) |
| `PATCH` | `/biodata/{profile_id}/unverify` | Remove verification | Admin only (`role: "admin"`) |

---

### **🔵 PROFILE MANAGEMENT**

| Method | Endpoint | Description | Who Can Access |
|--------|----------|-------------|----------------|
| `DELETE` | `/biodata/{profile_id}/permanent` | Permanently delete profile | Admin only (`role: "admin"`) |
| `GET` | `/biodata/stats/overview` | Get biodata statistics | Admin only (`role: "admin"`) |

---

### **🔵 ADMIN DASHBOARD**

| Method | Endpoint | Description | Who Can Access |
|--------|----------|-------------|----------------|
| `GET` | `/admin/biodata/detailed-profiles` | Get all detailed profiles | Admin only (`role: "admin"`) |
| `PATCH` | `/admin/biodata/{profile_id}/verification-status` | Update verification status | Admin only (`role: "admin"`) |

---

## 📊 **Summary by Authentication Level**

### **🟢 User Login Required (role: "user" or "admin")**
- **Total Endpoints**: 43
- **Basic CRUD**: 31 endpoints
- **Enhanced Features**: 12 endpoints

### **🔴 Admin Only (role: "admin")**
- **Total Endpoints**: 6
- **Verification Management**: 2 endpoints
- **Profile Management**: 2 endpoints  
- **Admin Dashboard**: 2 endpoints

### **🟡 Public (No Authentication)**
- **Total Endpoints**: 1
- **Analytics Tracking**: 1 endpoint

---

## 🔐 **Access Control Implementation**

```python
# Profile Owner Check
if profile.get("user_id") != current_user.username and current_user.role != "admin":
    raise HTTPException(status_code=403, detail="Access denied")

# Admin Only Check  
if current_user.role != "admin":
    raise HTTPException(status_code=403, detail="Admin access required")

# Owner Only Check
if profile.get("user_id") != current_user.username:
    raise HTTPException(status_code=403, detail="Access denied")
```

---

## 🎯 **Total API Coverage**

- **🟢 User Endpoints**: 43
- **🔴 Admin Endpoints**: 6  
- **🟡 Public Endpoints**: 1
- **📋 Total Endpoints**: **50**

This comprehensive biodata management system provides robust authentication and authorization following your FastAPI project's user model with "user" and "admin" roles! 🚀