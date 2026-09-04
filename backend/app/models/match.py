from sqlalchemy import Column, String, Float, Text, JSON, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from app.models.base import BaseModel


class JobMatch(BaseModel):
    __tablename__ = "job_matches"
    __table_args__ = (UniqueConstraint("job_id", "profile_id", name="uq_job_match_job_profile"),)

    job_id = Column(String(36), ForeignKey("jobs.id"), nullable=False, index=True)
    profile_id = Column(String(36), ForeignKey("candidate_profiles.id"), nullable=False)

    overall_score = Column(Float, nullable=False, default=0.0, index=True)
    skills_score = Column(Float, nullable=False, default=0.0)
    experience_score = Column(Float, nullable=False, default=0.0)
    domain_score = Column(Float, nullable=False, default=0.0)
    seniority_score = Column(Float, nullable=False, default=0.0)

    recommendation = Column(String(50), nullable=False, default="CONSIDER")  # EXCELLENT, STRONG, CONSIDER, WEAK, SKIP

    pros = Column(JSON, nullable=False, default=list)
    gaps = Column(JSON, nullable=False, default=list)
    dealbreakers = Column(JSON, nullable=False, default=list)
    missing_skills_status = Column(JSON, nullable=False, default=dict)  # {"Kubernetes": "MISSING", "Docker": "CONFIRMED"}

    explanation = Column(Text, nullable=True)

    job = relationship("Job", back_populates="matches")
