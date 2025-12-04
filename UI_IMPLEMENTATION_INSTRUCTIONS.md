# UI Implementation Instructions - Fresh News Push Notifications
## For gobarsahitimes.com (Next.js)

---

## 🎯 Overview

Implement a **bell button notification system** for news readers to subscribe to push notifications when new news articles are published.

**Backend API**: ✅ Ready at `https://api.projectdevops.in`
**VAPID Public Key**: ✅ `BMuKdCIpflnH4HN_xvBsFZLNe5DiBYKpIhRlgwtr3u5M00oenTPqz9A-XjlVR3itpBo1lIFIapAZJgy-GfM16Io`

---

## 📋 Implementation Checklist

- [ ] Create Service Worker file (`public/sw.js`)
- [ ] Create notification hook (`hooks/useNewsPush.ts`)
- [ ] Create bell button component (`components/NewsPushBell.tsx`)
- [ ] Add bell to header/navbar
- [ ] Test subscription flow
- [ ] Test notification reception

**Estimated Time**: 30-45 minutes

---

## 📁 File 1: Service Worker

**Path**: `public/sw.js`

```javascript
// public/sw.js
// Service Worker for Fresh News Push Notifications

const CACHE_NAME = 'news-push-v1';

// Install event
self.addEventListener('install', (event) => {
  console.log('[SW] Installing service worker...');
  self.skipWaiting();
});

// Activate event
self.addEventListener('activate', (event) => {
  console.log('[SW] Activating service worker...');
  event.waitUntil(self.clients.claim());
});

// Push notification received
self.addEventListener('push', (event) => {
  console.log('[SW] Push notification received:', event);

  let notificationData = {
    title: 'New News Article',
    body: 'Check out the latest news!',
    icon: '/icon-192x192.png',
    badge: '/badge-72x72.png',
    url: '/',
  };

  // Parse notification payload
  if (event.data) {
    try {
      const payload = event.data.json();
      notificationData = {
        title: payload.title || notificationData.title,
        body: payload.body || notificationData.body,
        icon: payload.icon || notificationData.icon,
        badge: payload.badge || notificationData.badge,
        url: payload.url || notificationData.url,
        image: payload.image, // Optional hero image
        tag: payload.tag || 'news-notification',
        requireInteraction: payload.requireInteraction || false,
        data: payload.data || {},
      };
    } catch (error) {
      console.error('[SW] Error parsing push payload:', error);
    }
  }

  // Show notification
  const promiseChain = self.registration.showNotification(
    notificationData.title,
    {
      body: notificationData.body,
      icon: notificationData.icon,
      badge: notificationData.badge,
      image: notificationData.image,
      tag: notificationData.tag,
      requireInteraction: notificationData.requireInteraction,
      data: {
        url: notificationData.url,
        ...notificationData.data,
      },
      actions: [
        {
          action: 'open',
          title: 'Read Now',
          icon: '/icons/read.png',
        },
        {
          action: 'close',
          title: 'Dismiss',
          icon: '/icons/close.png',
        },
      ],
    }
  );

  event.waitUntil(promiseChain);
});

// Notification click handler
self.addEventListener('notificationclick', (event) => {
  console.log('[SW] Notification clicked:', event);

  event.notification.close();

  if (event.action === 'close') {
    return;
  }

  // Open the URL (from notification data or default action)
  const urlToOpen = event.notification.data?.url || '/';

  const promiseChain = clients
    .matchAll({
      type: 'window',
      includeUncontrolled: true,
    })
    .then((windowClients) => {
      // Check if there's already a window open with this URL
      for (let i = 0; i < windowClients.length; i++) {
        const client = windowClients[i];
        if (client.url === urlToOpen && 'focus' in client) {
          return client.focus();
        }
      }
      // If not, open a new window
      if (clients.openWindow) {
        return clients.openWindow(urlToOpen);
      }
    });

  event.waitUntil(promiseChain);
});

// Background sync (optional - for offline support)
self.addEventListener('sync', (event) => {
  console.log('[SW] Background sync:', event);
  if (event.tag === 'sync-subscriptions') {
    // Handle sync logic here if needed
  }
});
```

---

## 📁 File 2: React Hook

**Path**: `hooks/useNewsPush.ts` (or `src/hooks/useNewsPush.ts`)

```typescript
// hooks/useNewsPush.ts
import { useState, useEffect, useCallback } from 'react';

interface NewsPushState {
  isSupported: boolean;
  isSubscribed: boolean;
  isLoading: boolean;
  error: string | null;
  permission: NotificationPermission;
}

interface UseNewsPushReturn extends NewsPushState {
  subscribe: () => Promise<void>;
  unsubscribe: () => Promise<void>;
  requestPermission: () => Promise<NotificationPermission>;
}

const API_BASE_URL = process.env.NEXT_PUBLIC_NEWS_API_BASE_URL || 'https://api.projectdevops.in';
const VAPID_PUBLIC_KEY = process.env.NEXT_PUBLIC_NEWS_VAPID_PUBLIC_KEY || 'BMuKdCIpflnH4HN_xvBsFZLNe5DiBYKpIhRlgwtr3u5M00oenTPqz9A-XjlVR3itpBo1lIFIapAZJgy-GfM16Io';

// Helper: Convert base64 VAPID key to Uint8Array
function urlBase64ToUint8Array(base64String: string): Uint8Array {
  const padding = '='.repeat((4 - (base64String.length % 4)) % 4);
  const base64 = (base64String + padding)
    .replace(/\-/g, '+')
    .replace(/_/g, '/');

  const rawData = window.atob(base64);
  const outputArray = new Uint8Array(rawData.length);

  for (let i = 0; i < rawData.length; ++i) {
    outputArray[i] = rawData.charCodeAt(i);
  }
  return outputArray;
}

export function useNewsPush(): UseNewsPushReturn {
  const [state, setState] = useState<NewsPushState>({
    isSupported: false,
    isSubscribed: false,
    isLoading: true,
    error: null,
    permission: 'default',
  });

  // Check browser support and current subscription status
  useEffect(() => {
    const checkSupport = async () => {
      // Check if browser supports notifications and service workers
      const isSupported =
        'serviceWorker' in navigator &&
        'PushManager' in window &&
        'Notification' in window;

      if (!isSupported) {
        setState((prev) => ({
          ...prev,
          isSupported: false,
          isLoading: false,
          error: 'Push notifications are not supported in this browser',
        }));
        return;
      }

      try {
        // Register service worker if not already registered
        let registration = await navigator.serviceWorker.getRegistration();
        
        if (!registration) {
          registration = await navigator.serviceWorker.register('/sw.js', {
            scope: '/',
          });
          console.log('Service Worker registered:', registration);
        }

        // Check current subscription status
        const subscription = await registration.pushManager.getSubscription();
        const permission = Notification.permission;

        setState({
          isSupported: true,
          isSubscribed: !!subscription,
          isLoading: false,
          error: null,
          permission,
        });
      } catch (error) {
        console.error('Error checking push support:', error);
        setState((prev) => ({
          ...prev,
          isSupported: true,
          isLoading: false,
          error: 'Failed to initialize push notifications',
        }));
      }
    };

    checkSupport();
  }, []);

  // Request notification permission
  const requestPermission = useCallback(async (): Promise<NotificationPermission> => {
    if (!('Notification' in window)) {
      return 'denied';
    }

    const permission = await Notification.requestPermission();
    setState((prev) => ({ ...prev, permission }));
    return permission;
  }, []);

  // Subscribe to push notifications
  const subscribe = useCallback(async () => {
    if (!state.isSupported) {
      setState((prev) => ({ ...prev, error: 'Push notifications not supported' }));
      return;
    }

    setState((prev) => ({ ...prev, isLoading: true, error: null }));

    try {
      // Request permission if not granted
      if (state.permission !== 'granted') {
        const permission = await requestPermission();
        if (permission !== 'granted') {
          throw new Error('Notification permission denied');
        }
      }

      // Get service worker registration
      const registration = await navigator.serviceWorker.ready;

      // Subscribe to push manager
      const subscription = await registration.pushManager.subscribe({
        userVisibleOnly: true,
        applicationServerKey: urlBase64ToUint8Array(VAPID_PUBLIC_KEY),
      });

      // Send subscription to backend
      const response = await fetch(`${API_BASE_URL}/news-push/subscribe`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          subscription: subscription.toJSON(),
          metadata: {
            user_agent: navigator.userAgent,
            platform: navigator.platform,
            language: navigator.language,
          },
        }),
      });

      if (!response.ok) {
        throw new Error('Failed to subscribe on server');
      }

      const data = await response.json();
      console.log('Subscribed successfully:', data);

      setState((prev) => ({
        ...prev,
        isSubscribed: true,
        isLoading: false,
      }));
    } catch (error) {
      console.error('Error subscribing to push:', error);
      setState((prev) => ({
        ...prev,
        isLoading: false,
        error: error instanceof Error ? error.message : 'Failed to subscribe',
      }));
    }
  }, [state.isSupported, state.permission, requestPermission]);

  // Unsubscribe from push notifications
  const unsubscribe = useCallback(async () => {
    if (!state.isSupported) {
      return;
    }

    setState((prev) => ({ ...prev, isLoading: true, error: null }));

    try {
      const registration = await navigator.serviceWorker.ready;
      const subscription = await registration.pushManager.getSubscription();

      if (!subscription) {
        setState((prev) => ({
          ...prev,
          isSubscribed: false,
          isLoading: false,
        }));
        return;
      }

      // Unsubscribe from backend
      const response = await fetch(`${API_BASE_URL}/news-push/unsubscribe`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          endpoint: subscription.endpoint,
        }),
      });

      if (!response.ok) {
        console.warn('Failed to unsubscribe from server, continuing...');
      }

      // Unsubscribe from browser
      await subscription.unsubscribe();

      setState((prev) => ({
        ...prev,
        isSubscribed: false,
        isLoading: false,
      }));

      console.log('Unsubscribed successfully');
    } catch (error) {
      console.error('Error unsubscribing from push:', error);
      setState((prev) => ({
        ...prev,
        isLoading: false,
        error: error instanceof Error ? error.message : 'Failed to unsubscribe',
      }));
    }
  }, [state.isSupported]);

  return {
    ...state,
    subscribe,
    unsubscribe,
    requestPermission,
  };
}
```

---

## 📁 File 3: Bell Button Component

**Path**: `components/NewsPushBell.tsx` (or `src/components/NewsPushBell.tsx`)

```typescript
// components/NewsPushBell.tsx
'use client';

import { useNewsPush } from '@/hooks/useNewsPush';
import { Bell, BellOff, BellRing, Loader2 } from 'lucide-react';
import { useState } from 'react';

export function NewsPushBell() {
  const { isSupported, isSubscribed, isLoading, error, subscribe, unsubscribe } = useNewsPush();
  const [showTooltip, setShowTooltip] = useState(false);

  const handleClick = async () => {
    if (isLoading) return;

    if (isSubscribed) {
      await unsubscribe();
    } else {
      await subscribe();
    }
  };

  // Don't render if browser doesn't support push notifications
  if (!isSupported) {
    return null;
  }

  return (
    <div className="relative">
      <button
        onClick={handleClick}
        disabled={isLoading}
        onMouseEnter={() => setShowTooltip(true)}
        onMouseLeave={() => setShowTooltip(false)}
        className={`
          relative p-2 rounded-full transition-all duration-200
          ${isSubscribed 
            ? 'bg-blue-100 text-blue-600 hover:bg-blue-200' 
            : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
          }
          ${isLoading ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}
          focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2
        `}
        aria-label={isSubscribed ? 'Unsubscribe from notifications' : 'Subscribe to notifications'}
        title={isSubscribed ? 'Subscribed to news notifications' : 'Subscribe to news notifications'}
      >
        {isLoading ? (
          <Loader2 className="w-5 h-5 animate-spin" />
        ) : isSubscribed ? (
          <BellRing className="w-5 h-5" />
        ) : (
          <Bell className="w-5 h-5" />
        )}

        {/* Active subscription indicator */}
        {isSubscribed && !isLoading && (
          <span className="absolute top-1 right-1 w-2 h-2 bg-blue-500 rounded-full animate-pulse" />
        )}
      </button>

      {/* Tooltip */}
      {showTooltip && !isLoading && (
        <div className="absolute top-full mt-2 right-0 z-50 px-3 py-2 text-sm font-medium text-white bg-gray-900 rounded-lg shadow-lg whitespace-nowrap">
          {isSubscribed
            ? 'Subscribed to news notifications'
            : 'Subscribe to get notified of new articles'}
          <div className="absolute -top-1 right-4 w-2 h-2 bg-gray-900 rotate-45" />
        </div>
      )}

      {/* Error message */}
      {error && (
        <div className="absolute top-full mt-2 right-0 z-50 px-3 py-2 text-sm text-red-600 bg-red-50 rounded-lg shadow-lg max-w-xs">
          {error}
        </div>
      )}
    </div>
  );
}
```

---

## 📁 File 4: Alternative Bell Component (Without lucide-react)

**Path**: `components/NewsPushBell.tsx` (if not using lucide-react icons)

```typescript
// components/NewsPushBell.tsx (Alternative without icon library)
'use client';

import { useNewsPush } from '@/hooks/useNewsPush';
import { useState } from 'react';

export function NewsPushBell() {
  const { isSupported, isSubscribed, isLoading, error, subscribe, unsubscribe } = useNewsPush();
  const [showTooltip, setShowTooltip] = useState(false);

  const handleClick = async () => {
    if (isLoading) return;

    if (isSubscribed) {
      await unsubscribe();
    } else {
      await subscribe();
    }
  };

  if (!isSupported) {
    return null;
  }

  return (
    <div className="relative">
      <button
        onClick={handleClick}
        disabled={isLoading}
        onMouseEnter={() => setShowTooltip(true)}
        onMouseLeave={() => setShowTooltip(false)}
        className={`
          relative p-2 rounded-full transition-all duration-200
          ${isSubscribed 
            ? 'bg-blue-100 text-blue-600 hover:bg-blue-200' 
            : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
          }
          ${isLoading ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}
          focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2
        `}
        aria-label={isSubscribed ? 'Unsubscribe from notifications' : 'Subscribe to notifications'}
      >
        {isLoading ? (
          <svg className="w-5 h-5 animate-spin" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
          </svg>
        ) : (
          <svg
            className="w-5 h-5"
            fill={isSubscribed ? 'currentColor' : 'none'}
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9"
            />
          </svg>
        )}

        {isSubscribed && !isLoading && (
          <span className="absolute top-1 right-1 w-2 h-2 bg-blue-500 rounded-full animate-pulse" />
        )}
      </button>

      {showTooltip && !isLoading && (
        <div className="absolute top-full mt-2 right-0 z-50 px-3 py-2 text-sm font-medium text-white bg-gray-900 rounded-lg shadow-lg whitespace-nowrap">
          {isSubscribed
            ? '🔔 Subscribed to news notifications'
            : '🔕 Subscribe to get notified of new articles'}
          <div className="absolute -top-1 right-4 w-2 h-2 bg-gray-900 rotate-45" />
        </div>
      )}

      {error && (
        <div className="absolute top-full mt-2 right-0 z-50 px-3 py-2 text-sm text-red-600 bg-red-50 rounded-lg shadow-lg max-w-xs">
          ⚠️ {error}
        </div>
      )}
    </div>
  );
}
```

---

## 📁 File 5: Add to Header/Navbar

**Example**: `components/Header.tsx` or `app/layout.tsx`

```typescript
import { NewsPushBell } from '@/components/NewsPushBell';

export function Header() {
  return (
    <header className="flex items-center justify-between px-4 py-3 bg-white shadow">
      <div className="flex items-center space-x-4">
        <h1 className="text-xl font-bold">Gobar Sahi Times</h1>
      </div>
      
      <div className="flex items-center space-x-4">
        {/* Other header items */}
        <nav className="flex items-center space-x-4">
          <a href="/">Home</a>
          <a href="/news">News</a>
          <a href="/about">About</a>
        </nav>
        
        {/* Add bell button here */}
        <NewsPushBell />
      </div>
    </header>
  );
}
```

---

## 🔧 Environment Variables

**File**: `.env.local` (for local development)

```bash
NEXT_PUBLIC_NEWS_API_BASE_URL=https://api.projectdevops.in
NEXT_PUBLIC_NEWS_VAPID_PUBLIC_KEY=BMuKdCIpflnH4HN_xvBsFZLNe5DiBYKpIhRlgwtr3u5M00oenTPqz9A-XjlVR3itpBo1lIFIapAZJgy-GfM16Io
```

**File**: `.env.production` (for production build)

```bash
NEXT_PUBLIC_NEWS_API_BASE_URL=https://api.projectdevops.in
NEXT_PUBLIC_NEWS_VAPID_PUBLIC_KEY=BMuKdCIpflnH4HN_xvBsFZLNe5DiBYKpIhRlgwtr3u5M00oenTPqz9A-XjlVR3itpBo1lIFIapAZJgy-GfM16Io
```

---

## 🧪 Testing Steps

### 1. Test Service Worker Registration
Open browser console and run:
```javascript
navigator.serviceWorker.getRegistration().then(reg => {
  console.log('Service Worker:', reg);
});
```

### 2. Test Subscription
1. Click the bell button
2. Grant notification permission when prompted
3. Check console for "Subscribed successfully" message
4. Verify bell icon changes to "active" state (with blue background)

### 3. Test Backend Connection
```javascript
// In browser console
fetch('https://api.projectdevops.in/news-push/stats')
  .then(r => r.json())
  .then(d => console.log('Stats:', d));
```

### 4. Send Test Notification
Use the backend test endpoint:
```bash
curl -X POST https://api.projectdevops.in/news-push/test \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Test News Alert",
    "message": "This is a test notification from Gobar Sahi Times!",
    "url": "https://gobarsahitimes.com"
  }'
```

You should see a browser notification appear!

### 5. Test Unsubscribe
1. Click the bell button again (when subscribed)
2. Check console for "Unsubscribed successfully"
3. Verify bell icon changes to "inactive" state

---

## 🎨 Styling Customization

### Option 1: Tailwind CSS (Included)
The component uses Tailwind classes. Customize in `NewsPushBell.tsx`:
```typescript
className="bg-blue-600 hover:bg-blue-700" // Change colors
```

### Option 2: CSS Modules
Create `NewsPushBell.module.css`:
```css
.bellButton {
  position: relative;
  padding: 0.5rem;
  border-radius: 9999px;
  transition: all 0.2s;
}

.bellButton:hover {
  background-color: #e5e7eb;
}

.bellButton.subscribed {
  background-color: #dbeafe;
  color: #2563eb;
}
```

### Option 3: Styled Components
```typescript
import styled from 'styled-components';

const BellButton = styled.button<{ $isSubscribed: boolean }>`
  position: relative;
  padding: 0.5rem;
  border-radius: 50%;
  background-color: ${props => props.$isSubscribed ? '#dbeafe' : '#f3f4f6'};
  color: ${props => props.$isSubscribed ? '#2563eb' : '#6b7280'};
  
  &:hover {
    background-color: ${props => props.$isSubscribed ? '#bfdbfe' : '#e5e7eb'};
  }
`;
```

---

## 🔍 Browser Compatibility

| Browser | Support | Notes |
|---------|---------|-------|
| Chrome 42+ | ✅ Full | Best support |
| Firefox 44+ | ✅ Full | Excellent support |
| Edge 17+ | ✅ Full | Full support |
| Safari 16+ | ✅ Full | macOS & iOS (requires iOS 16.4+) |
| Opera 39+ | ✅ Full | Based on Chromium |
| Samsung Internet | ✅ Full | Version 4.0+ |

**Note**: Safari on iOS requires iOS 16.4+ and macOS Ventura+

---

## 🐛 Troubleshooting

### Issue: Service Worker not registering
**Solution**: 
- Check HTTPS (required for service workers, except localhost)
- Verify `sw.js` is in `public/` folder
- Clear browser cache and reload

### Issue: Permission denied immediately
**Solution**:
- User previously blocked notifications
- Go to browser settings → Site settings → Notifications
- Reset permission for `gobarsahitimes.com`

### Issue: Bell button doesn't appear
**Solution**:
- Check browser console for errors
- Verify `useNewsPush` hook is imported correctly
- Confirm environment variables are set

### Issue: Notifications not appearing
**Solution**:
- Check browser notification settings (System Settings → Notifications)
- Verify backend `/test` endpoint works
- Check service worker console for errors
- Confirm subscription exists in backend stats

### Issue: CORS errors
**Solution**:
- Backend should already have CORS configured
- If issues persist, check FastAPI CORS middleware allows `gobarsahitimes.com`

---

## 📊 Analytics (Optional)

Track notification engagement:

```typescript
// In useNewsPush hook, add tracking
const subscribe = useCallback(async () => {
  // ... existing code ...
  
  // Track subscription
  if (window.gtag) {
    window.gtag('event', 'notification_subscribe', {
      event_category: 'engagement',
      event_label: 'news_push',
    });
  }
}, []);
```

---

## 🚀 Deployment Checklist

- [ ] All 5 files created and committed
- [ ] Environment variables added to `.env.production`
- [ ] GitHub Actions secrets configured (if using CI/CD)
- [ ] Service worker accessible at `/sw.js`
- [ ] Bell button visible in header
- [ ] Test on staging environment
- [ ] Test on multiple browsers
- [ ] Test on mobile devices
- [ ] Deploy to production
- [ ] Monitor backend stats endpoint

---

## 📞 Support

**Backend API Issues**: Check FastAPI logs
**Frontend Issues**: Check browser console
**Service Worker Issues**: Chrome DevTools → Application → Service Workers

**Backend API Status**: `https://api.projectdevops.in/news-push/stats`
**Public Key**: `BMuKdCIpflnH4HN_xvBsFZLNe5DiBYKpIhRlgwtr3u5M00oenTPqz9A-XjlVR3itpBo1lIFIapAZJgy-GfM16Io`

---

**Implementation Date**: December 5, 2025
**Estimated Completion Time**: 30-45 minutes
**Backend Status**: ✅ Ready and tested
