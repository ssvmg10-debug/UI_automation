"""
Action Resolver V3 - Resolves CLICK, TYPE, SELECT via SmartLocatorV3.
"""
from playwright.async_api import Page
from typing import Optional, Any
import logging

from app.locator_engine_v3.smart_locator import SmartLocatorV3

logger = logging.getLogger(__name__)


class ActionResolverV3:
    """Resolve actions using SmartLocatorV3."""

    def __init__(self):
        self.locator = SmartLocatorV3()

    async def resolve_click(self, page: Page, target: str):
        """Resolve CLICK target to locator."""
        return await self.locator.locate_click(page, target)

    async def resolve_input(self, page: Page, target: str):
        """Resolve TYPE target (input field) to locator."""
        return await self.locator.locate_input(page, target)

    async def resolve_select(self, page: Page, target: str):
        """Resolve SELECT target - use click locator for dropdown trigger."""
        return await self.locator.locate_click(page, target)
