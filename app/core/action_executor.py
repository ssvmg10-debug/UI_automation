"""
Action executor - the deterministic engine that performs actions.
Uses Enterprise v2 action resolvers (component + semantic) when applicable, then legacy pipeline.
"""
from playwright.async_api import Page
from typing import Optional, Dict, Any
import logging
import asyncio

from .dom_extractor import DOMExtractor
from .element_filter import ElementFilter
from .element_ranker import ElementRanker
from .outcome_validator import OutcomeValidator, PageState
from .dom_model import DOMElement
from .product_extractor import resolve_product
from .input_resolver import resolve_input
from .search_handler import handle_search
from .flow_handlers import select_delivery, click_all_checkboxes
from .region_model import detect_regions, get_region_for_context

logger = logging.getLogger(__name__)

def _get_resolver_registry():
    try:
        from app.action_resolvers import ResolverRegistry
        return ResolverRegistry()
    except Exception:
        return None


class ActionResult:
    """Result of an action execution."""
    
    def __init__(
        self, 
        success: bool, 
        element: Optional[DOMElement] = None,
        before_state: Optional[PageState] = None,
        after_state: Optional[PageState] = None,
        error: Optional[str] = None,
        attempts: int = 1
    ):
        self.success = success
        self.element = element
        self.before_state = before_state
        self.after_state = after_state
        self.error = error
        self.attempts = attempts
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "success": self.success,
            "element": self.element.to_dict() if self.element else None,
            "before_state": self.before_state.to_dict() if self.before_state else None,
            "after_state": self.after_state.to_dict() if self.after_state else None,
            "error": self.error,
            "attempts": self.attempts
        }


class ActionExecutor:
    """
    Deterministic action execution engine.
    This is the ONLY layer allowed to interact with the browser DOM.
    """
    
    def __init__(
        self, 
        max_retries: int = 3,
        score_threshold: float = 0.65,
        use_v2_resolvers: bool = True,
    ):
        """
        Initialize executor.
        
        Args:
            max_retries: Maximum retry attempts per action
            score_threshold: Minimum element score threshold
            use_v2_resolvers: If True, try Enterprise v2 action resolvers first (component + semantic)
        """
        self.extractor = DOMExtractor()
        self.filter = ElementFilter()
        self.ranker = ElementRanker(threshold=score_threshold)
        self.validator = OutcomeValidator(strict_mode=True)
        self.max_retries = max_retries
        self.use_v2_resolvers = use_v2_resolvers
        self._resolver_registry = None
    
    def _is_product_flow(self, page: Page, target_text: str) -> bool:
        """Heuristic: product-like target or e-commerce product listing URL."""
        t = (target_text or "").lower()
        if "star" in t or "lg " in t or "split ac" in t or "model" in t:
            return True
        url = page.url.lower()
        if "air-conditioners" in url or "product" in url:
            return True
        return False

    def _is_all_checkboxes_flow(self, target_text: str) -> bool:
        t = (target_text or "").lower()
        return "all checkbox" in t or "checkboxes" in t or "terms and condition" in t or "agree" in t or "accept all" in t

    async def _generic_click(
        self,
        page: Page,
        target_text: str,
        region_context: Optional[str] = None,
        wait_after: float = 0.5,
        before_state: Optional[PageState] = None,
    ) -> ActionResult:
        """Extract (DOMElement, Locator) pairs, filter, rank, then click the locator directly (no get_by_text)."""
        before = before_state or await self.validator.capture_state(page)
        pairs = await self.extractor.extract_clickables(page)
        elements = [e for e, _ in pairs]
        logger.info("[EXECUTOR] Extracted %d clickable elements", len(elements))
        filtered_elements = self.filter.apply_standard_filters(elements, "CLICK")
        filtered_pairs = [(e, loc) for e, loc in pairs if e in filtered_elements]
        # Fallback: if no elements passed (e.g. footer links, short labels), relax empty-text filter
        if not filtered_pairs and elements:
            visible = self.filter.filter_by_visibility(elements)
            clickable = self.filter.filter_by_action_type(visible, "CLICK")
            relaxed = self.filter.filter_by_size(clickable)
            filtered_pairs = [(e, loc) for e, loc in pairs if e in relaxed]
            if filtered_pairs:
                logger.info("[EXECUTOR] Using relaxed filter: %d elements", len(filtered_pairs))
        if region_context and filtered_pairs:
            regions = detect_regions([e for e, _ in filtered_pairs])
            region_key = get_region_for_context(region_context)
            region_elements = regions.get(region_key) or []
            if region_elements:
                region_set = {id(ee) for ee in region_elements}
                filtered_pairs = [(e, loc) for e, loc in filtered_pairs if id(e) in region_set]
                logger.info("[EXECUTOR] Using region '%s' (%d elements)", region_key, len(filtered_pairs))
        if not filtered_pairs:
            return ActionResult(success=False, error="No clickable elements found matching filters", before_state=before)
        filtered_elements = [e for e, _ in filtered_pairs]
        ranked_elements = self.ranker.get_top_candidates(
            filtered_elements, target_text, top_n=self.max_retries, region_context=region_context
        )
        if not ranked_elements:
            return ActionResult(success=False, error=f"No elements scored above threshold for '{target_text}'", before_state=before)
        for attempt, element in enumerate(ranked_elements, 1):
            locator = next((loc for e, loc in filtered_pairs if e is element), None) or next(
                (loc for e, loc in filtered_pairs if e.text == element.text and e.tag == element.tag), None
            )
            if not locator:
                logger.warning("Attempt %d: no locator for element '%s'", attempt, element.display_name[:50])
                continue
            try:
                logger.info("Attempt %d/%d: Clicking element (locator) '%s'", attempt, len(ranked_elements), element.display_name[:50])
                await locator.click(timeout=5000)
                await asyncio.sleep(wait_after)
                after_state = await self.validator.capture_state(page)
                if self.validator.validate_transition(before, after_state):
                    logger.info("✓ Click successful: '%s'", element.display_name[:50])
                    return ActionResult(success=True, element=element, before_state=before, after_state=after_state, attempts=attempt)
            except Exception as e:
                logger.warning("Attempt %d failed: %s", attempt, e)
        return ActionResult(success=False, error=f"All {len(ranked_elements)} attempts failed for '{target_text}'", before_state=before, attempts=len(ranked_elements))

    async def click(
        self,
        page: Page,
        target_text: str,
        region_context: Optional[str] = None,
        wait_after: float = 0.5,
    ) -> ActionResult:
        """
        Execute click with action-specific pipeline: product → all checkboxes → generic.
        """
        logger.info("[EXECUTOR] CLICK action: target='%s'", (target_text or "")[:80])
        before_state = await self.validator.capture_state(page)

        # V2: Try action resolvers first (product click, nav, button)
        if self.use_v2_resolvers:
            registry = self._resolver_registry or _get_resolver_registry()
            if registry:
                self._resolver_registry = registry
                res = await registry.resolve(page, "CLICK", target_text, None)
                if res.success and res.locator:
                    try:
                        await res.locator.click(timeout=5000)
                        await asyncio.sleep(wait_after)
                        after_state = await self.validator.capture_state(page)
                        if self.validator.validate_transition(before_state, after_state):
                            logger.info("✓ Click successful (v2 resolver)")
                            return ActionResult(success=True, before_state=before_state, after_state=after_state)
                    except Exception as e:
                        logger.debug("V2 resolver click failed, falling back: %s", e)

        # PRODUCT FLOW: long product name or e-commerce product page
        if self._is_product_flow(page, target_text):
            product_locator = await resolve_product(page, target_text)
            if product_locator:
                try:
                    await product_locator.click(timeout=5000)
                    await asyncio.sleep(wait_after)
                    after_state = await self.validator.capture_state(page)
                    if self.validator.validate_transition(before_state, after_state):
                        logger.info("✓ Product click successful (product resolver)")
                        return ActionResult(success=True, before_state=before_state, after_state=after_state)
                except Exception as e:
                    logger.warning("Product click failed: %s", e)

        # ALL CHECKBOXES FLOW
        if self._is_all_checkboxes_flow(target_text):
            if await click_all_checkboxes(page):
                await asyncio.sleep(wait_after)
                after_state = await self.validator.capture_state(page)
                logger.info("✓ All checkboxes checked")
                return ActionResult(success=True, before_state=before_state, after_state=after_state)

        # NORMAL CLICK FLOW
        return await self._generic_click(page, target_text, region_context=region_context, wait_after=wait_after, before_state=before_state)
    
    async def type_text(
        self,
        page: Page,
        target_field: str,
        text_to_type: str,
        clear_first: bool = True,
    ) -> ActionResult:
        """
        Type text: composite search flow (if target is Search) else strict input resolver.
        """
        logger.info("[EXECUTOR] TYPE action: field='%s' value='%s'", (target_field or "")[:60], (text_to_type or "")[:40])
        before_state = await self.validator.capture_state(page)

        # V2: Try type/search resolvers first
        if self.use_v2_resolvers:
            registry = self._resolver_registry or _get_resolver_registry()
            if registry:
                self._resolver_registry = registry
                res = await registry.resolve(page, "TYPE", target_field or "", text_to_type)
                if res.success:
                    after_state = await self.validator.capture_state(page)
                    logger.info("✓ Type successful (v2 resolver)")
                    return ActionResult(success=True, before_state=before_state, after_state=after_state)

        # SEARCH FLOW: composite (icon + input + Enter)
        if (target_field or "").lower().strip() == "search":
            if await handle_search(page, text_to_type or ""):
                after_state = await self.validator.capture_state(page)
                logger.info("✓ Search flow completed")
                return ActionResult(success=True, before_state=before_state, after_state=after_state)

        # STRICT INPUT RESOLVER: single input or placeholder/aria match
        field_locator = await resolve_input(page, target_field or "")
        if field_locator:
            try:
                if clear_first:
                    await field_locator.clear()
                await field_locator.fill(text_to_type or "")
                after_state = await self.validator.capture_state(page)
                logger.info("✓ Text typed (input resolver)")
                return ActionResult(success=True, before_state=before_state, after_state=after_state)
            except Exception as e:
                logger.warning("Input fill failed: %s", e)

        # FALLBACK: ranker-based (existing logic)
        elements = await self.extractor.extract_inputs(page)
        filtered_elements = self.filter.apply_standard_filters(elements, "TYPE")
        if not filtered_elements:
            return ActionResult(success=False, error="No input elements found", before_state=before_state)
        best_element = self.ranker.get_best_match(filtered_elements, target_field)
        if not best_element:
            return ActionResult(success=False, error=f"No input field found for '{target_field}'", before_state=before_state)
        try:
            if best_element.attributes.get("placeholder"):
                locator = page.get_by_placeholder(best_element.attributes["placeholder"])
            elif best_element.text:
                locator = page.get_by_label(best_element.text)
            else:
                locator = page.locator(f"input[name='{best_element.attributes.get('name')}']")
            if clear_first:
                await locator.clear()
            await locator.fill(text_to_type or "")
            after_state = await self.validator.capture_state(page)
            return ActionResult(success=True, element=best_element, before_state=before_state, after_state=after_state)
        except Exception as e:
            return ActionResult(success=False, error=f"Failed to type text: {e}", before_state=before_state)
    
    async def navigate(self, page: Page, url: str) -> ActionResult:
        """
        Navigate to URL.
        
        Args:
            page: Playwright page object
            url: Target URL
            
        Returns:
            ActionResult with execution details
        """
        logger.info("[EXECUTOR] NAVIGATE action: url=%s", url[:80] if url else "")
        
        before_state = await self.validator.capture_state(page)
        
        try:
            await page.goto(url, wait_until="domcontentloaded")
            
            after_state = await self.validator.capture_state(page)
            
            if self.validator.validate_navigation(before_state, after_state):
                logger.info(f"✓ Navigation successful: {url}")
                return ActionResult(
                    success=True,
                    before_state=before_state,
                    after_state=after_state
                )
            else:
                error_msg = "Navigation did not change URL"
                logger.error(error_msg)
                return ActionResult(
                    success=False, 
                    error=error_msg,
                    before_state=before_state,
                    after_state=after_state
                )
                
        except Exception as e:
            error_msg = f"Navigation failed: {e}"
            logger.error(error_msg)
            return ActionResult(success=False, error=error_msg, before_state=before_state)
    
    async def select_option(
        self,
        page: Page,
        target: str,
        value: str,
    ) -> ActionResult:
        """
        Select option: delivery/label flow (click label or radio) or generic dropdown.
        """
        logger.info("[EXECUTOR] SELECT action: target='%s' value='%s'", (target or "")[:50], (value or "")[:50])
        before_state = await self.validator.capture_state(page)
        target_lower = (target or "").lower()
        value_str = (value or "").strip()

        # V2: Try select resolver first
        if self.use_v2_resolvers:
            registry = self._resolver_registry or _get_resolver_registry()
            if registry:
                self._resolver_registry = registry
                res = await registry.resolve(page, "SELECT", target or "", value_str)
                if res.success and res.locator:
                    try:
                        await res.locator.click(timeout=5000)
                        after_state = await self.validator.capture_state(page)
                        logger.info("✓ Select successful (v2 resolver)")
                        return ActionResult(success=True, before_state=before_state, after_state=after_state)
                    except Exception as e:
                        logger.debug("V2 select failed: %s", e)

        # DELIVERY OPTION: label/radio, not dropdown
        if "delivery" in target_lower or "delivery" in (value_str.lower()):
            if await select_delivery(page, value_str or "free delivery"):
                after_state = await self.validator.capture_state(page)
                logger.info("✓ Delivery option selected")
                return ActionResult(success=True, before_state=before_state, after_state=after_state)
            return ActionResult(success=False, error=f"Could not select delivery: {value_str}", before_state=before_state)

        # Generic SELECT dropdown fallback
        try:
            selects = page.locator("select:visible")
            if await selects.count() > 0:
                await selects.first.select_option(label=value_str)
                after_state = await self.validator.capture_state(page)
                return ActionResult(success=True, before_state=before_state, after_state=after_state)
        except Exception as e:
            logger.debug("Select dropdown fallback: %s", e)
        return ActionResult(success=False, error=f"Could not select '{value_str}' for '{target}'", before_state=before_state)

    async def wait_for_element(
        self, 
        page: Page, 
        target_text: str,
        timeout: float = 10.0
    ) -> ActionResult:
        """
        Wait for element to appear.
        
        Args:
            page: Playwright page object
            target_text: Text of element to wait for
            timeout: Maximum wait time in seconds
            
        Returns:
            ActionResult with execution details
        """
        logger.info(f"Waiting for element: '{target_text}'")
        
        start_time = asyncio.get_event_loop().time()
        
        while asyncio.get_event_loop().time() - start_time < timeout:
            elements = await self.extractor.extract_all_interactive(page)
            filtered = self.filter.apply_standard_filters(elements, "CLICK")
            
            best_match = self.ranker.get_best_match(filtered, target_text)
            
            if best_match:
                logger.info(f"✓ Element found: '{best_match.display_name}'")
                return ActionResult(success=True, element=best_match)
            
            await asyncio.sleep(0.5)
        
        error_msg = f"Timeout waiting for '{target_text}'"
        logger.error(error_msg)
        return ActionResult(success=False, error=error_msg)
