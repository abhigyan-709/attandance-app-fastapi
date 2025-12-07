# Survey Form API - Integration Guide

## Overview
Survey form system for the news platform with all optional fields. Public submission endpoint with admin management capabilities.

## API Base URL
```
Production: https://api.projectdevops.in
Local: http://localhost:8000
```

---

## API Endpoints

### 1. Submit Survey Form (Public - No Auth Required)

**Endpoint:** `POST /api/survey`

**Description:** Public endpoint for users to submit survey responses. All fields are optional.

**Request Body:**
```json
{
  "name": "John Doe",
  "age": 30,
  "address": "123 Main Street",
  "city": "Mumbai",
  "pincode": "400001",
  "whatsapp_number": "+919876543210",
  "phone_number": "+919876543210",
  "email": "john.doe@example.com"
}
```

**Response (Success - 200):**
```json
{
  "message": "Survey submitted successfully",
  "survey_id": "674a5f8c9d8e7f6b5a4c3d2e",
  "submitted_at": "2025-12-07T10:30:00"
}
```

**cURL Example:**
```bash
curl -X POST "https://api.projectdevops.in/api/survey" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "John Doe",
    "age": 30,
    "city": "Mumbai",
    "email": "john@example.com"
  }'
```

---

### 2. Get All Surveys (Admin Only)

**Endpoint:** `GET /api/survey`

**Description:** Retrieve all survey submissions. Requires admin authentication.

**Headers:**
```
Authorization: Bearer <admin_jwt_token>
```

**Response (Success - 200):**
```json
[
  {
    "id": "674a5f8c9d8e7f6b5a4c3d2e",
    "name": "John Doe",
    "age": 30,
    "address": "123 Main Street",
    "city": "Mumbai",
    "pincode": "400001",
    "whatsapp_number": "+919876543210",
    "phone_number": "+919876543210",
    "email": "john.doe@example.com",
    "submitted_at": "2025-12-07T10:30:00"
  }
]
```

**cURL Example:**
```bash
curl -X GET "https://api.projectdevops.in/api/survey" \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN"
```

---

### 3. Get Survey by ID (Admin Only)

**Endpoint:** `GET /api/survey/{survey_id}`

**Description:** Retrieve a specific survey by ID. Requires admin authentication.

**Headers:**
```
Authorization: Bearer <admin_jwt_token>
```

**Response (Success - 200):**
```json
{
  "id": "674a5f8c9d8e7f6b5a4c3d2e",
  "name": "John Doe",
  "age": 30,
  "address": "123 Main Street",
  "city": "Mumbai",
  "pincode": "400001",
  "whatsapp_number": "+919876543210",
  "phone_number": "+919876543210",
  "email": "john.doe@example.com",
  "submitted_at": "2025-12-07T10:30:00"
}
```

**cURL Example:**
```bash
curl -X GET "https://api.projectdevops.in/api/survey/674a5f8c9d8e7f6b5a4c3d2e" \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN"
```

---

### 4. Delete Survey (Admin Only)

**Endpoint:** `DELETE /api/survey/{survey_id}`

**Description:** Delete a survey submission. Requires admin authentication.

**Headers:**
```
Authorization: Bearer <admin_jwt_token>
```

**Response (Success - 200):**
```json
{
  "message": "Survey deleted successfully",
  "survey_id": "674a5f8c9d8e7f6b5a4c3d2e"
}
```

**cURL Example:**
```bash
curl -X DELETE "https://api.projectdevops.in/api/survey/674a5f8c9d8e7f6b5a4c3d2e" \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN"
```

---

### 5. Get Survey Statistics (Admin Only)

**Endpoint:** `GET /api/survey/stats/summary`

**Description:** Get survey submission statistics including total count, top cities, and recent submissions. Requires admin authentication.

**Headers:**
```
Authorization: Bearer <admin_jwt_token>
```

**Response (Success - 200):**
```json
{
  "total_surveys": 150,
  "top_cities": [
    {"city": "Mumbai", "count": 45},
    {"city": "Delhi", "count": 38},
    {"city": "Bangalore", "count": 32}
  ],
  "recent_submissions": 5
}
```

**cURL Example:**
```bash
curl -X GET "https://api.projectdevops.in/api/survey/stats/summary" \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN"
```

---

## UI Development Guide

### Frontend Integration

#### 1. Survey Submission Form (Public Page)

**Location:** Can be integrated into news website footer, separate page, or popup modal

**HTML Structure Example:**
```html
<form id="surveyForm">
  <div class="form-group">
    <label for="name">Name</label>
    <input type="text" id="name" name="name" class="form-control">
  </div>
  
  <div class="form-group">
    <label for="age">Age</label>
    <input type="number" id="age" name="age" min="0" max="150" class="form-control">
  </div>
  
  <div class="form-group">
    <label for="address">Address</label>
    <textarea id="address" name="address" class="form-control" rows="3"></textarea>
  </div>
  
  <div class="form-group">
    <label for="city">City</label>
    <input type="text" id="city" name="city" class="form-control">
  </div>
  
  <div class="form-group">
    <label for="pincode">Pincode</label>
    <input type="text" id="pincode" name="pincode" class="form-control">
  </div>
  
  <div class="form-group">
    <label for="whatsapp">WhatsApp Number</label>
    <input type="tel" id="whatsapp" name="whatsapp_number" class="form-control" 
           placeholder="+91XXXXXXXXXX">
  </div>
  
  <div class="form-group">
    <label for="phone">Phone Number</label>
    <input type="tel" id="phone" name="phone_number" class="form-control" 
           placeholder="+91XXXXXXXXXX">
  </div>
  
  <div class="form-group">
    <label for="email">Email</label>
    <input type="email" id="email" name="email" class="form-control">
  </div>
  
  <button type="submit" class="btn btn-primary">Submit Survey</button>
</form>

<div id="surveyMessage" style="display:none;"></div>
```

**JavaScript Integration:**
```javascript
document.getElementById('surveyForm').addEventListener('submit', async (e) => {
  e.preventDefault();
  
  // Collect form data
  const formData = {
    name: document.getElementById('name').value || null,
    age: document.getElementById('age').value ? parseInt(document.getElementById('age').value) : null,
    address: document.getElementById('address').value || null,
    city: document.getElementById('city').value || null,
    pincode: document.getElementById('pincode').value || null,
    whatsapp_number: document.getElementById('whatsapp').value || null,
    phone_number: document.getElementById('phone').value || null,
    email: document.getElementById('email').value || null
  };
  
  // Remove null values (optional, server accepts them)
  Object.keys(formData).forEach(key => {
    if (formData[key] === null || formData[key] === '') {
      delete formData[key];
    }
  });
  
  try {
    const response = await fetch('https://api.projectdevops.in/api/survey', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(formData)
    });
    
    const result = await response.json();
    
    if (response.ok) {
      // Show success message
      const messageDiv = document.getElementById('surveyMessage');
      messageDiv.textContent = 'Survey submitted successfully! Thank you for your response.';
      messageDiv.className = 'alert alert-success';
      messageDiv.style.display = 'block';
      
      // Reset form
      document.getElementById('surveyForm').reset();
      
      // Hide message after 5 seconds
      setTimeout(() => {
        messageDiv.style.display = 'none';
      }, 5000);
    } else {
      throw new Error(result.detail || 'Submission failed');
    }
  } catch (error) {
    // Show error message
    const messageDiv = document.getElementById('surveyMessage');
    messageDiv.textContent = 'Error: ' + error.message;
    messageDiv.className = 'alert alert-danger';
    messageDiv.style.display = 'block';
  }
});
```

**React/Next.js Example:**
```jsx
import { useState } from 'react';

export default function SurveyForm() {
  const [formData, setFormData] = useState({
    name: '',
    age: '',
    address: '',
    city: '',
    pincode: '',
    whatsapp_number: '',
    phone_number: '',
    email: ''
  });
  const [message, setMessage] = useState({ type: '', text: '' });
  const [loading, setLoading] = useState(false);

  const handleChange = (e) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value
    });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setMessage({ type: '', text: '' });

    // Prepare data - remove empty fields
    const submitData = {};
    Object.keys(formData).forEach(key => {
      if (formData[key]) {
        submitData[key] = key === 'age' ? parseInt(formData[key]) : formData[key];
      }
    });

    try {
      const response = await fetch('https://api.projectdevops.in/api/survey', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(submitData)
      });

      const result = await response.json();

      if (response.ok) {
        setMessage({ 
          type: 'success', 
          text: 'Survey submitted successfully! Thank you.' 
        });
        // Reset form
        setFormData({
          name: '', age: '', address: '', city: '', pincode: '',
          whatsapp_number: '', phone_number: '', email: ''
        });
      } else {
        setMessage({ type: 'error', text: result.detail || 'Submission failed' });
      }
    } catch (error) {
      setMessage({ type: 'error', text: 'Network error. Please try again.' });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="survey-form-container">
      <h2>Reader Survey</h2>
      
      {message.text && (
        <div className={`alert alert-${message.type === 'success' ? 'success' : 'danger'}`}>
          {message.text}
        </div>
      )}

      <form onSubmit={handleSubmit}>
        <div className="mb-3">
          <label htmlFor="name" className="form-label">Name</label>
          <input
            type="text"
            className="form-control"
            id="name"
            name="name"
            value={formData.name}
            onChange={handleChange}
          />
        </div>

        <div className="mb-3">
          <label htmlFor="age" className="form-label">Age</label>
          <input
            type="number"
            className="form-control"
            id="age"
            name="age"
            min="0"
            max="150"
            value={formData.age}
            onChange={handleChange}
          />
        </div>

        <div className="mb-3">
          <label htmlFor="address" className="form-label">Address</label>
          <textarea
            className="form-control"
            id="address"
            name="address"
            rows="3"
            value={formData.address}
            onChange={handleChange}
          />
        </div>

        <div className="mb-3">
          <label htmlFor="city" className="form-label">City</label>
          <input
            type="text"
            className="form-control"
            id="city"
            name="city"
            value={formData.city}
            onChange={handleChange}
          />
        </div>

        <div className="mb-3">
          <label htmlFor="pincode" className="form-label">Pincode</label>
          <input
            type="text"
            className="form-control"
            id="pincode"
            name="pincode"
            value={formData.pincode}
            onChange={handleChange}
          />
        </div>

        <div className="mb-3">
          <label htmlFor="whatsapp_number" className="form-label">WhatsApp Number</label>
          <input
            type="tel"
            className="form-control"
            id="whatsapp_number"
            name="whatsapp_number"
            placeholder="+91XXXXXXXXXX"
            value={formData.whatsapp_number}
            onChange={handleChange}
          />
        </div>

        <div className="mb-3">
          <label htmlFor="phone_number" className="form-label">Phone Number</label>
          <input
            type="tel"
            className="form-control"
            id="phone_number"
            name="phone_number"
            placeholder="+91XXXXXXXXXX"
            value={formData.phone_number}
            onChange={handleChange}
          />
        </div>

        <div className="mb-3">
          <label htmlFor="email" className="form-label">Email</label>
          <input
            type="email"
            className="form-control"
            id="email"
            name="email"
            value={formData.email}
            onChange={handleChange}
          />
        </div>

        <button type="submit" className="btn btn-primary" disabled={loading}>
          {loading ? 'Submitting...' : 'Submit Survey'}
        </button>
      </form>
    </div>
  );
}
```

---

#### 2. Admin Dashboard - Survey Management

**Survey List Page:**
```jsx
import { useState, useEffect } from 'react';

export default function SurveyAdmin() {
  const [surveys, setSurveys] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchSurveys();
    fetchStats();
  }, []);

  const fetchSurveys = async () => {
    try {
      const token = localStorage.getItem('admin_token');
      const response = await fetch('https://api.projectdevops.in/api/survey', {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      const data = await response.json();
      setSurveys(data);
    } catch (error) {
      console.error('Error fetching surveys:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchStats = async () => {
    try {
      const token = localStorage.getItem('admin_token');
      const response = await fetch('https://api.projectdevops.in/api/survey/stats/summary', {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      const data = await response.json();
      setStats(data);
    } catch (error) {
      console.error('Error fetching stats:', error);
    }
  };

  const deleteSurvey = async (surveyId) => {
    if (!confirm('Are you sure you want to delete this survey?')) return;

    try {
      const token = localStorage.getItem('admin_token');
      const response = await fetch(`https://api.projectdevops.in/api/survey/${surveyId}`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });

      if (response.ok) {
        alert('Survey deleted successfully');
        fetchSurveys();
        fetchStats();
      }
    } catch (error) {
      console.error('Error deleting survey:', error);
      alert('Failed to delete survey');
    }
  };

  if (loading) return <div>Loading...</div>;

  return (
    <div className="admin-survey-container">
      <h1>Survey Management</h1>

      {/* Statistics Card */}
      {stats && (
        <div className="stats-card">
          <div className="stat-item">
            <h3>Total Surveys</h3>
            <p>{stats.total_surveys}</p>
          </div>
          <div className="stat-item">
            <h3>Top Cities</h3>
            <ul>
              {stats.top_cities.map((city, idx) => (
                <li key={idx}>{city.city}: {city.count}</li>
              ))}
            </ul>
          </div>
        </div>
      )}

      {/* Survey List Table */}
      <div className="survey-table">
        <table className="table">
          <thead>
            <tr>
              <th>ID</th>
              <th>Name</th>
              <th>Age</th>
              <th>City</th>
              <th>Email</th>
              <th>Phone</th>
              <th>Submitted At</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {surveys.map((survey) => (
              <tr key={survey.id}>
                <td>{survey.id.substring(0, 8)}...</td>
                <td>{survey.name || '-'}</td>
                <td>{survey.age || '-'}</td>
                <td>{survey.city || '-'}</td>
                <td>{survey.email || '-'}</td>
                <td>{survey.phone_number || '-'}</td>
                <td>{new Date(survey.submitted_at).toLocaleString()}</td>
                <td>
                  <button 
                    className="btn btn-sm btn-danger"
                    onClick={() => deleteSurvey(survey.id)}
                  >
                    Delete
                  </button>
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

## Field Validation

### Client-Side Validation
- **Age**: 0-150 (optional)
- **Email**: Valid email format (optional)
- **Phone/WhatsApp**: Recommend format +91XXXXXXXXXX but no strict validation
- **All other fields**: Free text, no validation

### Server-Side Validation
- Age must be between 0 and 150 if provided
- Email must be valid format if provided
- All fields are optional - can submit empty form

---

## Error Handling

### Common Error Responses

**400 Bad Request:**
```json
{
  "detail": "Invalid survey ID format"
}
```

**403 Forbidden:**
```json
{
  "detail": "Only admins can view all surveys"
}
```

**404 Not Found:**
```json
{
  "detail": "Survey not found"
}
```

**422 Validation Error:**
```json
{
  "detail": [
    {
      "loc": ["body", "age"],
      "msg": "ensure this value is less than or equal to 150",
      "type": "value_error.number.not_le"
    }
  ]
}
```

---

## Best Practices

### UI/UX Recommendations
1. **Form Placement**: Add survey form in footer, sidebar, or as modal popup
2. **Progressive Disclosure**: Start with essential fields, expand for more details
3. **Privacy Note**: Add text like "Your information is secure and will not be shared"
4. **Thank You Message**: Show confirmation after successful submission
5. **Loading States**: Display spinner during submission
6. **Field Indicators**: Mark all fields as "Optional" to reduce friction

### Admin Dashboard Features
1. **Export to CSV**: Add export functionality for survey data
2. **Filtering**: Filter by city, date range, or presence of email
3. **Search**: Search by name, email, or phone number
4. **Pagination**: For large datasets
5. **View Details**: Modal or detail page for full survey response

### Performance
- Public endpoint has no rate limiting currently
- Consider adding client-side debouncing on submit button
- Admin endpoints paginated by default (implement if needed)

---

## Testing

### Test the API
```bash
# Test public submission
curl -X POST "http://localhost:8000/api/survey" \
  -H "Content-Type: application/json" \
  -d '{"name":"Test User","city":"Mumbai"}'

# Test admin access (replace TOKEN)
curl -X GET "http://localhost:8000/api/survey" \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN"
```

### API Documentation
Access interactive API docs at:
- Swagger UI: `https://api.projectdevops.in/docs`
- ReDoc: `https://api.projectdevops.in/redoc`

---

## Database Schema

**Collection Name:** `surveys`

**Document Structure:**
```json
{
  "_id": ObjectId("674a5f8c9d8e7f6b5a4c3d2e"),
  "name": "John Doe",
  "age": 30,
  "address": "123 Main Street",
  "city": "Mumbai",
  "pincode": "400001",
  "whatsapp_number": "+919876543210",
  "phone_number": "+919876543210",
  "email": "john.doe@example.com",
  "submitted_at": ISODate("2025-12-07T10:30:00.000Z")
}
```

---

## Support

For questions or issues:
- Email: connect@projectdevops.in
- API Documentation: https://api.projectdevops.in/docs
