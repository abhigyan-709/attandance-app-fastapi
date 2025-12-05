# services/govt_jobs_scraper.py
"""
Government Jobs Web Scraping Service

Supports:
- RSS feed scraping
- HTML scraping with CSS selectors
- Job deduplication
- Auto-mapping to GovtJobCreate model

Requirements:
    pip install beautifulsoup4 feedparser lxml requests

Future enhancements:
    - Selenium for JavaScript-heavy sites
    - OCR for PDF notifications
    - AI-powered field extraction
"""
import logging
import re
import hashlib
from typing import List, Dict, Optional, Any
from datetime import datetime, timezone
from bs4 import BeautifulSoup
import requests

# Optional imports (install if needed)
try:
    import feedparser
    FEEDPARSER_AVAILABLE = True
except ImportError:
    FEEDPARSER_AVAILABLE = False
    logging.warning("feedparser not installed. RSS scraping disabled.")

from models.govt_jobs import GovtJobCreate, JobType, JobCategory, JobStatus, ApplicationMode

logger = logging.getLogger(__name__)


class JobScraper:
    """Base scraper class for government job websites"""
    
    def __init__(self, source_config: Dict[str, Any]):
        """
        Initialize scraper with source configuration
        
        Args:
            source_config: {
                "source_name": str,
                "source_url": str,
                "scraping_type": "rss" | "html" | "api",
                "selectors": {...},  # For HTML scraping
                "field_mappings": {...},
                "default_values": {...},
                "enabled": bool
            }
        """
        self.config = source_config
        self.source_name = source_config.get("source_name", "Unknown")
        self.source_url = source_config.get("source_url", "")
        self.scraping_type = source_config.get("scraping_type", "html")
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
    
    def scrape(self) -> List[Dict[str, Any]]:
        """
        Main scraping method
        
        Returns:
            List of job dictionaries ready to be converted to GovtJobCreate
        """
        if self.scraping_type == "rss":
            return self._scrape_rss()
        elif self.scraping_type == "html":
            return self._scrape_html()
        elif self.scraping_type == "api":
            return self._scrape_api()
        else:
            logger.error(f"Unknown scraping type: {self.scraping_type}")
            return []
    
    def _scrape_rss(self) -> List[Dict[str, Any]]:
        """Scrape RSS feed"""
        if not FEEDPARSER_AVAILABLE:
            logger.error("feedparser not installed")
            return []
        
        try:
            feed = feedparser.parse(self.source_url)
            jobs = []
            
            for entry in feed.entries:
                job_data = self._map_rss_entry(entry)
                if job_data:
                    jobs.append(job_data)
            
            logger.info(f"Scraped {len(jobs)} jobs from RSS: {self.source_name}")
            return jobs
        
        except Exception as e:
            logger.error(f"RSS scraping error for {self.source_name}: {e}")
            return []
    
    def _scrape_html(self) -> List[Dict[str, Any]]:
        """Scrape HTML page"""
        try:
            response = requests.get(self.source_url, headers=self.headers, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            selectors = self.config.get("selectors", {})
            
            jobs = []
            
            # Find job containers
            container_selector = selectors.get("job_container", "div.job-item")
            job_elements = soup.select(container_selector)
            
            for element in job_elements:
                job_data = self._extract_job_from_element(element, selectors)
                if job_data:
                    jobs.append(job_data)
            
            logger.info(f"Scraped {len(jobs)} jobs from HTML: {self.source_name}")
            return jobs
        
        except Exception as e:
            logger.error(f"HTML scraping error for {self.source_name}: {e}")
            return []
    
    def _scrape_api(self) -> List[Dict[str, Any]]:
        """Scrape from API endpoint"""
        try:
            response = requests.get(self.source_url, headers=self.headers, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            mappings = self.config.get("field_mappings", {})
            
            jobs = []
            
            # Extract jobs array from response
            jobs_key = mappings.get("jobs_array_key", "data")
            jobs_array = data.get(jobs_key, [])
            
            for item in jobs_array:
                job_data = self._map_api_response(item, mappings)
                if job_data:
                    jobs.append(job_data)
            
            logger.info(f"Scraped {len(jobs)} jobs from API: {self.source_name}")
            return jobs
        
        except Exception as e:
            logger.error(f"API scraping error for {self.source_name}: {e}")
            return []
    
    def _map_rss_entry(self, entry) -> Optional[Dict[str, Any]]:
        """Map RSS entry to job data"""
        try:
            mappings = self.config.get("field_mappings", {})
            defaults = self.config.get("default_values", {})
            
            # Extract title
            title = entry.get("title", "").strip()
            if not title:
                return None
            
            # Extract description
            description = entry.get("description", entry.get("summary", "")).strip()
            description = self._clean_html(description)
            
            # Extract link
            link = entry.get("link", "")
            
            # Extract date
            published_date = None
            if hasattr(entry, "published_parsed"):
                published_date = datetime(*entry.published_parsed[:6])
            
            # Build job data
            job_data = {
                "title": title,
                "short_description": description[:500] if description else "",
                "full_description": description,
                "notification_link": link,
                "apply_link": link,
                "organization_name": defaults.get("organization_name", self.source_name),
                "organization_short_name": defaults.get("organization_short_name", self.source_name),
                "job_type": defaults.get("job_type", JobType.CENTRAL.value),
                "category": defaults.get("category", JobCategory.OTHER.value),
                "post_name": self._extract_post_name(title),
                "status": JobStatus.PENDING_REVIEW.value,
                "application_mode": defaults.get("application_mode", ApplicationMode.ONLINE.value),
                "scraped_source": self.source_name,
                "scraped_url": self.source_url
            }
            
            # Add scraped timestamp
            if published_date:
                job_data["notification_date"] = published_date.date()
            
            return job_data
        
        except Exception as e:
            logger.error(f"Error mapping RSS entry: {e}")
            return None
    
    def _extract_job_from_element(self, element, selectors: Dict) -> Optional[Dict[str, Any]]:
        """Extract job data from HTML element"""
        try:
            defaults = self.config.get("default_values", {})
            
            # Extract fields using selectors
            title_selector = selectors.get("title", "h3.title")
            title_elem = element.select_one(title_selector)
            title = title_elem.get_text(strip=True) if title_elem else None
            
            if not title:
                return None
            
            # Description
            desc_selector = selectors.get("description", "div.description")
            desc_elem = element.select_one(desc_selector)
            description = desc_elem.get_text(strip=True) if desc_elem else ""
            
            # Link
            link_selector = selectors.get("link", "a")
            link_elem = element.select_one(link_selector)
            link = link_elem.get("href", "") if link_elem else ""
            
            if link and not link.startswith("http"):
                base_url = self.config.get("base_url", "")
                link = base_url + link
            
            # Date
            date_selector = selectors.get("date", "span.date")
            date_elem = element.select_one(date_selector)
            date_text = date_elem.get_text(strip=True) if date_elem else None
            notification_date = self._parse_date(date_text) if date_text else None
            
            # Build job data
            job_data = {
                "title": title,
                "short_description": description[:500] if description else "",
                "full_description": description,
                "notification_link": link,
                "apply_link": link,
                "organization_name": defaults.get("organization_name", self.source_name),
                "organization_short_name": defaults.get("organization_short_name", self.source_name),
                "job_type": defaults.get("job_type", JobType.CENTRAL.value),
                "category": defaults.get("category", JobCategory.OTHER.value),
                "post_name": self._extract_post_name(title),
                "status": JobStatus.PENDING_REVIEW.value,
                "application_mode": defaults.get("application_mode", ApplicationMode.ONLINE.value),
                "scraped_source": self.source_name,
                "scraped_url": self.source_url
            }
            
            if notification_date:
                job_data["notification_date"] = notification_date
            
            return job_data
        
        except Exception as e:
            logger.error(f"Error extracting job from element: {e}")
            return None
    
    def _map_api_response(self, item: Dict, mappings: Dict) -> Optional[Dict[str, Any]]:
        """Map API response to job data"""
        try:
            defaults = self.config.get("default_values", {})
            
            # Extract fields using mappings
            title = item.get(mappings.get("title", "title"), "").strip()
            if not title:
                return None
            
            description = item.get(mappings.get("description", "description"), "").strip()
            link = item.get(mappings.get("link", "url"), "")
            
            job_data = {
                "title": title,
                "short_description": description[:500] if description else "",
                "full_description": description,
                "notification_link": link,
                "apply_link": link,
                "organization_name": defaults.get("organization_name", self.source_name),
                "organization_short_name": defaults.get("organization_short_name", self.source_name),
                "job_type": defaults.get("job_type", JobType.CENTRAL.value),
                "category": defaults.get("category", JobCategory.OTHER.value),
                "post_name": self._extract_post_name(title),
                "status": JobStatus.PENDING_REVIEW.value,
                "application_mode": defaults.get("application_mode", ApplicationMode.ONLINE.value),
                "scraped_source": self.source_name,
                "scraped_url": self.source_url
            }
            
            return job_data
        
        except Exception as e:
            logger.error(f"Error mapping API response: {e}")
            return None
    
    def _extract_post_name(self, title: str) -> str:
        """Extract post name from title"""
        # Remove common prefixes
        title = re.sub(r'^(recruitment|vacancy|notification|hiring|jobs?)\s+', '', title, flags=re.IGNORECASE)
        
        # Try to find post name patterns
        # Example: "UPSC Recruitment 2024 - Engineer Posts"
        match = re.search(r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+(?:Post|Recruitment|Vacancy)', title, re.IGNORECASE)
        if match:
            return match.group(1)
        
        # Fallback: use first 100 chars
        return title[:100]
    
    def _clean_html(self, html_text: str) -> str:
        """Clean HTML tags from text"""
        soup = BeautifulSoup(html_text, 'html.parser')
        return soup.get_text(separator=' ', strip=True)
    
    def _parse_date(self, date_text: str) -> Optional[datetime.date]:
        """Parse date from various formats"""
        if not date_text:
            return None
        
        # Common date formats
        formats = [
            "%d/%m/%Y",
            "%d-%m-%Y",
            "%Y-%m-%d",
            "%d %B %Y",
            "%d %b %Y",
            "%B %d, %Y"
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(date_text.strip(), fmt).date()
            except ValueError:
                continue
        
        return None
    
    def generate_job_hash(self, job_data: Dict) -> str:
        """Generate unique hash for job deduplication"""
        # Create hash from title + organization + notification date
        hash_string = f"{job_data.get('title', '')}|{job_data.get('organization_short_name', '')}|{job_data.get('notification_date', '')}"
        return hashlib.md5(hash_string.encode()).hexdigest()


class ScraperManager:
    """Manage multiple scrapers"""
    
    def __init__(self, db_client):
        self.db = db_client
        self.scrapers: List[JobScraper] = []
    
    def load_sources_from_db(self):
        """Load scraping sources from database"""
        try:
            database = self.db["testdb"]
            collection = database["scraping_sources"]
            
            sources = collection.find({"enabled": True})
            
            for source in sources:
                scraper = JobScraper(source)
                self.scrapers.append(scraper)
            
            logger.info(f"Loaded {len(self.scrapers)} active scraping sources")
        
        except Exception as e:
            logger.error(f"Error loading scraping sources: {e}")
    
    def scrape_all(self) -> Dict[str, Any]:
        """
        Run all scrapers
        
        Returns:
            {
                "total_scraped": int,
                "sources": [{
                    "source_name": str,
                    "jobs_found": int,
                    "jobs_new": int,
                    "errors": []
                }]
            }
        """
        results = {
            "total_scraped": 0,
            "total_new": 0,
            "sources": []
        }
        
        for scraper in self.scrapers:
            try:
                logger.info(f"Scraping: {scraper.source_name}")
                
                jobs = scraper.scrape()
                new_jobs = self._deduplicate_and_save(jobs, scraper.source_name)
                
                results["total_scraped"] += len(jobs)
                results["total_new"] += len(new_jobs)
                results["sources"].append({
                    "source_name": scraper.source_name,
                    "jobs_found": len(jobs),
                    "jobs_new": len(new_jobs),
                    "errors": []
                })
            
            except Exception as e:
                logger.error(f"Error scraping {scraper.source_name}: {e}")
                results["sources"].append({
                    "source_name": scraper.source_name,
                    "jobs_found": 0,
                    "jobs_new": 0,
                    "errors": [str(e)]
                })
        
        # Log scraping run
        self._log_scraping_run(results)
        
        return results
    
    def _deduplicate_and_save(self, jobs: List[Dict], source_name: str) -> List[str]:
        """
        Check for duplicates and save new jobs
        
        Returns:
            List of new job IDs
        """
        database = self.db["testdb"]
        collection = database["govt_jobs"]
        
        new_job_ids = []
        
        for job_data in jobs:
            try:
                # Check if job exists (by title + organization)
                existing = collection.find_one({
                    "title": job_data["title"],
                    "organization_short_name": job_data["organization_short_name"]
                })
                
                if existing:
                    # Update last_scraped_at
                    collection.update_one(
                        {"_id": existing["_id"]},
                        {"$set": {"last_scraped_at": datetime.now(timezone.utc)}}
                    )
                    continue
                
                # Create new job (status: PENDING_REVIEW)
                now = datetime.now(timezone.utc)
                job_data.update({
                    "is_new": True,
                    "views_count": 0,
                    "clicks_count": 0,
                    "created_at": now,
                    "updated_at": now,
                    "published_at": None,
                    "last_scraped_at": now
                })
                
                # Generate slug
                from routes.govt_jobs import generate_unique_slug
                job_data["slug"] = generate_unique_slug(job_data["title"], collection)
                
                result = collection.insert_one(job_data)
                new_job_ids.append(str(result.inserted_id))
            
            except Exception as e:
                logger.error(f"Error saving job: {e}")
        
        return new_job_ids
    
    def _log_scraping_run(self, results: Dict):
        """Log scraping run to database"""
        try:
            database = self.db["testdb"]
            collection = database["scraping_logs"]
            
            log_entry = {
                "run_timestamp": datetime.now(timezone.utc),
                "total_scraped": results["total_scraped"],
                "total_new": results["total_new"],
                "sources": results["sources"],
                "duration_seconds": None  # Can be calculated
            }
            
            collection.insert_one(log_entry)
        
        except Exception as e:
            logger.error(f"Error logging scraping run: {e}")


# ==================== Example Scraping Configurations ====================

EXAMPLE_SOURCES = [
    {
        "source_name": "UPSC",
        "source_url": "https://upsc.gov.in/rss/recruitment-rss-feed",
        "scraping_type": "rss",
        "enabled": True,
        "default_values": {
            "organization_name": "Union Public Service Commission",
            "organization_short_name": "UPSC",
            "job_type": JobType.CENTRAL.value,
            "category": JobCategory.ENGINEERING.value,
            "application_mode": ApplicationMode.ONLINE.value
        }
    },
    {
        "source_name": "SSC",
        "source_url": "https://ssc.nic.in/",
        "scraping_type": "html",
        "enabled": False,  # Requires manual configuration
        "selectors": {
            "job_container": "div.job-listing",
            "title": "h3.job-title",
            "description": "div.job-desc",
            "link": "a.apply-link",
            "date": "span.posted-date"
        },
        "base_url": "https://ssc.nic.in",
        "default_values": {
            "organization_name": "Staff Selection Commission",
            "organization_short_name": "SSC",
            "job_type": JobType.CENTRAL.value,
            "category": JobCategory.CLERICAL.value
        }
    }
]
