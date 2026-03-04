from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime


class JobMatchOut(BaseModel):
    id: str
    job_id: str
    profile_id: str
    overall_score: float
    skills_score: float
    experience_score: float
    domain_score: float
    seniority_score: float
    recommendation: str  # EXCELLENT, STRONG, CONSIDER, WEAK, SKIP
    pros: List[str] = Field(default_factory=list)
    gaps: List[str] = Field(default_factory=list)
    dealbreakers: List[str] = Field(default_factory=list)
    missing_skills_status: Dict[str, str] = Field(default_factory=dict)
    explanation: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class MatchScoreExplanation(BaseModel):
    overall_score: float
    category_scores: Dict[str, float]
    pros: List[str]
    gaps: List[str]
    dealbreakers: List[str]
    recommendation: str
    reasoning: str
