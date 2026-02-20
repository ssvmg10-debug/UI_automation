"""
Strict input resolver for TYPE actions.
Deterministic: no threshold guesswork; single input => use it; else match by placeholder/aria.
"""
from playwright.async_api import Page
from typing import Optional, Any
import logging

logger = logging.getLogger(__name__)


async def resolve_input(page: Page, target: str) -> Optional[Any]:
    """
    Resolve the input field for a given target label (e.g. "Search", "Pincode").
    - If exactly one visible input, return it.
    - Else find input whose placeholder or aria-label contains target (case-insensitive).
    Returns Playwright Locator or None.
    """
    inputs = page.locator("input:visible, textarea:visible")
    count = await inputs.count()
    if count == 0:
        return None
    if count == 1:
        logger.info("[INPUT_RESOLVER] Single visible input, using it")
        return inputs.first

    target_lower = target.lower().strip()
    for i in range(count):
        loc = inputs.nth(i)
        try:
            placeholder = (await loc.get_attribute("placeholder")) or ""
            aria = (await loc.get_attribute("aria-label")) or ""
            combined = (placeholder + " " + aria).lower()
            if target_lower in combined:
                logger.info("[INPUT_RESOLVER] Matched by placeholder/aria: %s", combined[:50])
                return loc
        except Exception:
            continue
    return None
