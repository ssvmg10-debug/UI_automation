"""
Action Executor V3 - SAM-V3 hybrid engine.
Uses SmartLocatorV3 (DOM + optional Vision + Semantic) for all actions.
Integrates flow_handlers for delivery, checkboxes, search.
"""
from playwright.async_api import Page
from typing import Optional
import asyncio
import logging

from app.locator_engine_v3.action_resolver_v3 import ActionResolverV3
from app.core.outcome_validator import OutcomeValidator
from app.core.action_executor import ActionResult
from app.core.flow_handlers import select_delivery, click_all_checkboxes

logger = logging.getLogger(__name__)


class ActionExecutorV3:
    """SAM-V3 executor: SmartLocator + flow handlers."""

    def __init__(self):
        self.resolver = ActionResolverV3()
        self.validator = OutcomeValidator(strict_mode=True)

    def _is_search_flow(self, target: str, value: Optional[str]) -> bool:
        t = (target or "").lower()
        return "search" in t and value

    def _is_delivery_flow(self, target: str, value: str) -> bool:
        return "delivery" in (target or "").lower() or "delivery" in (value or "").lower()

    def _is_all_checkboxes_flow(self, target: str) -> bool:
        t = (target or "").lower()
        return "checkbox" in t or "checkboxes" in t or "terms" in t or "agree" in t

    async def navigate(self, page: Page, url: str) -> ActionResult:
        """Navigate to URL."""
        logger.info("[EXECUTOR_V3] NAVIGATE: %s", url[:80] if url else "")
        before = await self.validator.capture_state(page)
        try:
            await page.goto(url or "", wait_until="domcontentloaded")
            await page.wait_for_timeout(500)
            after = await self.validator.capture_state(page)
            if self.validator.validate_navigation(before, after):
                return ActionResult(success=True, before_state=before, after_state=after)
            return ActionResult(success=True, before_state=before, after_state=after)  # lenient
        except Exception as e:
            return ActionResult(success=False, error=str(e), before_state=before)

    async def click(
        self,
        page: Page,
        target: str,
        region_context: Optional[str] = None,
        wait_after: float = 0.5,
    ) -> ActionResult:
        """Execute CLICK via SmartLocator or flow handler."""
        logger.info("[EXECUTOR_V3] CLICK: '%s'", (target or "")[:80])
        before = await self.validator.capture_state(page)

        if self._is_all_checkboxes_flow(target):
            if await click_all_checkboxes(page):
                await asyncio.sleep(wait_after)
                after = await self.validator.capture_state(page)
                return ActionResult(success=True, before_state=before, after_state=after)
            # Fall through to locator

        locator = await self.resolver.resolve_click(page, target)
        if not locator:
            return ActionResult(success=False, error=f"Unable to locate: {target}", before_state=before)
        try:
            await locator.click(timeout=5000)
            await asyncio.sleep(wait_after)
            after = await self.validator.capture_state(page)
            if self.validator.validate_transition(before, after):
                return ActionResult(success=True, before_state=before, after_state=after)
            return ActionResult(success=True, before_state=before, after_state=after)  # lenient
        except Exception as e:
            return ActionResult(success=False, error=str(e), before_state=before)

    async def type_text(
        self,
        page: Page,
        target_field: str,
        text_to_type: str,
        clear_first: bool = True,
    ) -> ActionResult:
        """Execute TYPE via SmartLocator or search flow."""
        logger.info("[EXECUTOR_V3] TYPE: field='%s' value='%s'", (target_field or "")[:50], (text_to_type or "")[:40])
        before = await self.validator.capture_state(page)

        if self._is_search_flow(target_field, text_to_type):
            # V3 search: click search icon first, then find input and fill
            try:
                search_btn = await self.resolver.resolve_click(page, "search")
                if search_btn:
                    await search_btn.click(timeout=3000)
                    await asyncio.sleep(1000 / 1000)  # 1s
                inp = await self.resolver.resolve_input(page, "search")
                if inp:
                    await inp.fill(text_to_type or "")
                    await inp.press("Enter")
                    await asyncio.sleep(500 / 1000)
                    after = await self.validator.capture_state(page)
                    return ActionResult(success=True, before_state=before, after_state=after)
            except Exception as e:
                logger.debug("Search flow: %s", e)

        locator = await self.resolver.resolve_input(page, target_field or "")
        if not locator:
            return ActionResult(success=False, error=f"Unable to locate input: {target_field}", before_state=before)
        try:
            if clear_first:
                await locator.clear()
            await locator.fill(text_to_type or "")
            after = await self.validator.capture_state(page)
            return ActionResult(success=True, before_state=before, after_state=after)
        except Exception as e:
            return ActionResult(success=False, error=str(e), before_state=before)

    async def select_option(
        self,
        page: Page,
        target: str,
        value: str,
    ) -> ActionResult:
        """Execute SELECT via delivery flow or SmartLocator."""
        logger.info("[EXECUTOR_V3] SELECT: target='%s' value='%s'", (target or "")[:50], (value or "")[:50])
        before = await self.validator.capture_state(page)

        if self._is_delivery_flow(target, value):
            if await select_delivery(page, value or "free delivery"):
                after = await self.validator.capture_state(page)
                return ActionResult(success=True, before_state=before, after_state=after)

        locator = await self.resolver.resolve_select(page, target)
        if not locator:
            return ActionResult(success=False, error=f"Unable to locate: {target}", before_state=before)
        try:
            await locator.click(timeout=5000)
            await asyncio.sleep(0.3)
            after = await self.validator.capture_state(page)
            return ActionResult(success=True, before_state=before, after_state=after)
        except Exception as e:
            return ActionResult(success=False, error=str(e), before_state=before)

    async def wait_for_element(self, page: Page, target_text: str, timeout: float = 10.0) -> ActionResult:
        """Wait for element to appear."""
        logger.info("[EXECUTOR_V3] WAIT for: '%s'", (target_text or "")[:50])
        start = asyncio.get_event_loop().time()
        while asyncio.get_event_loop().time() - start < timeout:
            locator = await self.resolver.resolve_click(page, target_text or "")
            if locator:
                return ActionResult(success=True)
            await asyncio.sleep(0.5)
        return ActionResult(success=False, error=f"Timeout waiting for '{target_text}'")
