import hashlib
import numpy as np
from typing import List, Dict, Any, Optional
import httpx
from app.core.config import settings
from app.core.logging import logger


class EmbeddingService:
    def __init__(self):
        self.provider = settings.EMBEDDING_PROVIDER
        self.openai_key = settings.OPENAI_API_KEY

    def hash_text(self, text: str) -> str:
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    async def get_embedding(self, text: str) -> List[float]:
        """Generate a dense vector embedding for text."""
        cleaned_text = text.strip()[:8000]

        if self.provider == "openai" and self.openai_key:
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    resp = await client.post(
                        "https://api.openai.com/v1/embeddings",
                        headers={"Authorization": f"Bearer {self.openai_key}"},
                        json={
                            "input": cleaned_text,
                            "model": "text-embedding-3-small",
                        },
                    )
                    if resp.status_code == 200:
                        data = resp.json()
                        return data["data"][0]["embedding"]
            except Exception as e:
                logger.warning(f"OpenAI embedding call failed, falling back to local: {e}")

        # Local deterministic fallback (hash-projected dense pseudo-embedding for local offline mode)
        return self._generate_local_embedding(cleaned_text)

    def _generate_local_embedding(self, text: str, dim: int = 128) -> List[float]:
        """Deterministic, lightweight local vector generation for offline execution."""
        tokens = [t.lower() for t in text.split() if len(t) > 2]
        if not tokens:
            return [0.0] * dim

        vec = np.zeros(dim, dtype=np.float32)
        for token in tokens:
            h = int(hashlib.md5(token.encode("utf-8")).hexdigest(), 16)
            idx = h % dim
            val = ((h >> 8) % 100) / 100.0
            vec[idx] += val

        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm
        return vec.tolist()

    def cosine_similarity(self, vec_a: List[float], vec_b: List[float]) -> float:
        a = np.array(vec_a, dtype=np.float32)
        b = np.array(vec_b, dtype=np.float32)
        dot = np.dot(a, b)
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return float(dot / (norm_a * norm_b))


embedding_service = EmbeddingService()
