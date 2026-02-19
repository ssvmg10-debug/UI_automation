"""
Compute cosine similarity between user target and element text using embeddings.
"""
from typing import Union, List
import logging
from .embedding_loader import EmbeddingLoader

logger = logging.getLogger(__name__)


def _cosine_similarity_sklearn(emb1, emb2) -> float:
    from sklearn.metrics.pairwise import cosine_similarity
    import numpy as np
    a = np.asarray(emb1).reshape(1, -1)
    b = np.asarray(emb2).reshape(1, -1)
    return float(cosine_similarity(a, b)[0][0])


class EmbeddingScorer:
    def __init__(self):
        self.model = EmbeddingLoader.load()

    def score(self, user_target: str, element_text: str) -> float:
        if not user_target or not element_text:
            return 0.0
        if self.model is None:
            from difflib import SequenceMatcher
            return SequenceMatcher(None, user_target.lower(), (element_text or "").lower()).ratio()
        try:
            emb1 = self.model.encode([user_target])
            emb2 = self.model.encode([element_text])
            return _cosine_similarity_sklearn(emb1, emb2)
        except Exception as e:
            logger.debug("Embedding score failed: %s", e)
            from difflib import SequenceMatcher
            return SequenceMatcher(None, user_target.lower(), (element_text or "").lower()).ratio()
