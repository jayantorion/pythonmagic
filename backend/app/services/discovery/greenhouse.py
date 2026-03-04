import httpx
import html
import re
from typing import List, Optional
from bs4 import BeautifulSoup
from app.services.discovery.base import JobSource, SourceCapabilities
from app.schemas.job import JobCreate
from app.services.normalization.canonicalizer import canonicalizer
from app.core.logging import logger


class GreenhouseJobSource(JobSource):
    @property
    def source_name(self) -> str:
        return "greenhouse"

    @property
    def capabilities(self) -> SourceCapabilities:
        return SourceCapabilities(
            supports_search=True,
            supports_job_details=True,
            supports_salary=False,
            requires_api_key=False,
        )

    async def fetch_jobs_from_board(self, board_token: str, company_name: Optional[str] = None) -> List[JobCreate]:
        """Fetch all public job postings directly from a company's Greenhouse API."""
        url = f"https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs?content=true"
        jobs: List[JobCreate] = []

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(url)
                if resp.status_code != 200:
                    logger.warning(f"Greenhouse board {board_token} returned {resp.status_code}")
                    return []

                data = resp.json()
                raw_jobs = data.get("jobs", [])

                comp = company_name or canonicalizer.normalize_company_name(board_token)

                for rj in raw_jobs:
                    raw_html = rj.get("content", "")
                    clean_desc = BeautifulSoup(html.unescape(raw_html), "html.parser").get_text(separator="\n").strip()

                    title = rj.get("title", "")
                    loc = rj.get("location", {}).get("name", "Remote")
                    app_url = rj.get("absolute_url", "")
                    job_id = str(rj.get("id"))

                    # Determine remote type
                    remote_type = "unknown"
                    if "remote" in title.lower() or "remote" in loc.lower():
                        remote_type = "remote"
                    elif "hybrid" in loc.lower():
                        remote_type = "hybrid"
                    elif loc and loc.lower() != "remote":
                        remote_type = "on_site"

                    jobs.append(
                        JobCreate(
                            source="greenhouse",
                            external_id=job_id,
                            canonical_url=canonicalizer.canonicalize_url(app_url),
                            company_name=comp,
                            title=title,
                            normalized_title=canonicalizer.normalize_job_title(title),
                            location=loc,
                            remote_type=remote_type,
                            description_raw=clean_desc or f"Job position: {title} at {comp}. Location: {loc}",
                        )
                    )
        except Exception as e:
            logger.error(f"Error fetching from Greenhouse board {board_token}: {e}")

        return jobs

    async def fetch_jobs(self, query: str, location: Optional[str] = None, limit: int = 50) -> List[JobCreate]:
        # Top known Greenhouse companies in data/tech
        target_boards = ["databricks", "snowflake", "stripe", "canva", "figma", "airbnb", "reddit", "instacart"]
        all_jobs: List[JobCreate] = []

        for board in target_boards:
            board_jobs = await self.fetch_jobs_from_board(board)
            # Filter by query keyword in title or description
            filtered = [
                j for j in board_jobs
                if not query or query.lower() in j.title.lower() or query.lower() in j.description_raw.lower()
            ]
            all_jobs.extend(filtered)
            if len(all_jobs) >= limit:
                break

        return all_jobs[:limit]


greenhouse_source = GreenhouseJobSource()
