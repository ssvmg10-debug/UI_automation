"""
NavItem component: link or button inside nav/header/menu, often with short label.
"""
from typing import List
from playwright.async_api import Page
import logging

from .base import DetectedComponent, ComponentType

logger = logging.getLogger(__name__)

NAV_SELECTORS = "nav a, [role='navigation'] a, header a, [class*='nav'] a, [class*='menu'] a"


async def extract_nav_items(page: Page, max_items: int = 80) -> List[DetectedComponent]:
    """Extract navigation links (nav, header, menu)."""
    results: List[DetectedComponent] = []
    try:
        locators = page.locator(NAV_SELECTORS)
        n = await locators.count()
        for i in range(min(n, max_items)):
            try:
                el = locators.nth(i)
                if not await el.is_visible():
                    continue
                text = (await el.text_content()) or ""
                text = text.strip()
                if not text or len(text) > 80:
                    continue
                bbox = await el.bounding_box()
                comp = DetectedComponent(
                    component_type=ComponentType.NAV_ITEM,
                    text=text,
                    full_text=text,
                    locator=el,
                    bbox={"x": bbox["x"], "y": bbox["y"], "width": bbox["width"], "height": bbox["height"]} if bbox else None,
                )
                results.append(comp)
            except Exception as e:
                logger.debug("Nav item skip: %s", e)
    except Exception as e:
        logger.warning("Nav item extraction failed: %s", e)
    return results
