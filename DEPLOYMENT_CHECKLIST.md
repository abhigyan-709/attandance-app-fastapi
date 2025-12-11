# Designation System - Deployment Checklist

## ✅ Completed
- [x] Created designation master system models
- [x] Implemented designation CRUD API endpoints  
- [x] Added auto-assignment logic for grievances
- [x] Integrated designation validation in user updates
- [x] Created comprehensive documentation
- [x] Committed and pushed to GitHub (commit: a393b40)

---

## 🚀 Deployment Steps

### Step 1: Deploy to Production
```bash
# Pull latest changes on production server
cd /path/to/production/attandance-app-fastapi
git pull origin Abhigyans-Code

# Restart FastAPI application
# (Use your production restart method - systemd, docker, pm2, etc.)
sudo systemctl restart fastapi  # or your restart command
```

### Step 2: Initialize Default Designations
**⚠️ ONE-TIME SETUP - Run this immediately after deployment**

```bash
# Get admin token first
ADMIN_TOKEN="your_admin_jwt_token"

# Initialize 15 default designations
curl -X POST https://api.projectdevops.in/designations/initialize \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -v

# Expected response:
# {
#   "message": "Default designations initialized successfully",
#   "count": 15,
#   "designations": [
#     "Chief Editor", "Regional Editor", "Staff Editor",
#     "Senior Staff Editor", "CEO", "CTO", "CFO",
#     "Managing Editor", "Associate Editor", "Assistant Editor",
#     "Copy Editor", "Reporter", "Senior Reporter",
#     "Contributor", "Correspondent"
#   ]
# }
```

### Step 3: Sync Existing User Designations
**⚠️ IMPORTANT - Runs after Step 2 to fix existing author data**

```bash
# Sync all existing users with new designation system
curl -X POST https://api.projectdevops.in/designations/sync-users \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -v

# Expected response:
# {
#   "message": "User designations synced successfully",
#   "updated": 25,
#   "invalid": 2,
#   "total_valid_designations": 15
# }
```

### Step 4: Verify Designation System
```bash
# 1. Get all designations (public endpoint)
curl https://api.projectdevops.in/designations | jq '.[0:3]'

# 2. Get grievance handler designations
curl https://api.projectdevops.in/designations/grievance-handlers | jq

# 3. Check designation hierarchy
curl https://api.projectdevops.in/designations/users-by-designation \
  -H "Authorization: Bearer $ADMIN_TOKEN" | jq
```

### Step 5: Test User Update with Designation
```bash
# Update a test user's designation
curl -X PUT https://api.projectdevops.in/users/test_author \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "author_designation": "Chief Editor"
  }' | jq

# Verify auto-populated fields:
# - author_designation_level: "chief"
# - can_handle_grievances: true
# - author_designation_synced_at: "2024-12-11T..."
```

### Step 6: Test Grievance Auto-Assignment
```bash
# Submit test grievance
curl -X POST https://api.projectdevops.in/grievance/submit \
  -H "Content-Type: application/json" \
  -d '{
    "complainant_name": "Test User",
    "complainant_email": "test@example.com",
    "complainant_phone": "+919999999999",
    "category": "factual_error",
    "subject": "Test Auto-Assignment",
    "description": "Testing designation-based auto-assignment",
    "content_url": "https://example.com/article/123"
  }' | jq

# Verify response includes:
# - "assigned_to": "username_of_chief_editor_or_regional_editor"
# - Assignment should go to highest-level editor with can_handle_grievances=true
```

---

## 📋 Frontend Integration Checklist

### UI Changes Required

#### 1. Author Profile Form
- [ ] Replace free-text `author_designation` input with dropdown
- [ ] Fetch designations from `GET /designations`
- [ ] Sort designations by `display_order`
- [ ] Show designation description on hover

#### 2. Admin Dashboard - Designation Management
- [ ] Create new page: `/admin/designations`
- [ ] Display all designations in table
- [ ] Add "Initialize Defaults" button (one-time)
- [ ] Add "Sync Users" button (manual sync)
- [ ] Show designation hierarchy (level badges)
- [ ] Display grievance handling capability

#### 3. Admin Dashboard - User Management
- [ ] Update user edit modal with designation dropdown
- [ ] Display user's designation level badge
- [ ] Show grievance handling capability indicator
- [ ] Add filter: "Users by Designation"

#### 4. Grievance Dashboard
- [ ] Display assigned editor's designation
- [ ] Show designation level badge
- [ ] Add filter: "Complaints by Assigned Designation"
- [ ] Highlight auto-assigned complaints

---

## 🧪 Testing Scenarios

### Scenario 1: New Author Registration
1. Register new author account
2. Admin assigns designation "Staff Editor"
3. Verify `can_handle_grievances` is automatically set to `true`
4. Verify `author_designation_level` is set to "mid"

### Scenario 2: Designation Change
1. Update author from "Reporter" to "Regional Editor"
2. Verify `can_handle_grievances` changes from `false` to `true`
3. Verify `author_designation_level` changes from "junior" to "senior"
4. Verify `author_designation_synced_at` is updated

### Scenario 3: Grievance Auto-Assignment
1. Ensure Chief Editor exists with designation
2. Submit new grievance
3. Verify auto-assigned to Chief Editor
4. Remove Chief Editor, add Regional Editor
5. Submit grievance, verify assigned to Regional Editor

### Scenario 4: Invalid Designation
1. Try updating user with designation "Invalid Role"
2. Verify API returns 400 error
3. Verify error message: "Invalid designation selected"

---

## 🔍 Monitoring & Validation

### Database Queries

```javascript
// MongoDB shell - Check designations collection
use testdb;
db.designations.countDocuments();  // Should be 15
db.designations.find({ is_active: true }).pretty();

// Check users with designations
db.user.countDocuments({ author_designation: { $exists: true } });

// Check users with grievance capability
db.user.countDocuments({ can_handle_grievances: true });

// Check designation levels
db.user.aggregate([
  { $match: { author_designation: { $exists: true } } },
  { $group: { _id: "$author_designation_level", count: { $sum: 1 } } },
  { $sort: { _id: 1 } }
]);
```

### API Health Checks

```bash
# 1. Designation count
curl https://api.projectdevops.in/designations | jq 'length'
# Expected: 15

# 2. Grievance handlers count
curl https://api.projectdevops.in/designations/grievance-handlers | jq 'length'
# Expected: 5-7 (depending on active handlers)

# 3. Users with designations
curl https://api.projectdevops.in/designations/users-by-designation \
  -H "Authorization: Bearer $ADMIN_TOKEN" | jq '.total_users'
```

---

## ⚠️ Rollback Plan (If Issues Occur)

### Step 1: Revert Code
```bash
git revert a393b40
git push origin Abhigyans-Code
```

### Step 2: Clean Designation Data
```javascript
// MongoDB - Remove designation collections
use testdb;
db.designations.drop();

// Remove designation fields from users
db.user.updateMany(
  {},
  { 
    $unset: { 
      author_designation_level: "",
      can_handle_grievances: "",
      author_designation_synced_at: ""
    }
  }
);
```

### Step 3: Restore Previous Version
```bash
cd /path/to/production
git checkout 507d7db  # Previous commit
sudo systemctl restart fastapi
```

---

## 📞 Support Contacts

**Backend Developer:** [Your contact]
**Database Admin:** [DBA contact]
**DevOps:** [DevOps contact]

---

## 📚 Documentation Links

- **Implementation Guide:** `DESIGNATION_SYSTEM.md`
- **API Reference:** https://api.projectdevops.in/docs#/Designations
- **Grievance System:** `GRIEVANCE_SYSTEM.md`
- **Git Commit:** [a393b40](https://github.com/abhigyan-709/attandance-app-fastapi/commit/a393b40)

---

**Deployment Date:** _____________
**Deployed By:** _____________
**Verified By:** _____________

---

## ✅ Post-Deployment Verification

- [ ] All 15 designations initialized successfully
- [ ] Existing users synced with designations
- [ ] User update endpoint validates designations
- [ ] Grievance auto-assignment working correctly
- [ ] Frontend dropdown displays designations
- [ ] Admin dashboard shows designation management
- [ ] No errors in production logs
- [ ] Database indexes created (if needed)
- [ ] Monitoring alerts configured

**Status:** 🟢 Ready for Production Deployment
