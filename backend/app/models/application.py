import enum
from datetime import datetime
from sqlalchemy import Column, String, Text, DateTime, ForeignKey, Enum as SQLEnum, JSON
from sqlalchemy.orm import relationship
from app.models.base import BaseModel


class ApplicationStatus(str, enum.Enum):
    DISCOVERED = "DISCOVERED"
    SHORTLISTED = "SHORTLISTED"
    READY_TO_APPLY = "READY_TO_APPLY"
    APPLIED = "APPLIED"
    ASSESSMENT = "ASSESSMENT"
    RECRUITER_SCREEN = "RECRUITER_SCREEN"
    INTERVIEW = "INTERVIEW"
    TECHNICAL_INTERVIEW = "TECHNICAL_INTERVIEW"
    FINAL_INTERVIEW = "FINAL_INTERVIEW"
    OFFER = "OFFER"
    REJECTED = "REJECTED"
    WITHDRAWN = "WITHDRAWN"
    NO_RESPONSE = "NO_RESPONSE"


class Application(BaseModel):
    __tablename__ = "applications"

    job_id = Column(String(36), ForeignKey("jobs.id"), nullable=False, unique=True)
    profile_id = Column(String(36), ForeignKey("candidate_profiles.id"), nullable=False)
    resume_version_id = Column(String(36), ForeignKey("resume_versions.id"), nullable=True)

    status = Column(SQLEnum(ApplicationStatus), default=ApplicationStatus.DISCOVERED, nullable=False, index=True)
    applied_at = Column(DateTime, nullable=True)
    cover_letter = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)
    follow_up_date = Column(DateTime, nullable=True)
    portal_application_id = Column(String(255), nullable=True)

    # Relationships
    job = relationship("Job", back_populates="application")
    events = relationship("ApplicationEvent", back_populates="application", cascade="all, delete-orphan")


class ApplicationEvent(BaseModel):
    __tablename__ = "application_events"

    application_id = Column(String(36), ForeignKey("applications.id"), nullable=False)
    event_type = Column(String(50), nullable=False)  # status_change, note_added, interview_scheduled, email_received
    from_status = Column(String(50), nullable=True)
    to_status = Column(String(50), nullable=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    payload_json = Column(JSON, nullable=True)

    application = relationship("Application", back_populates="events")
