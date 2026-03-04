from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime
from app.schemas.job import JobOut


class ApplicationEventCreate(BaseModel):
    event_type: str
    from_status: Optional[str] = None
    to_status: Optional[str] = None
    title: str
    description: Optional[str] = None
    payload_json: Optional[Dict[str, Any]] = None


class ApplicationEventOut(BaseModel):
    id: str
    application_id: str
    event_type: str
    from_status: Optional[str]
    to_status: Optional[str]
    title: str
    description: Optional[str]
    payload_json: Optional[Dict[str, Any]]
    created_at: datetime

    class Config:
        from_attributes = True


class ApplicationUpdate(BaseModel):
    status: Optional[str] = None
    notes: Optional[str] = None
    follow_up_date: Optional[datetime] = None
    cover_letter: Optional[str] = None
    portal_application_id: Optional[str] = None


class ApplicationOut(BaseModel):
    id: str
    job_id: str
    profile_id: str
    resume_version_id: Optional[str]
    status: str
    applied_at: Optional[datetime]
    cover_letter: Optional[str]
    notes: Optional[str]
    follow_up_date: Optional[datetime]
    portal_application_id: Optional[str]
    created_at: datetime
    updated_at: datetime
    job: Optional[JobOut] = None
    events: List[ApplicationEventOut] = Field(default_factory=list)

    class Config:
        from_attributes = True
