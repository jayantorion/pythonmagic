import hashlib
from pathlib import Path
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.auth import get_current_active_user
from app.core.database import get_db
from app.core.config import STORAGE_DIR
from app.core.config_loader import config_loader
from app.core.logging import logger
from app.models.candidate import CandidateProfile, ProfileFact, CandidateAnswer, FactCategory, VerificationLevel
from app.models.user import User
from app.models.resume import Resume
from app.schemas.candidate import (
    CandidateProfileUpdate,
    CandidateProfileOut,
    ProfileFactCreate,
    ProfileFactOut,
    CandidateAnswerCreate,
    CandidateAnswerOut,
)
from app.schemas.resume import ResumeOut
from app.services.resume.parser import resume_parser
from app.services.ai.claude import claude_ai_provider

router = APIRouter(prefix="/candidate", tags=["Candidate Profile"])


def _map_fact_category(fact_type: str) -> FactCategory:
    ft = (fact_type or "skill").upper()
    if ft in ("SKILL", "TOOL"):
        return FactCategory.SKILL
    if ft == "EXPERIENCE":
        return FactCategory.EXPERIENCE
    if ft == "EDUCATION":
        return FactCategory.EDUCATION
    if ft == "CERTIFICATION":
        return FactCategory.CERTIFICATION
    if ft == "PROJECT":
        return FactCategory.PROJECT
    if ft == "METRIC":
        return FactCategory.METRIC
    return FactCategory.SKILL


async def get_or_create_user_profile(db: AsyncSession, user: User) -> CandidateProfile:
    """Return the CandidateProfile for the given user, creating one if missing.

    On first access for a brand-new user (defensive — should not happen post-registration),
    seeds from config/candidate_preferences.yaml.
    """
    result = await db.execute(
        select(CandidateProfile).where(CandidateProfile.user_id == user.id)
    )
    profile = result.scalars().first()
    if profile:
        return profile

    # Defensive: user somehow exists without a profile. Seed from YAML.
    profile_data = config_loader.get_default_profile()
    tech_priorities = config_loader.get_default_tech_priorities()
    preferences = config_loader.get_default_preferences()

    if not tech_priorities.get("must_have"):
        tech_priorities = {
            "must_have": ["Python", "SQL", "Spark", "Airflow"],
            "preferred": ["dbt", "Snowflake", "Databricks", "Kafka", "AWS"],
            "nice_to_have": ["Kubernetes", "Docker", "Terraform", "Iceberg"],
        }
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
        user_id=user.id,
        full_name=user.full_name or user.username,
        email=user.email,
        phone=profile_data.get("phone"),
        location=profile_data.get("location", "Bangalore, India"),
        domain=profile_data.get("domain", "Data Engineering"),
        target_roles=profile_data.get("target_roles") or ["Data Engineer", "Senior Data Engineer"],
        experience_years=profile_data.get("experience_years", 3.0),
        experience_level=profile_data.get("experience_level", "mid_senior"),
        tech_stack_priorities=tech_priorities,
        preferences=preferences,
        career_summary=profile_data.get("career_summary"),
    )
    db.add(profile)
    await db.flush()

    # Seed facts
    yaml_facts = config_loader.get_default_facts()
    if yaml_facts:
        facts = []
        for f in yaml_facts:
            value = f.get("fact_value", "")
            facts.append(
                ProfileFact(
                    profile_id=profile.id,
                    category=_map_fact_category(f.get("fact_type", "skill")),
                    entity_name=value.split("(")[0].strip()[:50] or value[:50],
                    content=value,
                    verification_level=VerificationLevel.VERIFIED
                    if f.get("verified", True)
                    else VerificationLevel.WORKING,
                    evidence_source="YAML Config Seed",
                    confidence=1.0 if f.get("verified", True) else 0.8,
                )
            )
        db.add_all(facts)

    await db.commit()
    await db.refresh(profile)
    logger.info(f"Defensively seeded profile for user '{user.username}'")
    return profile


@router.get("/profile", response_model=CandidateProfileOut)
async def get_profile(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    profile = await get_or_create_user_profile(db, current_user)
    return profile


@router.put("/profile", response_model=CandidateProfileOut)
async def update_profile(
    data: CandidateProfileUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    profile = await get_or_create_user_profile(db, current_user)

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
async def get_facts(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    profile = await get_or_create_user_profile(db, current_user)
    result = await db.execute(select(ProfileFact).where(ProfileFact.profile_id == profile.id))
    return result.scalars().all()


@router.post("/facts", response_model=ProfileFactOut)
async def create_fact(
    data: ProfileFactCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    profile = await get_or_create_user_profile(db, current_user)
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


@router.delete("/facts/{fact_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_fact(
    fact_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    profile = await get_or_create_user_profile(db, current_user)
    result = await db.execute(
        select(ProfileFact).where(
            ProfileFact.id == fact_id, ProfileFact.profile_id == profile.id
        )
    )
    fact = result.scalars().first()
    if not fact:
        raise HTTPException(status_code=404, detail="Fact not found")
    await db.delete(fact)
    await db.commit()
    return None


@router.get("/answers", response_model=List[CandidateAnswerOut])
async def get_answers(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    profile = await get_or_create_user_profile(db, current_user)
    result = await db.execute(select(CandidateAnswer).where(CandidateAnswer.profile_id == profile.id))
    return result.scalars().all()


@router.post("/answers", response_model=CandidateAnswerOut)
async def create_or_update_answer(
    data: CandidateAnswerCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    profile = await get_or_create_user_profile(db, current_user)
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
async def draft_answer(
    question: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    profile = await get_or_create_user_profile(db, current_user)
    q_hash = hashlib.sha256(question.strip().lower().encode("utf-8")).hexdigest()

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
    current_user: User = Depends(get_current_active_user),
):
    profile = await get_or_create_user_profile(db, current_user)
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

    saved_path = STORAGE_DIR / f"{profile.id}_{filename}"
    with open(saved_path, "wb") as f:
        f.write(content)

    ast = resume_parser.parse_to_ast(raw_text)
    ast_dict = ast.model_dump()

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
async def get_master_resume(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    profile = await get_or_create_user_profile(db, current_user)
    result = await db.execute(
        select(Resume).where(Resume.profile_id == profile.id, Resume.is_master == True).order_by(Resume.created_at.desc())
    )
    master = result.scalars().first()
    if not master:
        res2 = await db.execute(select(Resume).where(Resume.profile_id == profile.id).order_by(Resume.created_at.desc()))
        master = res2.scalars().first()
    return master
