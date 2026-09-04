from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, desc
from sqlalchemy.orm import selectinload

from app.core.auth import get_current_active_user
from app.core.database import get_db
from app.core.logging import logger
from app.models.job import Job, Company, JobEmbedding
from app.models.match import JobMatch
from app.models.candidate import CandidateProfile, ProfileFact
from app.models.user import User
from app.models.application import Application, ApplicationStatus, ApplicationEvent
from app.schemas.job import JobCreate, JobOut, JobIngestRequest
from app.services.normalization.canonicalizer import canonicalizer
from app.services.normalization.deduplicator import deduplication_engine
from app.services.matching.hard_filters import hard_filter_engine
from app.services.matching.explainer import matching_engine
from app.services.discovery.greenhouse import greenhouse_source
from app.services.discovery.lever import lever_source
from app.services.discovery.ashby import ashby_source
from app.services.discovery.universal_parser import universal_parser
from app.services.ai.claude import claude_ai_provider
from app.services.ai.embedding import embedding_service
from app.api.v1.candidate import get_or_create_user_profile

router = APIRouter(prefix="/jobs", tags=["Jobs & Discovery"])


def _attach_user_views(job: Job, profile_id: str) -> None:
    """Set transient `job.match` / `job.application` to the rows owned by this profile.

    The Job model now holds one-to-many `matches`/`applications`; the API/serializers
    expect the current user's single row exposed as `match`/`application`.
    """
    job.match = next((m for m in job.matches if m.profile_id == profile_id), None)
    job.application = next((a for a in job.applications if a.profile_id == profile_id), None)


@router.get("", response_model=List[JobOut])
async def list_jobs(
    query: Optional[str] = None,
    min_score: Optional[float] = None,
    status: Optional[str] = None,
    remote_only: bool = False,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """List jobs visible to the current user (those that have a JobMatch tied to their profile)."""
    profile = await get_or_create_user_profile(db, current_user)

    # Only show jobs that have a JobMatch tied to the current user's profile.
    # This guarantees user-scoping: a job ingested for user A is invisible to user B.
    stmt = (
        select(Job)
        .join(JobMatch, JobMatch.job_id == Job.id)
        .options(selectinload(Job.matches), selectinload(Job.company), selectinload(Job.applications))
        .where(JobMatch.profile_id == profile.id)
    )

    if query:
        stmt = stmt.where(
            or_(
                Job.title.ilike(f"%{query}%"),
                Job.company_name.ilike(f"%{query}%"),
                Job.description_raw.ilike(f"%{query}%"),
            )
        )

    if remote_only:
        stmt = stmt.where(Job.remote_type == "remote")

    if status:
        stmt = stmt.where(Job.status == status)

    if min_score is not None:
        stmt = stmt.where(JobMatch.overall_score >= min_score).order_by(desc(JobMatch.overall_score))
    else:
        stmt = stmt.order_by(desc(Job.discovered_at))

    stmt = stmt.distinct().offset(offset).limit(limit)
    result = await db.execute(stmt)
    jobs = result.scalars().unique().all()
    for job in jobs:
        _attach_user_views(job, profile.id)
    return jobs


@router.get("/{job_id}", response_model=JobOut)
async def get_job_detail(
    job_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    profile = await get_or_create_user_profile(db, current_user)

    stmt = (
        select(Job)
        .options(selectinload(Job.matches), selectinload(Job.company), selectinload(Job.applications))
        .where(Job.id == job_id)
    )
    result = await db.execute(stmt)
    job = result.scalars().first()
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    _attach_user_views(job, profile.id)

    # Enforce user-scoping: job must have a match (or application) tied to current user's profile
    if job.match is None and job.application is None and job.matches:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    return job


@router.post("/ingest", response_model=JobOut)
async def ingest_single_job(
    request: JobIngestRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Ingest a single job from a pasted URL or raw text description."""
    profile = await get_or_create_user_profile(db, current_user)

    try:
        job_create = await universal_parser.parse_from_url_or_text(request)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    is_dup, existing_job, dup_reason = await deduplication_engine.find_duplicate(
        db=db,
        source=job_create.source,
        external_id=job_create.external_id,
        canonical_url=job_create.canonical_url,
        company_name=job_create.company_name,
        title=job_create.title,
        location=job_create.location,
        description_raw=job_create.description_raw,
    )
    if is_dup and existing_job:
        # Verify the existing job belongs to this user (match exists for this profile)
        match_res = await db.execute(
            select(JobMatch).where(
                JobMatch.job_id == existing_job.id, JobMatch.profile_id == profile.id
            )
        )
        if match_res.scalars().first():
            logger.info(
                f"Duplicate job detected ({dup_reason}) for user '{current_user.username}': "
                f"returning existing record {existing_job.id}"
            )
            await db.refresh(existing_job)
            await db.refresh(existing_job, ["matches", "applications", "company"])
            _attach_user_views(existing_job, profile.id)
            return existing_job
        # Otherwise this job exists globally but the current user has no match yet —
        # create a user-scoped match + application for the EXISTING job (no new Job row).
        facts_res = await db.execute(select(ProfileFact).where(ProfileFact.profile_id == profile.id))
        facts = facts_res.scalars().all()
        match_result = await matching_engine.match_and_explain(job_create, profile, facts)
        job_match = JobMatch(
            job_id=existing_job.id,
            profile_id=profile.id,
            overall_score=match_result["overall_score"],
            skills_score=match_result["skills_score"],
            experience_score=match_result["experience_score"],
            domain_score=match_result["domain_score"],
            seniority_score=match_result["seniority_score"],
            recommendation=match_result["recommendation"],
            pros=match_result["pros"],
            gaps=match_result["gaps"],
            dealbreakers=match_result["dealbreakers"],
            missing_skills_status=match_result["missing_skills_status"],
            explanation=match_result["explanation"],
        )
        db.add(job_match)
        app_record = Application(
            job_id=existing_job.id,
            profile_id=profile.id,
            status=ApplicationStatus.DISCOVERED,
        )
        db.add(app_record)
        await db.commit()
        await db.refresh(existing_job)
        await db.refresh(existing_job, ["matches", "applications", "company"])
        _attach_user_views(existing_job, profile.id)
        logger.info(
            f"Linked existing job '{existing_job.title}' to user '{current_user.username}' ({dup_reason})"
        )
        return existing_job

    structured_reqs = await claude_ai_provider.analyze_job_description(
        job_create.description_raw, target_domain=profile.domain
    )
    job_create.requirements_structured = structured_reqs

    norm_comp = canonicalizer.normalize_company_name(job_create.company_name)
    comp_res = await db.execute(select(Company).where(Company.normalized_name == norm_comp))
    company = comp_res.scalars().first()
    if not company:
        company = Company(name=job_create.company_name, normalized_name=norm_comp)
        db.add(company)
        await db.flush()

    job = Job(
        source=job_create.source,
        external_id=job_create.external_id,
        canonical_url=job_create.canonical_url,
        company_id=company.id,
        company_name=job_create.company_name,
        title=job_create.title,
        normalized_title=job_create.normalized_title or canonicalizer.normalize_job_title(job_create.title),
        location=job_create.location,
        remote_type=job_create.remote_type,
        employment_type=job_create.employment_type or "full_time",
        salary_min=job_create.salary_min,
        salary_max=job_create.salary_max,
        salary_currency=job_create.salary_currency or "INR",
        salary_raw=job_create.salary_raw,
        description_raw=job_create.description_raw,
        requirements_structured=structured_reqs,
        posted_at=job_create.posted_at or datetime.utcnow(),
        status="discovered",
    )
    db.add(job)
    await db.flush()

    emb = await embedding_service.get_embedding(job.description_raw[:2000])
    job_emb = JobEmbedding(
        job_id=job.id,
        content_hash=embedding_service.hash_text(job.description_raw),
        embedding_json=emb,
    )
    db.add(job_emb)

    facts_res = await db.execute(select(ProfileFact).where(ProfileFact.profile_id == profile.id))
    facts = facts_res.scalars().all()

    match_result = await matching_engine.match_and_explain(job_create, profile, facts)
    job_match = JobMatch(
        job_id=job.id,
        profile_id=profile.id,
        overall_score=match_result["overall_score"],
        skills_score=match_result["skills_score"],
        experience_score=match_result["experience_score"],
        domain_score=match_result["domain_score"],
        seniority_score=match_result["seniority_score"],
        recommendation=match_result["recommendation"],
        pros=match_result["pros"],
        gaps=match_result["gaps"],
        dealbreakers=match_result["dealbreakers"],
        missing_skills_status=match_result["missing_skills_status"],
        explanation=match_result["explanation"],
    )
    db.add(job_match)

    app_record = Application(
        job_id=job.id,
        profile_id=profile.id,
        status=ApplicationStatus.DISCOVERED,
    )
    db.add(app_record)
    await db.flush()

    event = ApplicationEvent(
        application_id=app_record.id,
        event_type="discovered",
        to_status=ApplicationStatus.DISCOVERED.value,
        title="Job Discovered & Ingested",
        description=f"Job ingested via {job.source}. Match score: {job_match.overall_score}% ({job_match.recommendation})",
    )
    db.add(event)

    await db.commit()
    await db.refresh(job)
    return job


@router.post("/discover")
async def trigger_discovery(
    query: Optional[str] = None,
    limit: int = 15,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Scan compliant ATS feeds (Greenhouse, Lever, Ashby) for target domain jobs."""
    profile = await get_or_create_user_profile(db, current_user)
    search_term = query or profile.domain or "Data Engineer"

    logger.info(
        f"User '{current_user.username}' triggering multi-channel discovery for: '{search_term}'"
    )
    discovered_jobs: List[JobCreate] = []

    try:
        gh_jobs = await greenhouse_source.fetch_jobs(search_term, limit=limit)
        discovered_jobs.extend(gh_jobs)
    except Exception as e:
        logger.error(f"Greenhouse discovery failed: {e}")

    try:
        lever_jobs = await lever_source.fetch_jobs(search_term, limit=limit)
        discovered_jobs.extend(lever_jobs)
    except Exception as e:
        logger.error(f"Lever discovery failed: {e}")

    try:
        ashby_jobs = await ashby_source.fetch_jobs(search_term, limit=limit)
        discovered_jobs.extend(ashby_jobs)
    except Exception as e:
        logger.error(f"Ashby discovery failed: {e}")

    if not discovered_jobs:
        discovered_jobs = _get_default_seed_jobs()

    ingested_count = 0
    duplicate_count = 0
    filtered_count = 0
    linked_count = 0
    pending_app_job_ids = set()  # guard: same existing job may be matched by multiple discovered jobs
    pending_match_job_ids = set()  # guard for JobMatch uniqueness (job_id, profile_id)

    facts_res = await db.execute(select(ProfileFact).where(ProfileFact.profile_id == profile.id))
    facts = facts_res.scalars().all()

    for jc in discovered_jobs:
        filter_res = hard_filter_engine.evaluate(jc, profile)
        if not filter_res.passed:
            filtered_count += 1
            continue

        is_dup, existing_job, dup_reason = await deduplication_engine.find_duplicate(
            db=db,
            source=jc.source,
            external_id=jc.external_id,
            canonical_url=jc.canonical_url,
            company_name=jc.company_name,
            title=jc.title,
            location=jc.location,
            description_raw=jc.description_raw,
        )
        if is_dup:
            duplicate_count += 1
            # The job already exists globally, but this user may not have a
            # JobMatch/Application for it yet (user-scoped visibility relies on
            # JobMatch rows). Create one so the job shows up for this user.
            if existing_job is not None:
                existing_match_res = await db.execute(
                    select(JobMatch).where(
                        JobMatch.job_id == existing_job.id,
                        JobMatch.profile_id == profile.id,
                    )
                )
                existing_match = existing_match_res.scalars().first()
                if not existing_match and existing_job.id not in pending_match_job_ids:
                    match_res = await matching_engine.match_and_explain(jc, profile, facts)
                    job_match = JobMatch(
                        job_id=existing_job.id,
                        profile_id=profile.id,
                        overall_score=match_res["overall_score"],
                        skills_score=match_res["skills_score"],
                        experience_score=match_res["experience_score"],
                        domain_score=match_res["domain_score"],
                        seniority_score=match_res["seniority_score"],
                        recommendation=match_res["recommendation"],
                        pros=match_res["pros"],
                        gaps=match_res["gaps"],
                        dealbreakers=match_res["dealbreakers"],
                        missing_skills_status=match_res["missing_skills_status"],
                        explanation=match_res["explanation"],
                    )
                    db.add(job_match)
                    pending_match_job_ids.add(existing_job.id)
                    ingested_count += 1

                # Ensure the user also has a pipeline (Application) entry for this job
                if existing_job.id not in pending_app_job_ids:
                    existing_app_res = await db.execute(
                        select(Application).where(
                            Application.job_id == existing_job.id,
                            Application.profile_id == profile.id,
                        )
                    )
                    if not existing_app_res.scalars().first():
                        app_record = Application(
                            job_id=existing_job.id,
                            profile_id=profile.id,
                            status=ApplicationStatus.DISCOVERED,
                        )
                        db.add(app_record)
                    pending_app_job_ids.add(existing_job.id)

                logger.info(
                    f"Linked existing job '{existing_job.title}' to user profile "
                    f"{profile.id} ({dup_reason})"
                )
            continue

        norm_comp = canonicalizer.normalize_company_name(jc.company_name)
        comp_res = await db.execute(select(Company).where(Company.normalized_name == norm_comp))
        company = comp_res.scalars().first()
        if not company:
            company = Company(name=jc.company_name, normalized_name=norm_comp)
            db.add(company)
            await db.flush()

        structured_reqs = await claude_ai_provider.analyze_job_description(
            jc.description_raw, target_domain=profile.domain
        )
        jc.requirements_structured = structured_reqs

        job = Job(
            source=jc.source,
            external_id=jc.external_id,
            canonical_url=jc.canonical_url,
            company_id=company.id,
            company_name=jc.company_name,
            title=jc.title,
            normalized_title=jc.normalized_title or canonicalizer.normalize_job_title(jc.title),
            location=jc.location,
            remote_type=jc.remote_type,
            employment_type="full_time",
            description_raw=jc.description_raw,
            requirements_structured=structured_reqs,
            posted_at=datetime.utcnow(),
            status="discovered",
        )
        db.add(job)
        await db.flush()

        match_res = await matching_engine.match_and_explain(jc, profile, facts)
        job_match = JobMatch(
            job_id=job.id,
            profile_id=profile.id,
            overall_score=match_res["overall_score"],
            skills_score=match_res["skills_score"],
            experience_score=match_res["experience_score"],
            domain_score=match_res["domain_score"],
            seniority_score=match_res["seniority_score"],
            recommendation=match_res["recommendation"],
            pros=match_res["pros"],
            gaps=match_res["gaps"],
            dealbreakers=match_res["dealbreakers"],
            missing_skills_status=match_res["missing_skills_status"],
            explanation=match_res["explanation"],
        )
        db.add(job_match)
        pending_match_job_ids.add(job.id)

        app_record = Application(job_id=job.id, profile_id=profile.id, status=ApplicationStatus.DISCOVERED)
        db.add(app_record)
        pending_app_job_ids.add(job.id)

        ingested_count += 1

    await db.commit()

    return {
        "status": "completed",
        "discovered_total": len(discovered_jobs),
        "new_jobs_added": ingested_count,
        "duplicates_removed": duplicate_count,
        "filtered_out": filtered_count,
    }


def _get_default_seed_jobs() -> List[JobCreate]:
    return [
        JobCreate(
            source="greenhouse",
            external_id="gh_seed_001",
            canonical_url="https://boards.greenhouse.io/databricks/jobs/5001",
            company_name="Databricks",
            title="Senior Data Platform Engineer",
            normalized_title="Senior Data Engineer",
            location="Bangalore, India",
            remote_type="hybrid",
            description_raw="""We are seeking a Senior Data Platform Engineer to design, scale, and maintain our lakehouse infrastructure.
Requirements:
- 3+ years of experience with Python, SQL, and Apache Spark / PySpark.
- Hands-on experience with Delta Lake, Apache Airflow, and cloud infrastructure (AWS or Azure).
- Proven expertise in data modeling, query optimization, and building fault-tolerant ETL/ELT pipelines.
- Knowledge of Kafka and streaming architectures is a strong plus.""",
        ),
        JobCreate(
            source="lever",
            external_id="lev_seed_002",
            canonical_url="https://jobs.lever.co/snowflake/jobs/8002",
            company_name="Snowflake",
            title="Data Engineer - Core Pipelines",
            normalized_title="Data Engineer",
            location="Remote India",
            remote_type="remote",
            description_raw="""Join our Core Pipelines team to build mission-critical data processing systems.
Responsibilities:
- Develop robust data pipelines using Python, SQL, and Snowflake.
- Manage workflow orchestration using Apache Airflow or dbt.
- Collaborate with Analytics and ML teams to deliver clean, governed datasets.
Qualifications:
- 2+ years of production experience in Data Engineering.
- Strong SQL proficiency and experience with distributed systems.""",
        ),
        JobCreate(
            source="ashby",
            external_id="ash_seed_003",
            canonical_url="https://jobs.ashbyhq.com/postman/jobs/3003",
            company_name="Postman",
            title="Analytics & Data Engineer",
            normalized_title="Analytics Engineer",
            location="Bangalore, India",
            remote_type="remote",
            description_raw="""Postman is hiring a Data Engineer to scale product analytics pipelines.
What you'll do:
- Design data models in dbt, BigQuery, and Snowflake.
- Build automated data validation frameworks with Great Expectations.
- Work with Python, Airflow, and REST APIs to ingest telemetry data.""",
        ),
    ]
