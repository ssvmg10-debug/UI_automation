"""
Search resolver V2: find search input (placeholder/label), fill + Enter.
"""
from typing import Optional, Any
from playwright.async_api import Page
import logging
from app.core.component_detector import FormInputComponent
from app.core.element_ranker_v2 import ElementRankerV2

logger = logging.getLogger(__name__)


class SearchResolver:
    async def resolve(self, page: Page, target: str, value: Optional[str] = None) -> Optional[Any]:
        query = (value or target or "").strip()
        if not query:
            return None
        components = await FormInputComponent.detect(page)
        search_input = None
        for c in components:
            if "search" in (getattr(c, "text", "") or "").lower():
                search_input = c
                break
        if not search_input:
            ranked = ElementRankerV2().rank("search", components, top_n=1)
            if ranked and ranked[0][0] >= 0.1:
                search_input = ranked[0][1]
        if not search_input:
            return None
        locator = getattr(search_input, "locator", None)
        if not locator:
            return None
        try:
            await locator.fill(query)
            await locator.press("Enter")
            return locator
        except Exception as e:
            logger.debug("SearchResolver failed: %s", e)
            return None
