"""
Semantic similarity via embeddings (optional sentence-transformers).
Fallback to text similarity when not installed.
"""
from typing import Optional, List
import logging

logger = logging.getLogger(__name__)

_embedding_model = None


def _get_model():
    global _embedding_model
    if _embedding_model is not None:
        return _embedding_model
    try:
        from sentence_transformers import SentenceTransformer
        _embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
        return _embedding_model
    except ImportError:
        logger.info("sentence-transformers not installed; semantic scoring will use text fallback")
        return None


def embed_texts(texts: List[str]) -> Optional[List[List[float]]]:
    """Return list of embedding vectors, or None if model not available."""
    model = _get_model()
    if model is None or not texts:
        return None
    try:
        return model.encode(texts).tolist()
    except Exception as e:
        logger.debug("Embedding failed: %s", e)
        return None


def semantic_similarity(text_a: str, text_b: str) -> float:
    """
    Cosine similarity in [0,1] if embeddings available; else fallback to SequenceMatcher ratio.
    """
    model = _get_model()
    if model is None:
        from difflib import SequenceMatcher
        return SequenceMatcher(None, (text_a or "").lower(), (text_b or "").lower()).ratio()
    try:
        embs = model.encode([text_a or "", text_b or ""])
        a, b = embs[0], embs[1]
        dot = sum(x * y for x, y in zip(a, b))
        na = sum(x * x for x in a) ** 0.5
        nb = sum(x * x for x in b) ** 0.5
        if na == 0 or nb == 0:
            return 0.0
        cos = dot / (na * nb)
        return max(0.0, min(1.0, (cos + 1) / 2))  # map [-1,1] -> [0,1]
    except Exception as e:
        logger.debug("Semantic similarity failed: %s", e)
        from difflib import SequenceMatcher
        return SequenceMatcher(None, (text_a or "").lower(), (text_b or "").lower()).ratio()
