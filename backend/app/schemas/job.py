from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime


class JobRequirementsStructured(BaseModel):
    required_skills: List[str] = Field(default_factory=list)
    preferred_skills: List[str] = Field(default_factory=list)
    responsibilities: List[str] = Field(default_factory=list)
    tools_technologies: List[str] = Field(default_factory=list)
    experience_years_min: Optional[float] = None
    education: List[str] = Field(default_factory=list)
    dealbreakers: List[str] = Field(default_factory=list)


class CompanyOut(BaseModel):
    id: str
    name: str
    normalized_name: str
    website: Optional[str] = None
    industry: Optional[str] = None
    last_applied_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class JobCreate(BaseModel):
    source: str
    external_id: Optional[str] = None
    canonical_url: str
    company_name: str
    title: str
    normalized_title: Optional[str] = None
    location: Optional[str] = "Remote"
    remote_type: Optional[str] = "unknown"
    employment_type: Optional[str] = "full_time"
    salary_min: Optional[float] = None
    salary_max: Optional[float] = None
    salary_currency: Optional[str] = "INR"
    salary_raw: Optional[str] = None
    description_raw: str
    requirements_structured: Optional[JobRequirementsStructured] = None
    posted_at: Optional[datetime] = None


from app.schemas.match import JobMatchOut

class JobOut(BaseModel):
    id: str
    source: str
    external_id: Optional[str]
    canonical_url: str
    company_name: str
    company_id: Optional[str]
    title: str
    normalized_title: str
    location: Optional[str]
    remote_type: str
    employment_type: str
    salary_min: Optional[float]
    salary_max: Optional[float]
    salary_currency: Optional[str]
    salary_raw: Optional[str]
    description_raw: str
    requirements_structured: Optional[Dict[str, Any]]
    posted_at: Optional[datetime]
    discovered_at: datetime
    status: str
    match: Optional[JobMatchOut] = None

    class Config:
        from_attributes = True


class JobIngestRequest(BaseModel):
    url: Optional[str] = None
    raw_text: Optional[str] = None
    company_name: Optional[str] = None
    title: Optional[str] = None
    location: Optional[str] = None


class JobSearchQuery(BaseModel):
    query: Optional[str] = None
    domain: Optional[str] = None
    location: Optional[str] = None
    remote_only: bool = False
    min_match_score: Optional[float] = None
    status: Optional[str] = None
    limit: int = 50
    offset: int = 0
