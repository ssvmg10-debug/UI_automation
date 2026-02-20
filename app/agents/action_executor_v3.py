"""
Action Executor V3 - SAM-V3 hybrid engine.
Uses SmartLocatorV3 (DOM + optional Vision + Semantic) for all actions.
Integrates flow_handlers for delivery, checkboxes, search.
OPTIMIZED: Smart overlay handling and behavioral simulation.
"""
from playwright.async_api import Page
from typing import Optional
import asyncio
import logging

from app.locator_engine_v3.action_resolver_v3 import ActionResolverV3
from app.core.outcome_validator import OutcomeValidator
from app.core.action_executor import ActionResult
from app.core.flow_handlers import select_delivery, click_all_checkboxes
from app.core.smart_interaction_utils import (
    smart_click_with_overlay_handling,
    smart_wait_for_element,
    behavioral_hover,
    safe_type_with_focus,
    force_click_with_js
)

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
            
            # Clear DOM cache after navigation (new page = new DOM)
            if hasattr(self.resolver.locator, 'dom') and hasattr(self.resolver.locator.dom, 'clear_cache'):
                self.resolver.locator.dom.clear_cache()
            
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
        
        # Use smart click with overlay handling
        try:
            # Try behavioral hover first (expands dropdowns, shows tooltips)
            await behavioral_hover(page, locator)
            
            # Smart click with automatic overlay dismissal and retries
            success = await smart_click_with_overlay_handling(page, locator, max_retries=3)
            
            if not success:
                # Fallback to JS click
                logger.info("[EXECUTOR_V3] Fallback to JS click")
                success = await force_click_with_js(page, locator)
            
            if success:
                await asyncio.sleep(wait_after)
                after = await self.validator.capture_state(page)
                if self.validator.validate_transition(before, after):
                    return ActionResult(success=True, before_state=before, after_state=after)
                return ActionResult(success=True, before_state=before, after_state=after)  # lenient
            else:
                return ActionResult(success=False, error=f"Click failed after retries", before_state=before)
                
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
        
        # Use safe typing with focus
        success = await safe_type_with_focus(page, locator, text_to_type or "", clear_first=clear_first)
        
        if success:
            after = await self.validator.capture_state(page)
            return ActionResult(success=True, before_state=before, after_state=after)
        else:
            return ActionResult(success=False, error="Type operation failed", before_state=before)

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

    async def wait_for_element(self, page: Page, target_text: str, timeout: float = 30.0) -> ActionResult:
        """Wait for element to appear with smart overlay handling."""
        logger.info("[EXECUTOR_V3] WAIT for: '%s'", (target_text or "")[:50])
        
        # Use smart wait with overlay dismissal
        locator = await smart_wait_for_element(page, target_text or "", timeout=int(timeout * 1000))
        
        if locator:
            return ActionResult(success=True)
        return ActionResult(success=False, error=f"Timeout waiting for '{target_text}'")
