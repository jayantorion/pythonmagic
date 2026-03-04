from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional


class AIProvider(ABC):
    @abstractmethod
    async def analyze_job_description(self, description_raw: str, target_domain: str = "Data Engineering") -> Dict[str, Any]:
        """Extract structured requirements, skills, seniority, and dealbreakers from JD."""
        pass

    @abstractmethod
    async def evaluate_candidate_match(
        self,
        job_data: Dict[str, Any],
        candidate_data: Dict[str, Any],
        candidate_facts: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Compute multi-factor explainable match score with breakdown, pros, gaps, and recommendations."""
        pass

    @abstractmethod
    async def tailor_resume_ast(
        self,
        master_ast: Dict[str, Any],
        job_data: Dict[str, Any],
        candidate_facts: List[Dict[str, Any]],
        variant_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Tailor resume AST without fabricating ungrounded facts."""
        pass

    @abstractmethod
    async def draft_answer_for_question(
        self,
        question: str,
        candidate_profile: Dict[str, Any],
        candidate_facts: List[Dict[str, Any]],
    ) -> str:
        """Draft a factual application answer using only candidate facts."""
        pass

    @abstractmethod
    async def generate_cover_letter(
        self,
        job_data: Dict[str, Any],
        candidate_data: Dict[str, Any],
        tailored_ast: Dict[str, Any],
    ) -> str:
        """Generate a concise, professional, truthful cover letter."""
        pass
