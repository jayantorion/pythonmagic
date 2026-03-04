import httpx
from typing import List, Optional
from bs4 import BeautifulSoup
from app.services.discovery.base import JobSource, SourceCapabilities
from app.schemas.job import JobCreate
from app.services.normalization.canonicalizer import canonicalizer
from app.core.logging import logger


class AshbyJobSource(JobSource):
    @property
    def source_name(self) -> str:
        return "ashby"

    @property
    def capabilities(self) -> SourceCapabilities:
        return SourceCapabilities(
            supports_search=True,
            supports_job_details=True,
            supports_salary=False,
            requires_api_key=False,
        )

    async def fetch_jobs_from_board(self, board_token: str) -> List[JobCreate]:
        url = f"https://api.ashbyhq.com/posting-api/job-board/{board_token}"
        jobs: List[JobCreate] = []

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(url)
                if resp.status_code != 200:
                    return []

                data = resp.json()
                raw_jobs = data.get("jobs", [])
                comp_name = canonicalizer.normalize_company_name(board_token)

                for rj in raw_jobs:
                    title = rj.get("title", "")
                    job_id = str(rj.get("id", ""))
                    app_url = rj.get("jobUrl", "")
                    loc = rj.get("location", "Remote")
                    raw_desc = rj.get("descriptionHtml", "")
                    clean_desc = BeautifulSoup(raw_desc, "html.parser").get_text(separator="\n").strip() if raw_desc else ""

                    remote_type = "remote" if rj.get("isRemote") or "remote" in loc.lower() else "on_site"

                    jobs.append(
                        JobCreate(
                            source="ashby",
                            external_id=job_id,
                            canonical_url=canonicalizer.canonicalize_url(app_url),
                            company_name=comp_name,
                            title=title,
                            normalized_title=canonicalizer.normalize_job_title(title),
                            location=loc,
                            remote_type=remote_type,
                            description_raw=clean_desc or f"Role {title} at {comp_name}",
                        )
                    )
        except Exception as e:
            logger.error(f"Error fetching Ashby jobs for {board_token}: {e}")

        return jobs

    async def fetch_jobs(self, query: str, location: Optional[str] = None, limit: int = 50) -> List[JobCreate]:
        target_boards = ["openai", "anthropic", "linear", "retool", "postman", "deel", "ramp"]
        all_jobs: List[JobCreate] = []

        for board in target_boards:
            board_jobs = await self.fetch_jobs_from_board(board)
            filtered = [
                j for j in board_jobs
                if not query or query.lower() in j.title.lower() or query.lower() in j.description_raw.lower()
            ]
            all_jobs.extend(filtered)
            if len(all_jobs) >= limit:
                break

        return all_jobs[:limit]


ashby_source = AshbyJobSource()
