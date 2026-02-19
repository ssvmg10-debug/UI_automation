"""
Modal component: dialog, overlay, [role=dialog], often with close/primary action.
"""
from typing import List
from playwright.async_api import Page
import logging

from .base import DetectedComponent, ComponentType

logger = logging.getLogger(__name__)

MODAL_SELECTORS = "[role='dialog'], .modal, [class*='modal'], [class*='overlay'], dialog"


async def extract_modals(page: Page, max_modals: int = 5) -> List[DetectedComponent]:
    """Extract visible modal/dialog components (usually 0–2 on page)."""
    results: List[DetectedComponent] = []
    try:
        locators = page.locator(MODAL_SELECTORS)
        n = await locators.count()
        for i in range(min(n, max_modals)):
            try:
                el = locators.nth(i)
                if not await el.is_visible():
                    continue
                text = (await el.text_content()) or ""
                text = text.strip()[:200]
                bbox = await el.bounding_box()
                comp = DetectedComponent(
                    component_type=ComponentType.MODAL,
                    text=text or "Modal",
                    full_text=text,
                    locator=el,
                    bbox={"x": bbox["x"], "y": bbox["y"], "width": bbox["width"], "height": bbox["height"]} if bbox else None,
                )
                results.append(comp)
            except Exception as e:
                logger.debug("Modal skip: %s", e)
    except Exception as e:
        logger.warning("Modal extraction failed: %s", e)
    return results
