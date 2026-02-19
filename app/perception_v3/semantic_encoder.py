"""
Semantic Encoder V3 - sentence-transformers for similarity.
Preload at init to avoid cold start on first use.
"""
from sentence_transformers import SentenceTransformer
import numpy as np
import logging

logger = logging.getLogger(__name__)


class SemanticEncoderV3:
    """Embedding-based semantic similarity."""

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        logger.info("[SEMANTIC_V3] Loading model %s...", model_name)
        self.model = SentenceTransformer(model_name)
        logger.info("[SEMANTIC_V3] Model loaded")

    def embed(self, text: str) -> np.ndarray:
        if not text or not text.strip():
            return np.zeros(384, dtype=np.float32)  # MiniLM dim
        return self.model.encode([text], normalize_embeddings=True)[0]

    def embed_batch(self, texts: list[str], show_progress: bool = False) -> np.ndarray:
        """Encode all texts in one forward pass. Much faster than calling embed() per text."""
        if not texts:
            return np.zeros((0, 384), dtype=np.float32)
        valid = [(t or "").strip() or " " for t in texts]
        return self.model.encode(valid, normalize_embeddings=True, show_progress_bar=show_progress)

    def cosine(self, a: np.ndarray, b: np.ndarray) -> float:
        return float(np.dot(a, b))
