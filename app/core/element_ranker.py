"""
Enterprise-grade element ranking with production scoring logic.
Deterministic multi-factor scoring to select best element match.
Supports long product names: substring match, keyword overlap, parent text.
"""
import re
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


def _significant_tokens(text: str, min_len: int = 2) -> List[str]:
    """Extract significant tokens (skip tiny words, keep numbers and model parts)."""
    if not text:
        return []
    # Split on spaces, commas, parens; keep alphanumeric + dots (e.g. 1.5)
    tokens = re.findall(r"[a-zA-Z0-9.]+", text.lower())
    return [t for t in tokens if len(t) >= min_len or t.isdigit() or (t.replace(".", "").isdigit())]


class ElementRanker:
    """
    Enterprise-grade element ranking with multi-factor scoring.
    This is deterministic - no AI involved.
    """
    
    # Scoring weights (total = 1.0)
    WEIGHT_EXACT_MATCH = 0.30
    WEIGHT_SEMANTIC_SIMILARITY = 0.15
    WEIGHT_SUBSTRING_MATCH = 0.25   # product name: page shows "LG 5 Star... Gold Fin+" etc.
    WEIGHT_KEYWORD_OVERLAP = 0.15   # how many target keywords appear in element/parent text
    WEIGHT_ROLE_MATCH = 0.08
    WEIGHT_ARIA_LABEL = 0.12
    WEIGHT_VISIBILITY = 0.05
    WEIGHT_POSITION_BIAS = 0.05
    WEIGHT_CONTAINER_CONTEXT = 0.10
    
    # Min length for substring match so we don't match "LG" or "5" only
    MIN_SUBSTRING_LEN = 12
    
    # Long targets (e.g. product titles 60+ chars) never hit 0.65 due to truncation; use lower threshold.
    LONG_TARGET_LEN = 60
    LONG_TARGET_THRESHOLD = 0.35

    def __init__(self, threshold: float = 0.65):
        """
        Initialize ranker.
        
        Args:
            threshold: Minimum score threshold for acceptance (short targets)
        """
        self.threshold = threshold

    def _effective_threshold(self, target_text: str) -> float:
        if len((target_text or "").strip()) > self.LONG_TARGET_LEN:
            return self.LONG_TARGET_THRESHOLD
        return self.threshold
    
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
        element_text = (element.text or "").lower().strip()
        # Use element + parent text (product cards often have title in parent/children)
        parent_text = (element.parent_text or "").lower().strip()
        # For inputs, include placeholder and aria-label (e.g. "Search" matches placeholder "Search products")
        placeholder = (element.attributes.get("placeholder") or "").lower().strip()
        aria_label = (element.attributes.get("aria_label") or "").lower().strip()
        combined_text = (element_text + " " + parent_text + " " + placeholder + " " + aria_label).strip()[:600]
        if not combined_text:
            combined_text = element_text
        
        # 1. EXACT MATCH (highest weight)
        if element_text == target_lower:
            score += self.WEIGHT_EXACT_MATCH
            logger.debug(f"Exact match bonus: {self.WEIGHT_EXACT_MATCH}")
        
        # 2a. Substring dominance: target in element text (product title in DOM may be truncated)
        if target_lower and combined_text and target_lower in combined_text:
            score += 0.5
            logger.debug("Substring dominance: target in element/parent/placeholder/aria +0.5")
        elif target_lower and element_text and target_lower in element_text:
            score += 0.5
            logger.debug("Substring dominance: target in element text +0.5")

        # 2b. Placeholder/aria contains target (e.g. "Search" in placeholder "Search products")
        if target_lower and (target_lower in placeholder or target_lower in aria_label):
            score += self.WEIGHT_SUBSTRING_MATCH
            logger.debug(f"Target in placeholder/aria: +{self.WEIGHT_SUBSTRING_MATCH}")

        # 2c. SUBSTRING / CONTAINS (for long product names; page often shows truncated)
        if len(target_lower) >= self.MIN_SUBSTRING_LEN or len(combined_text) >= self.MIN_SUBSTRING_LEN:
            if target_lower in combined_text:
                score += self.WEIGHT_SUBSTRING_MATCH
                logger.debug(f"Target in element/parent: +{self.WEIGHT_SUBSTRING_MATCH}")
            elif combined_text in target_lower:
                score += self.WEIGHT_SUBSTRING_MATCH
                logger.debug(f"Element/parent in target: +{self.WEIGHT_SUBSTRING_MATCH}")
            else:
                # Substantial overlap: first N chars of target in combined (truncated product name)
                n = min(len(target_lower), len(combined_text), 80)
                if n >= self.MIN_SUBSTRING_LEN and (target_lower[:n] in combined_text or combined_text[:n] in target_lower):
                    score += self.WEIGHT_SUBSTRING_MATCH * 0.8
                    logger.debug(f"Substring overlap: +{self.WEIGHT_SUBSTRING_MATCH * 0.8}")
        
        # 3. KEYWORD OVERLAP (e.g. "LG", "5 Star", "1.5", "Split AC", "Gold Fin", "2025")
        target_tokens = _significant_tokens(target_text)
        if target_tokens:
            combined_tokens = set(_significant_tokens(combined_text))
            matches = sum(1 for t in target_tokens if t in combined_tokens)
            ratio = matches / len(target_tokens)
            score += ratio * self.WEIGHT_KEYWORD_OVERLAP
            logger.debug(f"Keyword overlap {matches}/{len(target_tokens)}: +{ratio * self.WEIGHT_KEYWORD_OVERLAP}")
        
        # 4. SEMANTIC SIMILARITY (use combined text so parent helps)
        text_sim = text_similarity(combined_text, target_text)
        score += text_sim * self.WEIGHT_SEMANTIC_SIMILARITY
        logger.debug(f"Text similarity score: {text_sim * self.WEIGHT_SEMANTIC_SIMILARITY}")
        
        # 6. ROLE MATCH
        if element.role in ["button", "link"]:
            score += self.WEIGHT_ROLE_MATCH
            logger.debug(f"Role match bonus: {self.WEIGHT_ROLE_MATCH}")
        
        # 7. ARIA LABEL MATCH
        aria_label = element.attributes.get("aria_label", "")
        if aria_label:
            aria_sim = text_similarity(aria_label, target_text)
            score += aria_sim * self.WEIGHT_ARIA_LABEL
            logger.debug(f"Aria label score: {aria_sim * self.WEIGHT_ARIA_LABEL}")
        
        # 8. VISIBILITY (should always be true after filtering)
        if element.visible:
            score += self.WEIGHT_VISIBILITY
        
        # 9. POSITION BIAS (prefer elements in upper part of page)
        if element.bounding_box:
            if element.bounding_box.y < 800:
                score += self.WEIGHT_POSITION_BIAS
                logger.debug(f"Position bias bonus: {self.WEIGHT_POSITION_BIAS}")
        
        # 10. CONTAINER CONTEXT
        if region_context and element.container:
            if region_context.lower() in element.container.lower():
                score += self.WEIGHT_CONTAINER_CONTEXT
                logger.debug(f"Container context bonus: {self.WEIGHT_CONTAINER_CONTEXT}")
        
        # 11. HISTORICAL SUCCESS (bonus, not part of base weights)
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
        # For long targets (e.g. product names), use a lower fallback threshold if none pass
        fallback_threshold = 0.40
        use_fallback = len((target_text or "").strip()) > 50
        effective_threshold = self._effective_threshold(target_text)
        
        scored_all: List[Tuple[float, DOMElement]] = []
        for element in elements:
            historical_success = False
            if history_lookup:
                element_key = f"{element.tag}_{element.text}_{element.attributes.get('id', '')}"
                historical_success = history_lookup.get(element_key, False)
            score = self.score_element(
                element, target_text, region_context, historical_success
            )
            scored_all.append((score, element))
            if score >= self.threshold:
                logger.debug(f"Element '{element.display_name}' scored {score:.3f}")
        
        scored_all.sort(key=lambda x: x[0], reverse=True)
        scored_elements = [(s, e) for s, e in scored_all if s >= effective_threshold]

        # Long target fallback: if no one passed, accept best candidate above fallback_threshold
        if not scored_elements and use_fallback and scored_all and scored_all[0][0] >= fallback_threshold:
            best_score, best_elem = scored_all[0]
            scored_elements = [(best_score, best_elem)]
            logger.info(
                f"Long target: no element above {self.threshold}; using best match "
                f"'{best_elem.display_name[:50]}...' with score {best_score:.3f} (>= {fallback_threshold})"
            )
        # Few-candidates fallback: e.g. 1–2 inputs (Search, Pincode) – use best if score >= 0.35
        if not scored_elements and len(elements) <= 5 and scored_all and scored_all[0][0] >= fallback_threshold:
            best_score, best_elem = scored_all[0]
            scored_elements = [(best_score, best_elem)]
            logger.info(
                f"Few candidates ({len(elements)}): using best match '{best_elem.display_name[:50]}' "
                f"with score {best_score:.3f} (>= {fallback_threshold})"
            )
        
        logger.info(
            "Ranked %d/%d elements above threshold %s",
            len(scored_elements), len(elements), effective_threshold
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
