# GTNews18 – News UI Multimedia & SEO Integration Guide

This document explains how to integrate **multiple images / GIFs / carousels** inside a news story and utilize the new **SEO-optimized slug system** for Hindi content.

The backend already supports this and remains backward compatible:
- Stores the main **feature image** as before (`image_url` in S3).
- Accepts **multiple additional content images** (including GIFs) for a news article.
- Stores each extra image as a `{ url, caption }` object in `content_images[]`.
- Keeps all old news posts fully compatible (they may simply have `content_images = []`).

---

## 1. Data Model (API Responses)

`GET /news` and `GET /news/{id}` return each post as:

```json
{
  "_id": "656f...",
  "title": "Sample News",
  "image_url": "https://...feature-image.jpg",      // unchanged
  "content": "<p>Story HTML ...</p>",               // rich text HTML
  "author_username": "editor1",
  "categories": "politics",
  "tags": ["india", "delhi"],

  "content_images": [
    {
      "url": "https://.../news/content/uuid-1.jpg",
      "caption": "Police at the protest site"
    },
    {
      "url": "https://.../news/content/uuid-2.gif",
      "caption": "GIF explaining the situation"
    }
  ],

  "published": true,
  "created_at": "...",
  "updated_at": "...",
  "comments": [ ... ],
  "views": 0,
  "liked_ips": [],
  "slug": "seo-slug-here",
  "meta_description": "..."
}
```

Notes:

- Old posts may:
  - Omit `content_images` entirely, or
  - Have `content_images: []`.
- The backend normalizes this; UI can always safely treat it as:
  - `content_images: NewsContentImage[] | []`.

### `NewsContentImage` shape

```ts
type NewsContentImage = {
  url: string;
  caption?: string | null;
};
```

---

## 2. Create / Update API Contract

### 2.1. Create News – `POST /news`

**Content type:** `multipart/form-data`.

Existing fields (already used by UI):

- `title: string` (Form)
- `content: string` (Form – HTML from rich text editor)
- `categories: string` (Form, optional)
- `tags: string[]` (Form – repeated keys or framework-specific)
- `published: boolean` (Form)
- `file: UploadFile` (feature image – required)

New/extended fields for content images:

- `content_images: UploadFile[]` (File – optional, can be multiple)
  - Can be JPG/PNG/WebP/GIF etc. (S3 key: `news/content/<uuid>.<ext>`).
- `content_image_captions: string[]` (Form – optional)
  - Must use same ordering as `content_images`.
  - Index `i` of `content_image_captions` corresponds to index `i` of `content_images`.
  - Empty or whitespace-only captions are ignored and stored as `null`.

#### 2.1.1. Example multipart request (React + Axios)

```ts
const formData = new FormData();

formData.append("title", title);
formData.append("content", editorHtml); // from rich text editor
formData.append("categories", selectedCategory);
tags.forEach(tag => formData.append("tags", tag));
formData.append("published", String(isPublished));

// Feature image (existing behavior)
formData.append("file", featureImageFile);

// New: multiple content images + captions
contentImages.forEach((img, index) => {
  formData.append("content_images", img.file);           // UploadFile[]
  formData.append("content_image_captions", img.caption ?? "");
});

await axios.post("/news", formData, {
  headers: {
    "Content-Type": "multipart/form-data",
    Authorization: `Bearer ${token}`,
  },
});
```

> **Important:** Do not change the name `file` – this is the existing feature image field and works fine. New images must use `content_images` and `content_image_captions`.

---

### 2.2. Edit / Update News – `PUT /news/{id}`

The update endpoint now also expects `multipart/form-data`. All fields are optional, so you can send only what changed.

Editable fields:

- `title?: string` (Form)
- `content?: string` (Form – HTML)
- `categories?: string` (Form)
- `tags?: string[]` (Form)
- `published?: boolean` (Form)

Gallery / content images:

- `existing_content_images?: string` (Form)
  - JSON string representing the **kept/updated** gallery items.
  - Shape: `[{ url: string, caption?: string | null }, ...]`.
  - If omitted, backend keeps whatever is already stored in DB.
- `content_images?: UploadFile[]` (File)
  - New images/GIFs to append to the gallery.
- `content_image_captions?: string[]` (Form)
  - Captions aligned by index with `content_images`.

#### 2.2.1. Example update request (React + Axios)

```ts
const formData = new FormData();

if (titleChanged) formData.append("title", title);
if (contentChanged) formData.append("content", editorHtml);
if (categoriesChanged) formData.append("categories", selectedCategory);
if (tagsChanged) tags.forEach(tag => formData.append("tags", tag));
if (publishedChanged) formData.append("published", String(isPublished));

// Existing gallery after user edits (remove / change captions in UI)
const existingGallery = currentGallery.map(img => ({
  url: img.url,
  caption: img.caption ?? null,
}));
formData.append("existing_content_images", JSON.stringify(existingGallery));

// Newly added files in edit mode
newContentImages.forEach((img, index) => {
  formData.append("content_images", img.file);
  formData.append("content_image_captions", img.caption ?? "");
});

await axios.put(`/news/${newsId}`, formData, {
  headers: {
    "Content-Type": "multipart/form-data",
    Authorization: `Bearer ${token}`,
  },
});
```

Notes:

- Feature image is **not** changed by this endpoint (no `file` field here) to avoid touching the existing, stable flow.
- Old posts that never send `existing_content_images` will keep their stored gallery automatically.

---

## 3. UI UX Guidelines

### 3.1. Editor Layout

- Keep the current layout:
  - Title, category, tags, publish toggle.
  - Feature image uploader (unchanged).
  - Rich text editor for `content` (HTML).
- Add a section **“Story Media (Gallery / Inline Images)”** below the editor:
  - Show a list/grid of gallery items:
    - Thumbnail preview.
    - Caption text input.
    - Buttons: *Insert into content*, *Remove*.

### 3.2. Using media inside the story

Two patterns are supported on the frontend without backend changes.

#### A. Bottom gallery / slider

- Render `image_url` as hero at top.
- Render `content` (HTML) as the main story.
- At the bottom, render a carousel/slider using `content_images`:
  - For each `{url, caption}` show image + optional caption.

#### B. Inline markers in HTML

- When user clicks “Insert image into content” for gallery index `i`, insert an HTML marker into editor content, e.g.:

  ```html
  <div data-news-image-index="0" class="news-inline-image"></div>
  ```

- On the article detail page, post-render:
  - Find elements with `data-news-image-index`.
  - Replace them with:

  ```html
  <figure class="news-inline-image">
    <img src={content_images[i].url} alt={content_images[i].caption || title} />
    {content_images[i].caption && <figcaption>{content_images[i].caption}</figcaption>}
  </figure>
  ```

- If index is invalid or `content_images` is empty, skip rendering that placeholder.

### 3.3. Carousels / Slides inside content

- For a group of images selected in the UI, insert a marker like:

  ```html
  <div data-news-carousel="0,1,2" class="news-inline-carousel"></div>
  ```

- At render time, parse `data-news-carousel` into indices `[0,1,2]` and mount a carousel component using those entries from `content_images`.

This keeps DB schema stable and moves presentation concerns to the frontend.

---

## 4. Backward Compatibility

- Old news might have no `content_images` field or have it empty.
- On read:
  - Treat `content_images` as `post.content_images ?? []`.
  - If length is `0`, simply render no gallery or inline media.
- On edit:
  - Initially `currentGallery = []`.
  - User can start uploading new images; they will be appended and stored.

---

## 5. Minimal Rendering Example (React)

```tsx
function NewsDetail({ post }: { post: NewsPost }) {
  const gallery = post.content_images ?? [];

  return (
    <article>
      {post.image_url && (
        <figure className="news-feature-image">
          <img src={post.image_url} alt={post.title} />
        </figure>
      )}

      <h1>{post.title}</h1>

      <div
        className="news-content"
        dangerouslySetInnerHTML={{ __html: post.content }}
      />

      {gallery.length > 0 && (
        <section className="news-gallery">
          {gallery.map((img, idx) => (
            <figure key={idx} className="news-gallery-item">
              <img src={img.url} alt={img.caption || post.title} />
              {img.caption && <figcaption>{img.caption}</figcaption>}
            </figure>
          ))}
        </section>
      )}
    </article>
  );
}
```

This is enough for your frontend team to implement rich multimedia stories without changing the existing feature image system.

---

## 6. SEO-Optimized Slug System for Hindi Content

### 6.1. Problem with Hindi URLs

Previously, Hindi titles created URLs like:
```
https://gobarsahitimes.com/news/मोतीझील-में-फंस-जाते-हैं-परीक्षार्थी-675e3a1b2c4d5e6f7a8b9c0d
```

Which becomes URL-encoded:
```
https://gobarsahitimes.com/news/%E0%A4%AE%E0%A5%8B%E0%A4%A4%E0%A5%80%E0%A4%9D%E0%A5%80%E0%A4%B2-...
```

**Issues:**
- Not SEO-friendly
- Hard to share on social media
- Some browsers/platforms don't handle well
- Google prefers Latin characters in URLs

### 6.2. New Transliteration-Based Slug System

Backend now automatically transliterates Hindi → Latin phonetic + uses short ID:

**Examples:**

| Hindi Title | Generated Slug |
|------------|----------------|
| मोतीझील में फंस जाते हैं परीक्षार्थी | `motijheel-men-phans-jaate-hain-pareeksharthee-a1b2c3d4` |
| पटना में भारी बारिश से तबाही | `patna-men-bhaaree-baarish-se-tabaahee-b2c3d4e5` |
| Bihar Election 2025 Updates | `bihar-election-2025-updates-c3d4e5f6` |
| बिहार में नई सड़क का निर्माण | `bihaar-men-nayee-sarak-kaa-nirmaan-d4e5f6a7` |

**Benefits:**
- ✅ Clean, readable URLs
- ✅ SEO-optimized (Google recommends Latin slugs)
- ✅ Easy to share everywhere
- ✅ Maintains semantic meaning
- ✅ Short IDs keep URLs concise

### 6.3. Backward Compatibility

The system handles:
1. **New slugs** (transliterated): Direct lookup by slug field
2. **Old slugs** (with Hindi): ID extraction and lookup
3. **Direct ObjectId**: Falls back to ID-based search

No old links will break!

### 6.4. Using Slugs in UI

**Get news by slug:**
```ts
// New format
const response = await fetch(`/news/slug/bihar-election-2025-a1b2c3d4`);

// Old format still works
const response = await fetch(`/news/slug/मोतीझील-में-फंस-675e3a1b2c4d5e6f7a8b9c0d`);
```

**Preview slug before publishing:**
```ts
const preview = await axios.post('/news/preview-slug', {
  title: 'मोतीझील में फंस जाते हैं परीक्षार्थी'
});

console.log(preview.data);
// {
//   "title": "मोतीझील में फंस जाते हैं परीक्षार्थी",
//   "slug": "motijheel-men-phans-jaate-hain-pareeksharthee-a1b2c3d4",
//   "url": "https://gtnews18.in/news/motijheel-men-phans-jaate-hain-pareeksharthee-a1b2c3d4",
//   "transliterated": "motijheel-men-phans-jaate-hain-pareeksharthee"
// }
```

**Display canonical URL:**
```tsx
<meta property="og:url" content={`https://gtnews18.in/news/${post.slug}`} />
<link rel="canonical" href={`https://gtnews18.in/news/${post.slug}`} />
```

### 6.5. Automatic Slug Generation

Slugs are auto-generated when:
- Creating new news: `POST /news` → slug stored in `post.slug`
- Updating old news: `GET /news/{id}` → slug auto-generated if missing
- Sitemap/RSS: Uses `slug` field or generates on-the-fly

No manual intervention needed!
