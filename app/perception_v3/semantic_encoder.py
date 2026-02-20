"""
Semantic Encoder V3 - sentence-transformers for similarity.
Preload at init to avoid cold start on first use.
OPTIMIZED: GPU acceleration + embedding cache + batched processing.
"""
from sentence_transformers import SentenceTransformer
import numpy as np
import logging
import torch
import hashlib
from typing import Dict, List

logger = logging.getLogger(__name__)


class SemanticEncoderV3:
    """Embedding-based semantic similarity with GPU acceleration and caching."""

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        logger.info("[SEMANTIC_V3] Loading model %s...", model_name)
        
        # Use GPU if available
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        if self.device == "cuda":
            logger.info("[SEMANTIC_V3] GPU detected - using CUDA acceleration")
        else:
            logger.info("[SEMANTIC_V3] GPU not available - using CPU")
        
        self.model = SentenceTransformer(model_name, device=self.device)
        
        # Embedding cache for repeated queries
        self._embedding_cache: Dict[str, np.ndarray] = {}
        self._cache_hits = 0
        self._cache_misses = 0
        
        logger.info("[SEMANTIC_V3] Model loaded on %s", self.device)

    def _get_cache_key(self, text: str) -> str:
        """Generate cache key from text."""
        return hashlib.md5(text.encode('utf-8')).hexdigest()

    def embed(self, text: str) -> np.ndarray:
        if not text or not text.strip():
            return np.zeros(384, dtype=np.float32)  # MiniLM dim
        
        # Check cache first
        cache_key = self._get_cache_key(text)
        if cache_key in self._embedding_cache:
            self._cache_hits += 1
            return self._embedding_cache[cache_key]
        
        # Cache miss - compute embedding
        self._cache_misses += 1
        embedding = self.model.encode([text], normalize_embeddings=True, device=self.device)[0]
        self._embedding_cache[cache_key] = embedding
        
        return embedding

    def embed_batch(self, texts: List[str], show_progress: bool = False, batch_size: int = 64) -> np.ndarray:
        """Encode all texts in batched forward passes with caching. Much faster than calling embed() per text."""
        if not texts:
            return np.zeros((0, 384), dtype=np.float32)
        
        valid = [(t or "").strip() or " " for t in texts]
        
        # Check cache for all texts
        cache_keys = [self._get_cache_key(t) for t in valid]
        uncached_indices = []
        uncached_texts = []
        result = np.zeros((len(valid), 384), dtype=np.float32)
        
        for i, (text, key) in enumerate(zip(valid, cache_keys)):
            if key in self._embedding_cache:
                result[i] = self._embedding_cache[key]
                self._cache_hits += 1
            else:
                uncached_indices.append(i)
                uncached_texts.append(text)
        
        # Compute embeddings for uncached texts only
        if uncached_texts:
            self._cache_misses += len(uncached_texts)
            logger.debug("[SEMANTIC_V3] Computing %d uncached embeddings (cache hits: %d)", 
                        len(uncached_texts), self._cache_hits)
            
            embeddings = self.model.encode(
                uncached_texts, 
                normalize_embeddings=True, 
                show_progress_bar=show_progress,
                batch_size=batch_size,
                device=self.device
            )
            
            # Store in cache and result
            for idx, embedding in zip(uncached_indices, embeddings):
                cache_key = cache_keys[idx]
                self._embedding_cache[cache_key] = embedding
                result[idx] = embedding
        else:
            logger.debug("[SEMANTIC_V3] All %d embeddings from cache!", len(texts))
        
        return result

    def cosine(self, a: np.ndarray, b: np.ndarray) -> float:
        return float(np.dot(a, b))
    
    def clear_cache(self):
        """Clear embedding cache."""
        self._embedding_cache.clear()
        self._cache_hits = 0
        self._cache_misses = 0
        logger.info("[SEMANTIC_V3] Cache cleared")
    
    def get_cache_stats(self) -> Dict[str, int]:
        """Get cache statistics."""
        return {
            "hits": self._cache_hits,
            "misses": self._cache_misses,
            "size": len(self._embedding_cache),
            "hit_rate": self._cache_hits / max(self._cache_hits + self._cache_misses, 1)
        }
