# News Draft & Scheduling Feature - UI Integration Guide

## Overview
The news system now supports **draft mode** and **scheduling** posts for future publication. All scheduling times are in **IST (Indian Standard Time)**.

---

## Feature Summary

### 1. Draft Mode
- Posts can be saved as drafts (not published)
- Set `published=false` to create a draft
- Drafts are only visible to admin/author users

### 2. Scheduled Publishing
- Schedule posts to auto-publish at a future IST time
- Posts auto-publish when scheduled time is reached
- Scheduled posts are automatically unpublished until scheduled time

### 3. Auto-Publish Mechanism
- Backend automatically checks and publishes scheduled posts
- Runs on every GET request (list, filter endpoints)
- No manual intervention required

---

## API Changes

### Create News (POST /news)

**New Parameters:**
```
scheduled_publish: bool (default: false)
scheduled_at: string (format: YYYY-MM-DDTHH:MM in IST)
```

**Scheduling Rules:**
1. If `scheduled_publish=true`, you MUST provide `scheduled_at`
2. `scheduled_at` must be a future time in IST timezone
3. When scheduling is enabled, `published` is automatically set to `false`

**Example 1: Create Draft Post**
```bash
curl -X POST https://api.projectdevops.in/news \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "title=Draft Post Title" \
  -F "summary=This is a draft" \
  -F "content=Full content here" \
  -F "slug=draft-post-slug" \
  -F "published=false" \
  -F "scheduled_publish=false"
```

**Example 2: Schedule Post for Future**
```bash
curl -X POST https://api.projectdevops.in/news \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "title=Scheduled Post" \
  -F "summary=Will publish tomorrow" \
  -F "content=Full content" \
  -F "slug=scheduled-post-slug" \
  -F "scheduled_publish=true" \
  -F "scheduled_at=2025-01-15T10:30"
```

**Example 3: Regular Published Post (No Scheduling)**
```bash
curl -X POST https://api.projectdevops.in/news \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "title=Regular Post" \
  -F "summary=Published immediately" \
  -F "content=Full content" \
  -F "slug=regular-post-slug" \
  -F "published=true" \
  -F "scheduled_publish=false"
```

---

### Update News (PUT /news/{id})

**New Parameters:**
```
scheduled_publish: bool (optional)
scheduled_at: string (optional, format: YYYY-MM-DDTHH:MM in IST)
```

**Update Scenarios:**

**Scenario 1: Enable Scheduling on Existing Post**
```bash
curl -X PUT https://api.projectdevops.in/news/POST_ID \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "scheduled_publish=true" \
  -F "scheduled_at=2025-01-20T15:00"
```
- Post becomes unpublished automatically
- Will auto-publish at scheduled time

**Scenario 2: Reschedule Existing Scheduled Post**
```bash
curl -X PUT https://api.projectdevops.in/news/POST_ID \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "scheduled_at=2025-01-22T09:00"
```
- Updates the scheduled time
- Post remains scheduled

**Scenario 3: Cancel Scheduling (Publish Now)**
```bash
curl -X PUT https://api.projectdevops.in/news/POST_ID \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "scheduled_publish=false" \
  -F "published=true"
```
- Removes scheduling
- Publishes post immediately

**Scenario 4: Convert Published Post to Draft**
```bash
curl -X PUT https://api.projectdevops.in/news/POST_ID \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "published=false" \
  -F "scheduled_publish=false"
```

---

### Get Scheduled Posts (GET /news/scheduled)

**New Endpoint** (Admin/Author Only)

Returns all posts with `scheduled_publish=true` sorted by scheduled time.

```bash
curl -X GET https://api.projectdevops.in/news/scheduled \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Response Format:**
```json
[
  {
    "_id": "post_id_1",
    "title": "Scheduled Post 1",
    "scheduled_publish": true,
    "scheduled_at": "2025-01-15T05:00:00Z",  // UTC in DB
    "published": false,
    ...
  },
  {
    "_id": "post_id_2",
    "title": "Scheduled Post 2",
    "scheduled_at": "2025-01-20T10:00:00Z",
    ...
  }
]
```

**Important:** `scheduled_at` in response is in **UTC**. Convert to IST for display:
```javascript
// Frontend conversion
const istTime = new Date(scheduled_at).toLocaleString('en-IN', { 
  timeZone: 'Asia/Kolkata',
  dateStyle: 'medium',
  timeStyle: 'short'
});
```

---

## UI Implementation Requirements

### 1. Create/Edit News Form

**Add Publishing Mode Selector:**
```
○ Publish Now
○ Save as Draft
○ Schedule for Later
```

**Conditional Fields:**

**When "Schedule for Later" is selected:**
- Show datetime picker for IST timezone
- Label: "Scheduled Time (IST)"
- Format: `YYYY-MM-DDTHH:MM`
- Validation:
  - Must be future time
  - Show error if time is in past
  - Display converted time (e.g., "Will publish on Jan 15, 2025 at 10:30 AM IST")

**When "Save as Draft" is selected:**
- No additional fields
- Simply set `published=false`, `scheduled_publish=false`

**When "Publish Now" is selected:**
- No additional fields
- Set `published=true`, `scheduled_publish=false`

---

### 2. News List View (Admin/Author)

**Status Column Display:**

For each post, show status badge:

```javascript
function getPostStatus(post) {
  if (post.scheduled_publish && !post.published) {
    return {
      label: `Scheduled: ${formatISTTime(post.scheduled_at)}`,
      color: 'orange',
      icon: '🕒'
    };
  }
  if (!post.published) {
    return {
      label: 'Draft',
      color: 'gray',
      icon: '📝'
    };
  }
  return {
    label: 'Published',
    color: 'green',
    icon: '✓'
  };
}
```

**Action Buttons:**
- Draft posts: "Edit" | "Publish Now" | "Schedule"
- Scheduled posts: "Edit" | "Reschedule" | "Publish Now" | "Cancel Schedule"
- Published posts: "Edit" | "Unpublish"

---

### 3. Scheduled Posts Dashboard

**New View:** `/admin/news/scheduled`

**Display:**
- List all scheduled posts
- Show countdown timer for each
- Sort by scheduled time (earliest first)
- Actions: Edit, Reschedule, Publish Now, Delete

**Example UI:**
```
┌─────────────────────────────────────────────────────┐
│ Scheduled Posts (3)                                 │
├─────────────────────────────────────────────────────┤
│ 🕒 Breaking News Story                              │
│    Scheduled: Jan 15, 2025 at 10:30 AM IST         │
│    Time remaining: 2 days, 3 hours                 │
│    [Edit] [Reschedule] [Publish Now] [Delete]      │
├─────────────────────────────────────────────────────┤
│ 🕒 Technology Update                                │
│    Scheduled: Jan 20, 2025 at 3:00 PM IST          │
│    Time remaining: 7 days, 5 hours                 │
│    [Edit] [Reschedule] [Publish Now] [Delete]      │
└─────────────────────────────────────────────────────┘
```

---

## Frontend Code Examples

### 1. Create Post with Scheduling

```javascript
async function createScheduledPost(formData) {
  const form = new FormData();
  
  // Basic fields
  form.append('title', formData.title);
  form.append('summary', formData.summary);
  form.append('content', formData.content);
  form.append('slug', formData.slug);
  
  // Publishing mode
  if (formData.publishMode === 'schedule') {
    form.append('scheduled_publish', 'true');
    form.append('scheduled_at', formatToIST(formData.scheduledTime));
    form.append('published', 'false');  // Will be auto-set, but explicit is safe
  } else if (formData.publishMode === 'draft') {
    form.append('published', 'false');
    form.append('scheduled_publish', 'false');
  } else {  // publish now
    form.append('published', 'true');
    form.append('scheduled_publish', 'false');
  }
  
  // Other fields (categories, tags, images, etc.)
  // ... add as per NEWS_UI_MULTIMEDIA_GUIDE.md
  
  const response = await fetch('https://api.projectdevops.in/news', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`
    },
    body: form
  });
  
  return response.json();
}

// Helper: Format datetime to YYYY-MM-DDTHH:MM
function formatToIST(dateTime) {
  // If dateTime is from datetime-local input, it's already in local time
  return dateTime.replace(/:\d{2}\.\d{3}Z$/, '').substring(0, 16);
}
```

### 2. Reschedule Post

```javascript
async function reschedulePost(postId, newScheduledTime) {
  const form = new FormData();
  form.append('scheduled_at', formatToIST(newScheduledTime));
  
  const response = await fetch(`https://api.projectdevops.in/news/${postId}`, {
    method: 'PUT',
    headers: {
      'Authorization': `Bearer ${token}`
    },
    body: form
  });
  
  return response.json();
}
```

### 3. Publish Scheduled Post Immediately

```javascript
async function publishNow(postId) {
  const form = new FormData();
  form.append('scheduled_publish', 'false');
  form.append('published', 'true');
  
  const response = await fetch(`https://api.projectdevops.in/news/${postId}`, {
    method: 'PUT',
    headers: {
      'Authorization': `Bearer ${token}`
    },
    body: form
  });
  
  return response.json();
}
```

### 4. Get Scheduled Posts

```javascript
async function getScheduledPosts() {
  const response = await fetch('https://api.projectdevops.in/news/scheduled', {
    headers: {
      'Authorization': `Bearer ${token}`
    }
  });
  
  const posts = await response.json();
  
  // Convert UTC to IST for display
  return posts.map(post => ({
    ...post,
    scheduled_at_ist: new Date(post.scheduled_at).toLocaleString('en-IN', {
      timeZone: 'Asia/Kolkata',
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    })
  }));
}
```

### 5. Countdown Timer Component

```javascript
function TimeRemaining({ scheduledAt }) {
  const [remaining, setRemaining] = useState('');
  
  useEffect(() => {
    const interval = setInterval(() => {
      const now = new Date();
      const scheduled = new Date(scheduledAt);
      const diff = scheduled - now;
      
      if (diff <= 0) {
        setRemaining('Publishing now...');
        return;
      }
      
      const days = Math.floor(diff / (1000 * 60 * 60 * 24));
      const hours = Math.floor((diff % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
      const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));
      
      setRemaining(`${days}d ${hours}h ${minutes}m`);
    }, 60000);  // Update every minute
    
    return () => clearInterval(interval);
  }, [scheduledAt]);
  
  return <span className="countdown">{remaining}</span>;
}
```

---

## Response Model Updates

The `NewsPost` response model now includes:

```json
{
  "_id": "post_id",
  "title": "Post Title",
  "slug": "post-slug",
  "published": false,
  "scheduled_publish": true,
  "scheduled_at": "2025-01-15T05:00:00Z",  // UTC timestamp
  "created_at": "2025-01-10T12:00:00Z",
  "updated_at": "2025-01-10T12:00:00Z",
  ...
}
```

**Key Fields:**
- `published`: Boolean - Whether post is live
- `scheduled_publish`: Boolean - Whether scheduling is enabled
- `scheduled_at`: DateTime (UTC) - When post will auto-publish

---

## Validation & Error Handling

### Frontend Validation

**Before submitting scheduled post:**
```javascript
function validateScheduledTime(scheduledAt) {
  const now = new Date();
  const scheduled = new Date(scheduledAt);
  
  if (scheduled <= now) {
    throw new Error('Scheduled time must be in the future');
  }
  
  // Optional: Check if scheduled time is within reasonable range
  const maxDays = 365;  // 1 year
  const maxDate = new Date(now.getTime() + (maxDays * 24 * 60 * 60 * 1000));
  
  if (scheduled > maxDate) {
    throw new Error(`Cannot schedule more than ${maxDays} days in advance`);
  }
  
  return true;
}
```

### Backend Errors

**Possible HTTP 400 errors:**
- `"scheduled_at is required when scheduled_publish is True"`
- `"Invalid scheduled_at format. Use YYYY-MM-DDTHH:MM"`
- `"Scheduled time must be in the future (IST: 2025-01-10 10:30 AM)"`

**Handle errors:**
```javascript
try {
  await createScheduledPost(formData);
} catch (error) {
  if (error.response?.status === 400) {
    // Show user-friendly message
    alert(error.response.data.detail);
  }
}
```

---

## Testing Checklist

### Manual Testing

**Test Case 1: Create Draft**
- [ ] Create post with `published=false`
- [ ] Verify post doesn't appear in public list
- [ ] Verify post appears in admin list with "Draft" badge

**Test Case 2: Schedule Post**
- [ ] Create post with scheduling (5 minutes in future)
- [ ] Verify `published` is automatically false
- [ ] Wait 5+ minutes and refresh public list
- [ ] Verify post auto-publishes

**Test Case 3: Reschedule**
- [ ] Create scheduled post
- [ ] Update `scheduled_at` to new time
- [ ] Verify new time is reflected
- [ ] Verify post still unpublished until new time

**Test Case 4: Cancel Scheduling**
- [ ] Create scheduled post
- [ ] Update with `scheduled_publish=false`
- [ ] Choose to publish or keep as draft
- [ ] Verify scheduling removed

**Test Case 5: Scheduled Posts List**
- [ ] Create 3 scheduled posts with different times
- [ ] Visit `/news/scheduled` endpoint
- [ ] Verify sorted by scheduled time (earliest first)
- [ ] Verify countdown timers working

**Test Case 6: Timezone Handling**
- [ ] Schedule post for "2025-01-15T10:30" (IST input)
- [ ] Verify stored as UTC in database
- [ ] Verify displays correctly as IST in frontend
- [ ] Verify publishes at correct IST time

---

## Database Schema

**New Fields in `news` Collection:**
```javascript
{
  // Existing fields
  "title": "...",
  "content": "...",
  "published": false,
  
  // New scheduling fields
  "scheduled_publish": true,
  "scheduled_at": ISODate("2025-01-15T05:00:00Z"),  // UTC
  
  // Standard timestamps
  "created_at": ISODate("..."),
  "updated_at": ISODate("...")
}
```

---

## Common Scenarios

### Scenario 1: Daily Morning News Scheduling
**Use Case:** Schedule today's news to publish at 6:00 AM IST tomorrow

**Steps:**
1. Create post with all content
2. Select "Schedule for Later"
3. Set time: "2025-01-11T06:00"
4. Submit - post saved as scheduled
5. At 6:00 AM IST next day, post auto-publishes

### Scenario 2: Breaking News Override
**Use Case:** Scheduled post exists, but breaking news needs immediate publish

**Steps:**
1. Go to scheduled post
2. Click "Publish Now"
3. Confirms removal of scheduling
4. Post publishes immediately

### Scenario 3: Bulk Scheduling
**Use Case:** Prepare week's worth of content

**Steps:**
1. Create 7 posts
2. Schedule each for different day at 6:00 AM IST
3. View in scheduled dashboard
4. Posts auto-publish each morning
5. Monitor via scheduled posts list

---

## Best Practices

1. **Always validate scheduled time on frontend** before submission
2. **Show IST timezone** clearly in datetime picker labels
3. **Display countdown timers** for scheduled posts
4. **Auto-refresh** scheduled posts list periodically
5. **Show confirmation** before canceling scheduling
6. **Log scheduling actions** for audit trail (optional)
7. **Handle timezone conversion** correctly (UTC storage, IST display)
8. **Test auto-publish** thoroughly before production use
9. **Monitor scheduled posts** regularly for failed publishes
10. **Provide clear status indicators** (Draft/Scheduled/Published)

---

## Troubleshooting

### Issue: Post not auto-publishing at scheduled time

**Possible Causes:**
1. Backend not receiving requests (auto-publish runs on GET requests)
2. Server timezone misconfigured
3. Scheduled time in past due to timezone confusion

**Solutions:**
1. Ensure public site has traffic or setup cron job to ping `/news` endpoint
2. Verify server uses UTC internally
3. Always validate scheduled time is future time in IST

### Issue: Timezone confusion

**Fix:**
- Always use IST for user input: `YYYY-MM-DDTHH:MM`
- Backend converts to UTC for storage
- Frontend converts back to IST for display
- Use `Asia/Kolkata` timezone, not `GMT+5:30`

### Issue: Scheduled post still showing after scheduled time

**Fix:**
- Hit any GET endpoint to trigger `_process_scheduled_posts()`
- Or manually update: `curl -X PUT /news/{id} -F "published=true"`

---

## Migration Guide (Existing Posts)

All existing posts have default values:
- `scheduled_publish`: false
- `scheduled_at`: null

No migration needed. Scheduling is opt-in.

---

## Next Features (Future Enhancements)

1. **Recurring schedules** - Weekly/daily posts
2. **Scheduling history** - Track when posts were scheduled/rescheduled
3. **Email notifications** - Notify authors when post publishes
4. **Draft revisions** - Version control for drafts
5. **Approval workflow** - Require admin approval before scheduling

---

## Support & Questions

For implementation questions:
- Check existing news endpoints documentation
- Review `NEWS_UI_MULTIMEDIA_GUIDE.md` for multimedia integration
- Test with curl commands before UI implementation
- Monitor backend logs for scheduling errors

---

**Last Updated:** January 2025  
**Version:** 1.0  
**Backend:** FastAPI + MongoDB + PyTZ  
**Timezone:** IST (Asia/Kolkata)
