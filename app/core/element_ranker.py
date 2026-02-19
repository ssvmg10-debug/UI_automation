"""
Enterprise-grade element ranking with production scoring logic.
Deterministic multi-factor scoring to select best element match.
"""
from difflib import SequenceMatcher
from typing import List, Tuple, Optional
import logging
from .dom_model import DOMElement

logger = logging.getLogger(__name__)


def text_similarity(a: str, b: str) -> float:
    """
    Calculate text similarity using sequence matcher.
    
    Args:
        a: First string
        b: Second string
        
    Returns:
        Similarity score between 0 and 1
    """
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


class ElementRanker:
    """
    Enterprise-grade element ranking with multi-factor scoring.
    This is deterministic - no AI involved.
    """
    
    # Scoring weights (total = 1.0)
    WEIGHT_EXACT_MATCH = 0.35
    WEIGHT_SEMANTIC_SIMILARITY = 0.20
    WEIGHT_ROLE_MATCH = 0.10
    WEIGHT_ARIA_LABEL = 0.15
    WEIGHT_VISIBILITY = 0.05
    WEIGHT_POSITION_BIAS = 0.05
    WEIGHT_CONTAINER_CONTEXT = 0.10
    
    def __init__(self, threshold: float = 0.65):
        """
        Initialize ranker.
        
        Args:
            threshold: Minimum score threshold for acceptance
        """
        self.threshold = threshold
    
    def score_element(
        self, 
        element: DOMElement, 
        target_text: str,
        region_context: Optional[str] = None,
        historical_success: bool = False
    ) -> float:
        """
        Calculate comprehensive score for element match.
        
        Args:
            element: DOMElement to score
            target_text: Target text to match against
            region_context: Expected container region
            historical_success: Whether this element succeeded before
            
        Returns:
            Score between 0.0 and 1.0
        """
        score = 0.0
        target_lower = target_text.lower().strip()
        element_text = element.text.lower().strip()
        
        # 1. EXACT MATCH (highest weight)
        if element_text == target_lower:
            score += self.WEIGHT_EXACT_MATCH
            logger.debug(f"Exact match bonus: {self.WEIGHT_EXACT_MATCH}")
        
        # 2. SEMANTIC SIMILARITY
        text_sim = text_similarity(element.text, target_text)
        score += text_sim * self.WEIGHT_SEMANTIC_SIMILARITY
        logger.debug(f"Text similarity score: {text_sim * self.WEIGHT_SEMANTIC_SIMILARITY}")
        
        # 3. ROLE MATCH
        if element.role in ["button", "link"]:
            score += self.WEIGHT_ROLE_MATCH
            logger.debug(f"Role match bonus: {self.WEIGHT_ROLE_MATCH}")
        
        # 4. ARIA LABEL MATCH
        aria_label = element.attributes.get("aria_label", "")
        if aria_label:
            aria_sim = text_similarity(aria_label, target_text)
            score += aria_sim * self.WEIGHT_ARIA_LABEL
            logger.debug(f"Aria label score: {aria_sim * self.WEIGHT_ARIA_LABEL}")
        
        # 5. VISIBILITY (should always be true after filtering)
        if element.visible:
            score += self.WEIGHT_VISIBILITY
        
        # 6. POSITION BIAS (prefer elements in upper part of page)
        if element.bounding_box:
            if element.bounding_box.y < 800:
                score += self.WEIGHT_POSITION_BIAS
                logger.debug(f"Position bias bonus: {self.WEIGHT_POSITION_BIAS}")
        
        # 7. CONTAINER CONTEXT
        if region_context and element.container:
            if region_context.lower() in element.container.lower():
                score += self.WEIGHT_CONTAINER_CONTEXT
                logger.debug(f"Container context bonus: {self.WEIGHT_CONTAINER_CONTEXT}")
        
        # 8. HISTORICAL SUCCESS (bonus, not part of base weights)
        if historical_success:
            score += 0.05
            logger.debug("Historical success bonus: 0.05")
        
        return min(score, 1.0)  # Cap at 1.0
    
    def rank_elements(
        self, 
        elements: List[DOMElement], 
        target_text: str,
        region_context: Optional[str] = None,
        history_lookup: Optional[dict] = None
    ) -> List[Tuple[float, DOMElement]]:
        """
        Rank elements by match score.
        
        Args:
            elements: List of DOMElement objects
            target_text: Target text to match
            region_context: Optional region context
            history_lookup: Optional history of successful elements
            
        Returns:
            List of (score, element) tuples, sorted by score descending
        """
        scored_elements = []
        
        for element in elements:
            # Check if element was historically successful
            historical_success = False
            if history_lookup:
                element_key = f"{element.tag}_{element.text}_{element.attributes.get('id', '')}"
                historical_success = history_lookup.get(element_key, False)
            
            score = self.score_element(
                element, 
                target_text, 
                region_context, 
                historical_success
            )
            
            if score >= self.threshold:
                scored_elements.append((score, element))
                logger.debug(
                    f"Element '{element.display_name}' scored {score:.3f}"
                )
        
        # Sort by score descending
        scored_elements.sort(key=lambda x: x[0], reverse=True)
        
        logger.info(
            f"Ranked {len(scored_elements)}/{len(elements)} elements above threshold {self.threshold}"
        )
        
        return scored_elements
    
    def get_top_candidates(
        self, 
        elements: List[DOMElement], 
        target_text: str,
        top_n: int = 3,
        region_context: Optional[str] = None
    ) -> List[DOMElement]:
        """
        Get top N candidate elements.
        
        Args:
            elements: List of DOMElement objects
            target_text: Target text to match
            top_n: Number of top candidates to return
            region_context: Optional region context
            
        Returns:
            List of top candidate elements
        """
        ranked = self.rank_elements(elements, target_text, region_context)
        top_candidates = [elem for score, elem in ranked[:top_n]]
        
        logger.info(f"Returning top {len(top_candidates)} candidates")
        return top_candidates
    
    def get_best_match(
        self, 
        elements: List[DOMElement], 
        target_text: str,
        region_context: Optional[str] = None
    ) -> Optional[DOMElement]:
        """
        Get single best matching element.
        
        Args:
            elements: List of DOMElement objects
            target_text: Target text to match
            region_context: Optional region context
            
        Returns:
            Best matching element or None
        """
        ranked = self.rank_elements(elements, target_text, region_context)
        
        if not ranked:
            logger.warning("No elements above threshold")
            return None
        
        best_score, best_element = ranked[0]
        logger.info(
            f"Best match: '{best_element.display_name}' with score {best_score:.3f}"
        )
        
        return best_element
