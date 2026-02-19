"""
Product click resolver V2: ProductCard.detect + ElementRankerV2.rank -> best.locator.
"""
from typing import Optional, Any
from playwright.async_api import Page
import logging
from app.core.component_detector import ProductCard
from app.core.element_ranker_v2 import ElementRankerV2
from app.core.wait_utils import wait_for_page_ready

logger = logging.getLogger(__name__)


class ProductClickResolver:
    async def resolve(self, page: Page, target: str, value: Optional[str] = None) -> Optional[Any]:
        # Scroll to load lazy product grids
        try:
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await page.wait_for_timeout(1500)
            await page.evaluate("window.scrollTo(0, 0)")
            await page.wait_for_timeout(500)
        except Exception:
            pass
        components = await ProductCard.detect(page)
        if not components:
            return None
        ranked = ElementRankerV2().rank(target, components, top_n=3)
        if not ranked:
            return None
        score, best = ranked[0]
        if score < 0.2:
            return None
        return getattr(best, "locator", None)
