"""
Element Ranker V3 - Pick best from fused results.
Threshold 0.38 (more permissive than legacy 0.65).
"""
from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class ElementRankerV3:
    """Select best locator from fused results."""

    def __init__(self, threshold: float = 0.38):
        self.threshold = threshold

    def pick_best(
        self,
        fused_results: List[Dict[str, Any]],
        threshold: Optional[float] = None,
    ):
        """Return best locator if score >= threshold, else None."""
        if not fused_results:
            return None
        th = threshold if threshold is not None else self.threshold
        best = fused_results[0]
        if best.get("score", 0) >= th:
            return best.get("locator")
        # Fallback: if we have few candidates, accept best above 0.25
        if len(fused_results) <= 5 and best.get("score", 0) >= 0.25:
            logger.info("[RANKER_V3] Accepting best below threshold (few candidates): %.2f", best.get("score"))
            return best.get("locator")
        return None
