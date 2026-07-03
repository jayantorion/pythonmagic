import hashlib
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

from app.core.database import get_db
from app.core.config import STORAGE_DIR
from app.core.config_loader import config_loader
from app.core.logging import logger
from app.models.candidate import CandidateProfile, ProfileFact, CandidateAnswer, FactCategory, VerificationLevel
from app.models.resume import Resume
from app.schemas.candidate import (
    CandidateProfileCreate,
    CandidateProfileUpdate,
    CandidateProfileOut,
    ProfileFactCreate,
    ProfileFactOut,
    CandidateAnswerCreate,
    CandidateAnswerOut,
)
from app.schemas.resume import ResumeOut, ResumeAST
from app.services.resume.parser import resume_parser
from app.services.ai.claude import claude_ai_provider

router = APIRouter(prefix="/candidate", tags=["Candidate Profile"])


async def get_or_create_default_profile(db: AsyncSession) -> CandidateProfile:
    """Get the existing candidate profile, or create one seeded from config/candidate_preferences.yaml.

    The profile values are loaded from the external YAML config so users can customize their
    profile without editing any Python code. Falls back to sensible defaults if YAML is missing.
    """
    result = await db.execute(select(CandidateProfile).limit(1))
    profile = result.scalars().first()
    if not profile:
        # Load profile data from external YAML config
        profile_data = config_loader.get_default_profile()
        tech_priorities = config_loader.get_default_tech_priorities()
        preferences = config_loader.get_default_preferences()

        # Fallback defaults if YAML config is missing or empty
        default_name = profile_data.get("full_name", "Default Candidate")
        default_email = profile_data.get("email", "candidate@example.com")
        default_domain = profile_data.get("domain", "Data Engineering")
        default_target_roles = profile_data.get("target_roles") or [
            "Data Engineer",
            "Senior Data Engineer",
            "Analytics Engineer",
            "Data Platform Engineer",
        ]
        default_experience_years = profile_data.get("experience_years", 3.0)
        default_career_summary = profile_data.get("career_summary") or (
            "Data engineer with experience building batch and streaming pipelines. "
            "Edit config/candidate_preferences.yaml to customize this profile."
        )

        # Ensure tech_priorities has all 3 categories even if YAML is partial
        if not tech_priorities.get("must_have"):
            tech_priorities = {
                "must_have": ["Python", "SQL", "Spark", "Airflow"],
                "preferred": ["dbt", "Snowflake", "Databricks", "Kafka", "AWS"],
                "nice_to_have": ["Kubernetes", "Docker", "Terraform", "Iceberg"],
            }

        # Ensure preferences dict has essential fields
        if not preferences:
            preferences = {
                "work_modes": ["remote", "hybrid", "on_site"],
                "preferred_locations": ["Bangalore", "Hyderabad", "Remote India"],
                "excluded_locations": [],
                "salary_expectation": {"min_amount": 2000000, "currency": "INR", "period": "annual"},
                "notice_period_days": 30,
                "employment_types": ["full_time"],
                "excluded_keywords": ["Senior Director", "Intern", "Staffing", "PHP"],
                "excluded_companies": [],
                "preferred_companies": [],
                "open_to_relocation": True,
                "work_authorization": "Citizen / Authorized",
            }

        profile = CandidateProfile(
            user_id="default_user",
            full_name=default_name,
            email=default_email,
            phone=profile_data.get("phone", "+91-9876543210"),
            location=profile_data.get("location", "Bangalore, India"),
            domain=default_domain,
            target_roles=default_target_roles,
            experience_years=default_experience_years,
            experience_level=profile_data.get("experience_level", "mid_senior"),
            tech_stack_priorities=tech_priorities,
            preferences=preferences,
            career_summary=default_career_summary,
        )
        db.add(profile)
        await db.commit()
        await db.refresh(profile)

        # Seed initial default facts from YAML (if available)
        yaml_facts = config_loader.get_default_facts()
        if yaml_facts:
            default_facts = []
            for f in yaml_facts:
                # Map fact_type to FactCategory enum
                category_str = f.get("fact_type", "skill").upper()
                if category_str == "SKILL":
                    category = FactCategory.SKILL
                elif category_str == "TOOL":
                    category = FactCategory.SKILL  # Treat tools as skills
                elif category_str == "EXPERIENCE":
                    category = FactCategory.EXPERIENCE
                elif category_str == "EDUCATION":
                    category = FactCategory.EDUCATION
                elif category_str == "CERTIFICATION":
                    category = FactCategory.CERTIFICATION
                else:
                    category = FactCategory.SKILL

                default_facts.append(
                    ProfileFact(
                        profile_id=profile.id,
                        category=category,
                        entity_name=f.get("fact_value", "").split("(")[0].strip()[:50],
                        content=f.get("fact_value", ""),
                        verification_level=VerificationLevel.VERIFIED if f.get("verified", True) else VerificationLevel.WORKING,
                        evidence_source="YAML Config Seed",
                        confidence=1.0 if f.get("verified", True) else 0.8,
                    )
                )
            db.add_all(default_facts)
            await db.commit()
            logger.info(f"Seeded {len(default_facts)} default facts from YAML config")
        else:
            # Fallback seed facts if YAML is missing
            default_facts = [
                ProfileFact(
                    profile_id=profile.id,
                    category=FactCategory.SKILL,
                    entity_name="PySpark",
                    content="Demonstrated production experience building batch and streaming PySpark jobs handling 500GB+ daily data.",
                    verification_level=VerificationLevel.VERIFIED,
                    evidence_source="Initial Profile Seed",
                    confidence=1.0,
                ),
                ProfileFact(
                    profile_id=profile.id,
                    category=FactCategory.SKILL,
                    entity_name="Apache Airflow",
                    content="Orchestrated 40+ complex DAGs in Apache Airflow with custom operators, SLA alerts, and backfilling.",
                    verification_level=VerificationLevel.VERIFIED,
                    evidence_source="Initial Profile Seed",
                    confidence=1.0,
                ),
                ProfileFact(
                    profile_id=profile.id,
                    category=FactCategory.SKILL,
                    entity_name="Snowflake",
                    content="Architected star and snowflake schema data models in Snowflake, optimizing clustering keys and reducing query runtimes by 35%.",
                    verification_level=VerificationLevel.VERIFIED,
                    evidence_source="Initial Profile Seed",
                    confidence=1.0,
                ),
                ProfileFact(
                    profile_id=profile.id,
                    category=FactCategory.SKILL,
                    entity_name="SQL & Python",
                    content="Expert-level proficiency in advanced SQL window functions, CTEs, indexing, and Python OOP/async programming.",
                    verification_level=VerificationLevel.VERIFIED,
                    evidence_source="Initial Profile Seed",
                    confidence=1.0,
                ),
            ]
            db.add_all(default_facts)
            await db.commit()
            logger.info("Seeded 4 fallback facts (YAML config not found)")

    return profile


@router.get("/profile", response_model=CandidateProfileOut)
async def get_profile(db: AsyncSession = Depends(get_db)):
    profile = await get_or_create_default_profile(db)
    return profile


@router.put("/profile", response_model=CandidateProfileOut)
async def update_profile(data: CandidateProfileUpdate, db: AsyncSession = Depends(get_db)):
    profile = await get_or_create_default_profile(db)

    update_dict = data.model_dump(exclude_unset=True)
    if "tech_stack_priorities" in update_dict and update_dict["tech_stack_priorities"]:
        update_dict["tech_stack_priorities"] = data.tech_stack_priorities.model_dump()
    if "preferences" in update_dict and update_dict["preferences"]:
        update_dict["preferences"] = data.preferences.model_dump()

    for k, v in update_dict.items():
        if v is not None:
            setattr(profile, k, v)

    await db.commit()
    await db.refresh(profile)
    return profile


@router.get("/facts", response_model=List[ProfileFactOut])
async def get_facts(db: AsyncSession = Depends(get_db)):
    profile = await get_or_create_default_profile(db)
    result = await db.execute(select(ProfileFact).where(ProfileFact.profile_id == profile.id))
    return result.scalars().all()


@router.post("/facts", response_model=ProfileFactOut)
async def create_fact(data: ProfileFactCreate, db: AsyncSession = Depends(get_db)):
    profile = await get_or_create_default_profile(db)
    fact = ProfileFact(
        profile_id=profile.id,
        category=FactCategory(data.category),
        entity_name=data.entity_name,
        content=data.content,
        verification_level=VerificationLevel(data.verification_level),
        evidence_source=data.evidence_source or "User Added",
        confidence=data.confidence,
    )
    db.add(fact)
    await db.commit()
    await db.refresh(fact)
    return fact


@router.get("/answers", response_model=List[CandidateAnswerOut])
async def get_answers(db: AsyncSession = Depends(get_db)):
    profile = await get_or_create_default_profile(db)
    result = await db.execute(select(CandidateAnswer).where(CandidateAnswer.profile_id == profile.id))
    return result.scalars().all()


@router.post("/answers", response_model=CandidateAnswerOut)
async def create_or_update_answer(data: CandidateAnswerCreate, db: AsyncSession = Depends(get_db)):
    profile = await get_or_create_default_profile(db)
    q_hash = hashlib.sha256(data.question_text.strip().lower().encode("utf-8")).hexdigest()

    result = await db.execute(
        select(CandidateAnswer).where(
            CandidateAnswer.profile_id == profile.id,
            CandidateAnswer.question_hash == q_hash,
        )
    )
    existing = result.scalars().first()
    if existing:
        existing.verified_answer = data.verified_answer
        existing.category = data.category or "general"
        await db.commit()
        await db.refresh(existing)
        return existing

    answer = CandidateAnswer(
        profile_id=profile.id,
        question_text=data.question_text,
        question_hash=q_hash,
        category=data.category or "general",
        verified_answer=data.verified_answer,
    )
    db.add(answer)
    await db.commit()
    await db.refresh(answer)
    return answer


@router.post("/answers/draft")
async def draft_answer(question: str, db: AsyncSession = Depends(get_db)):
    profile = await get_or_create_default_profile(db)
    q_hash = hashlib.sha256(question.strip().lower().encode("utf-8")).hexdigest()

    # Check if exact question already exists in answer bank
    result = await db.execute(
        select(CandidateAnswer).where(
            CandidateAnswer.profile_id == profile.id,
            CandidateAnswer.question_hash == q_hash,
        )
    )
    existing = result.scalars().first()
    if existing:
        return {
            "answer": existing.verified_answer,
            "source": "verified_answer_bank",
            "is_saved": True,
        }

    # Fetch facts to ground the answer
    facts_res = await db.execute(select(ProfileFact).where(ProfileFact.profile_id == profile.id))
    facts = [{"content": f.content, "entity": f.entity_name} for f in facts_res.scalars().all()]

    cand_dict = {
        "full_name": profile.full_name,
        "domain": profile.domain,
        "experience_years": profile.experience_years,
        "location": profile.location,
    }

    draft = await claude_ai_provider.draft_answer_for_question(question, cand_dict, facts)
    return {
        "answer": draft,
        "source": "ai_grounded_draft",
        "is_saved": False,
    }


@router.post("/resume/upload", response_model=ResumeOut)
async def upload_resume(
    file: UploadFile = File(...),
    is_master: bool = Form(True),
    db: AsyncSession = Depends(get_db),
):
    profile = await get_or_create_default_profile(db)
    content = await file.read()
    filename = file.filename or "resume.pdf"
    ext = Path(filename).suffix.lower()

    if ext == ".pdf":
        raw_text = resume_parser.extract_text_from_pdf(content)
        file_type = "pdf"
    elif ext in [".docx", ".doc"]:
        raw_text = resume_parser.extract_text_from_docx(content)
        file_type = "docx"
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported file format. Please upload a PDF or DOCX file.",
        )

    if not raw_text.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not extract text from the uploaded file. Please ensure it is not an encrypted or image-only scan.",
        )

    # Save physical file to storage
    saved_path = STORAGE_DIR / f"{profile.id}_{filename}"
    with open(saved_path, "wb") as f:
        f.write(content)

    # Parse AST
    ast = resume_parser.parse_to_ast(raw_text)
    ast_dict = ast.model_dump()

    # If is_master, demote any previous master resume
    if is_master:
        res = await db.execute(select(Resume).where(Resume.profile_id == profile.id, Resume.is_master == True))
        for old_master in res.scalars().all():
            old_master.is_master = False

    resume_record = Resume(
        profile_id=profile.id,
        name=filename,
        is_master=is_master,
        file_path=str(saved_path),
        file_type=file_type,
        raw_text=raw_text,
        parsed_ast=ast_dict,
    )
    db.add(resume_record)
    await db.commit()
    await db.refresh(resume_record)

    # Extract and store atomic facts
    atomic_facts = resume_parser.extract_atomic_facts(ast)
    for f_data in atomic_facts:
        fact = ProfileFact(
            profile_id=profile.id,
            category=FactCategory(f_data["category"]),
            entity_name=f_data.get("entity_name"),
            content=f_data["content"],
            verification_level=VerificationLevel(f_data["verification_level"]),
            evidence_source=f_data["evidence_source"],
            confidence=f_data["confidence"],
        )
        db.add(fact)

    await db.commit()
    logger.info(f"Parsed resume '{filename}' and stored {len(atomic_facts)} verified facts.")
    return resume_record


@router.get("/resume/master", response_model=Optional[ResumeOut])
async def get_master_resume(db: AsyncSession = Depends(get_db)):
    profile = await get_or_create_default_profile(db)
    result = await db.execute(
        select(Resume).where(Resume.profile_id == profile.id, Resume.is_master == True).order_by(Resume.created_at.desc())
    )
    master = result.scalars().first()
    if not master:
        # Fallback to any resume
        res2 = await db.execute(select(Resume).where(Resume.profile_id == profile.id).order_by(Resume.created_at.desc()))
        master = res2.scalars().first()
    return master
