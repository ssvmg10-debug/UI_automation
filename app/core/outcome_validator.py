"""
Outcome validation - ensures state transitions are meaningful.
Strong validation: DOM hash + URL; transition valid iff URL or DOM changed.
"""
from playwright.async_api import Page
from typing import Dict, Any, Optional
import logging
import hashlib

logger = logging.getLogger(__name__)


async def dom_hash(page: Page) -> str:
    """MD5 of full page content for strong state comparison."""
    try:
        content = await page.content()
        return hashlib.md5(content.encode()).hexdigest()
    except Exception:
        return ""


class PageState:
    """Represents the state of a page at a point in time (url + dom hash)."""
    
    def __init__(
        self, 
        url: str, 
        title: str = "", 
        dom_hash: Optional[str] = None,
        visible_text_hash: Optional[str] = None
    ):
        self.url = url
        self.title = title
        self.dom_hash = dom_hash or ""
        self.visible_text_hash = visible_text_hash or ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "url": self.url,
            "title": self.title,
            "dom_hash": self.dom_hash,
            "visible_text_hash": self.visible_text_hash
        }
    
    def __eq__(self, other) -> bool:
        if not isinstance(other, PageState):
            return False
        return self.url == other.url and self.dom_hash == other.dom_hash
    
    def __repr__(self) -> str:
        return f"PageState(url={self.url}, hash={self.dom_hash[:8] if self.dom_hash else ''})"


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
        Capture current page state: URL + full DOM content hash (MD5).
        Transition is valid iff URL or DOM hash changed.
        """
        try:
            url = page.url
            title = await page.title()
            hash_val = await dom_hash(page)
            state = PageState(url=url, title=title, dom_hash=hash_val)
            logger.debug("Captured state: %s", state)
            return state
        except Exception as e:
            logger.error("Error capturing state: %s", e)
            raise

    def validate_transition(
        self,
        before: PageState,
        after: PageState,
        expected_change: Optional[str] = None
    ) -> bool:
        """
        Strong validation: transition valid iff URL changed or DOM hash changed.
        """
        url_changed = before.url != after.url
        hash_changed = before.dom_hash != after.dom_hash
        valid = url_changed or hash_changed
        if valid:
            logger.info("✓ Valid state transition detected (URL or DOM changed)")
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
