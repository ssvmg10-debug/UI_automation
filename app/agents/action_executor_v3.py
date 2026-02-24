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
import re

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

    def _is_add_to_cart_flow(self, target: str) -> bool:
        """Detect Add to Cart / Add to Bag so we wait for cart to update before proceeding."""
        t = (target or "").lower()
        return "add to cart" in t or "add to bag" in t or "add to basket" in t

    def _is_checkout_flow(self, target: str) -> bool:
        """Detect Checkout button so we wait for the checkout page (Contact Information) before proceeding."""
        t = (target or "").lower().strip()
        return t == "checkout" or t == "proceed to checkout" or "checkout" in t and "express" not in t

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
                # Add-to-cart often updates via AJAX; wait for cart to update before next step (e.g. Checkout)
                if self._is_add_to_cart_flow(target):
                    wait_cart = 2.5
                    logger.info("[EXECUTOR_V3] Add-to-cart detected: waiting %.1fs for cart to update", wait_cart)
                    await asyncio.sleep(wait_cart)
                    try:
                        await page.wait_for_load_state("networkidle", timeout=3000)
                    except Exception:
                        pass
                # After clicking Checkout, wait for the checkout page (Contact Information) to load before proceeding
                if self._is_checkout_flow(target):
                    logger.info("[EXECUTOR_V3] Checkout click detected: waiting for checkout page (Contact Information)")
                    contact_loc = await smart_wait_for_element(page, "Contact Information", timeout=20000, check_interval=800)
                    if contact_loc:
                        logger.info("[EXECUTOR_V3] Checkout page loaded: Contact Information visible")
                    else:
                        logger.warning("[EXECUTOR_V3] Contact Information not found within 20s; proceeding anyway")
                await asyncio.sleep(wait_after)
                after = await self.validator.capture_state(page)
                # Clear DOM cache on navigation (new page = fresh scan for inputs/clickables)
                if before and after and getattr(before, "url", None) != getattr(after, "url", None):
                    if hasattr(self.resolver.locator, "dom") and hasattr(self.resolver.locator.dom, "clear_cache"):
                        self.resolver.locator.dom.clear_cache()
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
                    await search_btn.click(timeout=10000)
                    await asyncio.sleep(1)
                inp = await self.resolver.resolve_input(page, "search")
                if inp:
                    await inp.fill(text_to_type or "")
                    await inp.press("Enter")
                    await asyncio.sleep(0.5)
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
            # Fallback: try common select/combobox patterns by label/role/text before failing.
            target_text = target or ""
            try:
                target_pattern = re.compile(re.escape(target_text), re.I) if target_text else None
            except re.error:
                target_pattern = None

            # 1) Try standard label-based lookup (e.g. "State", "Country/Region").
            try:
                label_loc = page.get_by_label(target_text, exact=False)
                if await label_loc.count() > 0:
                    field = label_loc.first
                    # Prefer select-style interaction when possible.
                    try:
                        await field.select_option(value)
                    except Exception:
                        # If it's not a <select>, try filling, or inner select/input.
                        try:
                            await field.fill(value)
                        except Exception:
                            try:
                                handle = await field.element_handle()
                                if handle:
                                    inner_select = handle.locator("select").first
                                    if await inner_select.is_visible():
                                        await inner_select.select_option(value)
                                    else:
                                        inner_input = handle.locator("input, textarea").first
                                        if await inner_input.is_visible():
                                            await inner_input.fill(value)
                            except Exception:
                                pass
                    after = await self.validator.capture_state(page)
                    return ActionResult(success=True, before_state=before, after_state=after)
            except Exception:
                # Swallow and continue to other fallbacks.
                pass

            # 2) Try ARIA combobox by role/name (for custom dropdowns).
            if target_pattern:
                try:
                    combo = page.get_by_role("combobox", name=target_pattern).first
                    if await combo.is_visible():
                        try:
                            await combo.select_option(value)
                        except Exception:
                            await combo.fill(value)
                        after = await self.validator.capture_state(page)
                        return ActionResult(success=True, before_state=before, after_state=after)
                except Exception:
                    pass

            # 3) As a last resort, click a visible element containing the target text,
            #    then click an option containing the value text.
            try:
                text_loc = page.get_by_text(target_text, exact=False).first
                if await text_loc.is_visible():
                    await text_loc.click(timeout=3000)
                    option_loc = page.get_by_text(value or "", exact=False).first
                    if await option_loc.is_visible():
                        await option_loc.click(timeout=3000)
                        after = await self.validator.capture_state(page)
                        return ActionResult(success=True, before_state=before, after_state=after)
            except Exception:
                pass

            return ActionResult(success=False, error=f"Unable to locate: {target}", before_state=before)

        # Locator found: either native <select> (select_option) or custom dropdown (click to open, then click option)
        try:
            tag_name = await locator.evaluate("el => (el && el.tagName) ? el.tagName.toLowerCase() : ''")
            if tag_name == "select":
                await locator.select_option(value, timeout=15000)
                await asyncio.sleep(0.2)
                after = await self.validator.capture_state(page)
                return ActionResult(success=True, before_state=before, after_state=after)
            # Custom dropdown: click to open, then click the option with the value text
            await locator.click(timeout=15000)
            await asyncio.sleep(0.4)
            option_value = (value or "").strip()
            if option_value:
                option_loc = page.get_by_role("option", name=re.compile(re.escape(option_value), re.I)).first
                try:
                    if await option_loc.is_visible():
                        await option_loc.click(timeout=5000)
                    else:
                        option_loc = page.get_by_text(option_value, exact=False).first
                        if await option_loc.is_visible():
                            await option_loc.click(timeout=5000)
                except Exception:
                    option_loc = page.get_by_text(option_value, exact=False).first
                    if await option_loc.is_visible():
                        await option_loc.click(timeout=5000)
            await asyncio.sleep(0.2)
            after = await self.validator.capture_state(page)
            return ActionResult(success=True, before_state=before, after_state=after)
        except Exception as e:
            return ActionResult(success=False, error=str(e), before_state=before)

    async def wait_for_element(self, page: Page, target_text: str, timeout: float = 60.0) -> ActionResult:
        """Wait for element to appear. Supports alternatives: 'Contact Information or Email' tries each until one is found."""
        raw = (target_text or "").strip()
        logger.info("[EXECUTOR_V3] WAIT for: '%s'", raw[:60])
        timeout_ms = int(timeout * 1000)
        # Support "X or Y" so checkout can wait for "Contact Information" or "Email" (whichever appears first)
        parts = [p.strip() for p in raw.split(" or ") if p.strip()]
        if not parts:
            parts = [raw]
        per_part_ms = max(5000, timeout_ms // len(parts))
        for i, part in enumerate(parts):
            locator = await smart_wait_for_element(page, part, timeout=per_part_ms)
            if locator:
                return ActionResult(success=True)
        return ActionResult(success=False, error=f"Timeout waiting for '{raw}'")
