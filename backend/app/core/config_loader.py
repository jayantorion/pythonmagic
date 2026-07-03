"""
External YAML Configuration Loader for Candidate Preferences.

Loads and validates candidate preferences from config/candidate_preferences.yaml.
Provides typed accessors for all services that need candidate profile information.
Includes graceful fallback to hardcoded defaults if YAML is missing or invalid.
"""

from functools import lru_cache
from pathlib import Path
from typing import List, Optional, Dict, Any
import yaml
import logging
from pydantic import BaseModel, Field, ValidationError, model_validator

from app.core.config import settings

logger = logging.getLogger("job_assistant.config_loader")


# Pydantic models mirroring the YAML structure exactly
class Profile(BaseModel):
    full_name: str = Field(..., description="Full name of the candidate")
    email: str = Field(..., description="Email address")
    phone: Optional[str] = Field(None, description="Phone number")
    location: str = Field(..., description="Current location")
    domain: str = Field(..., description="Primary domain/field")
    experience_years: int = Field(..., ge=0, description="Years of experience")
    experience_level: str = Field(..., description="Experience level")
    target_roles: List[str] = Field(default_factory=list, description="Target job titles")
    career_summary: Optional[str] = Field(None, description="Career summary")


class TechStackPriorities(BaseModel):
    must_have: List[str] = Field(default_factory=list, description="Required skills")
    preferred: List[str] = Field(default_factory=list, description="Preferred skills")
    nice_to_have: List[str] = Field(default_factory=list, description="Nice-to-have skills")


class Preferences(BaseModel):
    work_modes: List[str] = Field(default_factory=lambda: ["remote", "hybrid", "onsite"])
    locations: List[str] = Field(default_factory=list)
    excluded_locations: List[str] = Field(default_factory=list)
    employment_types: List[str] = Field(default_factory=lambda: ["full_time", "contract"])
    excluded_keywords: List[str] = Field(default_factory=list)
    excluded_companies: List[str] = Field(default_factory=list)
    preferred_companies: List[str] = Field(default_factory=list)
    open_to_relocation: bool = Field(default=False)
    work_authorization: str = Field(default="Indian citizen; no sponsorship required")
    notice_period_days: int = Field(default=30, ge=0)
    salary_expectation: Dict[str, Any] = Field(
        default_factory=lambda: {"min_amount": 0, "currency": "INR", "period": "annual"}
    )


class CandidateEntry(BaseModel):
    id: str = Field(..., description="Unique identifier for this candidate entry")
    profile: Profile
    tech_stack_priorities: TechStackPriorities = Field(default_factory=TechStackPriorities)
    preferences: Preferences = Field(default_factory=Preferences)


class SalaryExpectation(BaseModel):
    min_amount: int = Field(..., ge=0)
    currency: str = Field(default="INR")
    period: str = Field(default="annual")


class Fact(BaseModel):
    fact_type: str = Field(..., description="Type of fact (skill, tool, experience, etc.)")
    fact_value: str = Field(..., description="The fact value")
    verified: bool = Field(..., description="Whether this fact is verified")


class CandidateFile(BaseModel):
    version: int = Field(default=1, description="Config file version")
    candidates: List[CandidateEntry] = Field(default_factory=list)
    heuristic_tech_keywords: List[str] = Field(default_factory=list)
    default_facts: List[Fact] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_at_least_one_candidate(self):
        if not self.candidates:
            raise ValueError("At least one candidate entry must be defined")
        return self


class ConfigLoader:
    def __init__(self, path: Path):
        self.path = path
        self._raw: dict | None = None
        self._model: CandidateFile | None = None
        self._load()

    def _load(self):
        """Load and validate the YAML configuration file."""
        if not self.path.exists():
            logger.warning(f"Config file not found: {self.path}. Falling back to hardcoded defaults.")
            return
        try:
            with self.path.open("r", encoding="utf-8") as f:
                self._raw = yaml.safe_load(f) or {}
            self._model = CandidateFile.model_validate(self._raw)
            logger.info(f"Loaded candidate config: {len(self._model.candidates)} candidate(s) from {self.path}")
        except (yaml.YAMLError, ValidationError) as e:
            logger.error(f"Failed to load/validate {self.path}: {e}")
            self._raw = {}
            self._model = None

    # Typed accessors for the default candidate (first or id="default")
    def get_default_profile(self) -> dict:
        """Get the profile data for the default candidate."""
        if not self._model or not self._model.candidates:
            return {}
        entry = next((c for c in self._model.candidates if c.id == "default"), self._model.candidates[0])
        return entry.profile.model_dump()

    def get_default_tech_priorities(self) -> dict:
        """Get the tech stack priorities for the default candidate."""
        if not self._model or not self._model.candidates:
            return {"must_have": [], "preferred": [], "nice_to_have": []}
        entry = next((c for c in self._model.candidates if c.id == "default"), self._model.candidates[0])
        return entry.tech_stack_priorities.model_dump()

    def get_default_preferences(self) -> dict:
        """Get the preferences for the default candidate."""
        if not self._model or not self._model.candidates:
            return {}
        entry = next((c for c in self._model.candidates if c.id == "default"), self._model.candidates[0])
        return entry.preferences.model_dump()

    def get_heuristic_keywords(self) -> List[str]:
        """Get the heuristic tech keywords list."""
        if not self._model:
            return []
        return list(self._model.heuristic_tech_keywords or [])

    def get_default_facts(self) -> List[dict]:
        """Get the default seed facts list."""
        if not self._model:
            return []
        return [f.model_dump() for f in (self._model.default_facts or [])]

    def is_valid(self) -> bool:
        """Check if the configuration was loaded successfully."""
        return self._model is not None and len(self._model.candidates) > 0


# Module-level singleton with LRU cache
@lru_cache(maxsize=1)
def get_config_loader() -> ConfigLoader:
    """Get the singleton ConfigLoader instance."""
    return ConfigLoader(settings.CANDIDATE_CONFIG_PATH)


# Convenience module-level instance (lazy-loaded via function above)
# Usage: from app.core.config_loader import config_loader
#        profile = config_loader.get_default_profile()
config_loader = get_config_loader()