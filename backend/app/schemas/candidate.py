from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime


class SalaryExpectation(BaseModel):
    min_amount: float = 2000000
    currency: str = "INR"
    period: str = "annual"  # annual, monthly, hourly


class TechStackPriorities(BaseModel):
    must_have: List[str] = Field(default_factory=lambda: ["Python", "SQL", "Spark", "Airflow"])
    preferred: List[str] = Field(default_factory=lambda: ["dbt", "Snowflake", "Databricks", "Kafka", "AWS"])
    nice_to_have: List[str] = Field(default_factory=lambda: ["Kubernetes", "Docker", "Terraform", "Iceberg"])


class PreferencesSchema(BaseModel):
    work_modes: List[str] = Field(default_factory=lambda: ["remote", "hybrid", "on_site"])
    preferred_locations: List[str] = Field(
        default_factory=lambda: ["Bangalore", "Hyderabad", "Remote India", "Remote Worldwide"]
    )
    excluded_locations: List[str] = Field(default_factory=list)
    salary_expectation: SalaryExpectation = Field(default_factory=SalaryExpectation)
    notice_period_days: int = 30
    employment_types: List[str] = Field(default_factory=lambda: ["full_time"])
    excluded_keywords: List[str] = Field(
        default_factory=lambda: ["Senior Director", "Intern", "Staffing", "PHP"]
    )
    excluded_companies: List[str] = Field(default_factory=list)
    preferred_companies: List[str] = Field(default_factory=list)
    open_to_relocation: bool = True
    work_authorization: str = "Citizen / Authorized"


class ProfileFactCreate(BaseModel):
    category: str  # EXPERIENCE, SKILL, EDUCATION, PROJECT, METRIC, CERTIFICATION
    entity_name: Optional[str] = None
    content: str
    verification_level: str = "VERIFIED"
    evidence_source: Optional[str] = None
    confidence: float = 1.0


class ProfileFactOut(ProfileFactCreate):
    id: str
    profile_id: str
    created_at: datetime

    class Config:
        from_attributes = True


class CandidateProfileCreate(BaseModel):
    full_name: str = "Candidate"
    email: Optional[str] = None
    phone: Optional[str] = None
    location: Optional[str] = "Bangalore, India"
    domain: str = "Data Engineering"
    target_roles: List[str] = Field(
        default_factory=lambda: ["Data Engineer", "Senior Data Engineer", "Analytics Engineer"]
    )
    experience_years: float = 3.0
    experience_level: str = "mid"
    tech_stack_priorities: TechStackPriorities = Field(default_factory=TechStackPriorities)
    preferences: PreferencesSchema = Field(default_factory=PreferencesSchema)
    career_summary: Optional[str] = None


class CandidateProfileUpdate(BaseModel):
    full_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    location: Optional[str] = None
    domain: Optional[str] = None
    target_roles: Optional[List[str]] = None
    experience_years: Optional[float] = None
    experience_level: Optional[str] = None
    tech_stack_priorities: Optional[TechStackPriorities] = None
    preferences: Optional[PreferencesSchema] = None
    career_summary: Optional[str] = None


class CandidateProfileOut(BaseModel):
    id: str
    user_id: Optional[str]
    full_name: str
    email: Optional[str]
    phone: Optional[str]
    location: Optional[str]
    domain: str
    target_roles: List[str]
    experience_years: float
    experience_level: str
    tech_stack_priorities: Dict[str, Any]
    preferences: Dict[str, Any]
    career_summary: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class CandidateAnswerCreate(BaseModel):
    question_text: str
    category: Optional[str] = "general"
    verified_answer: str


class CandidateAnswerOut(BaseModel):
    id: str
    profile_id: str
    question_text: str
    question_hash: str
    category: str
    verified_answer: str
    is_auto_generated: int
    created_at: datetime

    class Config:
        from_attributes = True
