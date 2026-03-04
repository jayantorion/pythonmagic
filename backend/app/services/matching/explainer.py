from typing import Dict, Any, List, Optional
from app.models.candidate import CandidateProfile, ProfileFact
from app.schemas.job import JobCreate, JobRequirementsStructured
from app.services.matching.lexical_ranker import lexical_ranker
from app.services.matching.vector_matcher import vector_matcher
from app.services.ai.claude import claude_ai_provider


class MatchingAndExplainerEngine:
    async def match_and_explain(
        self,
        job: JobCreate,
        profile: CandidateProfile,
        facts: List[ProfileFact],
    ) -> Dict[str, Any]:
        """Orchestrates multi-stage scoring and generates comprehensive explanations."""
        # 1. Lexical Score
        lexical_res = lexical_ranker.calculate_lexical_score(job.description_raw, job.title, profile)
        lexical_score = lexical_res["lexical_score"]

        # 2. Vector Semantic Similarity Score
        vector_score = await vector_matcher.compute_semantic_similarity(job.description_raw, profile)

        # 3. LLM Requirements Extraction & Match Analysis
        facts_list = [{"category": f.category, "content": f.content, "entity": f.entity_name} for f in facts]
        cand_dict = {
            "full_name": profile.full_name,
            "domain": profile.domain,
            "target_roles": profile.target_roles,
            "experience_years": profile.experience_years,
            "tech_stack_priorities": profile.tech_stack_priorities,
        }
        # requirements_structured may be a dict (when set by analyze_job_description)
        # or a Pydantic model (when read from DB). Handle both cases.
        req_struct = job.requirements_structured
        if req_struct is None:
            req_struct_dict = {}
        elif isinstance(req_struct, dict):
            req_struct_dict = req_struct
        else:
            req_struct_dict = req_struct.model_dump()

        job_dict = {
            "title": job.title,
            "company_name": job.company_name,
            "description_raw": job.description_raw,
            "requirements_structured": req_struct_dict,
        }

        llm_eval = await claude_ai_provider.evaluate_candidate_match(job_dict, cand_dict, facts_list)

        # Weighted blend of scores
        skills_score = round(llm_eval.get("skills_score", lexical_score), 1)
        exp_score = round(llm_eval.get("experience_score", 85.0), 1)
        domain_score = round(llm_eval.get("domain_score", 90.0), 1)
        seniority_score = round(llm_eval.get("seniority_score", 88.0), 1)

        # Explainable formula
        overall = (
            (skills_score * 0.35)
            + (exp_score * 0.25)
            + (domain_score * 0.15)
            + (seniority_score * 0.15)
            + (vector_score * 0.10)
        )
        overall = round(min(max(overall, 0.0), 100.0), 1)

        # Recommendation Category
        if overall >= 88.0:
            recommendation = "EXCELLENT"
        elif overall >= 78.0:
            recommendation = "STRONG"
        elif overall >= 65.0:
            recommendation = "CONSIDER"
        elif overall >= 50.0:
            recommendation = "WEAK"
        else:
            recommendation = "SKIP"

        pros = llm_eval.get("pros", [])
        if not pros and lexical_res["found_must_have"]:
            pros.append(f"Strong match on core technologies: {', '.join(lexical_res['found_must_have'])}")

        gaps = llm_eval.get("gaps", [])
        if not gaps and lexical_res["missing_must_have"]:
            gaps.append(f"Profile does not explicitly demonstrate: {', '.join(lexical_res['missing_must_have'])}")

        return {
            "overall_score": overall,
            "skills_score": skills_score,
            "experience_score": exp_score,
            "domain_score": domain_score,
            "seniority_score": seniority_score,
            "recommendation": recommendation,
            "pros": pros,
            "gaps": gaps,
            "dealbreakers": llm_eval.get("dealbreakers", []),
            "missing_skills_status": llm_eval.get("missing_skills_status", {}),
            "explanation": llm_eval.get(
                "explanation",
                f"Match evaluation for {job.title} at {job.company_name}. Candidate shows {overall}% alignment with role expectations.",
            ),
        }


matching_engine = MatchingAndExplainerEngine()
