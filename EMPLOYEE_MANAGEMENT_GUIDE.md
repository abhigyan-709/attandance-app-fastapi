# Employee Management System - API Documentation

## Overview
Complete employee management system for Gobarsahi Times News with file uploads, unique ID generation, QR code generation for eyecards, and role-based access control.

## Access Control

### Admin (Full Access)
- ✅ Create employees
- ✅ Update employees
- ✅ View all employees
- ✅ **Delete employees** (only admin)
- ✅ Generate QR codes
- ✅ View statistics

### Moderator (Limited Access)
- ✅ Create employees
- ✅ Update employees
- ✅ View all employees
- ❌ **Cannot delete** employees
- ✅ Generate QR codes
- ✅ View statistics

## Employee Model

### Required Fields
```json
{
  "name": "Raj Kumar Singh",
  "fathers_name": "Ram Kumar Singh",
  "mothers_name": "Sita Devi",
  "email": "raj.kumar@example.com",           // Unique
  "phone_number": "9876543210",               // Unique
  "district": "Muzaffarpur",
  "village": "Gobarsahi",
  "address": "Ward No. 5, Near School, Gobarsahi, Muzaffarpur",
  "aadhar_number": "123456789012",            // Unique, 12 digits
  "position": "Field Reporter",
  "employment_area_type": "ground",           // ground, remote, office
  "employment_area_location": "Muzaffarpur District",  // Required if ground
  "employment_date": "2024-01-15",
  "equipment_alloted": ["Camera", "Mic", "Eyecard"]
}
```

### File Uploads (Required)
- **resume_pdf**: Resume in PDF format
- **passport_photo**: Passport size photo (JPG/PNG)
- **aadhar_front**: Aadhar card front image
- **aadhar_back**: Aadhar card back image

All files uploaded to S3: `projectdevops-blogs-new/employees/`

### Auto-Generated Fields
- **employee_id**: Format `GTNE-YYYY-XXX` (e.g., `GTNE-2024-001`)
  - GTNE = Gobarsahi Times News Employee
  - YYYY = Current year
  - XXX = Sequential number (001, 002, 003...)

### Optional Fields
- **date_of_leaving**: Date when employee left (marks as inactive)
- **qr_code_url**: Generated after QR code creation

## API Endpoints

### Base URL
```
Production: https://api.projectdevops.in/api
Local: http://localhost:8000/api
```

### Authentication
All endpoints require JWT token in Authorization header:
```
Authorization: Bearer <your_jwt_token>
```

---

## 1. Create Employee

**Endpoint:** `POST /api/employees`

**Access:** Admin, Moderator

**Content-Type:** `multipart/form-data`

**Form Fields:**
```
name: Raj Kumar Singh
fathers_name: Ram Kumar Singh
mothers_name: Sita Devi
email: raj.kumar@example.com
phone_number: 9876543210
district: Muzaffarpur
village: Gobarsahi
address: Ward No. 5, Near School, Gobarsahi
aadhar_number: 123456789012
position: Field Reporter
employment_area_type: ground
employment_area_location: Muzaffarpur District
employment_date: 2024-01-15
equipment_alloted: ["Camera", "Mic", "Eyecard"]
```

**Files:**
```
resume_pdf: <file>
passport_photo: <file>
aadhar_front: <file>
aadhar_back: <file>
```

**cURL Example:**
```bash
curl -X POST "https://api.projectdevops.in/api/employees" \
  -H "Authorization: Bearer $TOKEN" \
  -F "name=Raj Kumar Singh" \
  -F "fathers_name=Ram Kumar Singh" \
  -F "mothers_name=Sita Devi" \
  -F "email=raj.kumar@example.com" \
  -F "phone_number=9876543210" \
  -F "district=Muzaffarpur" \
  -F "village=Gobarsahi" \
  -F "address=Ward No. 5, Near School, Gobarsahi, Muzaffarpur" \
  -F "aadhar_number=123456789012" \
  -F "position=Field Reporter" \
  -F "employment_area_type=ground" \
  -F "employment_area_location=Muzaffarpur District" \
  -F "employment_date=2024-01-15" \
  -F 'equipment_alloted=["Camera", "Mic", "Eyecard"]' \
  -F "resume_pdf=@resume.pdf" \
  -F "passport_photo=@photo.jpg" \
  -F "aadhar_front=@aadhar_front.jpg" \
  -F "aadhar_back=@aadhar_back.jpg"
```

**Success Response (201):**
```json
{
  "_id": "676a1b2c3d4e5f6g7h8i9j0k",
  "employee_id": "GTNE-2024-001",
  "name": "Raj Kumar Singh",
  "fathers_name": "Ram Kumar Singh",
  "mothers_name": "Sita Devi",
  "email": "raj.kumar@example.com",
  "phone_number": "9876543210",
  "district": "Muzaffarpur",
  "village": "Gobarsahi",
  "address": "Ward No. 5, Near School, Gobarsahi, Muzaffarpur",
  "aadhar_number": "123456789012",
  "resume_url": "https://projectdevops-blogs-new.s3.ap-south-1.amazonaws.com/employees/resumes/...",
  "passport_photo_url": "https://projectdevops-blogs-new.s3.ap-south-1.amazonaws.com/employees/photos/...",
  "aadhar_front_url": "https://projectdevops-blogs-new.s3.ap-south-1.amazonaws.com/employees/aadhar/...",
  "aadhar_back_url": "https://projectdevops-blogs-new.s3.ap-south-1.amazonaws.com/employees/aadhar/...",
  "position": "Field Reporter",
  "employment_area_type": "ground",
  "employment_area_location": "Muzaffarpur District",
  "employment_date": "2024-01-15",
  "date_of_leaving": null,
  "equipment_alloted": ["Camera", "Mic", "Eyecard"],
  "qr_code_url": null,
  "is_active": true,
  "created_at": "2024-12-17T10:30:00",
  "updated_at": "2024-12-17T10:30:00",
  "created_by": "admin"
}
```

**Error Responses:**
- `400`: Validation error, duplicate email/phone/aadhar
- `403`: Insufficient permissions
- `500`: Server error, file upload failed

---

## 2. Get All Employees

**Endpoint:** `GET /api/employees`

**Access:** Admin, Moderator

**Query Parameters:**
- `page` (default: 1): Page number
- `limit` (default: 10, max: 100): Items per page
- `is_active` (optional): Filter by active status
- `district` (optional): Filter by district name
- `position` (optional): Filter by position
- `employment_area_type` (optional): ground, remote, office

**Examples:**
```bash
# Get all employees (page 1)
curl "https://api.projectdevops.in/api/employees?page=1&limit=10" \
  -H "Authorization: Bearer $TOKEN"

# Get only active employees
curl "https://api.projectdevops.in/api/employees?is_active=true" \
  -H "Authorization: Bearer $TOKEN"

# Filter by district
curl "https://api.projectdevops.in/api/employees?district=Muzaffarpur" \
  -H "Authorization: Bearer $TOKEN"

# Filter by employment area
curl "https://api.projectdevops.in/api/employees?employment_area_type=ground" \
  -H "Authorization: Bearer $TOKEN"
```

**Success Response (200):**
```json
{
  "employees": [
    {
      "_id": "676a...",
      "employee_id": "GTNE-2024-001",
      "name": "Raj Kumar Singh",
      // ... full employee details
    }
  ],
  "total": 25,
  "page": 1,
  "limit": 10,
  "total_pages": 3
}
```

---

## 3. Get Employee by ID

**Endpoint:** `GET /api/employees/{employee_id}`

**Access:** Admin, Moderator

**Example:**
```bash
curl "https://api.projectdevops.in/api/employees/676a1b2c3d4e5f6g7h8i9j0k" \
  -H "Authorization: Bearer $TOKEN"
```

**Success Response (200):** Full employee object

---

## 4. Search by Employee ID

**Endpoint:** `GET /api/employees/search/by-employee-id/{emp_id}`

**Access:** Admin, Moderator

**Example:**
```bash
# Search by GTNE ID
curl "https://api.projectdevops.in/api/employees/search/by-employee-id/GTNE-2024-001" \
  -H "Authorization: Bearer $TOKEN"
```

**Success Response (200):** Full employee object

---

## 5. Update Employee

**Endpoint:** `PUT /api/employees/{employee_id}`

**Access:** Admin, Moderator

**Content-Type:** `multipart/form-data`

**All fields optional** - only send fields to update

**Form Fields:**
```
name: Updated Name                     (optional)
email: newemail@example.com           (optional, must be unique)
phone_number: 9876543211              (optional, must be unique)
position: Senior Reporter             (optional)
date_of_leaving: 2024-12-31          (optional, marks as inactive)
equipment_alloted: ["Camera", "Mic"]  (optional)
is_active: false                      (optional)
```

**Files (optional):**
```
resume_pdf: <new_file>
passport_photo: <new_file>
aadhar_front: <new_file>
aadhar_back: <new_file>
```

**Example - Update Position:**
```bash
curl -X PUT "https://api.projectdevops.in/api/employees/676a..." \
  -H "Authorization: Bearer $TOKEN" \
  -F "position=Senior Field Reporter"
```

**Example - Mark Employee Left:**
```bash
curl -X PUT "https://api.projectdevops.in/api/employees/676a..." \
  -H "Authorization: Bearer $TOKEN" \
  -F "date_of_leaving=2024-12-31" \
  -F "is_active=false"
```

**Success Response (200):** Updated employee object

---

## 6. Delete Employee

**Endpoint:** `DELETE /api/employees/{employee_id}`

**Access:** ⚠️ **Admin ONLY** (Moderators CANNOT delete)

**Example:**
```bash
curl -X DELETE "https://api.projectdevops.in/api/employees/676a..." \
  -H "Authorization: Bearer $TOKEN"
```

**Success Response (200):**
```json
{
  "message": "Employee GTNE-2024-001 deleted successfully"
}
```

**Error Response (403) for Moderators:**
```json
{
  "detail": "Admin access required"
}
```

---

## 7. Generate QR Code

**Endpoint:** `POST /api/employees/{employee_id}/generate-qr`

**Access:** Admin, Moderator

**Description:** Generates QR code containing employee data for eyecard printing

**QR Code Data Includes:**
- Employee ID
- Name
- Position
- Phone
- Email
- Employment Area
- Photo URL

**Example:**
```bash
curl -X POST "https://api.projectdevops.in/api/employees/676a.../generate-qr" \
  -H "Authorization: Bearer $TOKEN"
```

**Success Response (200):**
```json
{
  "employee_id": "GTNE-2024-001",
  "qr_code_url": "https://projectdevops-blogs-new.s3.ap-south-1.amazonaws.com/employees/qrcodes/GTNE-2024-001.png",
  "qr_code_data": "{\"employee_id\":\"GTNE-2024-001\",\"name\":\"Raj Kumar Singh\",\"position\":\"Field Reporter\",\"phone\":\"9876543210\",\"email\":\"raj.kumar@example.com\",\"employment_area\":\"ground\",\"photo_url\":\"https://...\"}",
  "generated_at": "2024-12-17T11:00:00"
}
```

**QR Code File:** Saved to S3 at `employees/qrcodes/{employee_id}.png`

---

## 8. Get QR Code

**Endpoint:** `GET /api/employees/{employee_id}/qr-code`

**Access:** Admin, Moderator

**Example:**
```bash
curl "https://api.projectdevops.in/api/employees/676a.../qr-code" \
  -H "Authorization: Bearer $TOKEN"
```

**Success Response (200):**
```json
{
  "qr_code_url": "https://projectdevops-blogs-new.s3.ap-south-1.amazonaws.com/employees/qrcodes/GTNE-2024-001.png"
}
```

---

## 9. Get Statistics

**Endpoint:** `GET /api/employees/stats/overview`

**Access:** Admin, Moderator

**Example:**
```bash
curl "https://api.projectdevops.in/api/employees/stats/overview" \
  -H "Authorization: Bearer $TOKEN"
```

**Success Response (200):**
```json
{
  "total_employees": 50,
  "active_employees": 45,
  "inactive_employees": 5,
  "by_area": {
    "ground": 30,
    "remote": 10,
    "office": 10
  }
}
```

---

## Eyecard Printing Workflow

### 1. Create Employee Profile
```bash
POST /api/employees
# Upload all required documents and details
```

### 2. Generate QR Code
```bash
POST /api/employees/{id}/generate-qr
# QR code uploaded to S3
```

### 3. Download QR Code & Photo
```bash
GET /api/employees/{id}/qr-code
# Get QR code URL

GET /api/employees/{id}
# Get passport_photo_url from response
```

### 4. Design Eyecard Template
**Front Side:**
- Company Logo (Gobarsahi Times)
- Employee Photo (passport_photo_url)
- Name
- Employee ID (GTNE-2024-001)
- Position

**Back Side:**
- QR Code (scan for full details)
- Contact Info
- Emergency Contact
- Valid Until Date

### 5. Print Eyecard
- Download QR code PNG and photo from S3
- Use design software (Photoshop/Canva)
- Print on PVC card stock

---

## Equipment Types

Available equipment that can be allotted:
- **Camera**: Professional camera for field reporting
- **Mic**: Microphone for interviews
- **Sticker**: Company stickers/branding
- **Eyecard**: Employee identification card

**Example JSON:**
```json
{
  "equipment_alloted": ["Camera", "Mic", "Eyecard"]
}
```

---

## Employment Areas

### Ground Deployment
```json
{
  "employment_area_type": "ground",
  "employment_area_location": "Muzaffarpur District"  // Required
}
```
Field reporters covering specific geographic areas

### Remote Work
```json
{
  "employment_area_type": "remote",
  "employment_area_location": null  // Optional
}
```
Work from home positions

### Office Work
```json
{
  "employment_area_type": "office",
  "employment_area_location": "Gobarsahi Head Office"  // Optional
}
```
Office-based roles

---

## Validation Rules

### Unique Constraints
- **Email**: Must be unique across all employees
- **Phone Number**: Must be unique across all employees
- **Aadhar Number**: Must be unique across all employees

### Format Validations
- **Phone Number**: 10-15 digits (with optional +)
- **Aadhar Number**: Exactly 12 digits
- **Email**: Valid email format

### File Validations
- **Resume**: PDF format
- **Photos/Aadhar**: JPG, PNG formats
- **Max File Size**: Handled by S3 (typically 10MB limit)

---

## Error Handling

### Common Errors

**400 - Validation Error:**
```json
{
  "detail": "Email already exists"
}
```

**403 - Permission Denied:**
```json
{
  "detail": "Admin access required"
}
```
(Moderator trying to delete)

**404 - Not Found:**
```json
{
  "detail": "Employee not found"
}
```

**500 - Server Error:**
```json
{
  "detail": "File upload failed: Connection timeout"
}
```

---

## Frontend Integration Examples

### Create Employee Form (React/Next.js)

```javascript
const handleSubmit = async (formData) => {
  const data = new FormData();
  
  // Add text fields
  data.append('name', formData.name);
  data.append('fathers_name', formData.fathersName);
  data.append('mothers_name', formData.mothersName);
  data.append('email', formData.email);
  data.append('phone_number', formData.phone);
  data.append('district', formData.district);
  data.append('village', formData.village);
  data.append('address', formData.address);
  data.append('aadhar_number', formData.aadhar);
  data.append('position', formData.position);
  data.append('employment_area_type', formData.areaType);
  data.append('employment_area_location', formData.location);
  data.append('employment_date', formData.joiningDate);
  data.append('equipment_alloted', JSON.stringify(formData.equipment));
  
  // Add files
  data.append('resume_pdf', formData.resumeFile);
  data.append('passport_photo', formData.photoFile);
  data.append('aadhar_front', formData.aadharFrontFile);
  data.append('aadhar_back', formData.aadharBackFile);
  
  const response = await fetch('/api/employees', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`
    },
    body: data
  });
  
  const result = await response.json();
  if (response.ok) {
    // Success - show employee ID
    alert(`Employee created: ${result.employee_id}`);
  }
};
```

### Generate & Display QR Code

```javascript
const generateQRCode = async (employeeId) => {
  const response = await fetch(`/api/employees/${employeeId}/generate-qr`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`
    }
  });
  
  const result = await response.json();
  
  // Display QR code
  return result.qr_code_url;
};

// In component
<div className="qr-code-section">
  <h3>Scan for Details</h3>
  <img src={qrCodeUrl} alt="Employee QR Code" />
  <button onClick={() => downloadQRCode(qrCodeUrl)}>
    Download QR Code
  </button>
</div>
```

### Employee List with Filters

```javascript
const fetchEmployees = async (filters) => {
  const params = new URLSearchParams({
    page: filters.page,
    limit: 20,
    ...(filters.isActive && { is_active: filters.isActive }),
    ...(filters.district && { district: filters.district }),
    ...(filters.position && { position: filters.position })
  });
  
  const response = await fetch(`/api/employees?${params}`, {
    headers: {
      'Authorization': `Bearer ${token}`
    }
  });
  
  return await response.json();
};
```

---

## Best Practices

1. **File Size Optimization**
   - Compress photos before upload (max 500KB recommended)
   - PDF resume should be under 2MB

2. **QR Code Generation**
   - Generate QR code immediately after employee creation
   - Store QR code URL in database for quick access

3. **Data Privacy**
   - Aadhar numbers are sensitive - ensure HTTPS
   - Restrict access to admin/moderator only
   - Don't expose employee data in public APIs

4. **Equipment Tracking**
   - Update equipment_alloted when issuing/returning items
   - Use consistent naming (Camera, not camera or CAMERA)

5. **Employee Status**
   - Set date_of_leaving when employee leaves
   - Automatically mark as inactive
   - Keep records for audit trail (don't delete unless necessary)

---

## Production Deployment Checklist

- [ ] Install dependencies: `pip install qrcode pillow`
- [ ] Verify S3 bucket access (projectdevops-blogs-new)
- [ ] Ensure AWS credentials in environment
- [ ] Test file uploads to S3
- [ ] Test QR code generation
- [ ] Verify role-based access (admin vs moderator)
- [ ] Test unique constraints (email, phone, aadhar)
- [ ] Create backup system for employee data
- [ ] Set up monitoring for failed uploads

---

## Database Collection

**Collection Name:** `employees`

**Indexes (Recommended):**
```javascript
db.employees.createIndex({ "employee_id": 1 }, { unique: true });
db.employees.createIndex({ "email": 1 }, { unique: true });
db.employees.createIndex({ "phone_number": 1 }, { unique: true });
db.employees.createIndex({ "aadhar_number": 1 }, { unique: true });
db.employees.createIndex({ "is_active": 1 });
db.employees.createIndex({ "district": 1 });
db.employees.createIndex({ "created_at": -1 });
```

---

## Support

For issues or questions:
- **Email**: connect@projectdevops.in
- **API Docs**: https://api.projectdevops.in/docs
- **GitHub Issues**: Create issue in project repository
