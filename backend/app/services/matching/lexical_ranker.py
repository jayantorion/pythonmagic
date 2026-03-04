import re
from typing import Dict, Any, List, Set
from app.models.candidate import CandidateProfile


class DomainLexicalRanker:
    def calculate_lexical_score(self, description: str, title: str, profile: CandidateProfile) -> Dict[str, Any]:
        """Calculates a weighted domain tech stack overlap score."""
        priorities = profile.tech_stack_priorities or {}
        must_have = [s.strip() for s in priorities.get("must_have", []) if s.strip()]
        preferred = [s.strip() for s in priorities.get("preferred", []) if s.strip()]
        nice_to_have = [s.strip() for s in priorities.get("nice_to_have", []) if s.strip()]

        full_text = f"{title} {description}".lower()

        found_must = [s for s in must_have if re.search(rf"\b{re.escape(s.lower())}\b", full_text)]
        found_pref = [s for s in preferred if re.search(rf"\b{re.escape(s.lower())}\b", full_text)]
        found_nice = [s for s in nice_to_have if re.search(rf"\b{re.escape(s.lower())}\b", full_text)]

        missing_must = [s for s in must_have if s not in found_must]

        # Weighting: must_have = 3.0, preferred = 1.5, nice_to_have = 0.5
        total_possible = (len(must_have) * 3.0) + (len(preferred) * 1.5) + (len(nice_to_have) * 0.5)
        earned = (len(found_must) * 3.0) + (len(found_pref) * 1.5) + (len(found_nice) * 0.5)

        raw_percentage = (earned / total_possible) * 100 if total_possible > 0 else 75.0
        score = min(max(raw_percentage, 0.0), 100.0)

        return {
            "lexical_score": round(score, 1),
            "found_must_have": found_must,
            "found_preferred": found_pref,
            "found_nice_to_have": found_nice,
            "missing_must_have": missing_must,
        }


lexical_ranker = DomainLexicalRanker()
