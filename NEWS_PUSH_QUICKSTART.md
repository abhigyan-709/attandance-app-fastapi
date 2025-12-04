# 🚀 Fresh News Push System - Quick Start Card

## ⚡ 5-Minute Backend Setup

### Step 1: Generate VAPID Keys
```bash
npm install -g web-push
web-push generate-vapid-keys
```

### Step 2: Add to Server .env
```bash
NEWS_VAPID_PUBLIC_KEY=BNcE8xV7...
NEWS_VAPID_PRIVATE_KEY=YourPrivate...
NEWS_VAPID_SUBJECT=mailto:connect@projectdevops.in
```

### Step 3: Restart & Verify
```bash
sudo systemctl restart your-service
curl https://api.projectdevops.in/news-push/health
```

✅ Expected: `{"status": "healthy", "vapid_configured": true}`

---

## 🎨 Frontend Integration (30 Minutes)

### Create 3 Files:
1. `public/news-sw.js` - Service Worker
2. `hooks/useNewsPush.ts` - React Hook  
3. `components/NewsPushBell.tsx` - Bell Button

### Add to Header:
```typescript
import { NewsPushBell } from '@/components/NewsPushBell';

<header>
  <NewsPushBell />
</header>
```

👉 **Full code in:** `NEWS_PUSH_SETUP.md`

---

## 📡 API Endpoints

Base: `https://api.projectdevops.in/news-push`

| Endpoint | Description |
|----------|-------------|
| `GET /config` | Get VAPID public key |
| `POST /subscribe` | Subscribe user |
| `POST /unsubscribe` | Unsubscribe user |
| `GET /stats` | Get statistics |
| `POST /test` | Send test notification |
| `GET /health` | Health check |

---

## ✅ Testing Checklist

- [ ] Generate VAPID keys
- [ ] Add to server .env
- [ ] Restart service
- [ ] Health check returns healthy
- [ ] Config returns public key
- [ ] Create 3 frontend files
- [ ] Add bell to header
- [ ] Click bell → subscribe
- [ ] Check MongoDB: `db.news_subscriptions.find()`
- [ ] Publish news article
- [ ] Receive notification
- [ ] Check stats endpoint

---

## 📚 Documentation

- **Complete Guide:** `NEWS_PUSH_SETUP.md` (all details)
- **Environment Vars:** `NEWS_PUSH_ENV_VARS.md` (quick ref)
- **Implementation:** `NEWS_PUSH_IMPLEMENTATION.md` (summary)

---

## 🆘 Quick Troubleshooting

**Health check unhealthy?**
→ Check .env variables and restart service

**No notifications?**
→ Verify permission granted and subscription active

**Frontend errors?**
→ Check service worker registered in DevTools

**More help:** See `NEWS_PUSH_SETUP.md` troubleshooting section

---

## 🎯 Key Features

- ✅ Separate system (won't conflict with existing)
- ✅ Collection: `news_subscriptions`
- ✅ Variables: `NEWS_VAPID_*`
- ✅ Routes: `/news-push/*`
- ✅ Auto-notify on news publish
- ✅ Works with scheduled posts
- ✅ Browser-native notifications
- ✅ Production-ready

---

**Setup time:** ~45 minutes total
**Status:** Ready to deploy! 🚀
