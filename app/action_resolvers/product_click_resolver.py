"""
Product click resolver: extract ProductCards, rank by semantic similarity, click anchor.
Scroll until found if needed.
"""
from typing import Optional
from playwright.async_api import Page
import logging

from .base import BaseActionResolver, ResolverResult
from app.components import extract_product_cards, ComponentType
from app.semantic_ranking import rank_components

logger = logging.getLogger(__name__)


class ProductClickResolver(BaseActionResolver):
    action_type = "product_click"

    async def resolve(
        self,
        page: Page,
        target: str,
        value: Optional[str] = None,
        scroll_before: bool = True,
        **kwargs,
    ) -> ResolverResult:
        if scroll_before:
            try:
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await page.wait_for_timeout(1500)
                await page.evaluate("window.scrollTo(0, 0)")
                await page.wait_for_timeout(500)
            except Exception:
                pass
        cards = await extract_product_cards(page, max_cards=80)
        if not cards:
            return ResolverResult(success=False, error="No product cards found")
        ranked = rank_components(cards, target, action="click", top_n=3)
        if not ranked:
            return ResolverResult(success=False, error="No product cards matched")
        best_score, best = ranked[0]
        if best_score < 0.25:
            return ResolverResult(success=False, error=f"Best product match score too low: {best_score:.2f}")
        locator = getattr(best, "locator", None)
        if not locator:
            return ResolverResult(success=False, error="Product card has no clickable locator")
        return ResolverResult(success=True, locator=locator)

    def applies(self, page: Page, target: str, action: str, **kwargs) -> bool:
        if action and action.upper() != "CLICK":
            return False
        t = (target or "").lower()
        url = (page.url or "").lower()
        # Product-like: long name, or we're on listing/product page
        if "star" in t or "lg " in t or "split ac" in t or "model" in t or len(target or "") > 50:
            return True
        if "air-conditioners" in url or "product" in url or "listing" in url:
            return True
        return False
