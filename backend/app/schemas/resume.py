from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime


class ContactInfo(BaseModel):
    full_name: str = ""
    email: str = ""
    phone: str = ""
    location: str = ""
    linkedin: Optional[str] = None
    github: Optional[str] = None
    portfolio: Optional[str] = None


class ExperienceItem(BaseModel):
    id: Optional[str] = None
    company: str
    title: str
    location: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    is_current: bool = False
    bullet_points: List[str] = Field(default_factory=list)
    technologies_used: List[str] = Field(default_factory=list)


class EducationItem(BaseModel):
    institution: str
    degree: str
    field_of_study: Optional[str] = None
    graduation_year: Optional[str] = None
    gpa: Optional[str] = None


class ProjectItem(BaseModel):
    name: str
    description: Optional[str] = None
    bullet_points: List[str] = Field(default_factory=list)
    technologies_used: List[str] = Field(default_factory=list)
    link: Optional[str] = None


class ResumeAST(BaseModel):
    contact: ContactInfo = Field(default_factory=ContactInfo)
    summary: str = ""
    skills: Dict[str, List[str]] = Field(default_factory=dict)
    experience: List[ExperienceItem] = Field(default_factory=list)
    education: List[EducationItem] = Field(default_factory=list)
    projects: List[ProjectItem] = Field(default_factory=list)
    certifications: List[str] = Field(default_factory=list)


class ResumeCreate(BaseModel):
    name: str
    is_master: bool = True
    parsed_ast: ResumeAST


class ResumeOut(BaseModel):
    id: str
    profile_id: str
    name: str
    is_master: bool
    file_path: Optional[str]
    file_type: str
    parsed_ast: Dict[str, Any]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ResumeTailorRequest(BaseModel):
    resume_id: Optional[str] = None  # Master resume to use (defaults to current master)
    job_id: str
    include_cover_letter: bool = False
    target_variant: Optional[str] = None  # e.g., "Data Engineer", "Analytics Engineer"


class ResumeVersionOut(BaseModel):
    id: str
    resume_id: str
    job_id: Optional[str]
    version_tag: str
    variant_type: str
    tailored_ast: Dict[str, Any]
    ats_score: float
    diff_provenance: Dict[str, Any]
    pdf_path: Optional[str]
    docx_path: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True
