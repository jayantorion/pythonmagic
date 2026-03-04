from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from app.schemas.job import JobCreate


class SourceCapabilities(BaseModel):
    supports_search: bool = True
    supports_job_details: bool = True
    supports_salary: bool = False
    supports_pagination: bool = False
    requires_api_key: bool = False
    rate_limit_rpm: int = 60


class JobSource(ABC):
    @property
    @abstractmethod
    def source_name(self) -> str:
        pass

    @property
    @abstractmethod
    def capabilities(self) -> SourceCapabilities:
        pass

    @abstractmethod
    async def fetch_jobs(self, query: str, location: Optional[str] = None, limit: int = 50) -> List[JobCreate]:
        pass
