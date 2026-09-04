from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.auth import get_current_active_user
from app.core.database import get_db
from app.core.logging import logger
from app.models.resume import Resume, ResumeVersion
from app.models.job import Job
from app.models.user import User
from app.models.candidate import ProfileFact
from app.models.application import Application, ApplicationStatus, ApplicationEvent
from app.schemas.resume import ResumeOut, ResumeVersionOut, ResumeTailorRequest
from app.services.resume.tailor import resume_tailor_engine
from app.services.resume.pdf_generator import doc_generator
from app.services.ai.claude import claude_ai_provider
from app.api.v1.candidate import get_or_create_user_profile

router = APIRouter(prefix="/resume", tags=["Resume Tailoring Engine"])


@router.post("/tailor", response_model=ResumeVersionOut)
async def tailor_resume_for_job(
    request: ResumeTailorRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    profile = await get_or_create_user_profile(db, current_user)

    # 1. Fetch target job (and verify it has a match for this user)
    job_res = await db.execute(
        select(Job)
        .options(selectinload(Job.matches))
        .where(Job.id == request.job_id)
    )
    job = job_res.scalars().first()
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Target job not found")
    if not any(m.profile_id == profile.id for m in job.matches):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Target job not found")

    # 2. Fetch master resume for the user
    if request.resume_id:
        resume_res = await db.execute(
            select(Resume).where(Resume.id == request.resume_id, Resume.profile_id == profile.id)
        )
    else:
        resume_res = await db.execute(
            select(Resume)
            .where(Resume.profile_id == profile.id, Resume.is_master == True)
            .order_by(Resume.created_at.desc())
        )
    master_resume = resume_res.scalars().first()
    if not master_resume:
        res_any = await db.execute(
            select(Resume).where(Resume.profile_id == profile.id).order_by(Resume.created_at.desc())
        )
        master_resume = res_any.scalars().first()

    master_ast = master_resume.parsed_ast if master_resume else {
        "contact": {"full_name": profile.full_name, "email": profile.email, "phone": profile.phone, "location": profile.location},
        "summary": profile.career_summary,
        "skills": {"Languages": ["Python", "SQL"], "Frameworks": ["Spark", "Airflow"], "Cloud & DB": ["Snowflake", "AWS"]},
        "experience": [{
            "company": "Enterprise Tech",
            "title": "Data Engineer",
            "start_date": "2021",
            "end_date": "Present",
            "bullet_points": [
                "Built resilient PySpark and Airflow data pipelines processing 500GB+ daily records.",
                "Optimized SQL queries and data models in Snowflake, reducing costs by 30%.",
            ],
            "technologies_used": ["Python", "SQL", "Spark", "Airflow", "Snowflake"],
        }],
        "education": [{"institution": "Engineering University", "degree": "B.Tech", "field_of_study": "Computer Science"}],
        "projects": [{"name": "Streaming Pipeline", "bullet_points": ["Kafka to Spark streaming ingestion"]}],
        "certifications": ["AWS Certified Data Analytics"],
    }

    # 3. Fetch verified facts (user-scoped)
    facts_res = await db.execute(select(ProfileFact).where(ProfileFact.profile_id == profile.id))
    verified_facts = facts_res.scalars().all()

    job_data = {
        "title": job.title,
        "company_name": job.company_name,
        "description_raw": job.description_raw,
        "requirements_structured": job.requirements_structured or {},
    }

    # 4. Run tailoring engine
    guarded_ast, diff_provenance, ats_score = await resume_tailor_engine.tailor_resume(
        master_ast=master_ast,
        job_data=job_data,
        verified_facts=verified_facts,
        variant_type=request.target_variant or "targeted",
    )

    version_tag = f"{job.company_name.lower().replace(' ', '_')}_{job.id[:8]}_v1"
    doc_path = doc_generator.save_html_and_pdf(guarded_ast, version_tag)

    resume_version = ResumeVersion(
        resume_id=master_resume.id if master_resume else "default_resume",
        job_id=job.id,
        version_tag=version_tag,
        variant_type=request.target_variant or "targeted",
        tailored_ast=guarded_ast,
        ats_score=ats_score,
        diff_provenance=diff_provenance,
        pdf_path=doc_path,
    )
    db.add(resume_version)
    await db.flush()

    # 5. Update application CRM (user-scoped)
    app_res = await db.execute(
        select(Application).where(
            Application.job_id == job.id, Application.profile_id == profile.id
        )
    )
    app_record = app_res.scalars().first()
    if app_record:
        app_record.resume_version_id = resume_version.id
        app_record.status = ApplicationStatus.READY_TO_APPLY

        event = ApplicationEvent(
            application_id=app_record.id,
            event_type="resume_tailored",
            from_status=ApplicationStatus.DISCOVERED.value,
            to_status=ApplicationStatus.READY_TO_APPLY.value,
            title="Resume Tailored & ATS Validated",
            description=f"Generated tailored resume with ATS Score: {ats_score}%. Grounding verification: {diff_provenance['grounding_check']}.",
        )
        db.add(event)

    await db.commit()
    await db.refresh(resume_version)
    return resume_version


@router.get("/versions", response_model=list[ResumeVersionOut])
async def list_resume_versions(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """List all resume versions owned by the current user."""
    profile = await get_or_create_user_profile(db, current_user)

    # ResumeVersion doesn't directly store profile_id; we go through Resume
    stmt = (
        select(ResumeVersion)
        .join(Resume, ResumeVersion.resume_id == Resume.id)
        .where(Resume.profile_id == profile.id)
        .order_by(ResumeVersion.created_at.desc())
    )
    result = await db.execute(stmt)
    return result.scalars().all()


@router.get("/versions/{version_id}", response_model=ResumeVersionOut)
async def get_resume_version(
    version_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    profile = await get_or_create_user_profile(db, current_user)

    stmt = (
        select(ResumeVersion)
        .join(Resume, ResumeVersion.resume_id == Resume.id)
        .where(ResumeVersion.id == version_id, Resume.profile_id == profile.id)
    )
    result = await db.execute(stmt)
    ver = result.scalars().first()
    if not ver:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resume version not found")
    return ver


@router.get("/versions/{version_id}/preview", response_class=HTMLResponse)
async def preview_resume_version_html(
    version_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    profile = await get_or_create_user_profile(db, current_user)
    stmt = (
        select(ResumeVersion)
        .join(Resume, ResumeVersion.resume_id == Resume.id)
        .where(ResumeVersion.id == version_id, Resume.profile_id == profile.id)
    )
    result = await db.execute(stmt)
    ver = result.scalars().first()
    if not ver:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resume version not found")

    html = doc_generator.generate_html_resume(ver.tailored_ast)
    return HTMLResponse(content=html)


@router.post("/cover-letter")
async def generate_cover_letter(
    job_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    profile = await get_or_create_user_profile(db, current_user)

    job_res = await db.execute(
        select(Job).options(selectinload(Job.matches)).where(Job.id == job_id)
    )
    job = job_res.scalars().first()
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    if not any(m.profile_id == profile.id for m in job.matches):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    job_data = {"title": job.title, "company_name": job.company_name, "description_raw": job.description_raw}
    cand_data = {"full_name": profile.full_name, "domain": profile.domain, "experience_years": profile.experience_years}

    # Latest tailored resume for this user/job
    ver_res = await db.execute(
        select(ResumeVersion)
        .join(Resume, ResumeVersion.resume_id == Resume.id)
        .where(ResumeVersion.job_id == job_id, Resume.profile_id == profile.id)
        .order_by(ResumeVersion.created_at.desc())
    )
    version = ver_res.scalars().first()
    ast = version.tailored_ast if version else {}

    letter = await claude_ai_provider.generate_cover_letter(job_data, cand_data, ast)

    app_res = await db.execute(
        select(Application).where(
            Application.job_id == job.id, Application.profile_id == profile.id
        )
    )
    app_record = app_res.scalars().first()
    if app_record:
        app_record.cover_letter = letter
        await db.commit()

    return {"cover_letter": letter, "job_id": job.id, "company_name": job.company_name}
