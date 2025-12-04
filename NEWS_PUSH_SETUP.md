# Fresh News Push Notification System - Complete Setup Guide

## 🎯 Overview

This is a **completely fresh and separate** web push notification system for news readers on **gobarsahitimes.com**. It's independent from any other push notification systems in your codebase.

### Key Features
- ✅ Browser-native push notifications (no app required)
- ✅ Works on Chrome, Firefox, Edge, Safari 16+
- ✅ Separate MongoDB collection: `news_subscriptions`
- ✅ Separate environment variables: `NEWS_VAPID_*`
- ✅ Automatic notifications when news is published
- ✅ Support for both manual and scheduled post publishing
- ✅ Bell button UI for easy subscribe/unsubscribe
- ✅ Admin statistics and testing endpoints

---

## 📋 Table of Contents
1. [Backend Setup](#backend-setup)
2. [Environment Variables](#environment-variables)
3. [Frontend Integration](#frontend-integration)
4. [API Endpoints](#api-endpoints)
5. [GitHub Actions Secrets](#github-actions-secrets)
6. [Testing](#testing)
7. [Troubleshooting](#troubleshooting)

---

## 🔧 Backend Setup

### Files Created

**Services:**
- `services/news_push.py` - Core VAPID push notification logic
  - `get_news_vapid_config()` - Get NEWS_VAPID environment variables
  - `send_news_push_notification()` - Send to single subscriber
  - `broadcast_news_notification()` - Send to all subscribers

**Models:**
- `models/news_push.py` - Pydantic models for requests/responses
  - `NewsPushSubscription`, `NewsPushSubscribeRequest`
  - `NewsPushStatsResponse`, `NewsPushConfigResponse`

**Routes:**
- `routes/news_push.py` - API endpoints for subscriptions
  - 7 endpoints under `/news-push/*`
  - Uses `news_subscriptions` MongoDB collection

**Integration:**
- `routes/news.py` - Integrated notification triggers
  - Notifies on manual publish (create_news)
  - Notifies on scheduled auto-publish
- `main.py` - Router registered

### MongoDB Collection

**Collection Name:** `news_subscriptions`

**Document Structure:**
```javascript
{
  "_id": ObjectId("..."),
  "endpoint": "https://fcm.googleapis.com/fcm/send/...",  // Push service endpoint
  "keys": {
    "p256dh": "...",  // Encryption key
    "auth": "..."     // Authentication secret
  },
  "expirationTime": null,
  "user_agent": "Mozilla/5.0 ...",
  "created_at": ISODate("2025-12-05T10:30:00Z"),
  "updated_at": ISODate("2025-12-05T10:30:00Z"),
  "is_active": true,
  "notification_count": 5,
  "last_notified_at": ISODate("2025-12-05T11:00:00Z")
}
```

---

## 🔐 Environment Variables

### Required Variables (Separate from other systems)

```bash
# NEWS_VAPID Keys (completely separate from any other VAPID keys)
NEWS_VAPID_PUBLIC_KEY="BNcE8xV..."  # Base64 public key starting with 'B'
NEWS_VAPID_PRIVATE_KEY="YourPrivateKeyHere"
NEWS_VAPID_SUBJECT="mailto:connect@projectdevops.in"

# Optional: News UI base URL (for notification links)
NEWS_BASE_URL="https://gobarsahitimes.com"
```

### Generate VAPID Keys

**Option 1: Using web-push CLI (Recommended)**
```bash
npm install -g web-push
web-push generate-vapid-keys
```

**Option 2: Using Python**
```bash
pip install py-vapid
vapid --gen
```

**Output Example:**
```
Public Key:
BNcE8xV7r9RhXcZmvFyQ_z8J...

Private Key:
YourPrivateKeyHere123...
```

### Add to Your Server

**1. Update `.env` file on your server:**
```bash
# SSH to your server
ssh user@api.projectdevops.in

# Edit .env file
nano /path/to/your/app/.env

# Add these lines:
NEWS_VAPID_PUBLIC_KEY=BNcE8xV7r9RhXcZmvFyQ_z8J...
NEWS_VAPID_PRIVATE_KEY=YourPrivateKeyHere123...
NEWS_VAPID_SUBJECT=mailto:connect@projectdevops.in
NEWS_BASE_URL=https://gobarsahitimes.com
```

**2. Restart your FastAPI service:**
```bash
sudo systemctl restart your-fastapi-service
# OR
pm2 restart your-app
```

**3. Verify configuration:**
```bash
curl https://api.projectdevops.in/news-push/health
```

Expected response:
```json
{
  "status": "healthy",
  "vapid_configured": true,
  "subject": "mailto:connect@projectdevops.in",
  "service": "news-push"
}
```

---

## 🎨 Frontend Integration

### Step 1: Create Service Worker

Create `public/news-sw.js` in your Next.js project:

```javascript
// public/news-sw.js
self.addEventListener('push', function(event) {
  console.log('[news-sw] Push notification received');

  const data = event.data ? event.data.json() : {
    title: 'New News',
    body: 'Check out our latest news',
    url: 'https://gobarsahitimes.com',
  };

  const options = {
    body: data.body,
    icon: data.icon || '/logo.png',
    badge: '/badge.png',
    image: data.image,
    data: {
      url: data.url || 'https://gobarsahitimes.com',
      news_id: data.data?.news_id,
    },
    actions: [
      { action: 'open', title: 'Read Now' },
      { action: 'close', title: 'Dismiss' }
    ],
    requireInteraction: false,
    vibrate: [200, 100, 200],
    timestamp: Date.now(),
  };

  event.waitUntil(
    self.registration.showNotification(data.title, options)
  );
});

self.addEventListener('notificationclick', function(event) {
  console.log('[news-sw] Notification clicked:', event.action);
  
  event.notification.close();

  if (event.action === 'close') {
    return;
  }

  // Open the news article
  const url = event.notification.data.url;
  
  event.waitUntil(
    clients.matchAll({ type: 'window', includeUncontrolled: true })
      .then(function(clientList) {
        // Try to focus existing tab
        for (let client of clientList) {
          if (client.url === url && 'focus' in client) {
            return client.focus();
          }
        }
        // Open new tab
        if (clients.openWindow) {
          return clients.openWindow(url);
        }
      })
  );
});

self.addEventListener('pushsubscriptionchange', function(event) {
  console.log('[news-sw] Subscription expired, resubscribing...');
  // Handle subscription renewal if needed
});
```

### Step 2: Create React Hook

Create `hooks/useNewsPush.ts`:

```typescript
// hooks/useNewsPush.ts
import { useState, useEffect } from 'react';

const API_URL = 'https://api.projectdevops.in';
const SW_PATH = '/news-sw.js';

interface NewsPushState {
  isSupported: boolean;
  isSubscribed: boolean;
  isLoading: boolean;
  permission: NotificationPermission;
}

export function useNewsPush() {
  const [state, setState] = useState<NewsPushState>({
    isSupported: false,
    isSubscribed: false,
    isLoading: true,
    permission: 'default' as NotificationPermission,
  });

  useEffect(() => {
    checkSupport();
  }, []);

  async function checkSupport() {
    if (!('serviceWorker' in navigator) || !('PushManager' in window)) {
      setState(prev => ({ ...prev, isSupported: false, isLoading: false }));
      return;
    }

    setState(prev => ({ ...prev, isSupported: true }));

    try {
      const registration = await navigator.serviceWorker.register(SW_PATH);
      const subscription = await registration.pushManager.getSubscription();
      
      setState(prev => ({
        ...prev,
        isSubscribed: !!subscription,
        permission: Notification.permission,
        isLoading: false,
      }));
    } catch (error) {
      console.error('[news-push] Error checking support:', error);
      setState(prev => ({ ...prev, isLoading: false }));
    }
  }

  async function subscribe() {
    setState(prev => ({ ...prev, isLoading: true }));

    try {
      // Request notification permission
      const permission = await Notification.requestPermission();
      
      if (permission !== 'granted') {
        alert('Please allow notifications to receive news updates');
        setState(prev => ({ ...prev, permission, isLoading: false }));
        return false;
      }

      // Get VAPID public key from backend
      const configRes = await fetch(`${API_URL}/news-push/config`);
      if (!configRes.ok) throw new Error('Failed to get VAPID config');
      
      const config = await configRes.json();
      const publicKey = config.public_key;

      // Register service worker
      const registration = await navigator.serviceWorker.register(SW_PATH);
      await navigator.serviceWorker.ready;

      // Subscribe to push
      const subscription = await registration.pushManager.subscribe({
        userVisibleOnly: true,
        applicationServerKey: urlBase64ToUint8Array(publicKey),
      });

      // Send subscription to backend
      const subscribeRes = await fetch(`${API_URL}/news-push/subscribe`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          subscription: {
            endpoint: subscription.endpoint,
            keys: {
              p256dh: arrayBufferToBase64(subscription.getKey('p256dh')!),
              auth: arrayBufferToBase64(subscription.getKey('auth')!),
            },
            expirationTime: subscription.expirationTime,
            user_agent: navigator.userAgent,
          },
        }),
      });

      if (!subscribeRes.ok) throw new Error('Failed to subscribe on backend');

      setState(prev => ({
        ...prev,
        isSubscribed: true,
        permission: 'granted',
        isLoading: false,
      }));

      return true;
    } catch (error) {
      console.error('[news-push] Subscribe error:', error);
      alert('Failed to subscribe to notifications. Please try again.');
      setState(prev => ({ ...prev, isLoading: false }));
      return false;
    }
  }

  async function unsubscribe() {
    setState(prev => ({ ...prev, isLoading: true }));

    try {
      const registration = await navigator.serviceWorker.getRegistration(SW_PATH);
      if (!registration) throw new Error('Service worker not found');

      const subscription = await registration.pushManager.getSubscription();
      if (!subscription) throw new Error('No subscription found');

      // Unsubscribe from push service
      await subscription.unsubscribe();

      // Notify backend
      await fetch(`${API_URL}/news-push/unsubscribe`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ endpoint: subscription.endpoint }),
      });

      setState(prev => ({
        ...prev,
        isSubscribed: false,
        isLoading: false,
      }));

      return true;
    } catch (error) {
      console.error('[news-push] Unsubscribe error:', error);
      alert('Failed to unsubscribe. Please try again.');
      setState(prev => ({ ...prev, isLoading: false }));
      return false;
    }
  }

  return {
    ...state,
    subscribe,
    unsubscribe,
  };
}

// Helper functions
function urlBase64ToUint8Array(base64String: string): Uint8Array {
  const padding = '='.repeat((4 - base64String.length % 4) % 4);
  const base64 = (base64String + padding)
    .replace(/-/g, '+')
    .replace(/_/g, '/');

  const rawData = window.atob(base64);
  const outputArray = new Uint8Array(rawData.length);

  for (let i = 0; i < rawData.length; ++i) {
    outputArray[i] = rawData.charCodeAt(i);
  }
  return outputArray;
}

function arrayBufferToBase64(buffer: ArrayBuffer): string {
  const bytes = new Uint8Array(buffer);
  let binary = '';
  for (let i = 0; i < bytes.byteLength; i++) {
    binary += String.fromCharCode(bytes[i]);
  }
  return window.btoa(binary);
}
```

### Step 3: Create Bell Button Component

Create `components/NewsPushBell.tsx`:

```typescript
// components/NewsPushBell.tsx
import { useNewsPush } from '@/hooks/useNewsPush';
import { Bell, BellOff, Loader2 } from 'lucide-react';

export function NewsPushBell() {
  const { isSupported, isSubscribed, isLoading, permission, subscribe, unsubscribe } = useNewsPush();

  // Don't show if not supported
  if (!isSupported) {
    return null;
  }

  const handleClick = async () => {
    if (isSubscribed) {
      await unsubscribe();
    } else {
      await subscribe();
    }
  };

  return (
    <button
      onClick={handleClick}
      disabled={isLoading}
      className="relative p-2 rounded-full hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
      title={isSubscribed ? 'Unsubscribe from notifications' : 'Subscribe to news notifications'}
    >
      {isLoading ? (
        <Loader2 className="w-6 h-6 animate-spin text-gray-600" />
      ) : isSubscribed ? (
        <>
          <Bell className="w-6 h-6 text-blue-600 fill-current" />
          <span className="absolute top-0 right-0 w-3 h-3 bg-green-500 rounded-full border-2 border-white" />
        </>
      ) : (
        <BellOff className="w-6 h-6 text-gray-600" />
      )}
    </button>
  );
}
```

### Step 4: Add to Header

Add the bell button to your site header:

```typescript
// components/Header.tsx or layouts/Header.tsx
import { NewsPushBell } from '@/components/NewsPushBell';

export function Header() {
  return (
    <header className="flex items-center justify-between p-4">
      <div className="logo">
        {/* Your logo */}
      </div>
      
      <nav className="flex items-center gap-4">
        {/* Your navigation items */}
        
        {/* News Push Bell Button */}
        <NewsPushBell />
      </nav>
    </header>
  );
}
```

---

## 📡 API Endpoints

All endpoints are under `/news-push` prefix:

### 1. Get VAPID Configuration (Public)
```
GET /news-push/config
```
Returns the `NEWS_VAPID_PUBLIC_KEY` for frontend subscription.

**Response:**
```json
{
  "public_key": "BNcE8xV7...",
  "subject": "mailto:connect@projectdevops.in"
}
```

### 2. Subscribe to Notifications (Public)
```
POST /news-push/subscribe
Content-Type: application/json
```

**Request Body:**
```json
{
  "subscription": {
    "endpoint": "https://fcm.googleapis.com/fcm/send/...",
    "keys": {
      "p256dh": "...",
      "auth": "..."
    },
    "expirationTime": null,
    "user_agent": "Mozilla/5.0 ..."
  }
}
```

**Response:**
```json
{
  "status": "subscribed",
  "message": "Subscribed successfully to news notifications"
}
```

### 3. Unsubscribe from Notifications (Public)
```
POST /news-push/unsubscribe
Content-Type: application/json
```

**Request Body:**
```json
{
  "endpoint": "https://fcm.googleapis.com/fcm/send/..."
}
```

**Response:**
```json
{
  "status": "unsubscribed",
  "message": "Unsubscribed successfully"
}
```

### 4. Check Subscription Status (Public)
```
GET /news-push/status/{endpoint:path}
```

**Response:**
```json
{
  "subscribed": true,
  "subscription_date": "2025-12-05T10:30:00Z",
  "notification_count": 5
}
```

### 5. Get Statistics (Public)
```
GET /news-push/stats
```

**Response:**
```json
{
  "total_subscriptions": 150,
  "total_notifications_sent": 750,
  "last_notification_at": "2025-12-05T11:00:00Z",
  "oldest_subscription": "2025-11-01T08:00:00Z",
  "newest_subscription": "2025-12-05T10:30:00Z"
}
```

### 6. Send Test Notification (Public)
```
POST /news-push/test
Content-Type: application/json
```

**Request Body:**
```json
{
  "endpoint": "https://fcm.googleapis.com/fcm/send/...",  // Optional: test specific endpoint
  "title": "Test Notification",
  "body": "This is a test",
  "url": "https://gobarsahitimes.com",
  "icon": "https://gobarsahitimes.com/logo.png",
  "image": "https://gobarsahitimes.com/test-image.jpg"
}
```

**Response:**
```json
{
  "status": "queued",
  "message": "Test notification queued for 1 subscription(s)",
  "count": 1
}
```

### 7. Health Check (Public)
```
GET /news-push/health
```

**Response:**
```json
{
  "status": "healthy",
  "vapid_configured": true,
  "subject": "mailto:connect@projectdevops.in",
  "service": "news-push"
}
```

---

## 🔐 GitHub Actions Secrets

Add these secrets to your GitHub repository for automated deployment:

**Navigate to:** Repository → Settings → Secrets and variables → Actions → New repository secret

### Required Secrets:

1. **NEWS_VAPID_PUBLIC_KEY**
   - Value: `BNcE8xV7...` (your public key)
   - Used in: Backend configuration

2. **NEWS_VAPID_PRIVATE_KEY**
   - Value: `YourPrivateKeyHere123...`
   - Used in: Backend push sending

3. **NEWS_VAPID_SUBJECT**
   - Value: `mailto:connect@projectdevops.in`
   - Used in: VAPID claims

4. **NEWS_BASE_URL**
   - Value: `https://gobarsahitimes.com`
   - Used in: Notification URL generation

### Update GitHub Actions Workflow

Add to your `.github/workflows/deploy.yml`:

```yaml
- name: Deploy Backend
  env:
    NEWS_VAPID_PUBLIC_KEY: ${{ secrets.NEWS_VAPID_PUBLIC_KEY }}
    NEWS_VAPID_PRIVATE_KEY: ${{ secrets.NEWS_VAPID_PRIVATE_KEY }}
    NEWS_VAPID_SUBJECT: ${{ secrets.NEWS_VAPID_SUBJECT }}
    NEWS_BASE_URL: ${{ secrets.NEWS_BASE_URL }}
  run: |
    # Your deployment commands
    echo "NEWS_VAPID_PUBLIC_KEY=$NEWS_VAPID_PUBLIC_KEY" >> .env
    echo "NEWS_VAPID_PRIVATE_KEY=$NEWS_VAPID_PRIVATE_KEY" >> .env
    echo "NEWS_VAPID_SUBJECT=$NEWS_VAPID_SUBJECT" >> .env
    echo "NEWS_BASE_URL=$NEWS_BASE_URL" >> .env
```

---

## 🧪 Testing

### 1. Test Backend Health
```bash
curl https://api.projectdevops.in/news-push/health
```

Expected: `{"status": "healthy", "vapid_configured": true}`

### 2. Test Get Config
```bash
curl https://api.projectdevops.in/news-push/config
```

Expected: Public key returned

### 3. Test Subscribe (Manual)
```bash
curl -X POST https://api.projectdevops.in/news-push/subscribe \
  -H "Content-Type: application/json" \
  -d '{
    "subscription": {
      "endpoint": "https://fcm.googleapis.com/fcm/send/test",
      "keys": {
        "p256dh": "test-p256dh",
        "auth": "test-auth"
      }
    }
  }'
```

### 4. Test Statistics
```bash
curl https://api.projectdevops.in/news-push/stats
```

### 5. Test Frontend Subscription
1. Open https://gobarsahitimes.com in Chrome/Firefox
2. Open DevTools Console
3. Click the bell button
4. Allow notifications when prompted
5. Check console for `[news-push]` logs
6. Verify in MongoDB: `db.news_subscriptions.find({is_active: true})`

### 6. Test Full Notification Flow
1. Publish a news article from admin panel
2. Check backend logs for `[news-push] Queued notification`
3. All subscribed users should receive notification
4. Verify notification count increased in stats

---

## 🐛 Troubleshooting

### Issue: "NEWS_VAPID keys not configured"

**Cause:** Environment variables not set

**Fix:**
```bash
# Check if variables exist
echo $NEWS_VAPID_PUBLIC_KEY

# Add to .env file
NEWS_VAPID_PUBLIC_KEY=BNcE8xV...
NEWS_VAPID_PRIVATE_KEY=YourPrivateKey...
NEWS_VAPID_SUBJECT=mailto:connect@projectdevops.in

# Restart service
sudo systemctl restart your-service
```

### Issue: "Failed to subscribe on backend"

**Possible Causes:**
1. CORS not allowing gobarsahitimes.com
2. NEWS_VAPID keys missing
3. MongoDB connection issue

**Fix:**
```python
# In main.py, ensure CORS includes your domain
allow_origins=[
    "https://gobarsahitimes.com",
    "https://www.gobarsahitimes.com",
]
```

### Issue: Notifications not appearing

**Checklist:**
- [ ] User granted notification permission?
- [ ] Service worker registered? (Check DevTools → Application → Service Workers)
- [ ] Subscription active in MongoDB? (`db.news_subscriptions.find()`)
- [ ] Backend logs show notification sent?
- [ ] Browser supports push notifications? (Check browser compatibility)

**Debug:**
```javascript
// In browser console
navigator.serviceWorker.getRegistration('/news-sw.js')
  .then(reg => reg.pushManager.getSubscription())
  .then(sub => console.log('Subscription:', sub));
```

### Issue: Subscription expired (410 error)

**Cause:** Push service endpoint expired (browser-side)

**Fix:** System automatically removes expired subscriptions. User needs to resubscribe by clicking bell button again.

### Issue: No notifications for scheduled posts

**Cause:** Scheduled post auto-publish may not be triggering

**Fix:**
1. Check `_process_scheduled_posts()` is called in `get_news()` endpoint
2. Verify scheduled_at time is in UTC
3. Check backend logs for auto-publish events
4. Test: `GET /news/scheduled` to see pending posts

---

## 📊 Monitoring

### Check Active Subscriptions
```bash
curl https://api.projectdevops.in/news-push/stats
```

### MongoDB Queries
```javascript
// Connect to MongoDB
mongo

// Use your database
use testdb

// Count active subscriptions
db.news_subscriptions.countDocuments({is_active: true})

// Get recent subscriptions
db.news_subscriptions.find({is_active: true}).sort({created_at: -1}).limit(10)

// Get notification statistics
db.news_subscriptions.aggregate([
  {$match: {is_active: true}},
  {$group: {
    _id: null,
    total: {$sum: 1},
    total_notifications: {$sum: "$notification_count"}
  }}
])
```

### Backend Logs
```bash
# View logs
tail -f /var/log/your-app.log

# Filter for news-push
tail -f /var/log/your-app.log | grep "news-push"
```

---

## 🚀 Deployment Checklist

### Backend
- [ ] Generate VAPID keys using `web-push generate-vapid-keys`
- [ ] Add `NEWS_VAPID_*` variables to `.env` file
- [ ] Add variables to GitHub Actions secrets
- [ ] Deploy backend and restart service
- [ ] Verify health check: `GET /news-push/health`
- [ ] Test config endpoint: `GET /news-push/config`

### Frontend
- [ ] Create `public/news-sw.js` service worker
- [ ] Create `hooks/useNewsPush.ts` hook
- [ ] Create `components/NewsPushBell.tsx` component
- [ ] Add bell to header/navbar
- [ ] Test subscription flow
- [ ] Test notification display

### Testing
- [ ] Subscribe from frontend
- [ ] Check MongoDB for subscription document
- [ ] Publish test news article
- [ ] Verify notification received
- [ ] Check stats endpoint for counts
- [ ] Test unsubscribe flow

---

## 📞 Support

If you encounter issues:

1. **Check health endpoint:** `GET /news-push/health`
2. **Check backend logs:** Look for `[news-push]` tags
3. **Check browser console:** Look for service worker errors
4. **Check MongoDB:** Verify `news_subscriptions` collection exists

**Common Issues:**
- VAPID keys not configured → Add to `.env` and restart
- CORS errors → Add domain to `allow_origins` in `main.py`
- Service worker not registering → Check path is `/news-sw.js`
- No notifications → Verify permission granted and subscription active

---

## 🎉 Success Criteria

Your system is working correctly when:

1. ✅ Health check returns `"vapid_configured": true`
2. ✅ Bell button appears on gobarsahitimes.com
3. ✅ Users can subscribe successfully
4. ✅ Subscriptions appear in MongoDB `news_subscriptions` collection
5. ✅ Publishing news triggers notification
6. ✅ Scheduled posts send notifications when auto-published
7. ✅ Users receive browser notifications
8. ✅ Stats endpoint shows correct counts
9. ✅ Users can unsubscribe successfully

---

## 📝 Summary

This is a **fresh, separate** news push notification system with:

- **Separate collection:** `news_subscriptions` (not interfering with other systems)
- **Separate variables:** `NEWS_VAPID_*` (completely independent)
- **Separate routes:** `/news-push/*` (clean API)
- **Clean integration:** Triggers only on news publish events

The system is production-ready and follows FastAPI best practices! 🚀
