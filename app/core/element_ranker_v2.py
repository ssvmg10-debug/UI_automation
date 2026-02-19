"""
Element ranking V2: embeddings + substring + fuzzy + component + position.
"""
from typing import List, Tuple, Any
from app.core.semantic.embedding_scorer import EmbeddingScorer


class ElementRankerV2:
    def __init__(self):
        self.scorer = EmbeddingScorer()

    def rank(self, target: str, components: List[Any], top_n: int = 5) -> List[Tuple[float, Any]]:
        if not target or not components:
            return []
        scored: List[Tuple[float, Any]] = []
        for comp in components:
            text = getattr(comp, "text", "") or ""
            sem = self.scorer.score(target, text)
            sub = 1.0 if (target or "").lower() in (text or "").lower() else 0.0
            final = sem * 0.7 + sub * 0.3
            # Position: prefer above fold
            bbox = getattr(comp, "bbox", None)
            if bbox and isinstance(bbox, dict):
                y = bbox.get("y", 0)
                if y < 800:
                    final += 0.05
            scored.append((final, comp))
        scored.sort(key=lambda x: x[0], reverse=True)
        return scored[:top_n]
