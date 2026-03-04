from sqlalchemy import Column, String, Integer, Float, Text, JSON, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from app.models.base import BaseModel


class Resume(BaseModel):
    __tablename__ = "resumes"

    profile_id = Column(String(36), ForeignKey("candidate_profiles.id"), nullable=False)
    name = Column(String(255), nullable=False)
    is_master = Column(Boolean, default=True, nullable=False)
    file_path = Column(String(500), nullable=True)
    file_type = Column(String(50), default="pdf")  # pdf, docx, json
    raw_text = Column(Text, nullable=True)

    # Structured Resume AST
    parsed_ast = Column(
        JSON,
        nullable=False,
        default=lambda: {
            "contact": {},
            "summary": "",
            "skills": {},
            "experience": [],
            "education": [],
            "projects": [],
            "certifications": [],
        },
    )

    profile = relationship("CandidateProfile", back_populates="resumes")
    versions = relationship("ResumeVersion", back_populates="master_resume", cascade="all, delete-orphan")


class ResumeVersion(BaseModel):
    __tablename__ = "resume_versions"

    resume_id = Column(String(36), ForeignKey("resumes.id"), nullable=False)
    job_id = Column(String(36), ForeignKey("jobs.id"), nullable=True)
    version_tag = Column(String(100), nullable=False)  # e.g., "job_1234_v1", "data_eng_backend_v2"
    variant_type = Column(String(100), default="targeted")  # targeted, strategic_variant

    tailored_ast = Column(JSON, nullable=False)
    ats_score = Column(Float, default=0.0)
    diff_provenance = Column(
        JSON,
        nullable=False,
        default=lambda: {
            "reordered_sections": [],
            "emphasized_skills": [],
            "bullet_mappings": [],
            "grounding_check": "PASSED",
        },
    )
    pdf_path = Column(String(500), nullable=True)
    docx_path = Column(String(500), nullable=True)

    master_resume = relationship("Resume", back_populates="versions")
