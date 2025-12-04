# Backend Workflow Update Guide
## Exact Changes Needed for `.github/workflows/backend.yaml`

---

## 📍 Current File Location
```
/Users/abhigyan709/attandance-app-fastapi/.github/workflows/backend.yaml
```

---

## 🔧 Change #1: Add to `.env` Creation Section

**Location**: Around lines 88-106 (inside the "Ensure /home/$USER/.env exists" block)

**Find this section:**
```yaml
if [ ! -f "/home/$USER/.env" ]; then
  echo "Creating .env file..."
  echo "MONGO_URI=${{ secrets.MONGO_URI }}" > /home/$USER/.env
  echo "AWS_ACCESS_KEY_ID=${{ secrets.AWS_ACCESS_KEY_ID }}" >> /home/$USER/.env
  echo "AWS_SECRET_ACCESS_KEY=${{ secrets.AWS_SECRET_ACCESS_KEY }}" >> /home/$USER/.env
  echo "AWS_REGION=${{ secrets.AWS_REGION }}" >> /home/$USER/.env
  echo "AWS_BUCKET_NAME=${{ secrets.AWS_BUCKET_NAME }}" >> /home/$USER/.env
  echo "MAIL_USERNAME=${{ secrets.MAIL_USERNAME }}" >> /home/$USER/.env
  echo "MAIL_PASSWORD=${{ secrets.MAIL_PASSWORD }}" >> /home/$USER/.env
  echo "MAIL_FROM=${{ secrets.MAIL_FROM }}" >> /home/$USER/.env
  echo "MAIL_PORT=${{ secrets.MAIL_PORT }}" >> /home/$USER/.env
  echo "MAIL_SERVER=${{ secrets.MAIL_SERVER }}" >> /home/$USER/.env
  echo "MAIL_STARTTLS=${{ secrets.MAIL_STARTTLS }}" >> /home/$USER/.env
  echo "MAIL_SSL_TLS=${{ secrets.MAIL_SSL_TLS }}" >> /home/$USER/.env
  echo "MAIL_FROM_NAME=${{ secrets.MAIL_FROM_NAME }}" >> /home/$USER/.env
  echo "REDIS_HOST=${{ secrets.REDIS_HOST }}" >> /home/$USER/.env
  echo "REDIS_PORT=${{ secrets.REDIS_PORT }}" >> /home/$USER/.env
  echo "REDIS_PASSWORD=${{ secrets.REDIS_PASSWORD }}" >> /home/$USER/.env
  echo "VAPID_PUBLIC_KEY=${{ secrets.VAPID_PUBLIC_KEY }}" >> /home/ubuntu/app.env
  echo "VAPID_PRIVATE_KEY=${{ secrets.VAPID_PRIVATE_KEY }}" >> /home/ubuntu/app.env
  echo "VAPID_SUBJECT=${{ secrets.VAPID_SUBJECT }}" >> /home/ubuntu/app.env
  echo "ADMIN_API_TOKEN=${{ secrets.ADMIN_API_TOKEN }}" >> /home/ubuntu/app.env
fi
```

**Add these 4 lines BEFORE the `fi`:**
```yaml
  echo "NEWS_VAPID_PUBLIC_KEY=${{ secrets.NEWS_VAPID_PUBLIC_KEY }}" >> /home/$USER/.env
  echo "NEWS_VAPID_PRIVATE_KEY=${{ secrets.NEWS_VAPID_PRIVATE_KEY }}" >> /home/$USER/.env
  echo "NEWS_VAPID_SUBJECT=${{ secrets.NEWS_VAPID_SUBJECT }}" >> /home/$USER/.env
  echo "NEWS_UI_BASE_URL=${{ secrets.NEWS_UI_BASE_URL }}" >> /home/$USER/.env
```

**After Change:**
```yaml
if [ ! -f "/home/$USER/.env" ]; then
  echo "Creating .env file..."
  echo "MONGO_URI=${{ secrets.MONGO_URI }}" > /home/$USER/.env
  # ... existing lines ...
  echo "REDIS_PASSWORD=${{ secrets.REDIS_PASSWORD }}" >> /home/$USER/.env
  echo "VAPID_PUBLIC_KEY=${{ secrets.VAPID_PUBLIC_KEY }}" >> /home/ubuntu/app.env
  echo "VAPID_PRIVATE_KEY=${{ secrets.VAPID_PRIVATE_KEY }}" >> /home/ubuntu/app.env
  echo "VAPID_SUBJECT=${{ secrets.VAPID_SUBJECT }}" >> /home/ubuntu/app.env
  echo "ADMIN_API_TOKEN=${{ secrets.ADMIN_API_TOKEN }}" >> /home/ubuntu/app.env
  echo "NEWS_VAPID_PUBLIC_KEY=${{ secrets.NEWS_VAPID_PUBLIC_KEY }}" >> /home/$USER/.env
  echo "NEWS_VAPID_PRIVATE_KEY=${{ secrets.NEWS_VAPID_PRIVATE_KEY }}" >> /home/$USER/.env
  echo "NEWS_VAPID_SUBJECT=${{ secrets.NEWS_VAPID_SUBJECT }}" >> /home/$USER/.env
  echo "NEWS_UI_BASE_URL=${{ secrets.NEWS_UI_BASE_URL }}" >> /home/$USER/.env
fi
```

---

## 🔧 Change #2: Add to `/home/ubuntu/app.env` Section

**Location**: Around lines 120-145 (after existing `grep -q` checks for VAPID_*)

**Find this section:**
```yaml
grep -q '^VAPID_PUBLIC_KEY=' /home/ubuntu/app.env && \
  sed -i 's|^VAPID_PUBLIC_KEY=.*|VAPID_PUBLIC_KEY=${{ secrets.VAPID_PUBLIC_KEY }}|' /home/ubuntu/app.env || \
  echo "VAPID_PUBLIC_KEY=${{ secrets.VAPID_PUBLIC_KEY }}" >> /home/ubuntu/app.env
grep -q '^VAPID_PRIVATE_KEY=' /home/ubuntu/app.env && \
  sed -i 's|^VAPID_PRIVATE_KEY=.*|VAPID_PRIVATE_KEY=${{ secrets.VAPID_PRIVATE_KEY }}|' /home/ubuntu/app.env || \
  echo "VAPID_PRIVATE_KEY=${{ secrets.VAPID_PRIVATE_KEY }}" >> /home/ubuntu/app.env
grep -q '^VAPID_SUBJECT=' /home/ubuntu/app.env && \
  sed -i 's|^VAPID_SUBJECT=.*|VAPID_SUBJECT=${{ secrets.VAPID_SUBJECT }}|' /home/ubuntu/app.env || \
  echo "VAPID_SUBJECT=${{ secrets.VAPID_SUBJECT }}" >> /home/ubuntu/app.env
```

**Add these blocks AFTER the existing VAPID checks:**
```yaml
# Fresh News Push VAPID Keys (separate from other notification systems)
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

**After Change:**
```yaml
grep -q '^VAPID_SUBJECT=' /home/ubuntu/app.env && \
  sed -i 's|^VAPID_SUBJECT=.*|VAPID_SUBJECT=${{ secrets.VAPID_SUBJECT }}|' /home/ubuntu/app.env || \
  echo "VAPID_SUBJECT=${{ secrets.VAPID_SUBJECT }}" >> /home/ubuntu/app.env

# Fresh News Push VAPID Keys (separate from other notification systems)
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

# Final run (your current container that stays up)
docker run -d --name attendance-app -p 8000:8000 \
```

---

## 📋 Summary of Changes

### Files Modified: 1
- `.github/workflows/backend.yaml`

### Lines Added: 20 lines total
- **4 lines** in `.env` creation section (Change #1)
- **16 lines** in `/home/ubuntu/app.env` section (Change #2)

### Secrets Referenced: 4 new secrets
1. `NEWS_VAPID_PUBLIC_KEY`
2. `NEWS_VAPID_PRIVATE_KEY`
3. `NEWS_VAPID_SUBJECT`
4. `NEWS_UI_BASE_URL`

---

## ✅ Pre-Commit Checklist

Before committing these changes, ensure:

- [ ] All 4 secrets added to GitHub repository settings
- [ ] VAPID keys generated using `web-push generate-vapid-keys`
- [ ] `NEWS_UI_BASE_URL` points to correct UI domain
- [ ] `NEWS_VAPID_SUBJECT` is a valid mailto: or https: URL
- [ ] No typos in secret names (must match exactly)

---

## 🚀 Deployment Process

1. **Make changes to `backend.yaml`** (as shown above)
2. **Commit and push**:
   ```bash
   git add .github/workflows/backend.yaml
   git commit -m "Add NEWS_VAPID secrets to deployment workflow"
   git push origin Abhigyans-Code
   ```
3. **GitHub Actions will automatically**:
   - Build Docker image
   - Push to ECR
   - Deploy to EC2
   - Create/update `.env` files with new secrets
4. **Verify deployment**:
   ```bash
   curl https://api.projectdevops.in/news-push/config
   ```

---

## 🧪 Testing After Deployment

### Test 1: Check Config Endpoint
```bash
curl https://api.projectdevops.in/news-push/config
```

**Expected Response:**
```json
{
  "public_key": "BMn7G8KqXJK7MxP...",
  "subject": "mailto:connect@projectdevops.in"
}
```

### Test 2: Check Stats Endpoint
```bash
curl https://api.projectdevops.in/news-push/stats
```

**Expected Response:**
```json
{
  "total_subscriptions": 0,
  "active_subscriptions": 0,
  "last_broadcast_at": null,
  "collection": "news_subscriptions"
}
```

### Test 3: Check Environment Variables on Server
```bash
# SSH into EC2
ssh -i your-key.pem ubuntu@your-ec2-ip

# Check if variables are in app.env
cat /home/ubuntu/app.env | grep NEWS_VAPID

# Expected output:
# NEWS_VAPID_PUBLIC_KEY=BMn7...
# NEWS_VAPID_PRIVATE_KEY=xKY...
# NEWS_VAPID_SUBJECT=mailto:...
# NEWS_UI_BASE_URL=https://...
```

---

## 🆘 Troubleshooting

### Issue: Secrets not found in workflow

**Error Message:**
```
Warning: Secret NEWS_VAPID_PUBLIC_KEY is not set
```

**Solution:**
1. Go to: GitHub Repo → Settings → Secrets → Actions
2. Verify all 4 secrets are added
3. Check for typos in secret names
4. Re-run workflow

### Issue: Variables not in container

**Error Message:**
```
NEWS_VAPID keys not configured. Push notifications will not work.
```

**Solution:**
1. SSH into EC2: `ssh ubuntu@your-ec2-ip`
2. Check `.env` file: `cat /home/ubuntu/app.env | grep NEWS`
3. If missing, manually add:
   ```bash
   echo "NEWS_VAPID_PUBLIC_KEY=your-key" >> /home/ubuntu/app.env
   docker restart attendance-app
   ```

### Issue: Workflow fails on deployment

**Solution:**
1. Check GitHub Actions logs for specific error
2. Verify EC2 instance is running and accessible
3. Confirm Docker is installed on EC2
4. Check AWS credentials in secrets

---

## 📞 Need Help?

- **Full Documentation**: `GITHUB_ACTIONS_SECRETS_GUIDE.md`
- **Quick Reference**: `SECRETS_QUICK_REFERENCE.md`
- **Environment Variables**: `NEWS_PUSH_ENV_VARIABLES.md`

---

**Last Updated**: December 5, 2025
**Target Branch**: `Abhigyans-Code`
