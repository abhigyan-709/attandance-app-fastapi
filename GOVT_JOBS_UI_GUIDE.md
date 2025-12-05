# Government Jobs - Complete UI Implementation Guide

## 📋 Table of Contents
1. [Admin Dashboard UI](#admin-dashboard-ui)
2. [User Interface UI](#user-interface-ui)
3. [Shared Components](#shared-components)
4. [API Integration Guide](#api-integration-guide)
5. [State Management](#state-management)

---

## 🔐 ADMIN DASHBOARD UI

### 1. Admin Dashboard Home
**Route**: `/admin/govt-jobs`

#### Components Required:
```jsx
// AdminDashboard.jsx
- DashboardStats (cards with counts)
- QuickActions (create, scrape, bulk upload buttons)
- RecentJobs (table with latest 10 jobs)
- SystemHealth (scraping status, last run times)
```

#### Layout:
```
┌─────────────────────────────────────────────────────┐
│  📊 Dashboard                           🔴 Admin    │
├─────────────────────────────────────────────────────┤
│  ┌──────┐  ┌──────┐  ┌──────┐  ┌──────┐          │
│  │ 1,234 │  │  567 │  │   89 │  │   45 │          │
│  │Active │  │ New  │  │Closing│  │Pending│         │
│  │ Jobs  │  │Today │  │ Soon  │  │Review │         │
│  └──────┘  └──────┘  └──────┘  └──────┘          │
│                                                      │
│  Quick Actions:                                     │
│  [+ Create Job]  [📥 Import]  [🔄 Run Scraper]    │
│                                                      │
│  Recent Jobs:                                       │
│  ┌────────────────────────────────────────────┐   │
│  │ Title         Org    Status   Views  Actions│   │
│  │ UPSC Engg... UPSC   Active   1.2K   Edit/Del│   │
│  │ SSC Clerk... SSC    Pending  0     Approve  │   │
│  └────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────┘
```

#### API Calls:
```javascript
// Fetch dashboard stats
GET /govt-jobs/stats/dashboard

// Fetch recent jobs
GET /govt-jobs/admin/all?page=1&limit=10
```

---

### 2. Admin Job Listing Page
**Route**: `/admin/govt-jobs/list`

#### Components:
```jsx
// AdminJobList.jsx
- FilterBar (status, type, category, search)
- JobsTable (sortable columns, bulk actions)
- Pagination
- BulkActionsToolbar
```

#### Features:
- **Filters**: Status, Job Type, Category, Organization, Date Range
- **Bulk Actions**: Activate, Close, Delete, Export
- **Quick Edit**: Toggle featured, urgent flags
- **Search**: Title, organization, keywords
- **Sort**: By date, views, clicks, status
- **Export**: CSV/Excel export

#### Layout:
```
┌─────────────────────────────────────────────────────┐
│  All Jobs                        [+ Create New]     │
├─────────────────────────────────────────────────────┤
│  Filters: [Status▾] [Type▾] [Category▾] [Search🔍]│
│                                                      │
│  [✓ Select All] Bulk: [Activate] [Close] [Delete] │
│                                                      │
│  ┌────────────────────────────────────────────┐   │
│  │☐ Title          Org   Status Type  Actions │   │
│  │☐ UPSC Engineer  UPSC  Active Central [...]│   │
│  │☐ SSC Clerk      SSC   Closed Central [...]│   │
│  │☐ BPSC Deputy... BPSC  Pending State  [...]│   │
│  └────────────────────────────────────────────┘   │
│  Showing 1-20 of 1,234     [← 1 2 3 ... 62 →]    │
└─────────────────────────────────────────────────────┘
```

#### Table Columns:
- Checkbox (bulk select)
- Title (link to edit)
- Organization
- Status (badge with color)
- Job Type
- Posted Date
- Application End
- Views / Clicks
- Badges (NEW, FEATURED, URGENT)
- Actions (Edit, Delete, View, Duplicate)

---

### 3. Create/Edit Job Form
**Route**: `/admin/govt-jobs/create` or `/admin/govt-jobs/edit/:id`

#### Form Sections:

**Tab 1: Basic Information**
```jsx
- Title * (auto-generate slug)
- Slug (editable, check availability)
- Short Description * (500 chars)
- Full Description * (rich text editor)
- Organization Name * + Short Name *
- Logo URL (image upload)
```

**Tab 2: Job Details**
```jsx
- Job Type * (dropdown: Central/State/PSU/Autonomous)
- State (if State Government)
- Category * (dropdown: 13 categories)
- Post Name *
- Total Vacancies * (number input)
- Reserved Vacancies (OBC, SC, ST, EWS, PwD)
```

**Tab 3: Eligibility**
```jsx
- Age Min/Max (numbers)
- Qualification * (tags/chips)
- Experience (years)
- Required Skills (tags)
```

**Tab 4: Salary & Benefits**
```jsx
- Salary Min/Max (numbers)
- Salary Text * (display text, e.g., "₹50,000 - ₹1,00,000")
- Other Benefits (textarea)
```

**Tab 5: Dates & Application**
```jsx
- Notification Date
- Application Begin Date *
- Application End Date *
- Last Date Fee Payment
- Exam Date
- Admit Card Date
- Result Date
- Application Mode * (Online/Offline/Both)
```

**Tab 6: Fees & Links**
```jsx
- Application Fee General/OBC/SC/ST (numbers)
- Notification Link * (URL)
- Apply Link * (URL)
- Official Website (URL)
- Syllabus Link (URL)
```

**Tab 7: Additional Info**
```jsx
- Work Locations * (chips/tags)
- Selection Process (steps)
- Important Notes (textarea)
- Documents Required (list)
```

**Tab 8: SEO & Settings**
```jsx
- Meta Title (optional)
- Meta Description (optional)
- Tags (chips)
- Status * (Draft/Pending/Active/Closed/Cancelled)
- Is Featured (checkbox)
- Is Urgent (checkbox - auto-managed warning)
```

#### Form Validation:
- Required fields marked with *
- Date validation (end > begin)
- URL validation
- Slug uniqueness check
- Salary range validation (max > min)

#### API Calls:
```javascript
// Create
POST /govt-jobs/admin/create
Body: GovtJobCreate model

// Update
PUT /govt-jobs/admin/{job_id}
Body: GovtJobUpdate model

// Check slug
GET /govt-jobs/admin/check-slug/{slug}

// Regenerate slug
POST /govt-jobs/admin/{job_id}/regenerate-slug?custom_slug=...
```

---

### 4. Bulk Import Page
**Route**: `/admin/govt-jobs/import`

#### Features:
- CSV/JSON file upload
- Template download (with sample data)
- Field mapping interface
- Preview before import
- Error handling & validation
- Import progress indicator

#### Layout:
```
┌─────────────────────────────────────────────────────┐
│  Bulk Import Jobs                                   │
├─────────────────────────────────────────────────────┤
│  Step 1: Download Template                         │
│  [📥 Download CSV Template] [📥 Download JSON]     │
│                                                      │
│  Step 2: Upload File                               │
│  ┌──────────────────────────────────────────┐     │
│  │  Drag & drop CSV/JSON file here          │     │
│  │  or [Browse Files]                        │     │
│  └──────────────────────────────────────────┘     │
│                                                      │
│  Step 3: Map Fields (auto-detected)               │
│  CSV Column         →  Database Field              │
│  job_title          →  [title ▾]                   │
│  organization       →  [organization_name ▾]       │
│                                                      │
│  Step 4: Preview & Import                         │
│  ┌────────────────────────────────────────────┐   │
│  │ 45 jobs ready to import                    │   │
│  │ 2 errors found (fix before import)         │   │
│  └────────────────────────────────────────────┘   │
│  [← Back] [Import All]                            │
└─────────────────────────────────────────────────────┘
```

#### API Call:
```javascript
POST /govt-jobs/admin/bulk-create
Body: { jobs: [GovtJobCreate, ...] }
```

---

### 5. Web Scraping Manager
**Route**: `/admin/govt-jobs/scraping`

#### Components:
```jsx
- ScrapingSourcesList (all configured sources)
- AddSourceForm (modal/drawer)
- ScrapingLogs (execution history)
- ManualTrigger (run scraper button)
```

#### Layout:
```
┌─────────────────────────────────────────────────────┐
│  Web Scraping Manager            [+ Add Source]    │
├─────────────────────────────────────────────────────┤
│  Active Sources:                                    │
│  ┌────────────────────────────────────────────┐   │
│  │ UPSC RSS Feed                    ✓ Enabled │   │
│  │ https://upsc.gov.in/rss...                 │   │
│  │ Last Run: 2 hours ago | Found: 5 new jobs │   │
│  │ [▶ Run Now] [✏ Edit] [🗑 Delete]          │   │
│  ├────────────────────────────────────────────┤   │
│  │ SSC Website                      ✗ Disabled│   │
│  │ https://ssc.nic.in                         │   │
│  │ Last Run: Never                            │   │
│  │ [▶ Run Now] [✏ Edit] [🗑 Delete]          │   │
│  └────────────────────────────────────────────┘   │
│                                                      │
│  Recent Scraping Logs:                             │
│  ┌────────────────────────────────────────────┐   │
│  │ Time        Source  Found New  Status      │   │
│  │ 10:30 AM   UPSC    8     3    ✓ Success   │   │
│  │ 06:15 AM   UPSC    12    7    ✓ Success   │   │
│  │ 02:00 AM   SSC     0     0    ✗ Failed    │   │
│  └────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────┘
```

#### Add Source Form:
```jsx
Fields:
- Source Name *
- Source URL *
- Scraping Type * (RSS/HTML/API)
- If HTML:
  - Job Container Selector
  - Title Selector
  - Description Selector
  - Link Selector
  - Date Selector
- Default Values:
  - Organization Name *
  - Job Type *
  - Category *
- Schedule (cron expression)
- Enabled (toggle)
```

#### API Calls:
```javascript
// List sources
GET /govt-jobs/scraper/sources

// Run scraping
POST /govt-jobs/scraper/run/{source_id}

// Note: Full scraping API needs implementation
```

---

### 6. Analytics & Reports
**Route**: `/admin/govt-jobs/analytics`

#### Metrics to Display:
- Total jobs by status (pie chart)
- Jobs by category (bar chart)
- Jobs by state (map or bar chart)
- Top organizations (table)
- Popular jobs (by views)
- Click-through rates
- Daily/weekly/monthly trends

#### Layout:
```
┌─────────────────────────────────────────────────────┐
│  Analytics & Reports         [Export Report ▾]     │
├─────────────────────────────────────────────────────┤
│  Date Range: [Last 30 Days ▾]                      │
│                                                      │
│  Overview:                                          │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐            │
│  │ 45,678  │ │ 12,345  │ │  3.2%   │            │
│  │ Total   │ │ Total   │ │ Avg CTR │            │
│  │ Views   │ │ Clicks  │ │         │            │
│  └─────────┘ └─────────┘ └─────────┘            │
│                                                      │
│  Jobs by Category:                                  │
│  ┌──────────────────────────────────────────┐     │
│  │ Engineering    ████████████ 234          │     │
│  │ Banking        ████████ 189              │     │
│  │ Teaching       ██████ 145                │     │
│  └──────────────────────────────────────────┘     │
│                                                      │
│  Top Performing Jobs:                              │
│  ┌────────────────────────────────────────────┐   │
│  │ Title              Views  Clicks  CTR      │   │
│  │ UPSC Engineer      8.9K   567    6.4%     │   │
│  │ SSC Clerk          6.7K   423    6.3%     │   │
│  └────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────┘
```

---

## 👤 USER INTERFACE UI

### 1. Homepage/Landing
**Route**: `/govt-jobs` or `/`

#### Components:
```jsx
- HeroSection (search bar, featured stats)
- FeaturedJobs (carousel/grid)
- LatestJobs (list with NEW badge)
- ClosingSoon (urgent jobs with countdown)
- BrowseByCategory (category cards)
- BrowseByState (state cards/map)
- BrowseByOrganization (top orgs)
- Testimonials (optional)
- Newsletter (optional)
```

#### Layout:
```
┌─────────────────────────────────────────────────────┐
│  🏛️ Government Jobs Portal            [🔍 Search]  │
├─────────────────────────────────────────────────────┤
│                                                      │
│        Find Your Dream Government Job               │
│     ┌────────────────────────────────────┐         │
│     │ 🔍 Search jobs, organizations...   │         │
│     └────────────────────────────────────┘         │
│      1,234 Active Jobs | 45 New Today              │
│                                                      │
│  🌟 Featured Jobs:                                 │
│  ┌───────┐ ┌───────┐ ┌───────┐                   │
│  │ UPSC  │ │ SSC   │ │ RRB   │                   │
│  │ Engg  │ │ Clerk │ │ NTPC  │                   │
│  │ 234   │ │ 567   │ │ 890   │                   │
│  │ Posts │ │ Posts │ │ Posts │                   │
│  └───────┘ └───────┘ └───────┘                   │
│                                                      │
│  🆕 Latest Jobs:                                   │
│  ┌──────────────────────────────────────────┐     │
│  │ [NEW] UPSC Engineering Services 2024     │     │
│  │ UPSC • 234 Posts • Apply by: 15 Jan     │     │
│  │ [View Details] [Apply Now →]            │     │
│  ├──────────────────────────────────────────┤     │
│  │ [NEW] SSC CHSL 2024 Notification        │     │
│  │ SSC • 4500 Posts • Apply by: 20 Jan     │     │
│  └──────────────────────────────────────────┘     │
│  [See All Jobs →]                                  │
│                                                      │
│  ⚡ Closing Soon:                                   │
│  [Jobs with deadline < 7 days, countdown timer]    │
│                                                      │
│  📂 Browse by Category:                            │
│  [Engineering] [Banking] [Teaching] [Railway]...   │
│                                                      │
│  🗺️ Browse by State:                               │
│  [Maharashtra (234)] [UP (189)] [Delhi (156)]...   │
└─────────────────────────────────────────────────────┘
```

#### API Calls:
```javascript
// Dashboard stats
GET /govt-jobs/stats/dashboard

// Featured jobs
GET /govt-jobs/featured/list?limit=6

// Latest jobs
GET /govt-jobs/latest/list?limit=10

// Closing soon
GET /govt-jobs/closing-soon/list?days=7&limit=5

// Categories with counts
GET /govt-jobs/filter/categories

// States with counts
GET /govt-jobs/filter/states
```

---

### 2. Job Listing Page
**Route**: `/govt-jobs/search` or `/govt-jobs/all`

#### Components:
```jsx
- FilterSidebar (collapsible on mobile)
- JobListingCards
- Pagination
- SortDropdown
- AppliedFilters (chips to remove)
```

#### Filters (Left Sidebar):
- **Search**: Keyword search
- **Job Type**: Central, State, PSU, Autonomous (checkboxes)
- **Categories**: All 13 categories (checkboxes)
- **States**: All states (searchable dropdown)
- **Organizations**: Popular orgs (searchable)
- **Status**: Active, New, Closing Soon (checkboxes)
- **Application Deadline**: Within 7/15/30 days
- **Salary Range**: Slider (min-max)
- **Posted Date**: Last 24h/7d/30d/All

#### Layout:
```
┌─────────────────────────────────────────────────────┐
│  Government Jobs                  [Sort: Latest ▾]  │
├──────────┬──────────────────────────────────────────┤
│ Filters  │  Results (234 jobs found)                │
│          │                                           │
│ Job Type │  ┌─────────────────────────────────┐    │
│ ☑Central │  │ [NEW] [FEATURED] UPSC Engineer  │    │
│ ☐State   │  │ Union Public Service Commission │    │
│ ☐PSU     │  │ 234 Posts • ₹50K-1L • Engineering│    │
│          │  │ 📍 All India • 🕐 Apply: 15 Jan │    │
│ Category │  │ [View Details] [Apply Now →]    │    │
│ ☑Engg    │  └─────────────────────────────────┘    │
│ ☐Banking │                                           │
│          │  ┌─────────────────────────────────┐    │
│ State    │  │ [URGENT] SSC CHSL 2024          │    │
│ 🔍 Search│  │ Staff Selection Commission      │    │
│ ☐All     │  │ 4,500 Posts • ₹25K-81K • Clerical│   │
│ ☐Delhi   │  │ 📍 All India • 🕐 5 days left   │    │
│          │  │ [View Details] [Apply Now →]    │    │
│ [Clear]  │  └─────────────────────────────────┘    │
│          │                                           │
│          │  Page 1 of 12  [← 1 2 3 ... 12 →]      │
└──────────┴──────────────────────────────────────────┘
```

#### Job Card Elements:
- Badges: NEW (blinking), FEATURED, URGENT
- Title (link to details)
- Organization name
- Key info: Posts, Salary, Category
- Location, Application deadline
- CTA buttons: View Details, Apply Now

#### API Call:
```javascript
GET /govt-jobs/?query=engineer&job_types=Central Government&categories=Engineering&states=Delhi&status=Active&is_new=true&is_featured=false&application_open=true&deadline_within_days=30&salary_min=50000&salary_max=100000&sort_by=created_at&sort_order=desc&page=1&limit=20
```

---

### 3. Job Details Page
**Route**: `/govt-jobs/:slug`

#### Components:
```jsx
- JobHeader (title, org, badges)
- KeyInfoCards (vacancies, salary, dates)
- JobDescription (full details)
- EligibilitySection
- HowToApply (steps)
- ImportantDates (timeline)
- Documents Required
- Selection Process
- RelatedJobs (sidebar)
- ShareButtons
- CTAs (Apply Now, Download Notification)
```

#### Layout:
```
┌─────────────────────────────────────────────────────┐
│  [NEW] [FEATURED] UPSC Engineering Services 2024   │
│  Union Public Service Commission (UPSC)            │
│  Posted: 2 days ago • Views: 8.9K                  │
│  [📤 Share] [🔖 Bookmark]                          │
├──────────────────────────┬──────────────────────────┤
│  Quick Info:             │  Related Jobs:          │
│  ┌────────┬────────┐    │  • SSC JE 2024          │
│  │ 234    │ ₹50K-  │    │  • RRB Engineer         │
│  │ Posts  │ 1L/mo  │    │  • BPSC Engineer        │
│  └────────┴────────┘    │                          │
│  📍 All India            │  Categories:            │
│  📅 Apply: 5 Jan-15 Jan  │  [Engineering]          │
│                          │  [Central Govt]         │
│  [🚀 APPLY NOW]          │                          │
│  [📥 Download Pdf]       │  Share:                 │
│                          │  [FB] [TW] [WA] [Copy]  │
├──────────────────────────┴──────────────────────────┤
│  About the Job:                                     │
│  The Union Public Service Commission invites...    │
│                                                      │
│  📋 Post Details:                                   │
│  Post Name: Engineering Services                   │
│  Total Vacancies: 234 (UR: 120, OBC: 63...)       │
│  Category: Engineering                              │
│                                                      │
│  ✅ Eligibility:                                    │
│  • Age: 21-30 years                                │
│  • Qualification: B.E./B.Tech in relevant field    │
│  • Experience: Not required                         │
│                                                      │
│  💰 Salary & Benefits:                             │
│  • Pay Scale: ₹50,000 - ₹1,00,000 per month       │
│  • Grade Pay: Level 10                             │
│  • Other Benefits: HRA, TA, Medical...             │
│                                                      │
│  📅 Important Dates:                               │
│  • Notification: 1 Jan 2024                        │
│  • Application Begin: 5 Jan 2024                   │
│  • Application End: 15 Jan 2024                    │
│  • Last Date Fee Payment: 17 Jan 2024              │
│  • Exam Date: TBA                                  │
│                                                      │
│  💳 Application Fee:                               │
│  • General/OBC: ₹200                               │
│  • SC/ST/PwD/Women: No Fee                         │
│                                                      │
│  📝 How to Apply:                                   │
│  1. Visit official website: www.upsc.gov.in        │
│  2. Click on "Apply Online" link                   │
│  3. Register/Login with credentials                │
│  4. Fill the application form                      │
│  5. Upload documents (photo, signature)            │
│  6. Pay application fee (if applicable)            │
│  7. Submit and save application                    │
│                                                      │
│  📄 Documents Required:                            │
│  • Educational certificates                         │
│  • Caste certificate (if applicable)               │
│  • PwD certificate (if applicable)                 │
│  • Recent passport size photo                      │
│  • Signature scan                                  │
│                                                      │
│  🎯 Selection Process:                             │
│  1. Preliminary Examination (objective)            │
│  2. Main Examination (descriptive)                 │
│  3. Interview/Personality Test                     │
│                                                      │
│  ⚠️ Important Notes:                               │
│  • Candidates must have valid email and mobile     │
│  • Only online applications will be accepted       │
│  • Keep application number for future reference    │
│                                                      │
│  🔗 Important Links:                               │
│  • [Official Notification PDF]                     │
│  • [Apply Online]                                  │
│  • [Official Website]                              │
│  • [Syllabus & Exam Pattern]                       │
│                                                      │
│  [🚀 APPLY NOW]  [📥 Download Notification]        │
└─────────────────────────────────────────────────────┘
```

#### API Calls:
```javascript
// Get job details
GET /govt-jobs/slug/{slug}

// Track click when Apply Now clicked
POST /govt-jobs/{job_id}/click
```

---

### 4. Category Pages
**Route**: `/govt-jobs/category/:category`

Similar to listing page but pre-filtered by category. Add:
- Category description at top
- Breadcrumb: Home > Jobs > Engineering
- Related categories at bottom

#### API Call:
```javascript
GET /govt-jobs/category/{category}?page=1&limit=20
```

---

### 5. State Pages
**Route**: `/govt-jobs/state/:state`

Similar to listing page but pre-filtered by state. Add:
- State name and description
- Breadcrumb: Home > Jobs > Maharashtra
- Nearby states at bottom

#### API Call:
```javascript
GET /govt-jobs/state/{state}?page=1&limit=20
```

---

### 6. Organization Pages
**Route**: `/govt-jobs/org/:organization`

List all jobs from specific organization. Add:
- Organization logo and info
- Total active jobs count
- Subscribe to alerts button

---

## 🧩 SHARED COMPONENTS

### 1. JobCard Component
```jsx
<JobCard job={job}>
  <Badges>
    {job.is_new && <Badge color="green" blink>NEW</Badge>}
    {job.is_featured && <Badge color="blue">FEATURED</Badge>}
    {job.is_urgent && <Badge color="red" blink>URGENT</Badge>}
  </Badges>
  <Title link={`/govt-jobs/${job.slug}`}>{job.title}</Title>
  <Organization>{job.organization_name}</Organization>
  <KeyInfo>
    <InfoItem icon="briefcase">{job.total_vacancies} Posts</InfoItem>
    <InfoItem icon="money">{job.salary_text}</InfoItem>
    <InfoItem icon="tag">{job.category}</InfoItem>
  </KeyInfo>
  <Footer>
    <Location>{job.work_locations.join(', ')}</Location>
    <Deadline>Apply by: {formatDate(job.application_end_date)}</Deadline>
  </Footer>
  <Actions>
    <Button variant="outline" link={`/govt-jobs/${job.slug}`}>
      View Details
    </Button>
    <Button variant="primary" onClick={() => handleApplyClick(job)}>
      Apply Now →
    </Button>
  </Actions>
</JobCard>
```

### 2. FilterSidebar Component
```jsx
<FilterSidebar filters={filters} onFilterChange={handleFilterChange}>
  <FilterSection title="Job Type">
    <Checkbox value="Central Government">Central</Checkbox>
    <Checkbox value="State Government">State</Checkbox>
    <Checkbox value="PSU">PSU</Checkbox>
    <Checkbox value="Autonomous Body">Autonomous</Checkbox>
  </FilterSection>
  
  <FilterSection title="Category">
    {categories.map(cat => (
      <Checkbox key={cat} value={cat}>{cat}</Checkbox>
    ))}
  </FilterSection>
  
  <FilterSection title="Salary Range">
    <RangeSlider min={0} max={500000} step={10000} />
  </FilterSection>
  
  <Button variant="outline" onClick={clearFilters}>
    Clear All Filters
  </Button>
</FilterSidebar>
```

### 3. Badge Component (with Blinking)
```jsx
<Badge color="green" blink={true}>NEW</Badge>

/* CSS */
@keyframes blink {
  0%, 50%, 100% { opacity: 1; }
  25%, 75% { opacity: 0.3; }
}

.badge-blink {
  animation: blink 2s infinite;
}
```

### 4. SearchBar Component
```jsx
<SearchBar
  placeholder="Search jobs, organizations, keywords..."
  onSearch={handleSearch}
  suggestions={suggestions}
  autocomplete
/>
```

---

## 🔌 API INTEGRATION GUIDE

### Setup Axios Instance
```javascript
// api/govtJobs.js
import axios from 'axios';

const API_BASE_URL = 'https://api.projectdevops.in/govt-jobs';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add auth token for admin requests
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('adminToken');
  if (token && config.url.includes('/admin/')) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export default api;
```

### API Functions
```javascript
// Public APIs
export const getJobs = (filters) => api.get('/', { params: filters });
export const getJobBySlug = (slug) => api.get(`/slug/${slug}`);
export const getDashboardStats = () => api.get('/stats/dashboard');
export const getFeaturedJobs = (limit = 10) => api.get(`/featured/list?limit=${limit}`);
export const getLatestJobs = (limit = 20) => api.get(`/latest/list?limit=${limit}`);
export const getClosingSoonJobs = (days = 7) => api.get(`/closing-soon/list?days=${days}`);
export const getCategories = () => api.get('/filter/categories');
export const getStates = () => api.get('/filter/states');
export const getOrganizations = () => api.get('/filter/organizations');
export const trackClick = (jobId) => api.post(`/${jobId}/click`);

// Admin APIs
export const createJob = (jobData) => api.post('/admin/create', jobData);
export const updateJob = (jobId, jobData) => api.put(`/admin/${jobId}`, jobData);
export const deleteJob = (jobId) => api.delete(`/admin/${jobId}`);
export const getAllJobsAdmin = (page, limit, status) => 
  api.get(`/admin/all?page=${page}&limit=${limit}${status ? `&status=${status}` : ''}`);
export const updateJobStatus = (jobId, status) => 
  api.patch(`/admin/${jobId}/status`, { new_status: status });
export const toggleFeatured = (jobId, isFeatured) => 
  api.patch(`/admin/${jobId}/feature`, { is_featured: isFeatured });
export const bulkCreate = (jobs) => api.post('/admin/bulk-create', { jobs });
export const bulkUpdateStatus = (jobIds, status) => 
  api.post('/admin/bulk-update-status', { job_ids: jobIds, status });
export const bulkDelete = (jobIds) => 
  api.delete('/admin/bulk-delete', { data: { job_ids: jobIds } });
export const checkSlugAvailability = (slug) => api.get(`/admin/check-slug/${slug}`);
export const regenerateSlug = (jobId, customSlug) => 
  api.post(`/admin/${jobId}/regenerate-slug${customSlug ? `?custom_slug=${customSlug}` : ''}`);
```

---

## 🗃️ STATE MANAGEMENT

### Using React Context (Simple)
```javascript
// context/GovtJobsContext.jsx
import React, { createContext, useState, useContext } from 'react';

const GovtJobsContext = createContext();

export const GovtJobsProvider = ({ children }) => {
  const [filters, setFilters] = useState({});
  const [jobs, setJobs] = useState([]);
  const [loading, setLoading] = useState(false);

  const fetchJobs = async (newFilters) => {
    setLoading(true);
    try {
      const response = await getJobs(newFilters);
      setJobs(response.data.jobs);
      setFilters(newFilters);
    } catch (error) {
      console.error('Error fetching jobs:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <GovtJobsContext.Provider value={{ jobs, filters, loading, fetchJobs }}>
      {children}
    </GovtJobsContext.Provider>
  );
};

export const useGovtJobs = () => useContext(GovtJobsContext);
```

### Using Redux Toolkit (Advanced)
```javascript
// store/govtJobsSlice.js
import { createSlice, createAsyncThunk } from '@reduxjs/toolkit';
import { getJobs, getJobBySlug } from '../api/govtJobs';

export const fetchJobs = createAsyncThunk(
  'govtJobs/fetchJobs',
  async (filters) => {
    const response = await getJobs(filters);
    return response.data;
  }
);

const govtJobsSlice = createSlice({
  name: 'govtJobs',
  initialState: {
    jobs: [],
    currentJob: null,
    filters: {},
    loading: false,
    error: null,
  },
  reducers: {
    setFilters: (state, action) => {
      state.filters = action.payload;
    },
    clearFilters: (state) => {
      state.filters = {};
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(fetchJobs.pending, (state) => {
        state.loading = true;
      })
      .addCase(fetchJobs.fulfilled, (state, action) => {
        state.loading = false;
        state.jobs = action.payload.jobs;
      })
      .addCase(fetchJobs.rejected, (state, action) => {
        state.loading = false;
        state.error = action.error.message;
      });
  },
});

export const { setFilters, clearFilters } = govtJobsSlice.actions;
export default govtJobsSlice.reducer;
```

---

## 🎨 DESIGN TOKENS

### Colors
```css
:root {
  /* Brand */
  --primary: #1e40af;
  --primary-hover: #1e3a8a;
  --secondary: #059669;
  
  /* Status */
  --status-active: #10b981;
  --status-closed: #ef4444;
  --status-pending: #f59e0b;
  
  /* Badges */
  --badge-new: #10b981;
  --badge-featured: #3b82f6;
  --badge-urgent: #ef4444;
  
  /* Neutral */
  --gray-50: #f9fafb;
  --gray-100: #f3f4f6;
  --gray-900: #111827;
}
```

### Typography
```css
/* Headings */
h1 { font-size: 2.5rem; font-weight: 700; }
h2 { font-size: 2rem; font-weight: 600; }
h3 { font-size: 1.5rem; font-weight: 600; }

/* Body */
body { font-size: 1rem; line-height: 1.5; }

/* Small */
.text-sm { font-size: 0.875rem; }
.text-xs { font-size: 0.75rem; }
```

---

## 📱 RESPONSIVE DESIGN

### Breakpoints
```css
/* Mobile first */
@media (min-width: 640px) { /* sm */ }
@media (min-width: 768px) { /* md */ }
@media (min-width: 1024px) { /* lg */ }
@media (min-width: 1280px) { /* xl */ }
```

### Mobile Adjustments
- Filters in drawer/modal (not sidebar)
- Stack job cards vertically
- Simplified job cards (less info)
- Bottom navigation for quick actions
- Sticky header with search
- Collapsible sections in job details

---

## ⚡ PERFORMANCE OPTIMIZATIONS

1. **Lazy Loading**: Load images and components on demand
2. **Pagination**: Don't load all jobs at once
3. **Caching**: Cache API responses (React Query/SWR)
4. **Debounce**: Debounce search input
5. **Virtual Scrolling**: For long lists
6. **Code Splitting**: Split routes and admin panel
7. **Image Optimization**: Compress logos and images
8. **CDN**: Serve static assets from CDN

---

## 🧪 TESTING CHECKLIST

### Functional Testing
- [ ] Job listing with all filters
- [ ] Job search with keywords
- [ ] Job details page loads correctly
- [ ] Apply button tracks clicks
- [ ] Admin can create/edit/delete jobs
- [ ] Bulk import works
- [ ] Pagination works
- [ ] Sort works correctly
- [ ] NEW badge appears for jobs < 3 days
- [ ] URGENT badge appears for deadline < 7 days

### Responsive Testing
- [ ] Mobile (375px, 414px)
- [ ] Tablet (768px, 1024px)
- [ ] Desktop (1280px, 1920px)

### Performance Testing
- [ ] Page load time < 3s
- [ ] Time to interactive < 5s
- [ ] API response time < 500ms
- [ ] Large lists handle 1000+ jobs

### SEO Testing
- [ ] Meta tags present
- [ ] Slugs are SEO-friendly
- [ ] Schema.org markup
- [ ] Sitemap generated
- [ ] Robots.txt configured

---

## 🚀 DEPLOYMENT CHECKLIST

### Frontend
- [ ] Build production bundle
- [ ] Optimize images
- [ ] Enable gzip/brotli
- [ ] Configure CDN
- [ ] Set up error tracking (Sentry)
- [ ] Analytics (GA, Mixpanel)
- [ ] SSL certificate
- [ ] Domain configured

### Backend (Already deployed)
- [x] API running at api.projectdevops.in
- [ ] Enable text search index on MongoDB
- [ ] Schedule background tasks (APScheduler)
- [ ] Configure CORS for production domain
- [ ] Set up monitoring (uptime, errors)
- [ ] Enable rate limiting
- [ ] Set up backups

---

## 📞 SUPPORT & DOCUMENTATION

### For Developers
- API Documentation: https://api.projectdevops.in/docs
- Swagger UI: Interactive API testing
- This guide: Complete UI specifications

### For Users
- FAQ page
- How to apply guide
- Contact form
- Email notifications (optional)

---

## 🎯 NEXT STEPS

1. **Phase 1**: Build User Interface
   - Homepage with featured jobs
   - Job listing page with filters
   - Job details page
   - Category/State pages

2. **Phase 2**: Build Admin Dashboard
   - Job management (CRUD)
   - Bulk import
   - Analytics dashboard

3. **Phase 3**: Advanced Features
   - Web scraping UI
   - Email alerts/notifications
   - User accounts (save jobs, alerts)
   - Mobile app

4. **Phase 4**: SEO & Marketing
   - Optimize for search engines
   - Social media integration
   - Blog/resources section
   - Affiliate partnerships

---

**Implementation Time Estimate**:
- User Interface: 3-4 weeks
- Admin Dashboard: 2-3 weeks
- Testing & Refinement: 1-2 weeks
- **Total**: 6-9 weeks for complete implementation

**Tech Stack Recommendation**:
- **Frontend**: React + Tailwind CSS + React Router
- **State**: Redux Toolkit or React Query
- **Forms**: React Hook Form + Yup validation
- **Charts**: Recharts or Chart.js
- **Icons**: Heroicons or Lucide React
- **Date Picker**: React DatePicker
- **Rich Text**: TipTap or Quill

**Good luck with the implementation! 🚀**
