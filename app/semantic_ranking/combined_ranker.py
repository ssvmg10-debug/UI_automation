"""
Semantic Element Ranking Model (Phase 2).
Combined score: semantic * 0.5 + visual * 0.2 + structural * 0.2 + component * 0.1.
Long-text: fuzzy + subsequence detection.
"""
from typing import List, Tuple, Optional, Any
from difflib import SequenceMatcher
import re
import logging

from .embedding_scorer import semantic_similarity

logger = logging.getLogger(__name__)

# Weights (sum = 1.0)
W_SEMANTIC = 0.5
W_VISUAL = 0.2
W_STRUCTURAL = 0.2
W_COMPONENT = 0.1

# Action -> preferred component types (for component_score)
ACTION_COMPONENT_PREF: dict = {
    "click": ["button", "nav_item", "product_card", "link"],
    "type": ["form_input", "search_overlay"],
    "select": ["radio_group", "form_input"],
}


def _fuzzy_subsequence(needle: str, haystack: str) -> float:
    """Score how well needle appears as subsequence in haystack (order preserved)."""
    if not needle or not haystack:
        return 0.0
    n, h = needle.lower(), haystack.lower()
    i, j, match = 0, 0, 0
    for c in n:
        while j < len(h):
            if h[j] == c:
                match += 1
                j += 1
                break
            j += 1
    return match / len(n) if n else 0.0


def _text_sim(a: str, b: str) -> float:
    return SequenceMatcher(None, (a or "").lower(), (b or "").lower()).ratio()


def _visual_score(bbox: Optional[dict], viewport_height: float = 900) -> float:
    """Prefer above fold, reasonable size."""
    if not bbox:
        return 0.5
    y = bbox.get("y", 0)
    w = bbox.get("width", 0)
    h = bbox.get("height", 0)
    above_fold = 1.0 - min(1.0, y / viewport_height) * 0.5
    size_ok = min(1.0, (w * h) / 1000) * 0.5
    return above_fold + size_ok


def _structural_score(tag: str, role: Optional[str], action: str) -> float:
    """Prefer tag/role that matches action."""
    if action == "click":
        if tag in ("button", "a") or role in ("button", "link"):
            return 1.0
        return 0.3
    if action == "type":
        if tag in ("input", "textarea") or role == "textbox":
            return 1.0
        return 0.2
    if action == "select":
        if tag == "select" or role in ("listbox", "radio"):
            return 1.0
        return 0.3
    return 0.5


def _component_score(component_type: Optional[str], action: str) -> float:
    """Prefer component type that matches action."""
    preferred = ACTION_COMPONENT_PREF.get(action.lower(), [])
    if not component_type:
        return 0.5
    ct = component_type.lower().replace("_", " ")
    for p in preferred:
        if p.replace("_", " ") in ct or ct in p.replace("_", " "):
            return 1.0
    return 0.3


def score_element_semantic(
    text: str,
    full_text: str,
    target: str,
    bbox: Optional[dict] = None,
    tag: str = "",
    role: Optional[str] = None,
    component_type: Optional[str] = None,
    action: str = "click",
) -> float:
    """
    Combined score for one element.
    Uses semantic (embedding or fuzzy) + visual + structural + component.
    """
    combined = (text or "") + " " + (full_text or "")
    combined = combined.strip()[:600]
    target = (target or "").strip()

    # Long-text: subsequence + fuzzy
    if len(target) > 40:
        sub = _fuzzy_subsequence(target, combined)
        fuzzy = _text_sim(target[:80], combined[:200])
        semantic = 0.6 * sub + 0.4 * fuzzy
        if target.lower() in combined.lower():
            semantic = max(semantic, 0.9)
    else:
        semantic = semantic_similarity(combined, target)

    visual = _visual_score(bbox)
    structural = _structural_score(tag, role, action)
    comp = _component_score(component_type, action)

    total = W_SEMANTIC * semantic + W_VISUAL * visual + W_STRUCTURAL * structural + W_COMPONENT * comp
    return min(1.0, total)


def rank_components(
    components: List[Any],
    target: str,
    action: str = "click",
    text_attr: str = "text",
    full_text_attr: str = "full_text",
    top_n: int = 5,
) -> List[Tuple[float, Any]]:
    """
    Rank DetectedComponent (or similar) by combined score.
    Returns list of (score, component) sorted descending.
    """
    scored: List[Tuple[float, Any]] = []
    for c in components:
        text = getattr(c, text_attr, None) or ""
        full = getattr(c, full_text_attr, None) or text
        bbox = getattr(c, "bbox", None)
        ct = getattr(c, "component_type", None)
        if hasattr(ct, "value"):
            ct = ct.value
        tag = getattr(c, "tag", "") or "div"
        role = getattr(c, "role", None)
        s = score_element_semantic(
            text=text,
            full_text=full,
            target=target,
            bbox=bbox,
            tag=tag,
            role=role,
            component_type=ct,
            action=action,
        )
        scored.append((s, c))
    scored.sort(key=lambda x: x[0], reverse=True)
    return scored[:top_n]
