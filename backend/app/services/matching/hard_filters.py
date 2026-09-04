import re
from typing import Tuple, List, Dict, Any, Optional
from app.models.candidate import CandidateProfile
from app.schemas.job import JobCreate
from app.core.logging import logger


class HardFilterResult:
    def __init__(self, passed: bool, reason: Optional[str] = None):
        self.passed = passed
        self.reason = reason


class DeterministicHardFilterEngine:
    def evaluate(self, job: JobCreate, profile: CandidateProfile) -> HardFilterResult:
        """Runs fast, zero-cost deterministic filtering against the candidate's preferences."""
        prefs = profile.preferences or {}

        # 1. Excluded Companies
        excluded_comps = [c.lower().strip() for c in prefs.get("excluded_companies", [])]
        if job.company_name.lower().strip() in excluded_comps:
            return HardFilterResult(False, f"Company '{job.company_name}' is in your excluded companies list.")

        # 2. Excluded Keywords in Title
        excluded_kws = [k.lower().strip() for k in prefs.get("excluded_keywords", [])]
        job_title_lower = job.title.lower()
        for kw in excluded_kws:
            if re.search(rf"\b{re.escape(kw)}\b", job_title_lower):
                return HardFilterResult(False, f"Job title matches excluded keyword: '{kw}'")

        # 3. Work Mode Compatibility
        allowed_work_modes = prefs.get("work_modes", ["remote", "hybrid", "on_site"])
        if job.remote_type != "unknown" and job.remote_type not in allowed_work_modes:
            # On-site jobs are allowed if the location is one of the candidate's preferred locations
            if job.remote_type == "on_site":
                preferred_locs = [l.lower().strip() for l in prefs.get("locations", []) if l]
                job_loc = (job.location or "").lower().strip()
                in_preferred = any(loc and loc in job_loc for loc in preferred_locs)
                if in_preferred:
                    return HardFilterResult(True, "On-site job in a preferred location — passed")
            # If candidate only wants remote, filter out on_site
            if "on_site" not in allowed_work_modes and job.remote_type == "on_site":
                return HardFilterResult(False, f"Work mode '{job.remote_type}' does not match preferred work modes {allowed_work_modes}")

        # 4. Salary Floor Check
        salary_exp = prefs.get("salary_expectation", {})
        min_salary = salary_exp.get("min_amount")
        if min_salary and job.salary_max and job.salary_max < min_salary:
            return HardFilterResult(False, f"Maximum salary ({job.salary_max}) is below your minimum expectation ({min_salary})")

        # 5. Experience Ceiling (Filter roles requiring far above candidate level, e.g. 8+ yrs when candidate has 3)
        if job.requirements_structured and job.requirements_structured.get("experience_years_min"):
            req_years = job.requirements_structured["experience_years_min"]
            cand_years = profile.experience_years or 3.0
            if req_years > (cand_years + 4.5):
                return HardFilterResult(False, f"Required experience ({req_years} yrs) significantly exceeds candidate profile ({cand_years} yrs)")

        return HardFilterResult(True, "Passed all deterministic hard filters")


hard_filter_engine = DeterministicHardFilterEngine()
