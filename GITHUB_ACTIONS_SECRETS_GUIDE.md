# GitHub Actions Secrets Configuration Guide
## Fresh News Push Notification System

This guide lists all secrets and environment variables needed for the **Fresh News Push Notification System** in both Backend API and UI repositories.

---

## 📋 Overview

The Fresh News Push system uses **separate VAPID keys** (`NEWS_VAPID_*`) to ensure complete isolation from other notification systems.

**Backend API**: `api.projectdevops.in` (FastAPI)
**UI**: `gobarsahitimes.com` (Next.js)

---

## 🔧 Backend API GitHub Actions Secrets

### Repository Settings Path:
```
Your Backend Repo → Settings → Secrets and variables → Actions → New repository secret
```

### Required Secrets for Fresh News Push System

#### 1. **NEWS_VAPID_PUBLIC_KEY** ✨ NEW
- **Description**: Public VAPID key for news push subscriptions (browser-side)
- **Used in**: Backend API + will be shared with UI team
- **Format**: Base64 URL-safe string (87 characters)
- **Example**: `BMn7G8KqXJK7MxP4nQo9vH2L8Yk3Tw1QzR6sE5M4kP3Vc2Zx9Y8W7V6U5T4S3R2Q1P0O9N8M7L6K5J4I3H2G1F0E`
- **How to Generate**: See "Generating VAPID Keys" section below

#### 2. **NEWS_VAPID_PRIVATE_KEY** ✨ NEW
- **Description**: Private VAPID key for news push (server-side only, never share)
- **Used in**: Backend API only (server-side signing)
- **Format**: Base64 URL-safe string (43 characters)
- **Example**: `xKYz8pQr3mNv2wTu1sVw0xYz9aB8cD7eF6gH5iJ4kL3M2N`
- **Security**: ⚠️ NEVER commit to code, NEVER share with frontend

#### 3. **NEWS_VAPID_SUBJECT** ✨ NEW
- **Description**: Contact email/URL for news push service (shown to browser vendors)
- **Used in**: Backend API (VAPID claims)
- **Format**: `mailto:your-email@domain.com` or `https://your-domain.com`
- **Example**: `mailto:connect@projectdevops.in`
- **Recommendation**: Use a monitored support email

#### 4. **NEWS_UI_BASE_URL** ✨ NEW
- **Description**: Base URL of your news UI for generating notification links
- **Used in**: Backend API (notification payload URLs)
- **Format**: Full HTTPS URL without trailing slash
- **Example**: `https://gobarsahitimes.com`
- **Purpose**: Creates clickable URLs like `https://gobarsahitimes.com/news/article-slug`

### Existing Secrets (Already Configured)
These are already in your backend GitHub Actions but listed for reference:

- `AWS_ACCESS_KEY_ID` - AWS credentials
- `AWS_SECRET_ACCESS_KEY` - AWS credentials
- `AWS_REGION` - AWS region (e.g., `ap-south-1`)
- `AWS_ACCOUNT_ID` - AWS account ID
- `AWS_BUCKET_NAME` - S3 bucket for news images
- `ECR_REPOSITORY` - ECR repo name
- `SSH_PRIVATE_KEY` - EC2 SSH key
- `EC2_HOST` - EC2 public IP
- `EC2_USER` - EC2 username (e.g., `ubuntu`)
- `MONGO_URI` - MongoDB connection string
- `MAIL_*` - Email configuration (8 secrets)
- `REDIS_*` - Redis configuration (3 secrets)
- `GEMINI_API_KEY` - AI API key
- `GEMINI_MODEL` - AI model name
- `ADMIN_API_TOKEN` - Admin authentication

---

## 🎨 UI (Next.js) GitHub Actions Secrets

### Repository Settings Path:
```
Your UI Repo → Settings → Secrets and variables → Actions → New repository secret
```

### Required Secrets for Fresh News Push System

#### 1. **NEXT_PUBLIC_NEWS_VAPID_PUBLIC_KEY** ✨ NEW
- **Description**: Public VAPID key for frontend subscription (browser-side)
- **Used in**: UI Service Worker and subscription hooks
- **Format**: Same as `NEWS_VAPID_PUBLIC_KEY` from backend
- **Value**: **COPY EXACT VALUE** from Backend `NEWS_VAPID_PUBLIC_KEY`
- **Exposed**: Yes (safe to expose in client-side code as `NEXT_PUBLIC_*`)

#### 2. **NEXT_PUBLIC_NEWS_API_BASE_URL** ✨ NEW
- **Description**: Backend API base URL for news push endpoints
- **Used in**: UI API calls to subscribe/unsubscribe/test notifications
- **Format**: Full HTTPS URL without trailing slash
- **Example**: `https://api.projectdevops.in`
- **Exposed**: Yes (safe to expose in client-side code)

#### 3. **NEWS_PUSH_ADMIN_TOKEN** ✨ NEW (Optional)
- **Description**: Admin API token for testing push notifications from UI admin panel
- **Used in**: UI admin interface for sending test notifications
- **Format**: Secure random string
- **Value**: **COPY EXACT VALUE** from Backend `ADMIN_API_TOKEN`
- **Exposed**: No (only used in server-side API routes if you build admin UI)

### Existing UI Secrets (If Any)
Your UI may already have secrets like:
- `NEXT_PUBLIC_API_URL` - May already exist, separate from news push
- Database connection strings
- Third-party API keys
- Analytics tokens

---

## 🔑 Generating VAPID Keys

### Method 1: Using `web-push` npm package (Recommended)

```bash
# Install web-push CLI globally
npm install -g web-push

# Generate VAPID keys
web-push generate-vapid-keys

# Output will look like:
===============VAPID KEYS===============
Public Key:
BMn7G8KqXJK7MxP4nQo9vH2L8Yk3Tw1QzR6sE5M4kP3Vc2Zx9Y8W7V6U5T4S3R2Q1P0O9N8M7L6K5J4I3H2G1F0E

Private Key:
xKYz8pQr3mNv2wTu1sVw0xYz9aB8cD7eF6gH5iJ4kL3M2N
========================================
```

### Method 2: Using Python `py-vapid`

```bash
# Install py-vapid
pip install py-vapid

# Generate keys
vapid --gen

# Output will show public and private keys
```

### Method 3: Using Online Generator (Not Recommended for Production)
- Visit: https://vapidkeys.com/
- ⚠️ Only use for testing; for production, generate locally for security

---

## 📝 Step-by-Step: Adding Secrets to Backend API

### 1. Generate VAPID Keys
```bash
npm install -g web-push
web-push generate-vapid-keys
```

### 2. Copy Public Key
- Copy the **Public Key** output
- Go to: Backend Repo → Settings → Secrets → Actions → New secret
- Name: `NEWS_VAPID_PUBLIC_KEY`
- Value: Paste public key
- Click "Add secret"

### 3. Copy Private Key
- Copy the **Private Key** output
- Go to: Backend Repo → Settings → Secrets → Actions → New secret
- Name: `NEWS_VAPID_PRIVATE_KEY`
- Value: Paste private key
- Click "Add secret"

### 4. Add Subject
- Go to: Backend Repo → Settings → Secrets → Actions → New secret
- Name: `NEWS_VAPID_SUBJECT`
- Value: `mailto:connect@projectdevops.in` (or your support email)
- Click "Add secret"

### 5. Add UI Base URL
- Go to: Backend Repo → Settings → Secrets → Actions → New secret
- Name: `NEWS_UI_BASE_URL`
- Value: `https://gobarsahitimes.com`
- Click "Add secret"

---

## 📝 Step-by-Step: Adding Secrets to UI Repository

### 1. Copy Public Key from Backend
- Go to your local terminal where you generated keys
- Copy the **Public Key** (same one used for backend)

### 2. Add to UI Secrets
- Go to: UI Repo → Settings → Secrets → Actions → New secret
- Name: `NEXT_PUBLIC_NEWS_VAPID_PUBLIC_KEY`
- Value: Paste the same public key
- Click "Add secret"

### 3. Add API Base URL
- Go to: UI Repo → Settings → Secrets → Actions → New secret
- Name: `NEXT_PUBLIC_NEWS_API_BASE_URL`
- Value: `https://api.projectdevops.in`
- Click "Add secret"

### 4. Add Admin Token (Optional)
- If your backend has `ADMIN_API_TOKEN`, copy its value
- Go to: UI Repo → Settings → Secrets → Actions → New secret
- Name: `NEWS_PUSH_ADMIN_TOKEN`
- Value: Paste the admin token
- Click "Add secret"

---

## 🔄 Updating Backend GitHub Actions Workflow

Your current backend workflow at `.github/workflows/backend.yaml` needs to include the new `NEWS_VAPID_*` secrets.

### Add to `.env` Creation Section

Find this section in your workflow (around line 88-106):

```yaml
# Ensure /home/$USER/.env exists and has runtime vars
if [ ! -f "/home/$USER/.env" ]; then
  echo "Creating .env file..."
  echo "MONGO_URI=${{ secrets.MONGO_URI }}" > /home/$USER/.env
  # ... other secrets ...
fi
```

**Add these lines** after the existing secrets:

```yaml
echo "NEWS_VAPID_PUBLIC_KEY=${{ secrets.NEWS_VAPID_PUBLIC_KEY }}" >> /home/$USER/.env
echo "NEWS_VAPID_PRIVATE_KEY=${{ secrets.NEWS_VAPID_PRIVATE_KEY }}" >> /home/$USER/.env
echo "NEWS_VAPID_SUBJECT=${{ secrets.NEWS_VAPID_SUBJECT }}" >> /home/$USER/.env
echo "NEWS_UI_BASE_URL=${{ secrets.NEWS_UI_BASE_URL }}" >> /home/$USER/.env
```

### Add to `/home/ubuntu/app.env` Section

Find this section (around line 120-145):

```yaml
grep -q '^VAPID_PUBLIC_KEY=' /home/ubuntu/app.env && \
  sed -i 's|^VAPID_PUBLIC_KEY=.*|VAPID_PUBLIC_KEY=${{ secrets.VAPID_PUBLIC_KEY }}|' /home/ubuntu/app.env || \
  echo "VAPID_PUBLIC_KEY=${{ secrets.VAPID_PUBLIC_KEY }}" >> /home/ubuntu/app.env
```

**Add these blocks** after the existing VAPID checks:

```yaml
# News Push VAPID Keys (separate from other systems)
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

---

## 🔄 UI GitHub Actions Workflow Example

Create or update `.github/workflows/deploy.yml` in your UI repository:

```yaml
name: Deploy Next.js UI

on:
  push:
    branches: [main, production]

jobs:
  deploy:
    runs-on: ubuntu-latest
    
    steps:
      - name: Checkout code
        uses: actions/checkout@v3
      
      - name: Setup Node.js
        uses: actions/setup-node@v3
        with:
          node-version: '18'
      
      - name: Install dependencies
        run: npm ci
      
      - name: Create .env.production
        run: |
          echo "NEXT_PUBLIC_NEWS_VAPID_PUBLIC_KEY=${{ secrets.NEXT_PUBLIC_NEWS_VAPID_PUBLIC_KEY }}" > .env.production
          echo "NEXT_PUBLIC_NEWS_API_BASE_URL=${{ secrets.NEXT_PUBLIC_NEWS_API_BASE_URL }}" >> .env.production
          echo "NEWS_PUSH_ADMIN_TOKEN=${{ secrets.NEWS_PUSH_ADMIN_TOKEN }}" >> .env.production
      
      - name: Build Next.js app
        run: npm run build
        env:
          NEXT_PUBLIC_NEWS_VAPID_PUBLIC_KEY: ${{ secrets.NEXT_PUBLIC_NEWS_VAPID_PUBLIC_KEY }}
          NEXT_PUBLIC_NEWS_API_BASE_URL: ${{ secrets.NEXT_PUBLIC_NEWS_API_BASE_URL }}
      
      - name: Deploy to production
        run: |
          # Your deployment commands here
          # e.g., rsync, scp, Vercel, Netlify, etc.
```

---

## 🧪 Testing the Configuration

### Backend API Test

```bash
# 1. Check VAPID config endpoint
curl https://api.projectdevops.in/news-push/config

# Expected response:
{
  "public_key": "BMn7G8KqXJK7MxP...",
  "subject": "mailto:connect@projectdevops.in"
}

# 2. Check stats endpoint
curl https://api.projectdevops.in/news-push/stats

# Expected response:
{
  "total_subscriptions": 0,
  "active_subscriptions": 0,
  "last_broadcast_at": null,
  "collection": "news_subscriptions"
}
```

### UI Test

```javascript
// In browser console on gobarsahitimes.com
console.log(process.env.NEXT_PUBLIC_NEWS_VAPID_PUBLIC_KEY);
console.log(process.env.NEXT_PUBLIC_NEWS_API_BASE_URL);

// Should output:
// "BMn7G8KqXJK7MxP..."
// "https://api.projectdevops.in"
```

---

## 📊 Secret Summary Table

| Secret Name | Backend API | UI (Next.js) | Description | Exposed to Browser? |
|-------------|-------------|--------------|-------------|---------------------|
| `NEWS_VAPID_PUBLIC_KEY` | ✅ Required | - | Public VAPID key (server) | No |
| `NEWS_VAPID_PRIVATE_KEY` | ✅ Required | - | Private VAPID key | No |
| `NEWS_VAPID_SUBJECT` | ✅ Required | - | Contact email/URL | No |
| `NEWS_UI_BASE_URL` | ✅ Required | - | UI base URL | No |
| `NEXT_PUBLIC_NEWS_VAPID_PUBLIC_KEY` | - | ✅ Required | Public VAPID key (client) | Yes (safe) |
| `NEXT_PUBLIC_NEWS_API_BASE_URL` | - | ✅ Required | API base URL | Yes (safe) |
| `NEWS_PUSH_ADMIN_TOKEN` | - | ⚠️ Optional | Admin testing token | No |

**Total New Secrets**: 
- Backend: **4 new secrets**
- UI: **2-3 new secrets** (3rd is optional)

---

## 🔒 Security Best Practices

### ✅ DO:
- Generate VAPID keys locally using CLI tools
- Store private keys only in GitHub Secrets (never in code)
- Use `NEXT_PUBLIC_*` prefix only for truly public values
- Rotate keys periodically (every 6-12 months)
- Monitor unauthorized access via stats endpoint
- Use HTTPS for all API endpoints

### ❌ DON'T:
- Never commit `.env` files to Git
- Never share `NEWS_VAPID_PRIVATE_KEY` with anyone
- Don't expose private keys in client-side code
- Don't use same VAPID keys across different apps
- Don't hardcode secrets in source code

---

## 🆘 Troubleshooting

### "VAPID keys not configured" in logs

**Solution**: 
1. Check secrets are added in GitHub repo settings
2. Verify workflow includes secrets in `.env` creation
3. Redeploy after adding secrets

### "Invalid VAPID keys" error

**Solution**:
1. Regenerate keys using `web-push generate-vapid-keys`
2. Update all secrets (backend + UI)
3. Clear browser cache and re-subscribe

### UI can't fetch public key

**Solution**:
1. Check `NEXT_PUBLIC_NEWS_API_BASE_URL` points to correct API
2. Verify backend `/news-push/config` endpoint returns 200
3. Check CORS settings on backend allow UI domain

### Notifications not sending

**Solution**:
1. Test endpoint: `POST /news-push/test`
2. Check backend logs for `WebPushException`
3. Verify user subscription is active in MongoDB
4. Confirm browser granted notification permission

---

## 📞 Support

**Backend API Issues**: Check FastAPI logs at EC2 instance
**UI Issues**: Check Next.js build logs in GitHub Actions
**VAPID Issues**: Regenerate keys and update all secrets

**Generated on**: December 5, 2025
**System**: Fresh News Push Notification System
**Version**: 1.0.0
