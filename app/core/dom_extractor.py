"""
DOM extraction and element discovery.
Visible-first: only query visible elements, then cap. Scroll before extraction on listing pages.
"""
import asyncio
from playwright.async_api import Page, Locator
from typing import List, Optional, Tuple
import logging
from .dom_model import DOMElement, BoundingBox

logger = logging.getLogger(__name__)

MAX_CLICKABLES_TO_EXTRACT = 350
MAX_INPUTS_TO_EXTRACT = 50
PER_ELEMENT_TIMEOUT_SEC = 2.0


async def _scroll_for_lazy_load(page: Page) -> None:
    """Scroll to load lazy content (e.g. product grids) then back. Call before extraction on listing pages."""
    try:
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        await page.wait_for_timeout(2000)
        await page.evaluate("window.scrollTo(0, 0)")
        await page.wait_for_timeout(500)
    except Exception:
        pass


def _is_listing_page(url: str) -> bool:
    """Heuristic: product listing / category page that may lazy-load."""
    u = url.lower()
    return "air-conditioners" in u or "product" in u or "/category" in u or "/listing" in u


async def _visible_clickable_indices_at_scroll(page: Page, selector: str, scroll_y: Optional[float] = None) -> List[int]:
    """Get indices of visible clickables at current scroll (or after scrolling to scroll_y)."""
    if scroll_y is not None:
        await page.evaluate(f"window.scrollTo(0, {scroll_y})")
        await page.wait_for_timeout(400)
    return await page.evaluate(
        """
        (selector) => {
            const nodes = document.querySelectorAll(selector);
            const out = [];
            for (let i = 0; i < nodes.length; i++) {
                const el = nodes[i];
                const r = el.getBoundingClientRect();
                if (r.width > 0 && r.height > 0 && el.offsetParent !== null) {
                    const style = window.getComputedStyle(el);
                    if (style.visibility !== 'hidden' && style.display !== 'none' && style.opacity !== '0')
                        out.push(i);
                }
            }
            return out;
        }
        """,
        selector,
    )


class DOMExtractor:
    """Extracts and structures DOM elements for deterministic processing."""

    def __init__(self):
        self.element_cache: dict = {}

    async def _extract_element_with_timeout(self, locator: Locator) -> Optional[DOMElement]:
        try:
            return await asyncio.wait_for(
                self._extract_element(locator),
                timeout=PER_ELEMENT_TIMEOUT_SEC
            )
        except asyncio.TimeoutError:
            logger.debug("Element extraction timed out, skipping")
            return None

    async def extract_clickables(self, page: Page) -> List[Tuple[DOMElement, Locator]]:
        """
        Visible-first extraction: get indices of visible clickables via JS, then extract only those (capped).
        On listing pages, scroll first to load lazy content (product cards).
        Returns (DOMElement, Locator) pairs so executor can click the locator directly (no get_by_text).
        """
        pairs: List[Tuple[DOMElement, Locator]] = []
        selector = "button, a, [role='button'], [role='link'], input[type='submit'], input[type='button']"

        try:
            if _is_listing_page(page.url):
                await _scroll_for_lazy_load(page)

            # Multi-region: on listing pages, snapshot top / mid / bottom and merge visible indices
            visible_indices: List[int]
            if _is_listing_page(page.url):
                try:
                    body_height = await page.evaluate("document.body.scrollHeight") or 3000
                    mid = body_height * 0.5
                    top_indices = await _visible_clickable_indices_at_scroll(page, selector, 0)
                    mid_indices = await _visible_clickable_indices_at_scroll(page, selector, mid)
                    bottom_indices = await _visible_clickable_indices_at_scroll(page, selector, body_height - 500)
                    await page.evaluate("window.scrollTo(0, 0)")
                    await page.wait_for_timeout(300)
                    visible_indices = sorted(set(top_indices + mid_indices + bottom_indices))
                    logger.info("Multi-region visible: top=%d mid=%d bottom=%d merged=%d", len(top_indices), len(mid_indices), len(bottom_indices), len(visible_indices))
                except Exception as mr_err:
                    logger.debug("Multi-region extraction failed, using single snapshot: %s", mr_err)
                    visible_indices = await _visible_clickable_indices_at_scroll(page, selector, None)
            else:
                visible_indices = await _visible_clickable_indices_at_scroll(page, selector, None)
            total_visible = len(visible_indices)
            loc = page.locator(selector)
            total_count = await loc.count()
            logger.info("Found %d visible clickable elements (of %d total)", total_visible, total_count)

            limit = min(total_visible, MAX_CLICKABLES_TO_EXTRACT)
            if total_visible > MAX_CLICKABLES_TO_EXTRACT:
                logger.info("Capping at first %d visible elements", limit)

            for idx in visible_indices[:limit]:
                el_loc = loc.nth(idx)
                el = await self._extract_element_with_timeout(el_loc)
                if el:
                    pairs.append((el, el_loc))

            logger.info("Extracted %d clickable elements", len(pairs))
        except Exception as e:
            logger.warning("Visible-first extraction failed, falling back: %s", e)
            if _is_listing_page(page.url):
                await _scroll_for_lazy_load(page)
            loc = page.locator(selector)
            count = await loc.count()
            to_process = min(count, MAX_CLICKABLES_TO_EXTRACT)
            for i in range(to_process):
                el_loc = loc.nth(i)
                el = await self._extract_element_with_timeout(el_loc)
                if el and el.visible:
                    pairs.append((el, el_loc))
            logger.info("Extracted %d visible clickable elements (fallback)", len(pairs))

        return pairs
    
    async def extract_inputs(self, page: Page) -> List[DOMElement]:
        """
        Extract all input elements from page.
        
        Args:
            page: Playwright page object
            
        Returns:
            List of structured DOMElement objects
        """
        elements = []
        
        selector = "input, textarea, select"
        
        try:
            locator = page.locator(selector)
            count = await locator.count()
            
            logger.info(f"Found {count} potential input elements")
            
            to_process = min(count, MAX_INPUTS_TO_EXTRACT)
            for i in range(to_process):
                element = await self._extract_element_with_timeout(locator.nth(i))
                if element and element.visible:
                    elements.append(element)
            
            logger.info(f"Extracted {len(elements)} visible input elements")
            
        except Exception as e:
            logger.error(f"Error extracting inputs: {e}")
        
        return elements
    
    async def extract_all_interactive(self, page: Page) -> List[DOMElement]:
        """
        Extract all interactive elements from page (for recovery/wait; no locators).
        """
        clickable_pairs = await self.extract_clickables(page)
        clickables = [e for e, _ in clickable_pairs]
        inputs = await self.extract_inputs(page)
        all_elements = clickables + inputs
        logger.info("Total interactive elements: %d", len(all_elements))
        return all_elements
    
    async def _extract_element(self, locator: Locator) -> Optional[DOMElement]:
        """
        Extract single element with full metadata.
        
        Args:
            locator: Playwright locator
            
        Returns:
            Structured DOMElement or None
        """
        try:
            # Check visibility first
            is_visible = await locator.is_visible()
            if not is_visible:
                return None
            
            # Extract basic properties
            tag = await locator.evaluate("el => el.tagName")
            text = await locator.text_content() or ""
            role = await locator.get_attribute("role")
            
            # Extract bounding box
            bbox_data = await locator.bounding_box()
            bbox = None
            if bbox_data:
                bbox = BoundingBox(
                    x=bbox_data["x"],
                    y=bbox_data["y"],
                    width=bbox_data["width"],
                    height=bbox_data["height"]
                )
            
            # Extract attributes
            attributes = {
                "aria_label": await locator.get_attribute("aria-label"),
                "data_testid": await locator.get_attribute("data-testid"),
                "id": await locator.get_attribute("id"),
                "class": await locator.get_attribute("class"),
                "type": await locator.get_attribute("type"),
                "name": await locator.get_attribute("name"),
                "placeholder": await locator.get_attribute("placeholder"),
                "title": await locator.get_attribute("title"),
                "href": await locator.get_attribute("href"),
            }
            
            # Remove None values
            attributes = {k: v for k, v in attributes.items() if v is not None}
            
            # Extract parent context
            parent_text = await locator.evaluate(
                "el => el.parentElement ? el.parentElement.textContent : null"
            )
            
            # Extract container
            container = await locator.evaluate(
                "el => el.closest('div[class*=\"container\"], section, article, nav, header, footer')?.className || null"
            )
            # Stable selector for click (avoid get_by_text so truncated product title still works)
            css_selector = await locator.evaluate(
                "el => { if (el.id && /^[a-zA-Z][a-zA-Z0-9_-]*$/.test(el.id)) return '#' + el.id; const t = el.getAttribute('data-testid'); if (t) return '[data-testid=\"' + t.replace(/\"/g, '\\\\\"') + '\"]'; return null; }"
            )
            if not css_selector and tag and str(tag).lower() == "a" and attributes.get("href"):
                href = attributes["href"]
                if href.startswith("/") and len(href) <= 100:
                    css_selector = f'a[href="{href}"]'

            return DOMElement(
                tag=tag,
                text=text.strip(),
                role=role,
                visible=is_visible,
                bounding_box=bbox,
                attributes=attributes,
                parent_text=parent_text,
                container=container,
                css_selector=css_selector
            )
            
        except Exception as e:
            logger.debug(f"Failed to extract element: {e}")
            return None
    
    async def extract_by_region(self, page: Page, region_selector: str) -> List[DOMElement]:
        """
        Extract elements within a specific region.
        
        Args:
            page: Playwright page object
            region_selector: CSS selector for region container
            
        Returns:
            List of DOMElement objects within region
        """
        elements = []
        
        try:
            region = page.locator(region_selector).first
            if not await region.is_visible():
                logger.warning(f"Region not visible: {region_selector}")
                return elements
            
            # Extract clickables within region
            clickables = region.locator("button, a, [role='button']")
            count = await clickables.count()
            
            for i in range(count):
                element = await self._extract_element(clickables.nth(i))
                if element and element.visible:
                    elements.append(element)
            
            logger.info(f"Extracted {len(elements)} elements from region")
            
        except Exception as e:
            logger.error(f"Error extracting from region: {e}")
        
        return elements
    
    def clear_cache(self) -> None:
        """Clear element cache."""
        self.element_cache.clear()
        logger.debug("Element cache cleared")
