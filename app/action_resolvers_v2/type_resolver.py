"""
Type resolver V2: FormInputComponent + ElementRankerV2, then fill.
"""
from typing import Optional, Any
from playwright.async_api import Page
import logging
from app.core.component_detector import FormInputComponent
from app.core.element_ranker_v2 import ElementRankerV2

logger = logging.getLogger(__name__)


class TypeResolver:
    async def resolve(self, page: Page, target: str, value: Optional[str] = None) -> Optional[Any]:
        if not value:
            return None
        components = await FormInputComponent.detect(page)
        if not components:
            return None
        ranked = ElementRankerV2().rank(target or "input", components, top_n=3)
        if not ranked or ranked[0][0] < 0.15:
            return None
        locator = ranked[0][1].locator
        try:
            await locator.fill(value)
            return locator
        except Exception as e:
            logger.debug("TypeResolver fill failed: %s", e)
            return None
