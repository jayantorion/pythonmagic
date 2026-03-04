import json
import re
import httpx
from bs4 import BeautifulSoup
from typing import Optional, Dict, Any
from app.schemas.job import JobCreate, JobIngestRequest
from app.services.normalization.canonicalizer import canonicalizer
from app.core.logging import logger


class UniversalJobParser:
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
    }

    async def parse_from_url_or_text(self, request: JobIngestRequest) -> JobCreate:
        """Parse job details from either a pasted URL or raw text."""
        if request.url:
            return await self.parse_from_url(request.url, request.company_name, request.title, request.location)
        elif request.raw_text:
            return self.parse_from_raw_text(request.raw_text, request.company_name, request.title, request.location)
        else:
            raise ValueError("Either URL or raw_text must be provided for job ingestion.")

    async def parse_from_url(
        self,
        url: str,
        company_name: Optional[str] = None,
        title: Optional[str] = None,
        location: Optional[str] = None,
    ) -> JobCreate:
        canonical_url = canonicalizer.canonicalize_url(url)

        try:
            async with httpx.AsyncClient(headers=self.HEADERS, follow_redirects=True, timeout=15.0) as client:
                resp = await client.get(url)
                if resp.status_code == 200:
                    soup = BeautifulSoup(resp.text, "html.parser")

                    # Check for schema.org JobPosting structured JSON-LD data
                    json_ld_job = self._extract_json_ld(soup)
                    if json_ld_job:
                        return json_ld_job

                    # Fallback to HTML meta / tag extraction
                    extracted_title = title or self._extract_html_title(soup)
                    extracted_company = company_name or self._extract_html_company(soup, url)
                    extracted_loc = location or self._extract_html_location(soup)
                    extracted_desc = self._extract_html_description(soup)

                    remote_type = "unknown"
                    if "remote" in extracted_title.lower() or "remote" in extracted_loc.lower():
                        remote_type = "remote"
                    elif "hybrid" in extracted_loc.lower():
                        remote_type = "hybrid"

                    return JobCreate(
                        source="universal_url_ingest",
                        canonical_url=canonical_url,
                        company_name=canonicalizer.normalize_company_name(extracted_company),
                        title=extracted_title,
                        normalized_title=canonicalizer.normalize_job_title(extracted_title),
                        location=extracted_loc,
                        remote_type=remote_type,
                        description_raw=extracted_desc,
                    )
        except Exception as e:
            logger.error(f"Error scraping job URL {url}: {e}")

        # Fallback if request failed or anti-bot challenge occurred
        fallback_title = title or "Data Engineer (Imported)"
        fallback_company = company_name or "Enterprise"
        return JobCreate(
            source="universal_url_ingest",
            canonical_url=canonical_url,
            company_name=canonicalizer.normalize_company_name(fallback_company),
            title=fallback_title,
            normalized_title=canonicalizer.normalize_job_title(fallback_title),
            location=location or "Remote",
            remote_type="remote",
            description_raw=f"Job imported from: {url}\nTitle: {fallback_title}\nCompany: {fallback_company}",
        )

    def parse_from_raw_text(
        self,
        raw_text: str,
        company_name: Optional[str] = None,
        title: Optional[str] = None,
        location: Optional[str] = None,
    ) -> JobCreate:
        lines = [l.strip() for l in raw_text.split("\n") if l.strip()]
        first_line = lines[0] if lines else "Data Engineer"

        extracted_title = title
        extracted_company = company_name

        if not extracted_title:
            if " at " in first_line:
                parts = first_line.split(" at ")
                extracted_title = parts[0].strip()
                if not extracted_company:
                    extracted_company = parts[1].strip()
            elif " - " in first_line:
                parts = first_line.split(" - ")
                extracted_title = parts[0].strip()
                if not extracted_company:
                    extracted_company = parts[1].strip()
            else:
                extracted_title = first_line

        extracted_company = extracted_company or "Target Company"
        loc = location or "Remote"

        return JobCreate(
            source="raw_text_ingest",
            canonical_url=f"text://{canonicalizer.normalize_company_name(extracted_company)}/{canonicalizer.normalize_job_title(extracted_title)}",
            company_name=canonicalizer.normalize_company_name(extracted_company),
            title=extracted_title,
            normalized_title=canonicalizer.normalize_job_title(extracted_title),
            location=loc,
            remote_type="remote" if "remote" in loc.lower() or "remote" in raw_text[:200].lower() else "on_site",
            description_raw=raw_text,
        )

    def _extract_json_ld(self, soup: BeautifulSoup) -> Optional[JobCreate]:
        scripts = soup.find_all("script", type="application/ld+json")
        for s in scripts:
            try:
                data = json.loads(s.string)
                if isinstance(data, list):
                    data = data[0]
                if data.get("@type") == "JobPosting":
                    title = data.get("title", "Data Engineer")
                    hiring_org = data.get("hiringOrganization", {})
                    company = hiring_org.get("name", "Target Company") if isinstance(hiring_org, dict) else str(hiring_org)
                    loc_data = data.get("jobLocation", {})
                    loc = "Remote"
                    if isinstance(loc_data, dict):
                        address = loc_data.get("address", {})
                        if isinstance(address, dict):
                            loc = address.get("addressLocality", "Remote")

                    desc_html = data.get("description", "")
                    clean_desc = BeautifulSoup(desc_html, "html.parser").get_text(separator="\n").strip()

                    return JobCreate(
                        source="json_ld_ingest",
                        canonical_url="https://imported-job.local",
                        company_name=canonicalizer.normalize_company_name(company),
                        title=title,
                        normalized_title=canonicalizer.normalize_job_title(title),
                        location=loc,
                        remote_type="remote" if "remote" in title.lower() or "remote" in loc.lower() else "on_site",
                        description_raw=clean_desc,
                    )
            except Exception:
                continue
        return None

    def _extract_html_title(self, soup: BeautifulSoup) -> str:
        for tag in ["h1", "title"]:
            found = soup.find(tag)
            if found and found.get_text():
                t = found.get_text().strip()
                t = re.sub(r"\s*[-|–]\s*(?:Careers|Jobs|LinkedIn|Naukri|Indeed).*$", "", t, flags=re.IGNORECASE)
                if len(t) < 80:
                    return t
        return "Data Engineer"

    def _extract_html_company(self, soup: BeautifulSoup, url: str) -> str:
        # Check meta tags
        meta_site = soup.find("meta", property="og:site_name")
        if meta_site and meta_site.get("content"):
            return meta_site["content"].strip()
        # Fallback to domain
        from urllib.parse import urlparse
        domain = urlparse(url).netloc.replace("www.", "").split(".")[0]
        return domain.capitalize()

    def _extract_html_location(self, soup: BeautifulSoup) -> str:
        text = soup.get_text()
        for loc in ["Bangalore", "Bengaluru", "Hyderabad", "Pune", "Mumbai", "Delhi", "Gurgaon", "Noida", "Remote"]:
            if re.search(rf"\b{loc}\b", text, re.IGNORECASE):
                return loc
        return "Remote"

    def _extract_html_description(self, soup: BeautifulSoup) -> str:
        # Remove scripts, styles, nav, footers
        for elem in soup(["script", "style", "nav", "header", "footer", "noscript", "svg"]):
            elem.decompose()

        # Target primary content areas
        main = soup.find(["article", "main"]) or soup.find("div", class_=re.compile(r"job[-_]?desc|description", re.IGNORECASE))
        if main:
            return main.get_text(separator="\n").strip()

        return soup.get_text(separator="\n").strip()[:8000]


universal_parser = UniversalJobParser()
