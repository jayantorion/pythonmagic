import re
import hashlib
from typing import Optional, List, Tuple, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_

from app.models.job import Job
from app.services.normalization.canonicalizer import canonicalizer
from app.services.ai.embedding import embedding_service
from app.core.logging import logger


class DeduplicationEngine:
    @staticmethod
    def _clean_text_tokens(text: str) -> set:
        clean = re.sub(r"[^\w\s]", "", text.lower())
        return set([w for w in clean.split() if len(w) > 3])

    def jaccard_similarity(self, tokens_a: set, tokens_b: set) -> float:
        if not tokens_a or not tokens_b:
            return 0.0
        intersection = len(tokens_a.intersection(tokens_b))
        union = len(tokens_a.union(tokens_b))
        return float(intersection / union) if union > 0 else 0.0

    async def find_duplicate(
        self,
        db: AsyncSession,
        source: str,
        external_id: Optional[str],
        canonical_url: str,
        company_name: str,
        title: str,
        location: Optional[str],
        description_raw: str,
    ) -> Tuple[bool, Optional[Job], str]:
        """Runs the 5-Tier Deduplication check against the database."""
        # Tier 1: Source + External ID Match
        if external_id:
            res1 = await db.execute(
                select(Job).where(Job.source == source, Job.external_id == external_id)
            )
            job1 = res1.scalars().first()
            if job1:
                return True, job1, "Tier 1: Exact Source + External ID Match"

        # Tier 2: Canonical URL Match
        clean_url = canonicalizer.canonicalize_url(canonical_url)
        if clean_url:
            res2 = await db.execute(select(Job).where(Job.canonical_url == clean_url))
            job2 = res2.scalars().first()
            if job2:
                return True, job2, "Tier 2: Canonical URL Match"

        # Tier 3: Normalized Company + Normalized Title Match
        norm_company = canonicalizer.normalize_company_name(company_name)
        norm_title = canonicalizer.normalize_job_title(title)

        res3 = await db.execute(
            select(Job).where(
                Job.company_name.ilike(f"%{norm_company}%"),
                Job.normalized_title == norm_title,
            )
        )
        candidates = res3.scalars().all()

        incoming_tokens = self._clean_text_tokens(description_raw)

        for cand in candidates:
            # Tier 3 check (Same company + title)
            if cand.company_name.lower() == norm_company.lower() and cand.normalized_title.lower() == norm_title.lower():
                # Tier 4: Text overlap check
                cand_tokens = self._clean_text_tokens(cand.description_raw)
                similarity = self.jaccard_similarity(incoming_tokens, cand_tokens)
                if similarity > 0.80:
                    return True, cand, f"Tier 4: High Text Similarity ({round(similarity*100, 1)}%) at Same Company"

                # Tier 5: Semantic Embedding Similarity Check
                emb_incoming = await embedding_service.get_embedding(description_raw[:1500])
                emb_cand = await embedding_service.get_embedding(cand.description_raw[:1500])
                cos_sim = embedding_service.cosine_similarity(emb_incoming, emb_cand)
                if cos_sim > 0.94:
                    return True, cand, f"Tier 5: Semantic Embedding Overlap ({round(cos_sim*100, 1)}%)"

        return False, None, "No duplicate found"


deduplication_engine = DeduplicationEngine()
