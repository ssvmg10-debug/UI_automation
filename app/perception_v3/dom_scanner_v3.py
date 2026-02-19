"""
DOM Scanner V3 - Scroll-through extraction with broader selectors.
Fixes: footer links, banner links, div[onclick], span[onclick].
Deduplication by (text, bbox) to avoid unhashable locator in set.
"""
from playwright.async_api import Page
from typing import List, Dict, Any, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class DOMScannerV3:
    """Extracts visible clickable elements via scroll-through (top, mid, bottom)."""

    CLICKABLE_SELECTOR = """
        a, button, [role='button'], [role='link'],
        div[onclick], span[onclick],
        input[type='submit'], input[type='button']
    """

    INPUT_SELECTOR = "input, textarea, select"

    async def scan_clickables(self, page: Page) -> List[Dict[str, Any]]:
        """
        Scroll through page to expose ALL visible clickables.
        Dedupe by (text, bbox) since locators are not hashable.
        """
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

        logger.info("[DOM_SCANNER_V3] Extracted %d unique clickables", len(results))
        return results

    async def scan_inputs(self, page: Page) -> List[Dict[str, Any]]:
        """Extract visible input elements."""
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
        return results
