"""
Filter resolver V2: click filter chip / category checkbox (e.g. "party speakers").
"""
from typing import Optional, Any
from playwright.async_api import Page
import logging
from app.core.component_detector import CheckboxComponent, ButtonComponent
from app.core.element_ranker_v2 import ElementRankerV2

logger = logging.getLogger(__name__)


class FilterResolver:
    async def resolve(self, page: Page, target: str, value: Optional[str] = None) -> Optional[Any]:
        # Filters are often checkboxes or buttons in a filter/sidebar region
        checkboxes = await CheckboxComponent.detect(page)
        buttons = await ButtonComponent.detect(page)
        combined = checkboxes + buttons
        if not combined:
            return None
        query = (target or value or "").strip()
        ranked = ElementRankerV2().rank(query, combined, top_n=3)
        if not ranked or ranked[0][0] < 0.2:
            return None
        locator = ranked[0][1].locator
        try:
            await locator.click()
            return locator
        except Exception as e:
            logger.debug("FilterResolver click failed: %s", e)
            return None
