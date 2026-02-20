"""
DOM Scanner V3 - Scroll-through extraction with broader selectors.
Fixes: footer links, banner links, div[onclick], span[onclick].
Deduplication by (text, bbox) to avoid unhashable locator in set.
OPTIMIZED: Incremental extraction with DOM hash caching.
"""
from playwright.async_api import Page
from typing import List, Dict, Any, Optional, Tuple
import logging
import hashlib

logger = logging.getLogger(__name__)


class DOMScannerV3:
    """Extracts visible clickable elements via scroll-through (top, mid, bottom) with caching."""
    
    def __init__(self):
        self._last_dom_hash: Optional[str] = None
        self._cached_clickables: List[Dict[str, Any]] = []
        self._cached_inputs: List[Dict[str, Any]] = []
        self._cache_hits = 0
        self._cache_misses = 0

    CLICKABLE_SELECTOR = """
        a, button, [role='button'], [role='link'],
        div[onclick], span[onclick],
        input[type='submit'], input[type='button']
    """

    INPUT_SELECTOR = "input, textarea, select"

    async def _compute_dom_hash(self, page: Page) -> str:
        """Fast hash of visible DOM structure."""
        try:
            dom_signature = await page.evaluate("""() => {
                const clickables = document.querySelectorAll('a:not([style*="display:none"]):not([style*="display: none"]), button:not([style*="display:none"]):not([style*="display: none"])');
                return Array.from(clickables).slice(0, 100).map(el => 
                    el.tagName + (el.textContent || '').slice(0, 20) + el.getBoundingClientRect().top
                ).join('|');
            }""")
            return hashlib.md5(dom_signature.encode('utf-8')).hexdigest()
        except Exception:
            return ""

    async def scan_clickables(self, page: Page, force_refresh: bool = False) -> List[Dict[str, Any]]:
        """
        Scroll through page to expose ALL visible clickables.
        Dedupe by (text, bbox) since locators are not hashable.
        OPTIMIZED: Uses cache if DOM hasn't changed.
        """
        # Check if DOM changed
        if not force_refresh:
            current_hash = await self._compute_dom_hash(page)
            if current_hash and current_hash == self._last_dom_hash and self._cached_clickables:
                self._cache_hits += 1
                logger.info("[DOM_SCANNER_V3] ✓ DOM unchanged, using cached %d clickables (cache hits: %d)", 
                           len(self._cached_clickables), self._cache_hits)
                return self._cached_clickables
        
        # Cache miss - full extraction
        self._cache_misses += 1
        logger.debug("[DOM_SCANNER_V3] Cache miss - performing full DOM extraction")
        
        try:
            await page.evaluate("window.scrollTo(0,0)")
            await page.wait_for_timeout(300)
        except Exception:
            pass

        height = await page.evaluate("document.body.scrollHeight")
        mid = height // 2
        positions = [0, mid, max(0, height - 100)]

        # Use list + seen keys for deduplication (locators are not hashable)
        seen: set = set()
        results: List[Dict[str, Any]] = []

        for pos in positions:
            try:
                await page.evaluate(f"window.scrollTo(0, {pos})")
                await page.wait_for_timeout(500)

                elements = await page.locator(self.CLICKABLE_SELECTOR).all()

                for el in elements:
                    try:
                        if not await el.is_visible():
                            continue
                        text = (await el.inner_text(timeout=500)).strip()
                        bbox = await el.bounding_box()
                        if not bbox:
                            continue
                        # Dedupe by (text, bbox) - use rounded coords for stability
                        key = (text[:100], round(bbox["x"]), round(bbox["y"]), round(bbox["width"]), round(bbox["height"]))
                        if key in seen:
                            continue
                        seen.add(key)
                        results.append({"locator": el, "text": text, "bbox": bbox})
                    except Exception:
                        continue
            except Exception as e:
                logger.debug("DOM scan at pos %s: %s", pos, e)

        # Update cache
        self._cached_clickables = results
        try:
            self._last_dom_hash = await self._compute_dom_hash(page)
        except Exception:
            pass
        
        logger.info("[DOM_SCANNER_V3] Extracted %d unique clickables", len(results))
        return results

    async def scan_inputs(self, page: Page, force_refresh: bool = False) -> List[Dict[str, Any]]:
        """Extract visible input elements with caching."""
        # Check cache for inputs
        if not force_refresh:
            current_hash = await self._compute_dom_hash(page)
            if current_hash and current_hash == self._last_dom_hash and self._cached_inputs:
                logger.debug("[DOM_SCANNER_V3] Using cached %d inputs", len(self._cached_inputs))
                return self._cached_inputs
        
        results: List[Dict[str, Any]] = []
        try:
            inputs = await page.locator(self.INPUT_SELECTOR).all()
            for el in inputs[:50]:  # cap
                try:
                    if not await el.is_visible():
                        continue
                    text = ""
                    try:
                        text = (await el.inner_text(timeout=300)).strip()
                    except Exception:
                        pass
                    placeholder = await el.get_attribute("placeholder") or ""
                    aria_label = await el.get_attribute("aria-label") or ""
                    name = await el.get_attribute("name") or ""
                    combined = f"{text} {placeholder} {aria_label} {name}".strip()
                    bbox = await el.bounding_box()
                    if bbox:
                        results.append({
                            "locator": el,
                            "text": combined or "(input)",
                            "bbox": bbox,
                        })
                except Exception:
                    continue
        except Exception as e:
            logger.debug("Input scan: %s", e)
        
        # Update cache
        self._cached_inputs = results
        return results
    
    def clear_cache(self):
        """Clear DOM cache (use after navigation)."""
        self._last_dom_hash = None
        self._cached_clickables = []
        self._cached_inputs = []
        logger.debug("[DOM_SCANNER_V3] Cache cleared")
    
    def get_cache_stats(self) -> Dict[str, int]:
        """Get cache statistics."""
        return {
            "hits": self._cache_hits,
            "misses": self._cache_misses,
            "clickables_cached": len(self._cached_clickables),
            "inputs_cached": len(self._cached_inputs)
        }
        return results
