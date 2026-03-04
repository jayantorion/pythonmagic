from typing import Dict, Any, List
from app.models.candidate import CandidateProfile
from app.schemas.job import JobCreate
from app.services.ai.embedding import embedding_service


class SemanticVectorMatcher:
    async def compute_semantic_similarity(self, job_text: str, profile: CandidateProfile) -> float:
        """Computes dense vector cosine similarity between candidate summary and job description."""
        profile_text = f"Candidate Domain: {profile.domain}. Target Roles: {', '.join(profile.target_roles or [])}. Summary: {profile.career_summary or ''}"

        emb_profile = await embedding_service.get_embedding(profile_text)
        emb_job = await embedding_service.get_embedding(job_text[:2000])

        sim = embedding_service.cosine_similarity(emb_profile, emb_job)
        # Scale typical cosine sim range (~0.5 - 0.95) to a 0-100 score
        normalized_score = max(0.0, min(100.0, (sim - 0.2) / 0.75 * 100))
        return round(normalized_score, 1)


vector_matcher = SemanticVectorMatcher()
