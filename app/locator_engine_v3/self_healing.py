"""
Self-Healing V3 - Fallback when primary match fails.
Try parent/sibling with basic relevance check.
"""
from playwright.async_api import Page
from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class SelfHealingV3:
    """Heal failed locator by trying parent or sibling."""

    async def heal(
        self,
        page: Page,
        target: str,
        last_results: List[Dict[str, Any]],
    ):
        """Try parent or sibling of top candidates. Validate before returning."""
        if not last_results:
            return None

        target_lower = (target or "").lower()

        for item in last_results[:3]:
            try:
                loc = item.get("locator")
                if not loc:
                    continue
                # Try parent
                parent = loc.locator("xpath=..")
                if await parent.count() > 0:
                    p = parent.first
                    if await p.is_visible():
                        text = (await p.inner_text(timeout=500)).strip().lower()
                        if target_lower in text or any(w in text for w in target_lower.split() if len(w) > 2):
                            logger.info("[SELF_HEAL_V3] Using parent")
                            return p
            except Exception:
                continue

        for item in last_results[:3]:
            try:
                loc = item.get("locator")
                if not loc:
                    continue
                sib = loc.locator("xpath=following-sibling::*[1]")
                if await sib.count() > 0:
                    s = sib.first
                    if await s.is_visible():
                        logger.info("[SELF_HEAL_V3] Using sibling")
                        return s
            except Exception:
                continue

        return None
