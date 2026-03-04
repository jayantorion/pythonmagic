from sqlalchemy import Column, String, Integer, Float, Text, JSON, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship
from datetime import datetime
from app.models.base import BaseModel


class Company(BaseModel):
    __tablename__ = "companies"

    name = Column(String(255), nullable=False)
    normalized_name = Column(String(255), nullable=False, index=True)
    website = Column(String(255), nullable=True)
    domain = Column(String(255), nullable=True)
    industry = Column(String(255), nullable=True)
    last_applied_at = Column(DateTime, nullable=True)
    notes = Column(Text, nullable=True)

    jobs = relationship("Job", back_populates="company")


class Job(BaseModel):
    __tablename__ = "jobs"

    source = Column(String(50), nullable=False, index=True)  # greenhouse, lever, ashby, adzuna, manual_url, etc.
    external_id = Column(String(255), nullable=True, index=True)
    canonical_url = Column(Text, nullable=False, index=True)
    company_id = Column(String(36), ForeignKey("companies.id"), nullable=True)
    company_name = Column(String(255), nullable=False)

    title = Column(String(255), nullable=False)
    normalized_title = Column(String(255), nullable=False, index=True)
    location = Column(String(255), nullable=True)
    remote_type = Column(String(50), default="unknown")  # remote, hybrid, on_site, unknown
    employment_type = Column(String(50), default="full_time")  # full_time, contract, internship, etc.

    salary_min = Column(Float, nullable=True)
    salary_max = Column(Float, nullable=True)
    salary_currency = Column(String(10), default="INR")
    salary_raw = Column(String(100), nullable=True)

    description_raw = Column(Text, nullable=False)
    requirements_structured = Column(
        JSON,
        nullable=True,
        default=lambda: {
            "required_skills": [],
            "preferred_skills": [],
            "responsibilities": [],
            "experience_years_min": None,
            "education": [],
            "tools_technologies": [],
            "dealbreakers": [],
        },
    )

    posted_at = Column(DateTime, nullable=True)
    discovered_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    status = Column(String(50), default="discovered", index=True)  # discovered, analyzing, matched, archived

    # Relationships
    company = relationship("Company", back_populates="jobs")
    match = relationship("JobMatch", back_populates="job", uselist=False, cascade="all, delete-orphan")
    application = relationship("Application", back_populates="job", uselist=False, cascade="all, delete-orphan")


class JobEmbedding(BaseModel):
    __tablename__ = "job_embeddings"

    job_id = Column(String(36), ForeignKey("jobs.id"), nullable=False, unique=True)
    content_hash = Column(String(64), nullable=False, index=True)
    embedding_json = Column(JSON, nullable=False)  # Stored as list of floats for SQLite & DB portability
