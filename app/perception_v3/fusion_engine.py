"""
Fusion Engine V3 - Combines DOM text + vision proximity + semantic similarity.
Weights: semantic 0.55, substring 0.30, vision 0.15 (configurable).
"""
from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


MAX_CANDIDATES = 200  # Cap to avoid huge batch encodes on very large pages


class FusionEngineV3:
    """Fuse DOM candidates with semantic and optional vision signals."""

    def __init__(
        self,
        weight_semantic: float = 0.55,
        weight_substring: float = 0.30,
        weight_vision: float = 0.15,
        max_candidates: int = MAX_CANDIDATES,
    ):
        self.weight_semantic = weight_semantic
        self.weight_substring = weight_substring
        self.weight_vision = weight_vision
        self.max_candidates = max_candidates

    def fuse(
        self,
        target: str,
        dom_candidates: List[Dict[str, Any]],
        vision_data: Optional[List[Dict[str, Any]]],
        target_emb,
        encoder,
    ) -> List[Dict[str, Any]]:
        """Score each DOM candidate and return sorted by score. Uses batch encoding for speed."""
        if not dom_candidates:
            return []
        target_lower = (target or "").lower().strip()

        # Cap candidates: prefer substring matches, then fill up to max_candidates
        if len(dom_candidates) > self.max_candidates:
            substring_matches = [c for c in dom_candidates if target_lower in ((c.get("text") or "").lower())]
            rest = [c for c in dom_candidates if c not in substring_matches]
            dom_candidates = substring_matches + rest[: self.max_candidates - len(substring_matches)]

        # Batch encode all DOM texts in one forward pass (avoids 430+ individual calls)
        dom_texts = [(item.get("text") or "").strip() for item in dom_candidates]
        dom_embeddings = encoder.embed_batch(dom_texts)

        results = []
        for i, item in enumerate(dom_candidates):
            dom_text = dom_texts[i]
            bbox = item.get("bbox")
            el = item.get("locator")

            # Semantic score (pre-computed embedding)
            emb = dom_embeddings[i] if i < len(dom_embeddings) else encoder.embed(dom_text)
            sem_score = float(encoder.cosine(target_emb, emb))

            # Substring (critical for LG products)
            substring_score = 1.0 if target_lower in dom_text.lower() else 0.0
            if substring_score == 0 and target_lower and dom_text.lower():
                words = target_lower.split()[:5]
                matches = sum(1 for w in words if len(w) > 2 and w in dom_text.lower())
                if matches >= 2:
                    substring_score = 0.7

            # Vision alignment (when vision data available)
            vision_score = self._vision_alignment(dom_text, bbox, vision_data) if vision_data else 0.0

            final = (
                sem_score * self.weight_semantic
                + substring_score * self.weight_substring
                + vision_score * self.weight_vision
            )

            results.append({
                "locator": el,
                "text": dom_text,
                "score": final,
                "bbox": bbox,
            })

        return sorted(results, key=lambda x: x["score"], reverse=True)

    def _vision_alignment(
        self,
        dom_text: str,
        dom_bbox: Optional[Dict],
        vision_data: List[Dict[str, Any]],
    ) -> float:
        """Check if vision text aligns with DOM text; optionally use bbox overlap."""
        if not dom_text or not vision_data:
            return 0.0
        dom_lower = dom_text.lower()
        for v in vision_data:
            v_text = (v.get("text") or "").strip().lower()
            if not v_text or len(v_text) < 2:
                continue
            if v_text in dom_lower or dom_lower in v_text:
                return 1.0
            # Partial word overlap
            v_words = set(w for w in v_text.split() if len(w) > 2)
            d_words = set(w for w in dom_lower.split() if len(w) > 2)
            if v_words & d_words:
                return 0.6
        return 0.0
