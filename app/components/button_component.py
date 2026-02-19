"""
Button component: button, [role=button], or a that looks like a button.
"""
from typing import List
from playwright.async_api import Page
import logging

from .base import DetectedComponent, ComponentType

logger = logging.getLogger(__name__)

BUTTON_SELECTORS = "button, [role='button'], a[class*='btn'], input[type='submit'], input[type='button']"


async def extract_buttons(page: Page, max_buttons: int = 100) -> List[DetectedComponent]:
    """Extract button-like components."""
    results: List[DetectedComponent] = []
    try:
        locators = page.locator(BUTTON_SELECTORS)
        n = await locators.count()
        for i in range(min(n, max_buttons)):
            try:
                el = locators.nth(i)
                if not await el.is_visible():
                    continue
                text = (await el.text_content()) or ""
                text = (text or await el.get_attribute("aria-label") or "").strip()
                if len(text) > 120:
                    text = text[:117] + "..."
                bbox = await el.bounding_box()
                comp = DetectedComponent(
                    component_type=ComponentType.BUTTON,
                    text=text,
                    full_text=text,
                    locator=el,
                    bbox={"x": bbox["x"], "y": bbox["y"], "width": bbox["width"], "height": bbox["height"]} if bbox else None,
                )
                results.append(comp)
            except Exception as e:
                logger.debug("Button skip: %s", e)
    except Exception as e:
        logger.warning("Button extraction failed: %s", e)
    return results
