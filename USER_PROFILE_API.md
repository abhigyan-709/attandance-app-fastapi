# User Profile Management API Documentation

## Overview
This document provides comprehensive information about the User Profile Management APIs, including profile updates and profile picture management.

## Authentication
All profile-related endpoints require JWT authentication. Include the JWT token in the Authorization header:
```
Authorization: Bearer <your_jwt_token>
```

## API Endpoints

### 1. Update User Profile
**Endpoint:** `PATCH /users/profile`
**Description:** Update current user's profile information
**Authentication:** Required
**Request Body:** UserProfileUpdate model

#### Fields Available for Update:
- `first_name` (string, optional): User's first name
- `last_name` (string, optional): User's last name  
- `email` (string, optional): User's email address (must be unique)
- `city` (string, optional): User's city
- `phone_number` (string, optional): User's phone number
- `state` (string, optional): User's state
- `pincode` (string, optional): User's postal/zip code
- `profile_picture_url` (string, optional): User's profile picture URL

#### cURL Examples:

##### Update Complete Profile
```bash
curl -X PATCH "http://localhost:8000/users/profile" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -d '{
    "first_name": "Rahul",
    "last_name": "Kumar",
    "email": "rahul.kumar@example.com",
    "city": "Patna",
    "phone_number": "+91-9876543210",
    "state": "Bihar",
    "pincode": "800001"
  }'
```

##### Update Only Phone Number and State
```bash
curl -X PATCH "http://localhost:8000/users/profile" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -d '{
    "phone_number": "+91-9876543210",
    "state": "Bihar"
  }'
```

##### Update Only Email
```bash
curl -X PATCH "http://localhost:8000/users/profile" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -d '{
    "email": "newemail@example.com"
  }'
```

##### Update Address Information
```bash
curl -X PATCH "http://localhost:8000/users/profile" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -d '{
    "city": "Muzaffarpur",
    "state": "Bihar",
    "pincode": "842001"
  }'
```

#### Response Format:
```json
{
  "message": "Profile updated successfully",
  "user": {
    "_id": "user_object_id",
    "username": "abhigkumar",
    "first_name": "Rahul",
    "last_name": "Kumar",
    "email": "rahul.kumar@example.com",
    "city": "Patna",
    "phone_number": "+91-9876543210",
    "state": "Bihar",
    "pincode": "800001",
    "profile_picture_url": "https://projectdevops-blogs-new.s3.ap-south-1.amazonaws.com/profile-pictures/user123_profile.jpg",
    "role": "user",
    "is_active": true,
    "updated_at": "2025-10-02T10:30:00"
  }
}
```

### 2. Get User Profile
**Endpoint:** `GET /users/profile`
**Description:** Get current user's complete profile information
**Authentication:** Required

#### cURL Example:
```bash
curl -X GET "http://localhost:8000/users/profile" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

#### Response Format:
```json
{
  "_id": "user_object_id",
  "username": "abhigkumar",
  "first_name": "Rahul", 
  "last_name": "Kumar",
  "email": "rahul.kumar@example.com",
  "city": "Patna",
  "phone_number": "+91-9876543210",
  "state": "Bihar", 
  "pincode": "800001",
  "profile_picture_url": "https://projectdevops-blogs-new.s3.ap-south-1.amazonaws.com/profile-pictures/user123_profile.jpg",
  "role": "user",
  "is_active": true,
  "created_at": "2025-10-01T08:00:00",
  "updated_at": "2025-10-02T10:30:00"
}
```

### 3. Upload Profile Picture
**Endpoint:** `POST /users/profile/upload-picture`
**Description:** Upload user's profile picture to S3
**Authentication:** Required
**Content-Type:** `multipart/form-data`

#### cURL Example:
```bash
curl -X POST "http://localhost:8000/users/profile/upload-picture" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -F "profile_picture=@/path/to/your/image.jpg"
```

#### File Requirements:
- **Allowed formats**: JPG, JPEG, PNG, GIF, WebP
- **Maximum size**: 5MB
- **Automatic optimization**: Images are stored with cache headers for performance

#### Response Format:
```json
{
  "message": "Profile picture uploaded successfully",
  "profile_picture_url": "https://projectdevops-blogs-new.s3.ap-south-1.amazonaws.com/profile-pictures/abhigkumar_uuid.jpg"
}
```

### 4. Delete Profile Picture
**Endpoint:** `DELETE /users/profile/delete-picture`
**Description:** Delete user's profile picture from S3
**Authentication:** Required

#### cURL Example:
```bash
curl -X DELETE "http://localhost:8000/users/profile/delete-picture" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

#### Response Format:
```json
{
  "message": "Profile picture deleted successfully"
}
```

## Error Responses

### 400 Bad Request - No Fields to Update
```json
{
  "detail": "No valid fields provided for update"
}
```

### 400 Bad Request - Email Already Exists
```json
{
  "detail": "Email is already registered to another user"
}
```

### 401 Unauthorized - Invalid or Missing Token
```json
{
  "detail": "Could not validate credentials"
}
```

### 404 Not Found - User Not Found
```json
{
  "detail": "User not found"
}
```

### 422 Validation Error - Invalid Data Format
```json
{
  "detail": [
    {
      "type": "string_type",
      "loc": ["body", "email"],
      "msg": "Input should be a valid string",
      "input": 12345
    }
  ]
}
```

## Complete Testing Workflow

### Step 1: User Registration
First, register a new user (this will provide the missing first_name and last_name):
```bash
curl -X POST "http://localhost:8000/register/" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser123",
    "first_name": "Test",
    "last_name": "User", 
    "email": "testuser@example.com",
    "password": "password123",
    "city": "Delhi",
    "role": "user",
    "is_active": true
  }'
```

### Step 2: User Login
```bash
curl -X POST "http://localhost:8000/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=testuser123&password=password123"
```

### Step 3: Update Profile with Token
```bash
curl -X PATCH "http://localhost:8000/users/profile" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN_FROM_STEP_2" \
  -d '{
    "phone_number": "+91-9999999999",
    "state": "Delhi",
    "pincode": "110001"
  }'
```

### Step 4: Get Updated Profile
```bash
curl -X GET "http://localhost:8000/users/profile" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

## Notes

1. **Partial Updates**: You can update any combination of the available fields. Only provided fields will be updated.

2. **Email Validation**: The system ensures email uniqueness across all users.

3. **Security**: Password is never returned in profile responses for security.

4. **Timestamps**: The `updated_at` field is automatically set when profile is updated.

5. **Database Storage**: New fields (phone_number, state, pincode) are stored directly in the user document.

6. **Backward Compatibility**: Existing users without these new fields will have them set to null until updated.

## HTTP Status Codes

- **200 OK**: Profile updated/retrieved successfully
- **400 Bad Request**: Invalid request data or business logic error
- **401 Unauthorized**: Authentication required or invalid token
- **404 Not Found**: User not found
- **422 Unprocessable Entity**: Validation errors in request data