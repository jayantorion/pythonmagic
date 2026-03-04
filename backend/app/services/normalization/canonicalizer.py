import re
from urllib.parse import urlparse, parse_qsl, urlencode, urlunparse
from typing import Tuple


class URLAndEntityCanonicalizer:
    TRACKING_PARAMS = {
        "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
        "ref", "source", "gh_src", "lever-source", "ashby_jid", "fbclid",
        "gclid", "mc_cid", "mc_eid", "trk", "trkEmail", "_hsenc", "_hsmi"
    }

    COMPANY_SUFFIXES = [
        r"\bllc\b", r"\binc\.?\b", r"\bpvt\.?\s*ltd\.?\b", r"\bltd\.?\b",
        r"\bcorp\.?\b", r"\bcorporation\b", r"\btechnologies\b", r"\btechnology\b",
        r"\bservices\b", r"\bsolutions\b", r"\bgroup\b", r"\bindia\b", r"\bglobal\b"
    ]

    def canonicalize_url(self, raw_url: str) -> str:
        """Strip tracking parameters and fragments while keeping identifying query params."""
        if not raw_url:
            return ""

        try:
            parsed = urlparse(raw_url.strip())
            # Normalize scheme and netloc to lowercase
            scheme = parsed.scheme.lower() or "https"
            netloc = parsed.netloc.lower().replace("www.", "")
            path = parsed.path.rstrip("/")

            # Filter out tracking query parameters
            query_tuples = parse_qsl(parsed.query, keep_blank_values=False)
            filtered_query = [
                (k, v) for k, v in query_tuples
                if k.lower() not in self.TRACKING_PARAMS and not k.lower().startswith("utm_")
            ]
            clean_query = urlencode(filtered_query)

            # Build canonical URL without fragment
            canonical = urlunparse((scheme, netloc, path, "", clean_query, ""))
            return canonical
        except Exception:
            return raw_url.strip()

    def normalize_company_name(self, name: str) -> str:
        """Normalize company name to canonical form (e.g. 'Google LLC' -> 'Google')."""
        if not name:
            return "Unknown Company"

        cleaned = name.strip()
        for suffix in self.COMPANY_SUFFIXES:
            cleaned = re.sub(suffix, "", cleaned, flags=re.IGNORECASE).strip()

        # Remove extra punctuation and whitespace
        cleaned = re.sub(r"[,\-_]+$", "", cleaned).strip()
        cleaned = re.sub(r"\s+", " ", cleaned)
        return cleaned.title() or name.strip()

    def normalize_job_title(self, title: str) -> str:
        """Normalize job title to standard role naming (e.g. 'Senior PySpark Data Engineer (Remote)' -> 'Senior Data Engineer')."""
        if not title:
            return "Software Engineer"

        cleaned = title.strip()
        # Remove parenthetical clauses like (Remote), (Hybrid), (Bangalore), (f/m/d), (Immediate Joiner)
        cleaned = re.sub(r"\(.*?\)|\[.*?\]", "", cleaned).strip()
        # Remove location suffixes
        cleaned = re.sub(r"-\s*(?:Remote|India|Bangalore|Hyderabad|Full\s*Time|Contract).*$", "", cleaned, flags=re.IGNORECASE).strip()

        # Map domain variations
        title_lower = cleaned.lower()
        if "data engineer" in title_lower or "pyspark" in title_lower or "etl" in title_lower:
            if "senior" in title_lower or "sr" in title_lower or "lead" in title_lower or "principal" in title_lower:
                return "Senior Data Engineer"
            return "Data Engineer"
        elif "analytics engineer" in title_lower:
            return "Analytics Engineer"
        elif "data platform" in title_lower:
            return "Data Platform Engineer"
        elif "backend" in title_lower or "python developer" in title_lower:
            if "senior" in title_lower or "sr" in title_lower:
                return "Senior Backend Engineer"
            return "Backend Engineer"
        elif "machine learning" in title_lower or "ml engineer" in title_lower or "ai engineer" in title_lower:
            return "AI/ML Engineer"

        return re.sub(r"\s+", " ", cleaned).title()


canonicalizer = URLAndEntityCanonicalizer()
