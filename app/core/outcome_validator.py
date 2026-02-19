"""
Outcome validation - ensures state transitions are meaningful.
This is CRITICAL to prevent random clicking behavior.
"""
from playwright.async_api import Page
from typing import Dict, Any, Optional
import logging
import hashlib

logger = logging.getLogger(__name__)


class PageState:
    """Represents the state of a page at a point in time."""
    
    def __init__(
        self, 
        url: str, 
        title: str, 
        dom_hash: Optional[str] = None,
        visible_text_hash: Optional[str] = None
    ):
        self.url = url
        self.title = title
        self.dom_hash = dom_hash
        self.visible_text_hash = visible_text_hash
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "url": self.url,
            "title": self.title,
            "dom_hash": self.dom_hash,
            "visible_text_hash": self.visible_text_hash
        }
    
    def __eq__(self, other) -> bool:
        """Check equality."""
        if not isinstance(other, PageState):
            return False
        return (
            self.url == other.url and
            self.title == other.title and
            self.dom_hash == other.dom_hash
        )
    
    def __repr__(self) -> str:
        return f"PageState(url={self.url}, title={self.title})"


class OutcomeValidator:
    """
    Validates that actions produce meaningful state transitions.
    Prevents random clicking and ensures deterministic behavior.
    """
    
    def __init__(self, strict_mode: bool = True):
        """
        Initialize validator.
        
        Args:
            strict_mode: If True, requires significant state change
        """
        self.strict_mode = strict_mode
    
    async def capture_state(self, page: Page) -> PageState:
        """
        Capture current page state.
        
        Args:
            page: Playwright page object
            
        Returns:
            PageState object representing current state
        """
        try:
            url = page.url
            title = await page.title()
            
            # Capture DOM structure hash
            dom_hash = await self._compute_dom_hash(page)
            
            # Capture visible text hash
            visible_text_hash = await self._compute_visible_text_hash(page)
            
            state = PageState(
                url=url,
                title=title,
                dom_hash=dom_hash,
                visible_text_hash=visible_text_hash
            )
            
            logger.debug(f"Captured state: {state}")
            return state
            
        except Exception as e:
            logger.error(f"Error capturing state: {e}")
            raise
    
    async def _compute_dom_hash(self, page: Page) -> str:
        """
        Compute hash of DOM structure.
        
        Args:
            page: Playwright page object
            
        Returns:
            SHA256 hash of DOM structure
        """
        try:
            dom_structure = await page.evaluate("""
                () => {
                    const getStructure = (node) => {
                        if (node.nodeType !== 1) return '';
                        return node.tagName + 
                               Array.from(node.children).map(getStructure).join('');
                    };
                    return getStructure(document.body);
                }
            """)
            
            return hashlib.sha256(dom_structure.encode()).hexdigest()[:16]
            
        except Exception as e:
            logger.debug(f"Could not compute DOM hash: {e}")
            return ""
    
    async def _compute_visible_text_hash(self, page: Page) -> str:
        """
        Compute hash of visible text content.
        
        Args:
            page: Playwright page object
            
        Returns:
            SHA256 hash of visible text
        """
        try:
            visible_text = await page.evaluate("""
                () => {
                    return document.body.innerText;
                }
            """)
            
            return hashlib.sha256(visible_text.encode()).hexdigest()[:16]
            
        except Exception as e:
            logger.debug(f"Could not compute text hash: {e}")
            return ""
    
    def validate_transition(
        self, 
        before: PageState, 
        after: PageState,
        expected_change: Optional[str] = None
    ) -> bool:
        """
        Validate that a meaningful state transition occurred.
        
        Args:
            before: State before action
            after: State after action
            expected_change: Optional expected change type
            
        Returns:
            True if valid transition, False otherwise
        """
        # Check URL change
        url_changed = before.url != after.url
        
        # Check title change
        title_changed = before.title != after.title
        
        # Check DOM change
        dom_changed = before.dom_hash != after.dom_hash
        
        # Check visible text change
        text_changed = before.visible_text_hash != after.visible_text_hash
        
        logger.debug(
            f"Transition validation: URL={url_changed}, Title={title_changed}, "
            f"DOM={dom_changed}, Text={text_changed}"
        )
        
        # In strict mode, require at least one significant change
        if self.strict_mode:
            valid = url_changed or title_changed or dom_changed or text_changed
        else:
            valid = url_changed or title_changed or text_changed
        
        if valid:
            logger.info("✓ Valid state transition detected")
        else:
            logger.warning("✗ No meaningful state transition detected")
        
        return valid
    
    def validate_navigation(self, before: PageState, after: PageState) -> bool:
        """
        Validate navigation action (must change URL).
        
        Args:
            before: State before navigation
            after: State after navigation
            
        Returns:
            True if URL changed
        """
        url_changed = before.url != after.url
        
        if url_changed:
            logger.info(f"✓ Navigation: {before.url} -> {after.url}")
        else:
            logger.warning(f"✗ No navigation occurred, still at: {before.url}")
        
        return url_changed
    
    def validate_modal_or_overlay(
        self, 
        before: PageState, 
        after: PageState
    ) -> bool:
        """
        Validate modal/overlay appearance (DOM changes but not URL).
        
        Args:
            before: State before action
            after: State after action
            
        Returns:
            True if DOM changed without URL change
        """
        url_same = before.url == after.url
        dom_changed = before.dom_hash != after.dom_hash
        
        valid = url_same and dom_changed
        
        if valid:
            logger.info("✓ Modal/overlay detected (DOM changed, URL same)")
        else:
            logger.warning("✗ No modal/overlay detected")
        
        return valid
    
    def is_error_state(self, state: PageState) -> bool:
        """
        Check if current state indicates an error.
        
        Args:
            state: Current page state
            
        Returns:
            True if error state detected
        """
        error_indicators = [
            "error",
            "404",
            "not found",
            "forbidden",
            "unauthorized"
        ]
        
        title_lower = state.title.lower()
        url_lower = state.url.lower()
        
        for indicator in error_indicators:
            if indicator in title_lower or indicator in url_lower:
                logger.warning(f"Error state detected: {indicator}")
                return True
        
        return False
