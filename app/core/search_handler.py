"""
Composite search flow: click search icon (if any), resolve input, fill, Enter.
"""
from playwright.async_api import Page
from typing import Optional
import logging

from .input_resolver import resolve_input

logger = logging.getLogger(__name__)


async def handle_search(page: Page, query: str) -> bool:
    """
    Execute search flow: optional search icon click, then type in search input and press Enter.
    Returns True if search was performed successfully.
    """
    try:
        # Click search icon if present
        icon = page.locator("button[aria-label*='search'], [aria-label*='Search']").first
        if await icon.count() > 0:
            try:
                await icon.click(timeout=3000)
                await page.wait_for_timeout(1000)
            except Exception:
                pass

        input_field = await resolve_input(page, "search")
        if not input_field:
            return False

        await input_field.fill(query)
        await input_field.press("Enter")
        await page.wait_for_timeout(2000)
        logger.info("[SEARCH_HANDLER] Search submitted: %s", query[:50])
        return True
    except Exception as e:
        logger.warning("[SEARCH_HANDLER] Failed: %s", e)
        return False
