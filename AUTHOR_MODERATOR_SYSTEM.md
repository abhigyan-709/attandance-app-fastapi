# Author & Moderator System Integration

## Overview
Enhanced user role system with author profiles and moderator capabilities for the news platform. Authors can create news articles with full profile attribution, while moderators can manage content.

---

## User Roles

### Available Roles
1. **Admin** - Full system access
2. **User** - Basic user with limited access
3. **Author** - Can create and manage news articles with profile attribution
4. **Moderator** - Can moderate content (admin-level content permissions)
5. **Vendor** - E-commerce vendor access

---

## Author Profile Fields

Authors have extended profile information that appears on their articles:

- `author_bio` - Biography/about text
- `author_profile_image` - Profile photo URL
- `author_designation` - Job title (e.g., "Senior Editor", "Staff Writer")
- `author_social_links` - Social media links object
- `articles_count` - Total published articles (auto-updated)

---

## API Endpoints

### Base URL
```
Production: https://api.projectdevops.in
Local: http://localhost:8000
```

---

## Author Management Endpoints

### 1. Get All Authors (Public)

**Endpoint:** `GET /authors`

**Description:** Retrieve list of all active authors with their profiles

**Response:**
```json
[
  {
    "username": "rahul_kumar",
    "full_name": "Rahul Kumar",
    "author_bio": "Senior journalist with 10 years of experience",
    "author_profile_image": "https://example.com/profile.jpg",
    "author_designation": "Senior Editor",
    "author_social_links": {
      "twitter": "https://twitter.com/example",
      "linkedin": "https://linkedin.com/in/example"
    },
    "articles_count": 45
  }
]
```

---

### 2. Get Author Profile (Public)

**Endpoint:** `GET /authors/{username}`

**Description:** Get detailed profile for specific author

**Response:**
```json
{
  "username": "rahul_kumar",
  "full_name": "Rahul Kumar",
  "email": "rahul@example.com",
  "city": "Patna",
  "author_bio": "Senior journalist with 10 years of experience",
  "author_profile_image": "https://example.com/profile.jpg",
  "author_designation": "Senior Editor",
  "author_social_links": {
    "twitter": "https://twitter.com/example"
  },
  "articles_count": 45,
  "created_at": "2025-01-15T10:30:00"
}
```

---

### 3. Update Author Profile

**Endpoint:** `PATCH /authors/{username}/profile`

**Description:** Update author profile information (author themselves or admin)

**Headers:**
```
Authorization: Bearer <jwt_token>
```

**Request Body:**
```json
{
  "author_bio": "Updated bio text",
  "author_designation": "Chief Editor",
  "author_social_links": {
    "twitter": "https://twitter.com/newhandle",
    "linkedin": "https://linkedin.com/in/profile"
  }
}
```

**Response:**
```json
{
  "message": "Author profile updated successfully"
}
```

---

### 4. Upload Author Profile Image

**Endpoint:** `POST /authors/{username}/upload-profile-image`

**Description:** Upload author profile photo to S3

**Headers:**
```
Authorization: Bearer <jwt_token>
Content-Type: multipart/form-data
```

**Request (Form Data):**
```
file: [image file]
```

**Response:**
```json
{
  "message": "Author profile image uploaded successfully",
  "image_url": "https://projectdevops-blogs-new.s3.ap-south-1.amazonaws.com/authors/username_profile_xyz.jpg"
}
```

---

## Moderator Management Endpoints

### 1. Get All Moderators (Admin Only)

**Endpoint:** `GET /moderators`

**Description:** List all users with moderator role

**Headers:**
```
Authorization: Bearer <admin_jwt_token>
```

**Response:**
```json
[
  {
    "_id": "674a5f8c9d8e7f6b5a4c3d2e",
    "username": "mod_john",
    "first_name": "John",
    "last_name": "Doe",
    "email": "john@example.com",
    "role": "moderator",
    "is_active": true
  }
]
```

---

## User Role Management

### 1. Update User Role (Admin Only)

**Endpoint:** `PATCH /users/{username}/role`

**Description:** Change user's role

**Headers:**
```
Authorization: Bearer <admin_jwt_token>
```

**Query Parameters:**
- `new_role` - One of: "user", "admin", "author", "moderator", "vendor"

**Example:**
```bash
curl -X PATCH "https://api.projectdevops.in/users/john_doe/role?new_role=author" \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN"
```

**Response:**
```json
{
  "message": "User role updated to 'author' successfully"
}
```

---

### 2. Get Users by Role (Admin Only)

**Endpoint:** `GET /users/by-role/{role}`

**Description:** Retrieve all users with specific role

**Headers:**
```
Authorization: Bearer <admin_jwt_token>
```

**Response:**
```json
{
  "role": "author",
  "count": 12,
  "users": [
    {
      "_id": "674a5f8c9d8e7f6b5a4c3d2e",
      "username": "author1",
      "first_name": "Jane",
      "last_name": "Smith",
      "role": "author",
      "articles_count": 23
    }
  ]
}
```

---

## News System Integration

### Author Attribution in News Posts

When creating news articles, author information is automatically embedded:

### Manual Author Selection (Admin/Moderator Only)

Admins and moderators can manually select which author to assign to a news article, even if they're not the one creating it.

**Create News with Custom Author:**
```bash
curl -X POST "https://api.projectdevops.in/news" \
  -H "Authorization: Bearer ADMIN_TOKEN" \
  -F "title=Breaking News" \
  -F "content=Article content..." \
  -F "custom_slug=breaking-news" \
  -F "author_username=john_author" \
  -F "file=@image.jpg"
```

**Update News Author:**
```bash
curl -X PUT "https://api.projectdevops.in/news/{news_id}" \
  -H "Authorization: Bearer ADMIN_TOKEN" \
  -F "author_username=new_author"
```

**Key Points:**
- Only admin and moderator roles can override the author
- The selected user must have "author" or "admin" role
- If no `author_username` is provided, the logged-in user is used as author
- Article counts are automatically adjusted when changing authors
- Author details are automatically fetched and embedded

**NewsPost Model (Enhanced):**
```json
{
  "_id": "674a5f8c9d8e7f6b5a4c3d2e",
  "title": "Breaking News Title",
  "content": "Article content...",
  "author_username": "rahul_kumar",
  "author_details": {
    "username": "rahul_kumar",
    "full_name": "Rahul Kumar",
    "author_profile_image": "https://example.com/profile.jpg",
    "author_designation": "Senior Editor",
    "author_bio": "Senior journalist with 10 years of experience"
  },
  "published": true,
  "created_at": "2025-12-08T10:30:00",
  "views": 150,
  "likes": 45
}
```

### Automatic Features

1. **Author Details Embedding** - Author profile automatically fetched and embedded when:
   - Creating new news post
   - Retrieving news posts (if not already embedded)

2. **Article Count Tracking** - `articles_count` automatically incremented when:
   - News post is published
   - Can be used for author leaderboards

3. **Backward Compatibility** - Existing news posts without `author_details`:
   - Will have author info fetched dynamically on retrieval
   - No data migration required

---

## Admin Features: Manual Author Assignment

### Overview
Admins and moderators can assign articles to any author, providing workflow flexibility for editorial teams.

### Use Cases
1. **Guest Posts** - Admin publishes articles written by specific authors
2. **Editorial Workflow** - Editor creates draft, assigns to staff writer
3. **Team Collaboration** - Content manager assigns articles to appropriate authors
4. **Corrections** - Fix incorrectly assigned author attributions

### How It Works

#### Creating News with Custom Author

When creating news, add `author_username` parameter:

**Form Data Parameters:**
```
title: "Article Title"
content: "Article content..."
custom_slug: "article-slug"
author_username: "target_author_username"  // Optional - Admin/Moderator only
file: [image file]
```

**Validation:**
- System verifies the target user exists
- Target user must have "author" or "admin" role
- If target user doesn't exist or isn't an author, returns 404/400 error
- Non-admin users cannot use this parameter (silently ignored)

**Example - Admin Creating Article for Author:**
```bash
curl -X POST "https://api.projectdevops.in/news" \
  -H "Authorization: Bearer ADMIN_TOKEN" \
  -H "Content-Type: multipart/form-data" \
  -F "title=Technology Trends 2025" \
  -F "content=In-depth analysis of tech trends..." \
  -F "custom_slug=tech-trends-2025" \
  -F "categories=Technology" \
  -F "author_username=rahul_kumar" \
  -F "published=true" \
  -F "file=@featured-image.jpg"
```

#### Updating Article Author

Change the author of existing articles:

**Form Data:**
```
author_username: "new_author_username"  // Admin/Moderator only
```

**Example - Changing Article Author:**
```bash
curl -X PUT "https://api.projectdevops.in/news/674a5f8c9d8e7f6b5a4c3d2e" \
  -H "Authorization: Bearer ADMIN_TOKEN" \
  -F "author_username=new_author"
```

**What Happens:**
1. Old author's `articles_count` decremented (if published)
2. New author's `articles_count` incremented (if published)
3. `author_username` field updated
4. `author_details` refreshed with new author's profile
5. Changes logged for audit trail

### Permissions

| Role | Can Create News | Can Assign to Other Authors | Can Change Existing Author |
|------|----------------|------------------------------|----------------------------|
| Admin | ✅ Yes | ✅ Yes | ✅ Yes |
| Moderator | ✅ Yes | ✅ Yes | ✅ Yes |
| Author | ✅ Yes | ❌ No (only self) | ❌ No |
| User | ❌ No | ❌ No | ❌ No |

### Error Handling

**Target Author Not Found:**
```json
{
  "detail": "Author 'unknown_user' not found"
}
```

**Target User Not an Author:**
```json
{
  "detail": "User 'john_doe' is not an author. Current role: user"
}
```

**Non-Admin Attempting Override:**
- Parameter silently ignored
- Article assigned to logged-in user
- Warning logged to server logs

### Frontend Implementation

```jsx
function CreateNewsForm({ currentUser }) {
  const [formData, setFormData] = useState({
    title: '',
    content: '',
    custom_slug: '',
    author_username: '', // Only shown for admin/moderator
  });
  
  const [authors, setAuthors] = useState([]);
  
  // Fetch all authors for dropdown (admin only)
  useEffect(() => {
    if (currentUser.role === 'admin' || currentUser.role === 'moderator') {
      fetch('https://api.projectdevops.in/authors')
        .then(res => res.json())
        .then(data => setAuthors(data));
    }
  }, [currentUser]);
  
  const handleSubmit = async (e) => {
    e.preventDefault();
    
    const formDataToSend = new FormData();
    formDataToSend.append('title', formData.title);
    formDataToSend.append('content', formData.content);
    formDataToSend.append('custom_slug', formData.custom_slug);
    
    // Add author override if admin selected one
    if (formData.author_username) {
      formDataToSend.append('author_username', formData.author_username);
    }
    
    formDataToSend.append('file', fileInput.files[0]);
    
    const token = localStorage.getItem('token');
    const response = await fetch('https://api.projectdevops.in/news', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`
      },
      body: formDataToSend
    });
    
    // Handle response...
  };
  
  return (
    <form onSubmit={handleSubmit}>
      <input
        type="text"
        placeholder="Title"
        value={formData.title}
        onChange={(e) => setFormData({...formData, title: e.target.value})}
      />
      
      <textarea
        placeholder="Content"
        value={formData.content}
        onChange={(e) => setFormData({...formData, content: e.target.value})}
      />
      
      {/* Show author selector only for admin/moderator */}
      {(currentUser.role === 'admin' || currentUser.role === 'moderator') && (
        <div className="author-selector">
          <label>Assign to Author (optional):</label>
          <select
            value={formData.author_username}
            onChange={(e) => setFormData({...formData, author_username: e.target.value})}
          >
            <option value="">-- Use my account --</option>
            {authors.map(author => (
              <option key={author.username} value={author.username}>
                {author.full_name} (@{author.username})
              </option>
            ))}
          </select>
          <p className="help-text">
            Leave empty to assign to yourself. Select an author to create on their behalf.
          </p>
        </div>
      )}
      
      <input type="file" ref={fileInput} required />
      <button type="submit">Create Article</button>
    </form>
  );
}
```

### Admin Panel - Change Article Author

```jsx
function ChangeArticleAuthor({ newsId, currentAuthor }) {
  const [authors, setAuthors] = useState([]);
  const [selectedAuthor, setSelectedAuthor] = useState('');
  
  useEffect(() => {
    fetch('https://api.projectdevops.in/authors')
      .then(res => res.json())
      .then(data => setAuthors(data));
  }, []);
  
  const handleChangeAuthor = async () => {
    if (!selectedAuthor) {
      alert('Please select an author');
      return;
    }
    
    const formData = new FormData();
    formData.append('author_username', selectedAuthor);
    
    const token = localStorage.getItem('admin_token');
    const response = await fetch(
      `https://api.projectdevops.in/news/${newsId}`,
      {
        method: 'PUT',
        headers: {
          'Authorization': `Bearer ${token}`
        },
        body: formData
      }
    );
    
    if (response.ok) {
      alert('Author changed successfully');
      window.location.reload();
    } else {
      const error = await response.json();
      alert(`Error: ${error.detail}`);
    }
  };
  
  return (
    <div className="change-author-section">
      <h3>Change Article Author</h3>
      <p>Current Author: <strong>{currentAuthor}</strong></p>
      
      <select
        value={selectedAuthor}
        onChange={(e) => setSelectedAuthor(e.target.value)}
      >
        <option value="">Select New Author</option>
        {authors.map(author => (
          <option key={author.username} value={author.username}>
            {author.full_name} (@{author.username})
          </option>
        ))}
      </select>
      
      <button onClick={handleChangeAuthor}>Change Author</button>
      
      <div className="warning">
        ⚠️ This will update article counts for both old and new authors.
      </div>
    </div>
  );
}
```

### Audit Trail

All author changes are logged:

```python
# Server logs contain:
[update_news] Admin/Moderator admin_user changed author from old_author to new_author
```

Consider implementing a dedicated audit log collection for tracking all article author changes:

```javascript
// audit_log collection
{
  "action": "author_changed",
  "news_id": "674a5f8c9d8e7f6b5a4c3d2e",
  "old_author": "john_smith",
  "new_author": "jane_doe",
  "changed_by": "admin_user",
  "changed_at": ISODate("2025-12-08T10:30:00Z"),
  "reason": "Editorial reassignment"
}
```

---

## Frontend Integration Guide

### Display Author Card in News Article

```jsx
// React Component Example
function AuthorCard({ authorDetails }) {
  if (!authorDetails) return null;
  
  return (
    <div className="author-card">
      {authorDetails.author_profile_image && (
        <img 
          src={authorDetails.author_profile_image} 
          alt={authorDetails.full_name}
          className="author-avatar"
        />
      )}
      <div className="author-info">
        <h4>{authorDetails.full_name}</h4>
        {authorDetails.author_designation && (
          <p className="designation">{authorDetails.author_designation}</p>
        )}
        {authorDetails.author_bio && (
          <p className="bio">{authorDetails.author_bio}</p>
        )}
        {authorDetails.author_social_links && (
          <div className="social-links">
            {Object.entries(authorDetails.author_social_links).map(([platform, url]) => (
              <a key={platform} href={url} target="_blank" rel="noopener noreferrer">
                {platform}
              </a>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

// Usage in News Article
function NewsArticle({ article }) {
  return (
    <article>
      <h1>{article.title}</h1>
      <AuthorCard authorDetails={article.author_details} />
      <div className="content">{article.content}</div>
    </article>
  );
}
```

---

### Author Profile Page

```jsx
function AuthorProfilePage({ username }) {
  const [author, setAuthor] = useState(null);
  const [articles, setArticles] = useState([]);
  
  useEffect(() => {
    // Fetch author profile
    fetch(`https://api.projectdevops.in/authors/${username}`)
      .then(res => res.json())
      .then(data => setAuthor(data));
    
    // Fetch author's articles
    fetch(`https://api.projectdevops.in/news?author=${username}`)
      .then(res => res.json())
      .then(data => setArticles(data));
  }, [username]);
  
  if (!author) return <div>Loading...</div>;
  
  return (
    <div className="author-profile-page">
      <div className="author-header">
        {author.author_profile_image && (
          <img src={author.author_profile_image} alt={author.full_name} />
        )}
        <div>
          <h1>{author.full_name}</h1>
          <p className="designation">{author.author_designation}</p>
          <p className="bio">{author.author_bio}</p>
          <p className="stats">
            {author.articles_count} articles published
          </p>
        </div>
      </div>
      
      <div className="author-articles">
        <h2>Recent Articles</h2>
        {articles.map(article => (
          <ArticleCard key={article._id} article={article} />
        ))}
      </div>
    </div>
  );
}
```

---

### Authors Directory Page

```jsx
function AuthorsDirectory() {
  const [authors, setAuthors] = useState([]);
  
  useEffect(() => {
    fetch('https://api.projectdevops.in/authors')
      .then(res => res.json())
      .then(data => setAuthors(data));
  }, []);
  
  return (
    <div className="authors-directory">
      <h1>Our Authors</h1>
      <div className="authors-grid">
        {authors.map(author => (
          <div key={author.username} className="author-card">
            <img src={author.author_profile_image} alt={author.full_name} />
            <h3>{author.full_name}</h3>
            <p>{author.author_designation}</p>
            <p className="article-count">{author.articles_count} articles</p>
            <Link to={`/authors/${author.username}`}>View Profile</Link>
          </div>
        ))}
      </div>
    </div>
  );
}
```

---

## Admin Panel Integration

### Role Management Interface

```jsx
function UserRoleManager({ user }) {
  const [selectedRole, setSelectedRole] = useState(user.role);
  const roles = ['user', 'author', 'moderator', 'vendor', 'admin'];
  
  const updateRole = async () => {
    const token = localStorage.getItem('admin_token');
    const response = await fetch(
      `https://api.projectdevops.in/users/${user.username}/role?new_role=${selectedRole}`,
      {
        method: 'PATCH',
        headers: {
          'Authorization': `Bearer ${token}`
        }
      }
    );
    
    if (response.ok) {
      alert('Role updated successfully');
    }
  };
  
  return (
    <div className="role-manager">
      <label>User Role for {user.username}</label>
      <select value={selectedRole} onChange={(e) => setSelectedRole(e.target.value)}>
        {roles.map(role => (
          <option key={role} value={role}>{role}</option>
        ))}
      </select>
      <button onClick={updateRole}>Update Role</button>
    </div>
  );
}
```

---

## Database Schema

### Users Collection (Updated)

```javascript
{
  "_id": ObjectId,
  "username": "string",
  "first_name": "string",
  "last_name": "string",
  "email": "string",
  "password": "hashed_string",
  "city": "string",
  "role": "user|admin|author|moderator|vendor",
  "is_active": true,
  
  // Author-specific fields (optional)
  "author_bio": "string",
  "author_profile_image": "url_string",
  "author_designation": "string",
  "author_social_links": {
    "twitter": "url",
    "linkedin": "url",
    "facebook": "url"
  },
  "articles_count": 0,
  
  "created_at": ISODate,
  "updated_at": ISODate
}
```

### News Collection (Updated)

```javascript
{
  "_id": ObjectId,
  "title": "string",
  "content": "string",
  "image_url": "string",
  "author_username": "string",  // Primary author reference
  
  // Embedded author profile
  "author_details": {
    "username": "string",
    "full_name": "string",
    "author_profile_image": "url",
    "author_designation": "string",
    "author_bio": "string"
  },
  
  "categories": "string",
  "tags": ["array"],
  "published": true,
  "created_at": ISODate,
  "views": 0,
  "likes": 0
}
```

---

## Migration Notes

### For Existing Systems

1. **No Breaking Changes** - All new fields are optional
2. **Backward Compatible** - Existing news posts work without author_details
3. **Dynamic Loading** - Author details fetched on-demand for old posts
4. **Gradual Migration** - Can update existing posts to include author_details over time

### Recommended Migration Steps

1. Update user roles to include "author" and "moderator"
2. Have authors update their profiles with bio, designation, photo
3. Existing news posts automatically get author details on retrieval
4. (Optional) Run bulk update to embed author_details in all existing posts

---

## Security Considerations

1. **Role-Based Access**
   - Only admins can change user roles
   - Authors can only edit their own profiles
   - Moderators have content management permissions

2. **Data Privacy**
   - Password never exposed in API responses
   - Email excluded from public author endpoints
   - Only active authors shown in public listings

3. **Image Uploads**
   - Validated file types (JPEG, PNG, WebP)
   - Stored securely in S3
   - Unique filenames prevent conflicts

---

## Testing

### cURL Examples

**Get all authors:**
```bash
curl https://api.projectdevops.in/authors
```

**Get specific author:**
```bash
curl https://api.projectdevops.in/authors/rahul_kumar
```

**Update author profile:**
```bash
curl -X PATCH https://api.projectdevops.in/authors/rahul_kumar/profile \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "author_bio": "Updated bio",
    "author_designation": "Chief Editor"
  }'
```

**Change user role (admin):**
```bash
curl -X PATCH "https://api.projectdevops.in/users/john_doe/role?new_role=author" \
  -H "Authorization: Bearer ADMIN_TOKEN"
```

---

## Support

For questions or issues:
- Email: connect@projectdevops.in
- API Documentation: https://api.projectdevops.in/docs
