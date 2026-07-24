"""
Authentication endpoints: register / login / login (json) / me / change-password / delete.

On registration, a User row is created and a CandidateProfile is seeded
from config/candidate_preferences.yaml. The user gets a JWT in the response
which they include as `Authorization: Bearer <token>` on subsequent calls.
"""
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.auth import get_current_active_user
from app.core.database import get_db
from app.core.logging import logger
from app.core.security import (
    create_access_token,
    hash_password,
    verify_password,
)
from app.models.candidate import CandidateProfile, FactCategory, ProfileFact, VerificationLevel
from app.models.user import User
from app.schemas.auth import (
    ChangePasswordRequest,
    LoginRequest,
    RegisterRequest,
    TokenOut,
    UserOut,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])


def _seed_profile_for_user(user: User, profile_data: dict) -> CandidateProfile:
    """Build a CandidateProfile seeded from YAML defaults for the new user."""
    return CandidateProfile(
        user_id=user.id,
        full_name=profile_data.get("full_name") or user.full_name or user.username,
        email=profile_data.get("email") or user.email,
        phone=profile_data.get("phone"),
        location=profile_data.get("location", "Bangalore, India"),
        domain=profile_data.get("domain", "Data Engineering"),
        target_roles=profile_data.get("target_roles") or [
            "Data Engineer",
            "Senior Data Engineer",
            "Analytics Engineer",
        ],
        experience_years=profile_data.get("experience_years", 3.0),
        experience_level=profile_data.get("experience_level", "mid_senior"),
        tech_stack_priorities=_ensure_tech_priorities(),
        preferences=_ensure_preferences(),
        career_summary=profile_data.get("career_summary"),
    )


def _ensure_tech_priorities() -> dict:
    """Pull tech priorities from YAML config_loader with safe fallback."""
    from app.core.config_loader import config_loader
    tech = config_loader.get_default_tech_priorities()
    if not tech.get("must_have"):
        tech = {
            "must_have": ["Python", "SQL", "Spark", "Airflow"],
            "preferred": ["dbt", "Snowflake", "Databricks", "Kafka", "AWS"],
            "nice_to_have": ["Kubernetes", "Docker", "Terraform", "Iceberg"],
        }
    return tech


def _ensure_preferences() -> dict:
    """Pull preferences from YAML config_loader with safe fallback."""
    from app.core.config_loader import config_loader
    prefs = config_loader.get_default_preferences()
    if not prefs:
        prefs = {
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
    return prefs


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


async def _seed_facts_from_yaml(db: AsyncSession, profile: CandidateProfile) -> int:
    """Insert YAML-seeded default facts for the new user's profile."""
    from app.core.config_loader import config_loader

    yaml_facts = config_loader.get_default_facts()
    if not yaml_facts:
        return 0

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
    await db.flush()
    return len(facts)


@router.post("/register", response_model=TokenOut, status_code=status.HTTP_201_CREATED)
async def register(data: RegisterRequest, db: Annotated[AsyncSession, Depends(get_db)]):
    """Create a new user account. Returns a JWT access token on success."""
    result = await db.execute(select(User).where(User.username == data.username))
    if result.scalars().first():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username already taken")

    if data.email:
        result = await db.execute(select(User).where(User.email == data.email))
        if result.scalars().first():
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

    user = User(
        username=data.username,
        email=data.email,
        hashed_password=hash_password(data.password),
        full_name=data.full_name,
        is_active=True,
    )
    db.add(user)
    await db.flush()

    from app.core.config_loader import config_loader
    profile_data = config_loader.get_default_profile()
    profile = _seed_profile_for_user(user, profile_data)
    db.add(profile)
    await db.flush()

    n_facts = await _seed_facts_from_yaml(db, profile)

    await db.commit()
    await db.refresh(user)
    await db.refresh(profile)

    logger.info(
        f"Registered new user '{user.username}' (id={user.id}) with profile id={profile.id} "
        f"and {n_facts} seed facts"
    )

    token = create_access_token(user.id, user.username)
    return TokenOut(
        access_token=token,
        token_type="bearer",
        user=UserOut.model_validate(user),
        expires_in_hours=settings.JWT_EXPIRE_HOURS,
    )


async def _authenticate(username: str, password: str, db: AsyncSession) -> TokenOut:
    """Shared auth logic for /login (form) and /login/json (body)."""
    result = await db.execute(select(User).where(User.username == username))
    user = result.scalars().first()
    if not user or not verify_password(password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is deactivated",
        )

    user.last_login_at = datetime.utcnow()
    await db.commit()
    await db.refresh(user)

    token = create_access_token(user.id, user.username)
    return TokenOut(
        access_token=token,
        token_type="bearer",
        user=UserOut.model_validate(user),
        expires_in_hours=settings.JWT_EXPIRE_HOURS,
    )


@router.post("/login", response_model=TokenOut)
async def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """OAuth2 password-form login (Swagger / OpenAPI docs)."""
    return await _authenticate(form_data.username, form_data.password, db)


@router.post("/login/json", response_model=TokenOut)
async def login_json(
    data: LoginRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """JSON-body login (the frontend uses this)."""
    return await _authenticate(data.username, data.password, db)


@router.get("/me", response_model=UserOut)
async def get_me(current_user: Annotated[User, Depends(get_current_active_user)]):
    """Return the currently authenticated user."""
    return current_user


@router.post("/change-password")
async def change_password(
    data: ChangePasswordRequest,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Change the current user's password."""
    if not verify_password(data.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )

    current_user.hashed_password = hash_password(data.new_password)
    await db.commit()
    logger.info(f"Password changed for user '{current_user.username}'")
    return {"status": "password_updated"}


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
async def delete_account(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Delete the current user (cascades to profile, facts, jobs, applications)."""
    username = current_user.username
    await db.delete(current_user)
    await db.commit()
    logger.info(f"Deleted user '{username}'")
    return None
