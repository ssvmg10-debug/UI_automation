"""
Wait utilities: call after every click and navigation for page readiness.
"""
from playwright.async_api import Page
import logging

logger = logging.getLogger(__name__)


async def wait_for_page_ready(page: Page, timeout_ms: int = 15000) -> None:
    """Wait for network idle and domcontentloaded."""
    try:
        await page.wait_for_load_state("domcontentloaded", timeout=timeout_ms)
    except Exception as e:
        logger.debug("domcontentloaded: %s", e)
    try:
        await page.wait_for_load_state("networkidle", timeout=min(8000, timeout_ms))
    except Exception as e:
        logger.debug("networkidle: %s", e)
