import httpx
import html
from typing import List, Optional
from bs4 import BeautifulSoup
from app.services.discovery.base import JobSource, SourceCapabilities
from app.schemas.job import JobCreate
from app.services.normalization.canonicalizer import canonicalizer
from app.core.logging import logger


class LeverJobSource(JobSource):
    @property
    def source_name(self) -> str:
        return "lever"

    @property
    def capabilities(self) -> SourceCapabilities:
        return SourceCapabilities(
            supports_search=True,
            supports_job_details=True,
            supports_salary=False,
            requires_api_key=False,
        )

    async def fetch_jobs_from_company(self, company_slug: str) -> List[JobCreate]:
        url = f"https://api.lever.co/v0/postings/{company_slug}?mode=json"
        jobs: List[JobCreate] = []

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(url)
                if resp.status_code != 200:
                    return []

                raw_list = resp.json()
                comp_name = canonicalizer.normalize_company_name(company_slug)

                for item in raw_list:
                    title = item.get("text", "")
                    job_id = str(item.get("id", ""))
                    hosted_url = item.get("hostedUrl", "")
                    categories = item.get("categories", {})
                    loc = categories.get("location", "Remote")
                    desc_plain = item.get("descriptionPlain", "") or ""

                    # Additional lists like requirements
                    lists = item.get("lists", [])
                    extra_desc = []
                    for l in lists:
                        extra_desc.append(l.get("text", "") + ":\n" + BeautifulSoup(l.get("content", ""), "html.parser").get_text())

                    full_desc = desc_plain + "\n\n" + "\n".join(extra_desc)

                    remote_type = "unknown"
                    if "remote" in title.lower() or "remote" in loc.lower():
                        remote_type = "remote"
                    elif "hybrid" in loc.lower():
                        remote_type = "hybrid"

                    jobs.append(
                        JobCreate(
                            source="lever",
                            external_id=job_id,
                            canonical_url=canonicalizer.canonicalize_url(hosted_url),
                            company_name=comp_name,
                            title=title,
                            normalized_title=canonicalizer.normalize_job_title(title),
                            location=loc,
                            remote_type=remote_type,
                            description_raw=full_desc.strip() or f"Position {title} at {comp_name}",
                        )
                    )
        except Exception as e:
            logger.error(f"Error fetching from Lever company {company_slug}: {e}")

        return jobs

    async def fetch_jobs(self, query: str, location: Optional[str] = None, limit: int = 50) -> List[JobCreate]:
        target_companies = ["spotify", "netflix", "affirm", "atlassian", "palantir", "plaid"]
        all_jobs: List[JobCreate] = []

        for comp in target_companies:
            comp_jobs = await self.fetch_jobs_from_company(comp)
            filtered = [
                j for j in comp_jobs
                if not query or query.lower() in j.title.lower() or query.lower() in j.description_raw.lower()
            ]
            all_jobs.extend(filtered)
            if len(all_jobs) >= limit:
                break

        return all_jobs[:limit]


lever_source = LeverJobSource()
