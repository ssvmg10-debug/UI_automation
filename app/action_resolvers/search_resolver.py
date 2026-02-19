"""
Search resolver: find search input (icon + input or overlay), fill and submit.
"""
from typing import Optional
from playwright.async_api import Page
import logging

from .base import BaseActionResolver, ResolverResult
from app.components import extract_form_inputs, extract_buttons, ComponentType
from app.semantic_ranking import rank_components

logger = logging.getLogger(__name__)


class SearchResolver(BaseActionResolver):
    action_type = "search"

    async def resolve(
        self,
        page: Page,
        target: str,
        value: Optional[str] = None,
        **kwargs,
    ) -> ResolverResult:
        query = (value or target or "").strip()
        if not query:
            return ResolverResult(success=False, error="No search query")
        # Try placeholder/label "search" or "search products"
        inputs = await extract_form_inputs(page, max_inputs=30)
        search_input = None
        for c in inputs:
            text = (getattr(c, "text", "") or "").lower()
            placeholder = (getattr(c, "slots", {}) or {}).get("placeholder", "") or ""
            if "search" in text or "search" in placeholder.lower():
                search_input = c
                break
        if not search_input:
            return ResolverResult(success=False, error="No search input found")
        locator = getattr(search_input, "locator", None)
        if not locator:
            return ResolverResult(success=False, error="Search input has no locator")
        try:
            await locator.fill(query)
            await locator.press("Enter")
            await page.wait_for_timeout(1000)
            return ResolverResult(success=True, locator=locator)
        except Exception as e:
            return ResolverResult(success=False, error=str(e))

    def applies(self, page: Page, target: str, action: str, **kwargs) -> bool:
        if action and action.upper() != "TYPE":
            return False
        t = (target or "").lower()
        return "search" in t
