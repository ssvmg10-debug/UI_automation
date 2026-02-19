"""
Product card grouping and resolution.
Product title text is nested inside card; we group by container and match target to card text.
"""
from difflib import SequenceMatcher
from playwright.async_api import Page
from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


def _similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


async def _scroll_before_product_match(page: Page) -> None:
    """Scroll to load lazy content before matching products."""
    await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
    await page.wait_for_timeout(1500)
    await page.evaluate("window.scrollTo(0, 0)")
    await page.wait_for_timeout(500)


async def extract_product_cards(page: Page) -> List[Dict[str, Any]]:
    """
    Extract product cards: divs with class containing 'product' and their link.
    Returns list of {"text": card text content, "locator": Playwright locator for the anchor}.
    """
    results: List[Dict[str, Any]] = []
    try:
        # Broad selector: common patterns for product cards
        cards = page.locator(
            "div[class*='product'], article[class*='product'], "
            "[data-testid*='product'], .product-card, .product-item"
        )
        n = await cards.count()
        for i in range(min(n, 80)):  # cap for performance
            try:
                card = cards.nth(i)
                if not await card.is_visible():
                    continue
                text = (await card.text_content()) or ""
                anchor = card.locator("a").first
                if await anchor.count() > 0:
                    results.append({"text": text.strip(), "locator": anchor})
            except Exception:
                continue
    except Exception as e:
        logger.debug("extract_product_cards: %s", e)
    return results


async def resolve_product(page: Page, target: str) -> Optional[Any]:
    """
    Resolve a product by name (e.g. long LG model name).
    Scrolls first, then matches card text to target; returns best matching anchor locator or None.
    """
    await _scroll_before_product_match(page)
    cards = await extract_product_cards(page)
    if not cards:
        return None

    scored: List[tuple] = []
    target_lower = target.lower()
    for card in cards:
        text = (card.get("text") or "").lower()
        score = _similarity(text, target)
        if target_lower in text:
            score += 0.3
        scored.append((score, card))

    scored.sort(key=lambda x: x[0], reverse=True)
    if scored and scored[0][0] > 0.4:
        best = scored[0][1]
        return best.get("locator")
    return None
