"""
Smart Interaction Utilities - Advanced interaction patterns for reliability.
Includes overlay detection, behavioral simulation (hover, scroll), and smart waiting.
"""
import re
from playwright.async_api import Page, Locator
from typing import Optional
import asyncio
import logging

logger = logging.getLogger(__name__)


async def detect_and_dismiss_overlays(page: Page) -> bool:
    """
    Detect and dismiss common overlays (modals, popups, dimmed backgrounds).
    Returns True if overlays were found and dismissed.
    """
    overlay_selectors = [
        '.c-pop-msg__dimmed',
        '.modal-backdrop',
        '[class*="overlay"]',
        '[class*="dimmed"]',
        '.popup-overlay',
        '[class*="modal-overlay"]',
        '[style*="position: fixed"][style*="z-index"]'
    ]
    
    found_overlays = False
    
    for selector in overlay_selectors:
        try:
            overlays = await page.locator(selector).all()
            if overlays:
                found_overlays = True
                logger.info(f"✓ Detected {len(overlays)} overlay(s) matching '{selector}'")
                break
        except Exception:
            continue
    
    if not found_overlays:
        return False
    
    logger.info("[SMART_INTERACTION] Attempting to dismiss overlays...")
    
    # Strategy 1: Press ESC key
    try:
        await page.keyboard.press('Escape')
        await asyncio.sleep(0.5)
        logger.debug("✓ Pressed ESC key")
    except Exception as e:
        logger.debug(f"ESC key failed: {e}")
    
    # Strategy 2: Click outside (top-left corner)
    try:
        await page.mouse.click(10, 10)
        await asyncio.sleep(0.5)
        logger.debug("✓ Clicked outside overlay")
    except Exception as e:
        logger.debug(f"Click outside failed: {e}")
    
    # Strategy 3: Look for close button
    close_selectors = [
        '[aria-label*="close" i]',
        '[class*="close"]',
        'button:has-text("×")',
        'button:has-text("Close")'
    ]
    
    for close_sel in close_selectors:
        try:
            close_btn = page.locator(close_sel).first
            if await close_btn.is_visible():
                await close_btn.click(timeout=2000)
                await asyncio.sleep(0.3)
                logger.debug(f"✓ Clicked close button: {close_sel}")
                break
        except Exception:
            continue
    
    return True


async def smart_click_with_overlay_handling(
    page: Page, 
    locator: Locator, 
    max_retries: int = 3,
    wait_between_retries: float = 1.0
) -> bool:
    """
    Click element with automatic overlay detection and retry logic.
    Returns True if click succeeded, False otherwise.
    """
    for attempt in range(max_retries):
        try:
            # Check for overlays before clicking
            await detect_and_dismiss_overlays(page)
            
            # Ensure element is in viewport
            await locator.scroll_into_view_if_needed()
            await asyncio.sleep(0.2)
            
            # Try click
            await locator.click(timeout=15000)  # 15s for slow enterprise pages
            logger.info(f"✓ Click succeeded on attempt {attempt + 1}")
            return True
            
        except Exception as e:
            error_msg = str(e).lower()
            
            # Check if overlay is blocking
            if "intercepts pointer events" in error_msg or "not stable" in error_msg:
                logger.warning(f"Attempt {attempt + 1}: Overlay blocking click - {e}")
                
                # Dismiss overlays and retry
                await detect_and_dismiss_overlays(page)
                await asyncio.sleep(wait_between_retries)
                
                if attempt < max_retries - 1:
                    logger.info(f"Retrying click (attempt {attempt + 2}/{max_retries})...")
                    continue
            
            # Other errors
            logger.error(f"Click failed on attempt {attempt + 1}: {e}")
            if attempt == max_retries - 1:
                return False
    
    return False


async def behavioral_hover(page: Page, locator: Locator) -> bool:
    """
    Hover over element with human-like behavior.
    Returns True if hover succeeded.
    """
    try:
        # Scroll into view first
        await locator.scroll_into_view_if_needed()
        await asyncio.sleep(0.1)
        
        # Hover
        await locator.hover(timeout=3000)
        await asyncio.sleep(0.3)  # Wait for hover effects
        
        logger.debug("✓ Hover succeeded")
        return True
    except Exception as e:
        logger.debug(f"Hover failed: {e}")
        return False


async def behavioral_scroll_to_element(page: Page, locator: Locator, offset: int = 100) -> bool:
    """
    Scroll element into view with offset for better visibility.
    Returns True if scroll succeeded.
    """
    try:
        # Get element position
        bbox = await locator.bounding_box()
        if not bbox:
            return False
        
        # Calculate scroll position with offset
        target_y = bbox['y'] - offset
        
        # Smooth scroll
        await page.evaluate(f"window.scrollTo({{top: {target_y}, behavior: 'smooth'}})")
        await asyncio.sleep(0.5)
        
        logger.debug(f"✓ Scrolled to element (y={target_y})")
        return True
    except Exception as e:
        logger.debug(f"Scroll failed: {e}")
        return False


async def smart_wait_for_element(
    page: Page, 
    target: str, 
    timeout: int = 60000,  # 60s - enterprise pages can load slowly
    check_interval: int = 1000
) -> Optional[Locator]:
    """
    Wait for element with periodic overlay dismissal.
    Uses multiple strategies: text, label, role, and scroll to find elements.
    Returns locator if found, None otherwise.
    """
    try:
        start_time = asyncio.get_running_loop().time()
    except RuntimeError:
        start_time = __import__("time").monotonic()
    max_time = start_time + (timeout / 1000)
    
    logger.info(f"[SMART_WAIT] Waiting for element: '{target}' (timeout={timeout}ms)")
    
    # Strategies: text, label, role, heading - order matters
    target_re = re.compile(re.escape(target), re.I) if target else None

    def _try_strategies():
        strategies = []
        if not target:
            return strategies
        # 1. Text contains - handles "1 Contact Information", "Contact Information"
        strategies.append(("text", lambda: page.get_by_text(target, exact=False).first))
        # 2. Label - for form sections/inputs
        strategies.append(("label", lambda: page.get_by_label(target, exact=False).first))
        # 3. Role heading - for section headings (regex for partial match)
        if target_re:
            strategies.append(("heading", lambda: page.get_by_role("heading", name=target_re).first))
            strategies.append(("region", lambda: page.get_by_role("region", name=target_re).first))
        return strategies
    
    checks = 0
    last_scroll_y = 0
    def _now():
        try:
            return asyncio.get_running_loop().time()
        except RuntimeError:
            return __import__("time").monotonic()
    while _now() < max_time:
        checks += 1
        
        try:
            # Check for overlays every few attempts
            if checks % 3 == 0:
                await detect_and_dismiss_overlays(page)
            
            # Try each strategy
            for name, get_locator in _try_strategies():
                try:
                    locator = get_locator()
                    if locator and await locator.is_visible():
                        logger.info(f"✓ Element found after {checks} checks (strategy: {name})")
                        return locator
                except Exception:
                    pass
            
            # Scroll periodically to expose lazy-loaded content (e.g. checkout form)
            if checks % 5 == 0 and checks > 1:
                try:
                    scroll_y = await page.evaluate("window.scrollY")
                    doc_height = await page.evaluate("document.body.scrollHeight")
                    view_height = await page.evaluate("window.innerHeight")
                    # Scroll down in chunks
                    next_y = min(scroll_y + view_height * 0.6, doc_height - view_height)
                    if next_y > last_scroll_y and next_y < doc_height:
                        await page.evaluate(f"window.scrollTo(0, {next_y})")
                        last_scroll_y = next_y
                        await asyncio.sleep(0.3)
                    elif scroll_y < 100:
                        await page.evaluate("window.scrollTo(0, 0)")
                        last_scroll_y = 0
                except Exception:
                    pass
            
        except Exception:
            pass
        
        # Wait before next check
        await asyncio.sleep(check_interval / 1000)
    
    logger.warning(f"✗ Element not found after {checks} checks ({timeout}ms)")
    return None


async def force_click_with_js(page: Page, locator: Locator) -> bool:
    """
    Force click using JavaScript as fallback.
    Returns True if click succeeded.
    """
    try:
        await page.evaluate("el => el.click()", await locator.element_handle())
        logger.debug("✓ JS click succeeded")
        return True
    except Exception as e:
        logger.debug(f"JS click failed: {e}")
        return False


async def safe_type_with_focus(page: Page, locator: Locator, text: str, clear_first: bool = True) -> bool:
    """
    Type text with proper focus and clearing.
    Returns True if typing succeeded.
    """
    try:
        # Ensure element is in view and focused
        await locator.scroll_into_view_if_needed()
        await asyncio.sleep(0.1)
        
        await locator.focus()
        await asyncio.sleep(0.1)
        
        # Clear if needed
        if clear_first:
            await locator.clear()
            await asyncio.sleep(0.1)
        
        # Type with human-like delay
        await locator.type(text, delay=50)
        await asyncio.sleep(0.2)
        
        logger.debug(f"✓ Typed text: '{text[:30]}...'")
        return True
    except Exception as e:
        logger.debug(f"Type failed: {e}")
        return False
