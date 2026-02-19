"""
Delivery method resolver V2: RadioGroupComponent for "free delivery".
"""
from typing import Optional, Any
from playwright.async_api import Page
import logging
from app.core.component_detector import RadioGroupComponent
from app.core.element_ranker_v2 import ElementRankerV2

logger = logging.getLogger(__name__)


class DeliveryMethodResolver:
    async def resolve(self, page: Page, target: str, value: Optional[str] = None) -> Optional[Any]:
        components = await RadioGroupComponent.detect(page)
        if not components:
            return None
        query = (target or value or "free delivery").strip().lower()
        ranked = ElementRankerV2().rank(query, components, top_n=5)
        if not ranked or ranked[0][0] < 0.15:
            return None
        locator = ranked[0][1].locator
        try:
            await locator.click()
            return locator
        except Exception as e:
            logger.debug("DeliveryMethodResolver click failed: %s", e)
            return None
