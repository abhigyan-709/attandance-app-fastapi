# News Push System - Environment Variables Quick Reference

## ⚡ Quick Setup (5 Minutes)

### 1. Generate VAPID Keys
```bash
npm install -g web-push
web-push generate-vapid-keys
```

### 2. Add to Server .env File
```bash
# Add these 3 lines to your .env file
NEWS_VAPID_PUBLIC_KEY=BNcE8xV7r9RhXcZmvFyQ_z8J...
NEWS_VAPID_PRIVATE_KEY=YourPrivateKeyHere123...
NEWS_VAPID_SUBJECT=mailto:connect@projectdevops.in

# Optional (already have default)
NEWS_BASE_URL=https://gobarsahitimes.com
```

### 3. Restart Service
```bash
sudo systemctl restart your-fastapi-service
```

### 4. Verify
```bash
curl https://api.projectdevops.in/news-push/health
```

---

## 📋 Complete Variable List

### Backend Environment Variables

| Variable | Required | Example | Description |
|----------|----------|---------|-------------|
| `NEWS_VAPID_PUBLIC_KEY` | ✅ Yes | `BNcE8xV7...` | VAPID public key for frontend subscription |
| `NEWS_VAPID_PRIVATE_KEY` | ✅ Yes | `YourPrivate...` | VAPID private key for sending notifications |
| `NEWS_VAPID_SUBJECT` | ✅ Yes | `mailto:connect@projectdevops.in` | VAPID subject (email or URL) |
| `NEWS_BASE_URL` | ⚠️ Optional | `https://gobarsahitimes.com` | Base URL for notification links (defaults to gtnews18.in) |

---

## 🔐 GitHub Actions Secrets

Add these secrets to your GitHub repository:

1. **NEWS_VAPID_PUBLIC_KEY**
   - Same as backend public key
   
2. **NEWS_VAPID_PRIVATE_KEY**
   - Same as backend private key
   
3. **NEWS_VAPID_SUBJECT**
   - Same as backend subject
   
4. **NEWS_BASE_URL**
   - Same as backend URL

### How to Add:
1. Go to your GitHub repository
2. Navigate to: **Settings** → **Secrets and variables** → **Actions**
3. Click **New repository secret**
4. Add each secret with exact name and value

---

## 🚨 Important Notes

### Separate from Other Systems
- These variables are **completely separate** from any other push notification system
- Uses its own MongoDB collection: `news_subscriptions`
- Does NOT interfere with existing `push_tokens` or other collections
- Prefix `NEWS_` ensures no conflicts

### Security
- ⚠️ **NEVER** commit VAPID keys to git
- ⚠️ Keep private key secret (only on server)
- ✅ Public key can be exposed to frontend (it's meant to be public)
- ✅ Add `.env` to `.gitignore`

### Production vs Development

**Production (.env on server):**
```bash
NEWS_VAPID_PUBLIC_KEY=BProduction...
NEWS_VAPID_PRIVATE_KEY=ProductionPrivate...
NEWS_VAPID_SUBJECT=mailto:connect@projectdevops.in
NEWS_BASE_URL=https://gobarsahitimes.com
```

**Development (local .env):**
```bash
NEWS_VAPID_PUBLIC_KEY=BDevelopment...
NEWS_VAPID_PRIVATE_KEY=DevelopmentPrivate...
NEWS_VAPID_SUBJECT=mailto:dev@localhost
NEWS_BASE_URL=http://localhost:3000
```

---

## ✅ Validation Checklist

Run these checks after setting variables:

### 1. Check Variables Loaded
```bash
# SSH to server
ssh user@api.projectdevops.in

# Check if variables are set (don't print values for security)
env | grep NEWS_VAPID | wc -l
# Should output: 3 or more
```

### 2. Health Check Endpoint
```bash
curl https://api.projectdevops.in/news-push/health
```

**Expected Response:**
```json
{
  "status": "healthy",
  "vapid_configured": true,
  "subject": "mailto:connect@projectdevops.in",
  "service": "news-push"
}
```

### 3. Config Endpoint (Public Key)
```bash
curl https://api.projectdevops.in/news-push/config
```

**Expected Response:**
```json
{
  "public_key": "BNcE8xV7...",
  "subject": "mailto:connect@projectdevops.in"
}
```

### 4. Stats Endpoint
```bash
curl https://api.projectdevops.in/news-push/stats
```

**Expected Response:**
```json
{
  "total_subscriptions": 0,
  "total_notifications_sent": 0,
  "last_notification_at": null,
  "oldest_subscription": null,
  "newest_subscription": null
}
```

---

## 🐛 Troubleshooting

### Error: "NEWS_VAPID keys not configured"

**Cause:** Environment variables not loaded

**Fix:**
```bash
# 1. Check .env file exists
ls -la /path/to/your/app/.env

# 2. Check .env content (carefully, don't expose keys)
cat /path/to/your/app/.env | grep NEWS_VAPID_PUBLIC_KEY

# 3. Restart service
sudo systemctl restart your-service

# 4. Check logs
sudo journalctl -u your-service -f
```

### Error: "Invalid VAPID key format"

**Cause:** Public key doesn't start with 'B'

**Fix:**
```bash
# Regenerate keys
web-push generate-vapid-keys

# Ensure public key starts with 'B'
# Example: BNcE8xV7r9RhXcZmvFyQ_z8J...
```

### Health Check Returns "unhealthy"

**Possible Issues:**
1. Environment variables not set
2. Typo in variable names (must be exact: `NEWS_VAPID_PUBLIC_KEY`)
3. Service not restarted after adding variables
4. Wrong .env file location

**Fix:**
```bash
# Check variable names match exactly
grep NEWS_VAPID /path/to/.env

# Restart service
sudo systemctl restart your-service

# Check health
curl http://localhost:8000/news-push/health
```

---

## 📊 Monitoring

### Check Configuration
```bash
# Health check (shows if VAPID configured)
curl https://api.projectdevops.in/news-push/health

# Get public key (verifies backend serving correct key)
curl https://api.projectdevops.in/news-push/config
```

### Check Activity
```bash
# Get subscription statistics
curl https://api.projectdevops.in/news-push/stats

# Check MongoDB
mongo
use testdb
db.news_subscriptions.countDocuments({is_active: true})
```

---

## 🎯 Summary

**3 Required Variables:**
1. `NEWS_VAPID_PUBLIC_KEY` - For frontend subscription
2. `NEWS_VAPID_PRIVATE_KEY` - For backend sending
3. `NEWS_VAPID_SUBJECT` - VAPID contact info

**1 Optional Variable:**
4. `NEWS_BASE_URL` - For notification URLs (has default)

**Setup Time:** 5 minutes
**System Status:** Independent, separate from other push systems

All variables use `NEWS_` prefix to avoid conflicts! 🎉
