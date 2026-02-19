"""
Action executor - the deterministic engine that performs actions.
AI is NOT allowed to directly interact with DOM. Only this layer can.
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

logger = logging.getLogger(__name__)


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
        score_threshold: float = 0.65
    ):
        """
        Initialize executor.
        
        Args:
            max_retries: Maximum retry attempts per action
            score_threshold: Minimum element score threshold
        """
        self.extractor = DOMExtractor()
        self.filter = ElementFilter()
        self.ranker = ElementRanker(threshold=score_threshold)
        self.validator = OutcomeValidator(strict_mode=True)
        self.max_retries = max_retries
    
    async def click(
        self, 
        page: Page, 
        target_text: str,
        region_context: Optional[str] = None,
        wait_after: float = 0.5
    ) -> ActionResult:
        """
        Execute click action with validation.
        
        Args:
            page: Playwright page object
            target_text: Text of element to click
            region_context: Optional region to search within
            wait_after: Seconds to wait after click
            
        Returns:
            ActionResult with execution details
        """
        logger.info(f"Executing CLICK action: '{target_text}'")
        
        # Capture state before action
        before_state = await self.validator.capture_state(page)
        
        # Extract all clickable elements
        elements = await self.extractor.extract_clickables(page)
        logger.info(f"Extracted {len(elements)} clickable elements")
        
        # Apply filters
        filtered_elements = self.filter.apply_standard_filters(elements, "CLICK")
        
        if not filtered_elements:
            error_msg = f"No clickable elements found matching filters"
            logger.error(error_msg)
            return ActionResult(success=False, error=error_msg, before_state=before_state)
        
        # Rank elements
        ranked_elements = self.ranker.get_top_candidates(
            filtered_elements, 
            target_text,
            top_n=self.max_retries,
            region_context=region_context
        )
        
        if not ranked_elements:
            error_msg = f"No elements scored above threshold for '{target_text}'"
            logger.error(error_msg)
            return ActionResult(success=False, error=error_msg, before_state=before_state)
        
        # Try top candidates
        for attempt, element in enumerate(ranked_elements, 1):
            try:
                logger.info(
                    f"Attempt {attempt}/{len(ranked_elements)}: "
                    f"Clicking '{element.display_name}'"
                )
                
                # Perform click
                await page.get_by_text(element.text, exact=False).first.click(timeout=5000)
                
                # Wait for potential page transition
                await asyncio.sleep(wait_after)
                
                # Capture state after action
                after_state = await self.validator.capture_state(page)
                
                # Validate transition
                if self.validator.validate_transition(before_state, after_state):
                    logger.info(f"✓ Click successful: '{element.display_name}'")
                    return ActionResult(
                        success=True,
                        element=element,
                        before_state=before_state,
                        after_state=after_state,
                        attempts=attempt
                    )
                else:
                    logger.warning(
                        f"Click performed but no valid state transition detected"
                    )
                    
            except Exception as e:
                logger.warning(f"Attempt {attempt} failed: {e}")
                continue
        
        # All attempts failed
        error_msg = f"All {len(ranked_elements)} attempts failed for '{target_text}'"
        logger.error(error_msg)
        return ActionResult(
            success=False, 
            error=error_msg,
            before_state=before_state,
            attempts=len(ranked_elements)
        )
    
    async def type_text(
        self, 
        page: Page, 
        target_field: str,
        text_to_type: str,
        clear_first: bool = True
    ) -> ActionResult:
        """
        Type text into input field.
        
        Args:
            page: Playwright page object
            target_field: Label or placeholder of input field
            text_to_type: Text to type
            clear_first: Clear field before typing
            
        Returns:
            ActionResult with execution details
        """
        logger.info(f"Executing TYPE action: '{target_field}' = '{text_to_type}'")
        
        before_state = await self.validator.capture_state(page)
        
        # Extract input elements
        elements = await self.extractor.extract_inputs(page)
        logger.info(f"Extracted {len(elements)} input elements")
        
        # Apply filters
        filtered_elements = self.filter.apply_standard_filters(elements, "TYPE")
        
        if not filtered_elements:
            error_msg = "No input elements found"
            logger.error(error_msg)
            return ActionResult(success=False, error=error_msg, before_state=before_state)
        
        # Rank elements
        best_element = self.ranker.get_best_match(filtered_elements, target_field)
        
        if not best_element:
            error_msg = f"No input field found for '{target_field}'"
            logger.error(error_msg)
            return ActionResult(success=False, error=error_msg, before_state=before_state)
        
        try:
            # Find input locator
            if best_element.attributes.get("placeholder"):
                locator = page.get_by_placeholder(best_element.attributes["placeholder"])
            elif best_element.text:
                locator = page.get_by_label(best_element.text)
            else:
                locator = page.locator(f"input[name='{best_element.attributes.get('name')}']")
            
            # Clear if needed
            if clear_first:
                await locator.clear()
            
            # Type text
            await locator.fill(text_to_type)
            
            logger.info(f"✓ Text typed successfully into '{best_element.display_name}'")
            
            after_state = await self.validator.capture_state(page)
            
            return ActionResult(
                success=True,
                element=best_element,
                before_state=before_state,
                after_state=after_state
            )
            
        except Exception as e:
            error_msg = f"Failed to type text: {e}"
            logger.error(error_msg)
            return ActionResult(success=False, error=error_msg, before_state=before_state)
    
    async def navigate(self, page: Page, url: str) -> ActionResult:
        """
        Navigate to URL.
        
        Args:
            page: Playwright page object
            url: Target URL
            
        Returns:
            ActionResult with execution details
        """
        logger.info(f"Executing NAVIGATE action: {url}")
        
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
