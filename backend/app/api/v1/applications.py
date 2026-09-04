from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func
from sqlalchemy.orm import selectinload

from app.core.auth import get_current_active_user
from app.core.database import get_db
from app.core.logging import logger
from app.models.application import Application, ApplicationEvent, ApplicationStatus
from app.models.job import Job
from app.models.user import User
from app.schemas.application import ApplicationOut, ApplicationUpdate, ApplicationEventOut
from app.api.v1.candidate import get_or_create_user_profile
from app.api.v1.jobs import _attach_user_views

router = APIRouter(prefix="/applications", tags=["Application CRM & Tracking"])


@router.get("", response_model=List[ApplicationOut])
async def list_applications(
    status_filter: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """List all applications for the current user, grouped by lifecycle state for Kanban view."""
    profile = await get_or_create_user_profile(db, current_user)

    stmt = (
        select(Application)
        .options(
            selectinload(Application.job).selectinload(Job.matches),
            selectinload(Application.events),
        )
        .where(Application.profile_id == profile.id)
        .order_by(desc(Application.created_at))
    )

    if status_filter:
        try:
            stmt = stmt.where(Application.status == ApplicationStatus(status_filter))
        except ValueError:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid status filter")

    result = await db.execute(stmt)
    apps = result.scalars().unique().all()
    for a in apps:
        if a.job is not None:
            _attach_user_views(a.job, profile.id)
    return apps


@router.get("/{application_id}", response_model=ApplicationOut)
async def get_application(
    application_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    profile = await get_or_create_user_profile(db, current_user)
    stmt = (
        select(Application)
        .options(selectinload(Application.job).selectinload(Job.matches), selectinload(Application.events))
        .where(Application.id == application_id, Application.profile_id == profile.id)
    )
    result = await db.execute(stmt)
    app = result.scalars().first()
    if not app:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")
    if app.job is not None:
        _attach_user_views(app.job, profile.id)
    return app


@router.patch("/{application_id}", response_model=ApplicationOut)
async def update_application(
    application_id: str,
    payload: ApplicationUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Update the application status, add notes, or schedule a follow-up."""
    profile = await get_or_create_user_profile(db, current_user)

    stmt = select(Application).where(
        Application.id == application_id, Application.profile_id == profile.id
    )
    result = await db.execute(stmt)
    app_record = result.scalars().first()
    if not app_record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")

    old_status = app_record.status

    if payload.status is not None:
        try:
            new_status = ApplicationStatus(payload.status)
            app_record.status = new_status

            if new_status == ApplicationStatus.APPLIED and not app_record.applied_at:
                app_record.applied_at = datetime.utcnow()

            event = ApplicationEvent(
                application_id=app_record.id,
                event_type="status_change",
                from_status=old_status.value,
                to_status=new_status.value,
                title=f"Status: {old_status.value} → {new_status.value}",
                description=f"Application status updated to {new_status.value}.",
            )
            db.add(event)
        except ValueError:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid status value")

    if payload.notes is not None:
        app_record.notes = payload.notes
        event = ApplicationEvent(
            application_id=app_record.id,
            event_type="note_added",
            title="Notes Updated",
            description=payload.notes[:200] + ("..." if len(payload.notes) > 200 else ""),
        )
        db.add(event)

    if payload.follow_up_date is not None:
        app_record.follow_up_date = payload.follow_up_date
        event = ApplicationEvent(
            application_id=app_record.id,
            event_type="follow_up_scheduled",
            title="Follow-up Scheduled",
            description=f"Follow-up date set to {payload.follow_up_date.isoformat()}",
        )
        db.add(event)

    if payload.cover_letter is not None:
        app_record.cover_letter = payload.cover_letter

    if payload.portal_application_id is not None:
        app_record.portal_application_id = payload.portal_application_id
        event = ApplicationEvent(
            application_id=app_record.id,
            event_type="applied_externally",
            title="Marked as Applied Externally",
            description=f"External application ID / confirmation: {payload.portal_application_id}",
            to_status=app_record.status.value,
        )
        db.add(event)

    await db.commit()
    await db.refresh(app_record)
    return app_record


@router.get("/{application_id}/timeline", response_model=List[ApplicationEventOut])
async def get_application_timeline(
    application_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    profile = await get_or_create_user_profile(db, current_user)
    # Verify ownership first
    owner_check = await db.execute(
        select(Application.id).where(
            Application.id == application_id, Application.profile_id == profile.id
        )
    )
    if not owner_check.scalars().first():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")

    stmt = (
        select(ApplicationEvent)
        .where(ApplicationEvent.application_id == application_id)
        .order_by(ApplicationEvent.created_at.asc())
    )
    result = await db.execute(stmt)
    return result.scalars().all()


@router.post("/{application_id}/interview")
async def add_interview_event(
    application_id: str,
    interview_date: datetime,
    interview_type: str = "Phone Screen",
    notes: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Add a dedicated interview event to the application timeline."""
    profile = await get_or_create_user_profile(db, current_user)

    stmt = select(Application).where(
        Application.id == application_id, Application.profile_id == profile.id
    )
    result = await db.execute(stmt)
    app_record = result.scalars().first()
    if not app_record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")

    event = ApplicationEvent(
        application_id=app_record.id,
        event_type="interview_scheduled",
        title=f"{interview_type} Scheduled",
        description=f"{interview_type} on {interview_date.isoformat()}. {notes or ''}",
        payload_json={"interview_date": interview_date.isoformat(), "interview_type": interview_type},
    )
    db.add(event)

    if app_record.status not in [ApplicationStatus.INTERVIEW, ApplicationStatus.TECHNICAL_INTERVIEW, ApplicationStatus.FINAL_INTERVIEW, ApplicationStatus.OFFER]:
        old_status = app_record.status
        app_record.status = ApplicationStatus.INTERVIEW
        event2 = ApplicationEvent(
            application_id=app_record.id,
            event_type="status_change",
            from_status=old_status.value,
            to_status=ApplicationStatus.INTERVIEW.value,
            title="Status Auto-Updated to INTERVIEW",
        )
        db.add(event2)

    await db.commit()
    return {"status": "interview_logged", "event_title": event.title}


@router.get("/stats/summary")
async def get_application_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Return aggregate statistics for the dashboard, scoped to the current user."""
    profile = await get_or_create_user_profile(db, current_user)

    counts = await db.execute(
        select(Application.status, func.count(Application.id))
        .where(Application.profile_id == profile.id)
        .group_by(Application.status)
    )
    status_counts = {s.value: c for s, c in counts.all()}

    total = sum(status_counts.values())

    return {
        "total_applications": total,
        "discovered": status_counts.get("DISCOVERED", 0),
        "shortlisted": status_counts.get("SHORTLISTED", 0),
        "ready_to_apply": status_counts.get("READY_TO_APPLY", 0),
        "applied": status_counts.get("APPLIED", 0),
        "interviewing": status_counts.get("INTERVIEW", 0) + status_counts.get("TECHNICAL_INTERVIEW", 0) + status_counts.get("FINAL_INTERVIEW", 0) + status_counts.get("RECRUITER_SCREEN", 0),
        "offers": status_counts.get("OFFER", 0),
        "rejected": status_counts.get("REJECTED", 0),
    }
