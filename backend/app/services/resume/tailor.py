import re
from typing import Dict, Any, List, Tuple
from app.models.candidate import ProfileFact
from app.schemas.job import JobCreate
from app.schemas.resume import ResumeAST
from app.services.ai.claude import claude_ai_provider
from app.services.resume.diff_guard import diff_guard
from app.core.logging import logger


class ResumeTailoringEngine:
    async def tailor_resume(
        self,
        master_ast: Dict[str, Any],
        job_data: Dict[str, Any],
        verified_facts: List[ProfileFact],
        variant_type: str = "targeted",
    ) -> Tuple[Dict[str, Any], Dict[str, Any], float]:
        """End-to-end ATS resume tailoring with Diff Guard verification."""
        facts_list = [{"category": f.category, "content": f.content, "entity": f.entity_name} for f in verified_facts]

        # 1. AI Tailoring Call
        raw_tailored_ast = await claude_ai_provider.tailor_resume_ast(
            master_ast=master_ast,
            job_data=job_data,
            candidate_facts=facts_list,
            variant_type=variant_type,
        )

        # 2. Diff Guard Verification Pass
        guarded_ast, diff_provenance = diff_guard.verify_and_guard(
            tailored_ast=raw_tailored_ast,
            master_ast=master_ast,
            verified_facts=verified_facts,
        )

        # 3. Calculate ATS Compliance Score
        ats_score = self._calculate_ats_score(guarded_ast, job_data)

        return guarded_ast, diff_provenance, ats_score

    def _calculate_ats_score(self, ast: Dict[str, Any], job_data: Dict[str, Any]) -> float:
        score = 80.0  # Base ATS score for standard clean hierarchy

        # Check contact info
        contact = ast.get("contact", {})
        if contact.get("email") and contact.get("phone"):
            score += 5.0

        # Check keyword density
        job_desc = job_data.get("description_raw", "").lower()
        req_skills = job_data.get("requirements_structured", {}).get("required_skills", [])

        resume_text = str(ast).lower()
        matched_skills = [s for s in req_skills if s.lower() in resume_text]
        if req_skills:
            keyword_ratio = len(matched_skills) / len(req_skills)
            score += min(keyword_ratio * 10.0, 10.0)

        # Action verbs check in bullets
        action_verbs = ["engineered", "developed", "architected", "built", "optimized", "implemented", "scaled", "automated"]
        exp_list = ast.get("experience", [])
        has_verbs = 0
        total_bullets = 0
        for exp in exp_list:
            for b in exp.get("bullet_points", []):
                total_bullets += 1
                if any(v in b.lower() for v in action_verbs):
                    has_verbs += 1

        if total_bullets > 0 and (has_verbs / total_bullets) > 0.6:
            score += 5.0

        return round(min(score, 98.5), 1)


resume_tailor_engine = ResumeTailoringEngine()
