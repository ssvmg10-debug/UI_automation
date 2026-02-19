"""
ProductCard component: image, text cluster 20–200 chars, price, Buy Now / anchor.
"""
import re
from typing import List, Dict, Any, Optional
from playwright.async_api import Page, Locator
import logging

from .base import DetectedComponent, ComponentType, ComponentSignature

logger = logging.getLogger(__name__)

# Product-card container selectors (class/data patterns, not fragile XPath)
CARD_SELECTORS = [
    "div[class*='product']",
    "article[class*='product']",
    "[data-testid*='product']",
    ".product-card",
    ".product-item",
    "[class*='ProductCard']",
]

PRICE_PATTERN = re.compile(r"₹|Rs\.?|INR|\d{1,3}(?:,\d{3})*(?:\.\d{2})?|\d+(?:\.\d{2})?\s*(?:MRP|Price)", re.I)
BUY_NOW_PATTERN = re.compile(r"buy\s*now|add\s*to\s*cart|view\s*details|see\s*more", re.I)


def _text_length_ok(text: str, min_len: int = 20, max_len: int = 500) -> bool:
    t = (text or "").strip()
    return min_len <= len(t) <= max_len


def _has_price_like(text: str) -> bool:
    return bool(PRICE_PATTERN.search(text or ""))


def _has_buy_now(text: str) -> bool:
    return bool(BUY_NOW_PATTERN.search(text or ""))


async def extract_product_cards(page: Page, max_cards: int = 80) -> List[DetectedComponent]:
    """
    Extract ProductCard components: container with image, text cluster, price, anchor.
    Returns DetectedComponent list with locator = anchor inside card (for click).
    """
    results: List[DetectedComponent] = []
    combined_selector = ", ".join(CARD_SELECTORS)
    try:
        cards = page.locator(combined_selector)
        n = await cards.count()
        for i in range(min(n, max_cards)):
            try:
                card = cards.nth(i)
                if not await card.is_visible():
                    continue
                full_text = (await card.text_content()) or ""
                full_text = full_text.strip()
                if not _text_length_ok(full_text, 10, 800):
                    continue
                anchor = card.locator("a").first
                has_anchor = await anchor.count() > 0
                if not has_anchor:
                    continue
                # Primary text: often first line or title
                primary = full_text.split("\n")[0].strip() if full_text else ""
                if len(primary) > 120:
                    primary = primary[:117] + "..."
                sig = ComponentSignature(
                    has_image=await card.locator("img").count() > 0,
                    text_length_min=20,
                    text_length_max=500,
                    has_anchor=True,
                    has_price_like=_has_price_like(full_text),
                    has_button_like=_has_buy_now(full_text),
                    container_keywords=["product", "card", "item"],
                )
                bbox = await anchor.bounding_box()
                comp = DetectedComponent(
                    component_type=ComponentType.PRODUCT_CARD,
                    text=primary,
                    full_text=full_text,
                    locator=anchor,
                    slots={"anchor": anchor, "full_text": full_text},
                    bbox={"x": bbox["x"], "y": bbox["y"], "width": bbox["width"], "height": bbox["height"]} if bbox else None,
                    container=await card.get_attribute("class"),
                    signature=sig,
                )
                results.append(comp)
            except Exception as e:
                logger.debug("Product card extract skip: %s", e)
    except Exception as e:
        logger.warning("Product card extraction failed: %s", e)
    return results
