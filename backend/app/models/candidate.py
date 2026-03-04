from sqlalchemy import Column, String, Integer, Float, Text, JSON, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship
import enum
from app.models.base import BaseModel


class VerificationLevel(str, enum.Enum):
    VERIFIED = "VERIFIED"
    STRONG = "STRONG"
    WORKING = "WORKING"
    UNKNOWN = "UNKNOWN"
    CONFLICTING = "CONFLICTING"


class FactCategory(str, enum.Enum):
    EXPERIENCE = "EXPERIENCE"
    SKILL = "SKILL"
    EDUCATION = "EDUCATION"
    PROJECT = "PROJECT"
    METRIC = "METRIC"
    CERTIFICATION = "CERTIFICATION"


class CandidateProfile(BaseModel):
    __tablename__ = "candidate_profiles"

    user_id = Column(String(36), nullable=True, default="default_user")
    full_name = Column(String(255), nullable=False, default="Candidate")
    email = Column(String(255), nullable=True)
    phone = Column(String(50), nullable=True)
    location = Column(String(255), nullable=True)

    # Primary Domain (e.g., "Data Engineering", "Backend Development", "AI/ML")
    domain = Column(String(100), nullable=False, default="Data Engineering")
    target_roles = Column(JSON, nullable=False, default=lambda: ["Data Engineer", "Senior Data Engineer", "Analytics Engineer"])
    experience_years = Column(Float, nullable=False, default=3.0)
    experience_level = Column(String(50), nullable=False, default="mid")

    # Naukri-Style Dynamic Tech Stack Priorities
    tech_stack_priorities = Column(
        JSON,
        nullable=False,
        default=lambda: {
            "must_have": ["Python", "SQL", "Spark", "Airflow"],
            "preferred": ["dbt", "Snowflake", "Databricks", "Kafka", "AWS"],
            "nice_to_have": ["Kubernetes", "Docker", "Terraform", "Iceberg"],
        },
    )

    # Detailed Preferences
    preferences = Column(
        JSON,
        nullable=False,
        default=lambda: {
            "work_modes": ["remote", "hybrid", "on_site"],
            "preferred_locations": ["Bangalore", "Hyderabad", "Remote India", "Remote Worldwide"],
            "excluded_locations": [],
            "salary_expectation": {
                "min_amount": 2000000,
                "currency": "INR",
                "period": "annual",
            },
            "notice_period_days": 30,
            "employment_types": ["full_time"],
            "excluded_keywords": ["Senior Director", "Intern", "Staffing", "PHP"],
            "excluded_companies": [],
            "preferred_companies": [],
            "open_to_relocation": True,
            "work_authorization": "Citizen / Authorized",
        },
    )

    # Summary
    career_summary = Column(Text, nullable=True)

    # Relationships
    facts = relationship("ProfileFact", back_populates="profile", cascade="all, delete-orphan")
    answers = relationship("CandidateAnswer", back_populates="profile", cascade="all, delete-orphan")
    resumes = relationship("Resume", back_populates="profile", cascade="all, delete-orphan")


class ProfileFact(BaseModel):
    __tablename__ = "profile_facts"

    profile_id = Column(String(36), ForeignKey("candidate_profiles.id"), nullable=False)
    category = Column(SQLEnum(FactCategory), nullable=False)
    entity_name = Column(String(255), nullable=True)  # e.g., "Apache Spark", "Snowflake", "Google"
    content = Column(Text, nullable=False)  # Atomic fact description / bullet
    verification_level = Column(SQLEnum(VerificationLevel), default=VerificationLevel.VERIFIED, nullable=False)
    evidence_source = Column(String(255), nullable=True)  # e.g., "Master Resume - Ex Company", "Manual User Confirmation"
    confidence = Column(Float, default=1.0, nullable=False)

    profile = relationship("CandidateProfile", back_populates="facts")


class CandidateAnswer(BaseModel):
    __tablename__ = "candidate_answers"

    profile_id = Column(String(36), ForeignKey("candidate_profiles.id"), nullable=False)
    question_text = Column(Text, nullable=False)
    question_hash = Column(String(64), nullable=False, index=True)
    category = Column(String(100), default="general")
    verified_answer = Column(Text, nullable=False)
    is_auto_generated = Column(Integer, default=0)

    profile = relationship("CandidateProfile", back_populates="answers")
