"""
Load sentence-transformers model once at startup.
"""
from typing import Optional, Any
import logging

logger = logging.getLogger(__name__)

_model: Optional[Any] = None


class EmbeddingLoader:
    _model = None

    @classmethod
    def load(cls) -> Any:
        global _model
        if cls._model is None and _model is None:
            try:
                from sentence_transformers import SentenceTransformer
                cls._model = SentenceTransformer("all-MiniLM-L6-v2")
                _model = cls._model
                logger.info("Loaded sentence-transformers model: all-MiniLM-L6-v2")
            except ImportError as e:
                logger.warning("sentence_transformers not installed: %s", e)
                cls._model = False
                _model = False
        return cls._model if cls._model is not False else _model if _model is not False else None
