# News Slug System Migration Guide

## Problem
Your old URL: `https://gobarsahitimes.com/news/692ff47f4c8578100cd9ded6`
Uses only the ObjectId, not SEO-friendly.

## Solution
New URL: `https://gobarsahitimes.com/news/bihar-election-2025-100cd9de`
Uses transliterated Hindi + short ID for better SEO.

---

## Step 1: Migrate Existing News (Backend)

### Option A: One-Time Migration (Recommended)

Call the admin endpoint to regenerate slugs for all existing news:

```bash
curl -X POST 'https://api.projectdevops.in/news/regenerate-all-slugs' \
  -H 'Authorization: Bearer YOUR_ADMIN_TOKEN' \
  -H 'Content-Type: application/json'
```

**Response:**
```json
{
  "message": "Successfully regenerated slugs for 150 news posts",
  "updated_count": 150
}
```

This updates all news in MongoDB with proper `slug` fields.

### Option B: Automatic (Lazy Loading)

Do nothing! When you fetch news via:
- `GET /news` 
- `GET /news/{id}`

The backend automatically generates and returns `slug` in the response, even for old posts.

---

## Step 2: Update Frontend URLs

### Current UI Code (Using ObjectId):
```tsx
// ❌ Old way
<Link href={`/news/${post._id}`}>
  {post.title}
</Link>

// Generates: /news/692ff47f4c8578100cd9ded6
```

### New UI Code (Using Slug):
```tsx
// ✅ New way
<Link href={`/news/${post.slug}`}>
  {post.title}
</Link>

// Generates: /news/bihar-election-2025-100cd9de
```

### Backward Compatible Fallback:
```tsx
// ✅ Best approach (handles both old and new)
const newsUrl = post.slug || post._id;

<Link href={`/news/${newsUrl}`}>
  {post.title}
</Link>
```

---

## Step 3: Update Your News Detail Page Route

### Next.js Example:

**File: `pages/news/[slug].tsx` or `app/news/[slug]/page.tsx`**

```tsx
export default function NewsDetailPage({ params }: { params: { slug: string } }) {
  const { slug } = params;
  
  // Fetch by slug (works for both old ObjectId and new slug format)
  const { data: news } = useSWR(`/news/slug/${slug}`, fetcher);
  
  return (
    <article>
      <h1>{news.title}</h1>
      <div dangerouslySetInnerHTML={{ __html: news.content }} />
      {/* ... rest of your UI */}
    </article>
  );
}
```

**The backend handles both:**
- New: `/news/slug/bihar-election-2025-100cd9de` ✅
- Old: `/news/slug/692ff47f4c8578100cd9ded6` ✅

---

## Step 4: Update Meta Tags for SEO

```tsx
<Head>
  <title>{news.meta_title || news.title}</title>
  <meta name="description" content={news.meta_description} />
  <meta name="keywords" content={news.keywords?.join(', ')} />
  
  {/* Canonical URL with new slug */}
  <link rel="canonical" href={`https://gobarsahitimes.com/news/${news.slug}`} />
  
  {/* Open Graph */}
  <meta property="og:url" content={`https://gobarsahitimes.com/news/${news.slug}`} />
  <meta property="og:title" content={news.title} />
  <meta property="og:image" content={news.image_url} />
  
  {/* Twitter */}
  <meta name="twitter:card" content="summary_large_image" />
  <meta name="twitter:url" content={`https://gobarsahitimes.com/news/${news.slug}`} />
</Head>
```

---

## Step 5: Update News List/Card Components

```tsx
// News card component
function NewsCard({ post }: { post: NewsPost }) {
  return (
    <article>
      <Link href={`/news/${post.slug}`}>
        <img src={post.image_url} alt={post.title} />
        <h2>{post.title}</h2>
      </Link>
      <p>{post.meta_description}</p>
    </article>
  );
}
```

---

## Testing

### 1. Test Old URL Redirects
```bash
# Old ObjectId URL should still work
curl https://api.projectdevops.in/news/slug/692ff47f4c8578100cd9ded6

# Should return the same news with new slug in response
```

### 2. Test New Slug URLs
```bash
# New transliterated slug
curl https://api.projectdevops.in/news/slug/bihar-election-2025-100cd9de

# Should return news successfully
```

### 3. Preview Slugs
```bash
curl -X POST https://api.projectdevops.in/news/preview-slug \
  -H 'Content-Type: application/json' \
  -d '{"title": "मोतीझील में फंस जाते हैं परीक्षार्थी"}'

# Response:
# {
#   "title": "मोतीझील में फंस जाते हैं परीक्षार्थी",
#   "slug": "motijheel-men-phans-jaate-hain-pareeksharthee-100cd9de",
#   "url": "https://gtnews18.in/news/motijheel-men-phans-jaate-hain-pareeksharthee-100cd9de",
#   "transliterated": "motijheel-men-phans-jaate-hain-pareeksharthee"
# }
```

---

## Summary: What Changed?

| Before | After |
|--------|-------|
| URL: `/news/692ff47f4c8578100cd9ded6` | URL: `/news/bihar-election-2025-100cd9de` |
| Not SEO-friendly | SEO-optimized |
| Hard to share | Easy to share |
| No semantic meaning | Readable & meaningful |

### UI Changes Required:
1. Replace `post._id` with `post.slug` in links ✅
2. Use `/news/slug/${slug}` API endpoint ✅
3. Update meta tags with `news.slug` ✅

### No Breaking Changes:
- Old URLs still work ✅
- Backend handles both formats ✅
- Automatic slug generation ✅

---

## Quick Migration Checklist

- [ ] Run `/news/regenerate-all-slugs` endpoint as admin
- [ ] Update news list/card components to use `post.slug`
- [ ] Update news detail page to fetch via `/news/slug/${slug}`
- [ ] Update meta tags and canonical URLs
- [ ] Test old URLs still work
- [ ] Deploy frontend changes

**Estimated Time:** 30 minutes
**Breaking Changes:** None (fully backward compatible)
