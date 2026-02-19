"""
Flow-specific handlers: delivery option (label/radio), checkboxes.
"""
from playwright.async_api import Page
from typing import Optional
import logging

logger = logging.getLogger(__name__)


async def select_delivery(page: Page, option_text: str) -> bool:
    """
    Delivery selection is usually label/radio, not a SELECT dropdown.
    Click the visible label whose text contains option_text (e.g. "Free Delivery").
    """
    try:
        labels = page.locator("label:visible")
        n = await labels.count()
        option_lower = option_text.lower()
        for i in range(n):
            label = labels.nth(i)
            text = (await label.text_content()) or ""
            if option_lower in text.lower():
                await label.click(timeout=3000)
                logger.info("[FLOW] Selected delivery: %s", text.strip()[:50])
                return True
        # Fallback: radio by value or name
        radios = page.locator("input[type='radio']:visible")
        nr = await radios.count()
        for i in range(nr):
            r = radios.nth(i)
            val = (await r.get_attribute("value")) or ""
            if option_lower in val.lower():
                await r.click(timeout=3000)
                return True
        return False
    except Exception as e:
        logger.warning("[FLOW] select_delivery failed: %s", e)
        return False


async def click_all_checkboxes(page: Page) -> bool:
    """Check all visible checkboxes that are not already checked (e.g. T&C, consent)."""
    try:
        boxes = page.locator("input[type='checkbox']:visible")
        n = await boxes.count()
        clicked = 0
        for i in range(n):
            box = boxes.nth(i)
            if not await box.is_checked():
                await box.check(timeout=2000)
                clicked += 1
        logger.info("[FLOW] Checked %d checkbox(es)", clicked)
        return True
    except Exception as e:
        logger.warning("[FLOW] click_all_checkboxes failed: %s", e)
        return False
