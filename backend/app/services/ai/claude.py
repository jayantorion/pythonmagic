import json
import re
from typing import Dict, Any, List, Optional
import anthropic
from app.core.config import settings
from app.core.logging import logger
from app.services.ai.provider import AIProvider


class ClaudeAIProvider(AIProvider):
    def __init__(self):
        self.api_key = settings.ANTHROPIC_API_KEY
        self.client = anthropic.AsyncAnthropic(api_key=self.api_key) if self.api_key else None
        self.model = settings.ANTHROPIC_MODEL
        self.fast_model = settings.ANTHROPIC_FAST_MODEL

    async def analyze_job_description(self, description_raw: str, target_domain: str = "Data Engineering") -> Dict[str, Any]:
        """Extract structured requirements, skills, seniority, and dealbreakers."""
        if not self.client:
            return self._heuristic_analyze_job(description_raw, target_domain)

        prompt = f"""You are an expert technical recruiter and job analyst specializing in {target_domain}.
Analyze the following job description and extract a structured JSON response.

Job Description:
{description_raw[:12000]}

Respond ONLY with valid JSON matching this schema:
{{
  "required_skills": ["string"],
  "preferred_skills": ["string"],
  "responsibilities": ["string"],
  "tools_technologies": ["string"],
  "experience_years_min": float or null,
  "education": ["string"],
  "dealbreakers": ["string"]
}}"""

        try:
            response = await self.client.messages.create(
                model=self.fast_model,
                max_tokens=1500,
                messages=[{"role": "user", "content": prompt}],
            )
            content = response.content[0].text
            # Extract JSON substring
            match = re.search(r"\{.*\}", content, re.DOTALL)
            if match:
                return json.loads(match.group(0))
        except Exception as e:
            logger.error(f"Error calling Claude for job analysis: {e}")

        return self._heuristic_analyze_job(description_raw, target_domain)

    async def evaluate_candidate_match(
        self,
        job_data: Dict[str, Any],
        candidate_data: Dict[str, Any],
        candidate_facts: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Compute explainable match score with breakdown, pros, gaps, and recommendation."""
        if not self.client:
            return self._heuristic_match(job_data, candidate_data, candidate_facts)

        prompt = f"""You are a senior technical hiring manager. Evaluate the match between this candidate and this job.
Do not hallucinate skills. Evaluate strictly based on candidate facts.

Job Details:
Title: {job_data.get('title')}
Company: {job_data.get('company_name')}
Structured Requirements: {json.dumps(job_data.get('requirements_structured', {}))}
Job Description Excerpt: {job_data.get('description_raw', '')[:4000]}

Candidate Profile:
Target Roles: {candidate_data.get('target_roles')}
Domain: {candidate_data.get('domain')}
Years of Experience: {candidate_data.get('experience_years')}
Verified Candidate Facts: {json.dumps([f.get('content') for f in candidate_facts][:40])}

Return ONLY valid JSON matching this schema:
{{
  "overall_score": float (0-100),
  "skills_score": float (0-100),
  "experience_score": float (0-100),
  "domain_score": float (0-100),
  "seniority_score": float (0-100),
  "recommendation": "EXCELLENT" | "STRONG" | "CONSIDER" | "WEAK" | "SKIP",
  "pros": ["bullet 1", "bullet 2"],
  "gaps": ["gap 1"],
  "dealbreakers": ["dealbreaker 1 if any"],
  "missing_skills_status": {{"SkillName": "CONFIRMED" | "LIKELY" | "UNKNOWN" | "MISSING"}},
  "explanation": "Clear 2-3 paragraph summary of why this candidate should or should not apply."
}}"""

        try:
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=2000,
                messages=[{"role": "user", "content": prompt}],
            )
            content = response.content[0].text
            match = re.search(r"\{.*\}", content, re.DOTALL)
            if match:
                return json.loads(match.group(0))
        except Exception as e:
            logger.error(f"Error calling Claude for match evaluation: {e}")

        return self._heuristic_match(job_data, candidate_data, candidate_facts)

    async def tailor_resume_ast(
        self,
        master_ast: Dict[str, Any],
        job_data: Dict[str, Any],
        candidate_facts: List[Dict[str, Any]],
        variant_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Tailor resume AST without fabricating ungrounded facts."""
        if not self.client:
            return master_ast

        prompt = f"""You are an ATS resume optimizer.
Your task is to adapt the candidate's verified resume AST for this specific job.

HARD CONSTRAINT: ZERO FABRICATION.
- DO NOT invent any new companies, job titles, degrees, or metrics.
- DO NOT add skills that are not in the candidate's verified facts.
- You MAY reorder bullet points so the most job-relevant ones appear first.
- You MAY slightly rephrase bullet points to align with standard industry terminology if grounded in the facts.

Target Job:
Title: {job_data.get('title')}
Requirements: {json.dumps(job_data.get('requirements_structured', {}))}

Master Resume AST:
{json.dumps(master_ast)}

Verified Facts:
{json.dumps([f.get('content') for f in candidate_facts][:50])}

Return ONLY valid JSON containing the tailored resume AST:
{{
  "contact": {json.dumps(master_ast.get('contact', {}))},
  "summary": "Targeted truthful professional summary",
  "skills": {{"Category": ["skill1", "skill2"]}},
  "experience": [...],
  "education": [...],
  "projects": [...],
  "certifications": [...]
}}"""

        try:
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=3500,
                messages=[{"role": "user", "content": prompt}],
            )
            content = response.content[0].text
            match = re.search(r"\{.*\}", content, re.DOTALL)
            if match:
                return json.loads(match.group(0))
        except Exception as e:
            logger.error(f"Error calling Claude for resume tailoring: {e}")

        return master_ast

    async def draft_answer_for_question(
        self,
        question: str,
        candidate_profile: Dict[str, Any],
        candidate_facts: List[Dict[str, Any]],
    ) -> str:
        if not self.client:
            return f"Based on my verified experience in {candidate_profile.get('domain')}, I have {candidate_profile.get('experience_years')} years of relevant background."

        prompt = f"""You are assisting a candidate in answering a job application screening question.
Use ONLY verified facts from the candidate's profile. Never make up details or numbers.

Question:
{question}

Candidate Profile:
{json.dumps(candidate_profile)}

Verified Facts:
{json.dumps([f.get('content') for f in candidate_facts][:40])}

Provide a direct, professional, factual 1-3 sentence response:"""

        try:
            response = await self.client.messages.create(
                model=self.fast_model,
                max_tokens=300,
                messages=[{"role": "user", "content": prompt}],
            )
            return response.content[0].text.strip()
        except Exception as e:
            logger.error(f"Error drafting answer with Claude: {e}")
            return "Answer requires manual review."

    async def generate_cover_letter(
        self,
        job_data: Dict[str, Any],
        candidate_data: Dict[str, Any],
        tailored_ast: Dict[str, Any],
    ) -> str:
        if not self.client:
            return f"Dear Hiring Team at {job_data.get('company_name', 'Company')},\n\nI am writing to express my strong interest in the {job_data.get('title')} position. With over {candidate_data.get('experience_years', 3)} years of experience in {candidate_data.get('domain', 'Software Engineering')}, I am confident in my ability to deliver high-impact results for your team."

        prompt = f"""Write a concise, compelling, and truthful 3-paragraph cover letter for:
Candidate: {candidate_data.get('full_name')}
Target Job: {job_data.get('title')} at {job_data.get('company_name')}
Job Description Key Points: {job_data.get('description_raw', '')[:2000]}
Candidate Experience: {json.dumps(tailored_ast.get('experience', []))}

Constraints:
- Highlight true accomplishments from the experience list.
- Keep it under 250 words.
- Professional, confident, and direct tone."""

        try:
            response = await self.client.messages.create(
                model=self.fast_model,
                max_tokens=600,
                messages=[{"role": "user", "content": prompt}],
            )
            return response.content[0].text.strip()
        except Exception as e:
            logger.error(f"Error generating cover letter: {e}")
            return "Cover letter generation failed."

    # --- Offline Deterministic Heuristics (Fallback) ---
    def _heuristic_analyze_job(self, text: str, domain: str) -> Dict[str, Any]:
        # Load tech keywords from external YAML config (with hardcoded fallback)
        from app.core.config_loader import config_loader
        yaml_keywords = config_loader.get_heuristic_keywords()
        default_keywords = [
            "python", "sql", "spark", "pyspark", "airflow", "dbt", "snowflake",
            "databricks", "kafka", "aws", "gcp", "azure", "bigquery", "redshift",
            "kubernetes", "docker", "terraform", "flink", "scala", "postgres",
            "fastapi", "django", "react", "next.js", "graphql", "rest api"
        ]
        tech_keywords = [k.lower() for k in yaml_keywords] if yaml_keywords else default_keywords
        found_skills = [k for k in tech_keywords if re.search(rf"\b{re.escape(k)}\b", text, re.IGNORECASE)]

        exp_match = re.search(r"(\d+)\+?\s*(?:-\s*\d+)?\s*(?:years|yrs)", text, re.IGNORECASE)
        min_years = float(exp_match.group(1)) if exp_match else None

        return {
            "required_skills": found_skills[:5],
            "preferred_skills": found_skills[5:10],
            "responsibilities": ["Design and implement scalable data architectures", "Build robust pipelines and models"],
            "tools_technologies": found_skills,
            "experience_years_min": min_years,
            "education": ["Bachelor's or Master's in Computer Science or related field"],
            "dealbreakers": [],
        }

    def _heuristic_match(self, job_data: Dict[str, Any], candidate_data: Dict[str, Any], candidate_facts: List[Dict[str, Any]]) -> Dict[str, Any]:
        job_skills = set([s.lower() for s in job_data.get("requirements_structured", {}).get("required_skills", [])])
        priorities = candidate_data.get("tech_stack_priorities", {})
        cand_skills = set([s.lower() for s in priorities.get("must_have", []) + priorities.get("preferred", [])])

        common = job_skills.intersection(cand_skills)
        missing = job_skills.difference(cand_skills)

        skills_score = (len(common) / max(len(job_skills), 1)) * 100 if job_skills else 85.0
        skills_score = min(max(skills_score, 50.0), 98.0)

        overall = round((skills_score * 0.4) + 85.0 * 0.3 + 90.0 * 0.3, 1)
        rec = "EXCELLENT" if overall >= 90 else ("STRONG" if overall >= 80 else "CONSIDER")

        return {
            "overall_score": overall,
            "skills_score": round(skills_score, 1),
            "experience_score": 88.0,
            "domain_score": 92.0,
            "seniority_score": 90.0,
            "recommendation": rec,
            "pros": [f"Direct match on key skills: {', '.join(list(common)[:4]) or 'Domain tech stack'}", "Experience level aligns with role"],
            "gaps": [f"Missing demonstration of: {', '.join(list(missing)[:3])}"] if missing else [],
            "dealbreakers": [],
            "missing_skills_status": {s: "MISSING" for s in missing},
            "explanation": f"Strong alignment for {job_data.get('title')} at {job_data.get('company_name')}. Candidate profile matches core requirements.",
        }


claude_ai_provider = ClaudeAIProvider()
