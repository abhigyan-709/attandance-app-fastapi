# Secrets Quick Reference Card
## Fresh News Push Notification System

---

## 🎯 Quick Setup Checklist

### Step 1: Generate VAPID Keys (One Time)
```bash
npm install -g web-push
web-push generate-vapid-keys
```

### Step 2: Add to Backend API GitHub Secrets
| Secret Name | Value Source | Example |
|-------------|--------------|---------|
| `NEWS_VAPID_PUBLIC_KEY` | Copy from generation output | `BMn7G8Kq...` (87 chars) |
| `NEWS_VAPID_PRIVATE_KEY` | Copy from generation output | `xKYz8pQr...` (43 chars) |
| `NEWS_VAPID_SUBJECT` | Your support email | `mailto:connect@projectdevops.in` |
| `NEWS_UI_BASE_URL` | Your news UI URL | `https://gobarsahitimes.com` |

### Step 3: Add to UI (Next.js) GitHub Secrets
| Secret Name | Value Source |
|-------------|--------------|
| `NEXT_PUBLIC_NEWS_VAPID_PUBLIC_KEY` | Same as Backend `NEWS_VAPID_PUBLIC_KEY` |
| `NEXT_PUBLIC_NEWS_API_BASE_URL` | `https://api.projectdevops.in` |
| `NEWS_PUSH_ADMIN_TOKEN` | Optional: Same as Backend `ADMIN_API_TOKEN` |

### Step 4: Update Backend Workflow
Edit `.github/workflows/backend.yaml` - add 4 lines to `.env` creation:
```yaml
echo "NEWS_VAPID_PUBLIC_KEY=${{ secrets.NEWS_VAPID_PUBLIC_KEY }}" >> /home/$USER/.env
echo "NEWS_VAPID_PRIVATE_KEY=${{ secrets.NEWS_VAPID_PRIVATE_KEY }}" >> /home/$USER/.env
echo "NEWS_VAPID_SUBJECT=${{ secrets.NEWS_VAPID_SUBJECT }}" >> /home/$USER/.env
echo "NEWS_UI_BASE_URL=${{ secrets.NEWS_UI_BASE_URL }}" >> /home/$USER/.env
```

### Step 5: Update `/home/ubuntu/app.env` Section
Add these blocks after existing VAPID checks:
```yaml
grep -q '^NEWS_VAPID_PUBLIC_KEY=' /home/ubuntu/app.env && \
  sed -i 's|^NEWS_VAPID_PUBLIC_KEY=.*|NEWS_VAPID_PUBLIC_KEY=${{ secrets.NEWS_VAPID_PUBLIC_KEY }}|' /home/ubuntu/app.env || \
  echo "NEWS_VAPID_PUBLIC_KEY=${{ secrets.NEWS_VAPID_PUBLIC_KEY }}" >> /home/ubuntu/app.env

grep -q '^NEWS_VAPID_PRIVATE_KEY=' /home/ubuntu/app.env && \
  sed -i 's|^NEWS_VAPID_PRIVATE_KEY=.*|NEWS_VAPID_PRIVATE_KEY=${{ secrets.NEWS_VAPID_PRIVATE_KEY }}|' /home/ubuntu/app.env || \
  echo "NEWS_VAPID_PRIVATE_KEY=${{ secrets.NEWS_VAPID_PRIVATE_KEY }}" >> /home/ubuntu/app.env

grep -q '^NEWS_VAPID_SUBJECT=' /home/ubuntu/app.env && \
  sed -i 's|^NEWS_VAPID_SUBJECT=.*|NEWS_VAPID_SUBJECT=${{ secrets.NEWS_VAPID_SUBJECT }}|' /home/ubuntu/app.env || \
  echo "NEWS_VAPID_SUBJECT=${{ secrets.NEWS_VAPID_SUBJECT }}" >> /home/ubuntu/app.env

grep -q '^NEWS_UI_BASE_URL=' /home/ubuntu/app.env && \
  sed -i 's|^NEWS_UI_BASE_URL=.*|NEWS_UI_BASE_URL=${{ secrets.NEWS_UI_BASE_URL }}|' /home/ubuntu/app.env || \
  echo "NEWS_UI_BASE_URL=${{ secrets.NEWS_UI_BASE_URL }}" >> /home/ubuntu/app.env
```

### Step 6: Push & Deploy
```bash
git add .
git commit -m "Add Fresh News Push notification system"
git push origin Abhigyans-Code
```

---

## 📋 Secret Names At A Glance

### Backend API Repository (4 New Secrets)
```
✨ NEWS_VAPID_PUBLIC_KEY
✨ NEWS_VAPID_PRIVATE_KEY  
✨ NEWS_VAPID_SUBJECT
✨ NEWS_UI_BASE_URL
```

### UI Repository (2-3 New Secrets)
```
✨ NEXT_PUBLIC_NEWS_VAPID_PUBLIC_KEY
✨ NEXT_PUBLIC_NEWS_API_BASE_URL
⚠️  NEWS_PUSH_ADMIN_TOKEN (optional)
```

---

## 🧪 Quick Test Commands

### Test Backend Config
```bash
curl https://api.projectdevops.in/news-push/config
```

### Test Backend Stats
```bash
curl https://api.projectdevops.in/news-push/stats
```

### Test UI Environment Variables (Browser Console)
```javascript
console.log(process.env.NEXT_PUBLIC_NEWS_VAPID_PUBLIC_KEY);
console.log(process.env.NEXT_PUBLIC_NEWS_API_BASE_URL);
```

---

## 🔗 Where to Add Secrets

### Backend API
```
GitHub Repo → Settings → Secrets and variables → Actions → New repository secret
```

### UI (Next.js)
```
GitHub Repo → Settings → Secrets and variables → Actions → New repository secret
```

---

## ⚡ Time Estimate
- **VAPID Key Generation**: 1 minute
- **Adding Backend Secrets**: 2 minutes (4 secrets)
- **Adding UI Secrets**: 1 minute (2-3 secrets)
- **Updating Workflow**: 3 minutes
- **Testing**: 2 minutes
- **Total**: ~10 minutes

---

## 🆘 Common Issues

| Issue | Solution |
|-------|----------|
| "VAPID keys not configured" | Add secrets to GitHub, update workflow, redeploy |
| "Invalid VAPID keys" | Regenerate keys, update all secrets |
| UI can't connect | Check `NEXT_PUBLIC_NEWS_API_BASE_URL` is correct |
| No notifications | Check browser permission, test with `/test` endpoint |

---

## 📞 Support Files
- **Full Guide**: `GITHUB_ACTIONS_SECRETS_GUIDE.md`
- **Environment Variables**: `NEWS_PUSH_ENV_VARIABLES.md`
- **Setup Summary**: `NEWS_PUSH_SETUP_SUMMARY.md`

---

**Last Updated**: December 5, 2025
