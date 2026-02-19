"""
State shortcuts: (page_type, target) -> URL or skip.
Enables "from listing page, target 'Split AC' -> known URL" without full fragment match.
"""
from typing import Optional, Dict, Tuple, List
import logging

logger = logging.getLogger(__name__)

# (page_type, target_lower_substring) -> path or full URL pattern
STATE_SHORTCUTS: List[Tuple[str, str, str]] = [
    ("listing", "split air conditioner", "/air-conditioners/split-air-conditioners/"),
    ("listing", "water purifier", "/water-purifiers/"),
    ("homepage", "air solutions", "/air-conditioners/"),
    ("homepage", "split ac", "/air-conditioners/split-air-conditioners/"),
]


class StateShortcutRegistry:
    """Resolve (current_page_type, target) to URL path for navigation shortcut."""

    def __init__(self, shortcuts: Optional[List[Tuple[str, str, str]]] = None):
        self.shortcuts = shortcuts or STATE_SHORTCUTS

    def resolve(self, base_url: str, page_type: str, target: str) -> Optional[str]:
        """If (page_type, target) matches a known shortcut, return full URL."""
        target_lower = (target or "").lower().strip()
        page_type_lower = (page_type or "").lower()
        base = base_url.rstrip("/")
        if "://" in base:
            base_domain = base.split("/")[0] + "//" + base.split("/")[2]
        else:
            base_domain = base
        for ptype, key, path in self.shortcuts:
            if ptype in page_type_lower and key in target_lower:
                return base_domain + path
        return None
