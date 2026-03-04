import json
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, and_, desc
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.logging import logger
from app.models.job import Job, Company, JobEmbedding
from app.models.match import JobMatch
from app.models.candidate import CandidateProfile, ProfileFact
from app.models.application import Application, ApplicationStatus, ApplicationEvent
from app.schemas.job import JobCreate, JobOut, JobIngestRequest, JobSearchQuery
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
from app.api.v1.candidate import get_or_create_default_profile

router = APIRouter(prefix="/jobs", tags=["Jobs & Discovery"])


@router.get("", response_model=List[JobOut])
async def list_jobs(
    query: Optional[str] = None,
    min_score: Optional[float] = None,
    status: Optional[str] = None,
    remote_only: bool = False,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Job).options(selectinload(Job.match), selectinload(Job.company))

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

    # Join on match to filter by min score or order by overall score
    if min_score is not None:
        stmt = stmt.join(JobMatch).where(JobMatch.overall_score >= min_score).order_by(desc(JobMatch.overall_score))
    else:
        stmt = stmt.outerjoin(JobMatch).order_by(desc(JobMatch.overall_score), desc(Job.discovered_at))

    stmt = stmt.offset(offset).limit(limit)
    result = await db.execute(stmt)
    jobs = result.scalars().all()
    return jobs


@router.get("/{job_id}", response_model=JobOut)
async def get_job_detail(job_id: str, db: AsyncSession = Depends(get_db)):
    stmt = (
        select(Job)
        .options(selectinload(Job.match), selectinload(Job.company), selectinload(Job.application))
        .where(Job.id == job_id)
    )
    result = await db.execute(stmt)
    job = result.scalars().first()
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    return job


@router.post("/ingest", response_model=JobOut)
async def ingest_single_job(request: JobIngestRequest, db: AsyncSession = Depends(get_db)):
    """Ingest a single job from a pasted URL or raw text description."""
    profile = await get_or_create_default_profile(db)

    # 1. Parse raw input into JobCreate schema
    try:
        job_create = await universal_parser.parse_from_url_or_text(request)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    # 2. Check 5-Tier Deduplication
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
        logger.info(f"Duplicate job detected ({dup_reason}): returning existing record {existing_job.id}")
        return existing_job

    # 3. AI Structured Extraction
    structured_reqs = await claude_ai_provider.analyze_job_description(
        job_create.description_raw, target_domain=profile.domain
    )
    job_create.requirements_structured = structured_reqs

    # 4. Get or Create Company
    norm_comp = canonicalizer.normalize_company_name(job_create.company_name)
    comp_res = await db.execute(select(Company).where(Company.normalized_name == norm_comp))
    company = comp_res.scalars().first()
    if not company:
        company = Company(name=job_create.company_name, normalized_name=norm_comp)
        db.add(company)
        await db.flush()

    # 5. Save Job
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

    # 6. Save Embedding
    emb = await embedding_service.get_embedding(job.description_raw[:2000])
    job_emb = JobEmbedding(
        job_id=job.id,
        content_hash=embedding_service.hash_text(job.description_raw),
        embedding_json=emb,
    )
    db.add(job_emb)

    # 7. Compute Match Score & Explanations
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

    # 8. Create Application CRM record in DISCOVERED state
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
):
    """Scan compliant ATS feeds (Greenhouse, Lever, Ashby) for target domain jobs."""
    profile = await get_or_create_default_profile(db)
    search_term = query or profile.domain or "Data Engineer"

    logger.info(f"Triggering multi-channel discovery for: '{search_term}'")
    discovered_jobs: List[JobCreate] = []

    # Fetch concurrently from sources
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

    # Fallback seed jobs if network or rate limits occur
    if not discovered_jobs:
        discovered_jobs = _get_default_seed_jobs()

    ingested_count = 0
    duplicate_count = 0
    filtered_count = 0

    facts_res = await db.execute(select(ProfileFact).where(ProfileFact.profile_id == profile.id))
    facts = facts_res.scalars().all()

    for jc in discovered_jobs:
        # Check hard filters
        filter_res = hard_filter_engine.evaluate(jc, profile)
        if not filter_res.passed:
            filtered_count += 1
            continue

        # Check deduplication
        is_dup, _, _ = await deduplication_engine.find_duplicate(
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
            continue

        # Create Company
        norm_comp = canonicalizer.normalize_company_name(jc.company_name)
        comp_res = await db.execute(select(Company).where(Company.normalized_name == norm_comp))
        company = comp_res.scalars().first()
        if not company:
            company = Company(name=jc.company_name, normalized_name=norm_comp)
            db.add(company)
            await db.flush()

        # Structured analysis & match
        structured_reqs = await claude_ai_provider.analyze_job_description(jc.description_raw, target_domain=profile.domain)
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

        app_record = Application(job_id=job.id, profile_id=profile.id, status=ApplicationStatus.DISCOVERED)
        db.add(app_record)

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
