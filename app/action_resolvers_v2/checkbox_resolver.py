"""
Checkbox resolver V2: click all checkboxes (terms, agree) or one by label.
"""
from typing import Optional, Any, List
from playwright.async_api import Page
import logging
from app.core.component_detector import CheckboxComponent
from app.core.element_ranker_v2 import ElementRankerV2

logger = logging.getLogger(__name__)


class CheckboxResolver:
    async def resolve(self, page: Page, target: str, value: Optional[str] = None) -> Optional[Any]:
        components = await CheckboxComponent.detect(page)
        if not components:
            return None
        target_lower = (target or value or "").lower()
        if "all" in target_lower or "every" in target_lower or "checkboxes" in target_lower or "terms" in target_lower:
            # Click all visible checkboxes
            for comp in components:
                try:
                    await comp.locator.click()
                    await page.wait_for_timeout(200)
                except Exception:
                    continue
            return True
        ranked = ElementRankerV2().rank(target or "agree", components, top_n=5)
        if not ranked or ranked[0][0] < 0.15:
            return None
        locator = ranked[0][1].locator
        try:
            await locator.click()
            return locator
        except Exception as e:
            logger.debug("CheckboxResolver click failed: %s", e)
            return None
